#!/usr/bin/env python3
"""
FSI Vessel Arrival Monitor v3.11.0 — Hardened
=============================================
Local:  python fsi_monitor.py          -> http://localhost:8090
Cloud:  set PORT env var (Render auto-sets it)

Data Sources:
  Bilbao PA    - ~65 vessels, 3 weeks ahead (Googlebot UA bypass, incl. flags)
  Marin PA     - ~10 vessels, 10 days
  ShipNext     - 9 ports, all planned vessels (no flags; resolved via VF)
  VesselFinder - Marin/Vilagarcia + flag resolution + supplement

v3.11.0 fixes all 19 audited weak points. See PLAN-v3.11.0.md.
"""
import http.server, json, os, re, socketserver, sys, threading, time, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, parse_qs, unquote

VERSION = "3.11.0"
PORT = int(os.environ.get("PORT", 8090))
HOST = "0.0.0.0"

VF_BASE   = "https://www.vesselfinder.com"
SN_BASE   = "https://shipnext.com/api/v1/ports"
BILBAO_URL = "https://www.bilbaoport.eus/en/vessel-activity/scheduled-calls/"
MARIN_URL  = "https://www.apmarin.com/es/paginas/buques_esperados"

# ShipNext port IDs (resolved from /api/v1/ports/public/{sefName})
SN_PORTS = {
    "ESGIJ": "58238f70821bd20e38598a87",  # Gijon
    "ESAVS": "58206e746c69920ef8543580",  # Aviles
    "ESTAN": "5828c5146742c90cc0eb71c7",  # Santander
    # ESBIO (Bilbao) uses direct PA scrape - 3 weeks planning, better than ShipNext
    "ESPAS": "582826581c912f0ebcb63c9e",  # Pasajes
    "FRBAY": "58209fb4f4f7e611988749eb",  # Bayonne
    "ESSCI": "5829003f6742c90cc0eb7296",  # San Ciprian
    "ESFER": "582365a0821bd20e385989d8",  # Ferrol
    "ESCOR": "582303d7821bd20e38598841",  # A Coruna
    "ESVGO": "582a46575baa9509b886eeed",  # Vigo
    # ESMRN (Marin) and ESVIL (Vilagarcia) not in ShipNext -> VF
}

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.environ.get("DATA_DIR", SCRIPT_DIR)
DB_FILE    = os.path.join(DATA_DIR, "fsi_vessels_db.json")
SEED_FILE  = os.path.join(SCRIPT_DIR, "flags.json")   # committed to git - survives restarts

UA     = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
UA_BOT = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
XMAP   = {"XB": "PT", "XA": "DK", "XI": "NO"}
TRACKED_FLAGS = ("MT", "LR", "MH", "HK")

BILBAO_FLAGS = {
    "mt":"MT","lr":"LR","mh":"MH","pa":"PA","cy":"CY","pt":"PT","no":"NO",
    "nl":"NL","ag":"AG","bb":"BB","ie":"IE","fr":"FR","de":"DE","fi":"FI",
    "hk":"HK","cn":"CN","gb":"GB","es":"ES","it":"IT","dk":"DK","sg":"SG",
    "bs":"BS","gi":"GI","bm":"BM","tr":"TR","gr":"GR","se":"SE",
}

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# --- FIX #9/#20: ETA normalisation (Spanish + English months) --------------
MONTHS = {
    "jan":1,"ene":1,"feb":2,"mar":3,"apr":4,"abr":4,"may":5,"jun":6,
    "jul":7,"aug":8,"ago":8,"sep":9,"set":9,"oct":10,"nov":11,"dec":12,"dic":12,
}

def parse_eta(raw):
    """Normalise any source ETA into (iso_string, display_string).
    Handles: ISO8601, '5 Ago', '29 Jul', '25/07 20:00', 'Jun 09, 14:00'."""
    if not raw:
        return "", ""
    s = str(raw).strip()
    now = datetime.now()
    dt = None
    try:
        # ISO 8601 (ShipNext)
        if re.match(r"^\d{4}-\d{2}-\d{2}", s):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
        # DD/MM[/YY[YY]] [HH:MM]   (Marin, Aviles CSV, Vilagarcia feed)
        elif re.match(r"^\d{1,2}/\d{1,2}", s):
            m = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?:[ T]+(\d{1,2}):(\d{2}))?", s)
            d, mo = int(m.group(1)), int(m.group(2))
            hh = int(m.group(4) or 0); mi = int(m.group(5) or 0)
            if m.group(3):                        # explicit year present - trust it
                yr = int(m.group(3))
                if yr < 100: yr += 2000
            else:
                yr = now.year
                if mo < now.month - 6: yr += 1    # year rollover
            dt = datetime(yr, mo, d, hh, mi)
        else:
            # '5 Ago' / '29 Jul' (Bilbao)  |  'Jun 09, 14:00' (VF/ShipNext display)
            m = re.match(r"^(\d{1,2})\s+([A-Za-zÁ-úá-ú]{3,})", s)
            if m:
                d, mon = int(m.group(1)), m.group(2)[:3].lower()
            else:
                m = re.match(r"^([A-Za-z]{3,})\.?\s+(\d{1,2})", s)
                if not m: return "", s
                mon, d = m.group(1)[:3].lower(), int(m.group(2))
            mo = MONTHS.get(mon)
            if not mo: return "", s
            tm = re.search(r"(\d{1,2}):(\d{2})", s)
            hh = int(tm.group(1)) if tm else 0
            mi = int(tm.group(2)) if tm else 0
            yr = now.year
            if mo < now.month - 6: yr += 1
            dt = datetime(yr, mo, d, hh, mi)
    except Exception:
        return "", s
    if not dt:
        return "", s
    return dt.isoformat(timespec="minutes"), dt.strftime("%d %b, %H:%M")

# --- FIX #11/#20: name cleaning & key normalisation -----------------------
_NAME_OK = re.compile(r"^[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9 .,'&()/+-]{1,48}$")
_JUNK = {"buque","vessel","ship","name","nombre","total","totales","n/a","-","--",
         "eta","etd","fecha","date","escala","barco"}

def clean_name(raw):
    """Strip provisional '*' markers, padding, HTML residue. '' => reject row."""
    if not raw: return ""
    n = re.sub(r"<[^>]+>", " ", str(raw))
    n = n.replace("\xa0", " ")
    n = re.sub(r"[\*\u2020\u2021]+\s*$", "", n)     # trailing * / dagger = provisional
    n = re.sub(r"\s+", " ", n).strip(" -–—.")
    if not n or len(n) < 2: return ""
    if n.lower() in _JUNK: return ""
    if n.isdigit(): return ""
    if not _NAME_OK.match(n): return ""
    return n

def norm_key(name):
    """Collapse to a stable dedupe key: 'Containerships Nord *' == 'containerships  nord'."""
    return re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")

# --- FIX #1/#2/#6: DB layer - in-memory, locked, atomic, seeded -----------
_DB = None
_DB_LOCK = threading.RLock()
_DB_DIRTY = False
_flag_neg = {}          # FIX #8: negative cache {imo: ts}
NEG_TTL = 86400         # 24 h

def _blank_db():
    return {"vessels": {}, "flags": {},
            "meta": {"created": datetime.now().isoformat(timespec="seconds"),
                     "runs": 0, "lastRun": None, "version": VERSION}}

def load_db():
    """Return the in-memory DB. Reads disk ONCE at first call."""
    global _DB
    with _DB_LOCK:
        if _DB is not None:
            return _DB
        db = _blank_db()
        if os.path.exists(DB_FILE):
            try:
                with open(DB_FILE, "r", encoding="utf-8") as f:
                    disk = json.load(f)
                if isinstance(disk, dict):
                    db["vessels"] = disk.get("vessels", {}) or {}
                    db["flags"]   = disk.get("flags", {}) or {}
                    m = disk.get("meta", {}) or {}
                    db["meta"].update({k: v for k, v in m.items() if v is not None})
            except Exception as e:
                log(f"DB read failed ({e}) - starting fresh, old file kept")
        # FIX #6: merge committed seed (seed never overwrites live DB values)
        if os.path.exists(SEED_FILE):
            try:
                with open(SEED_FILE, "r", encoding="utf-8") as f:
                    seed = json.load(f)
                n = 0
                for imo, fc in (seed or {}).items():
                    if imo not in db["flags"] and re.match(r"^[A-Z]{2}$", str(fc)):
                        db["flags"][imo] = fc; n += 1
                log(f"flags.json seed loaded: +{n} (total {len(db['flags'])})")
            except Exception as e:
                log(f"seed load failed: {e}")
        db["meta"].setdefault("runs", 0)
        db["meta"].setdefault("created", datetime.now().isoformat(timespec="seconds"))
        db["meta"]["version"] = VERSION
        _DB = db
        return _DB

def save_db(db=None):
    """FIX #2: atomic write under lock. Safe under 25-thread concurrency."""
    global _DB_DIRTY
    with _DB_LOCK:
        d = db if db is not None else _DB
        if d is None: return
        tmp = DB_FILE + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=1, ensure_ascii=False)
            os.replace(tmp, DB_FILE)      # atomic on POSIX
            _DB_DIRTY = False
        except Exception as e:
            log(f"DB save error: {e}")
            try: os.remove(tmp)
            except Exception: pass

def bump_run():
    """FIX #3/#4: every fetch endpoint records a run."""
    with _DB_LOCK:
        db = load_db()
        db.setdefault("meta", {})
        db["meta"]["runs"] = db["meta"].get("runs", 0) + 1
        db["meta"]["lastRun"] = datetime.now().isoformat(timespec="seconds")

# --- FIX #10/#11: merge that actually updates -----------------------------
def merge_into_db(db, vessels, port_id, port_name, source_tag):
    now = datetime.now().isoformat(timespec="seconds")
    added = updated = 0
    with _DB_LOCK:
        db.setdefault("vessels", {})
        for v in vessels:
            imo  = (v.get("imo") or "").strip()
            name = v.get("name", "")
            if not imo and not name:
                continue
            key = f"{imo}_{port_id}" if imo else f"N_{norm_key(name)}_{port_id}"
            rec = db["vessels"].get(key)
            if rec:
                rec["lastSeen"] = now
                rec["name"] = name or rec.get("name", "")
                # FIX #10: volatile fields ALWAYS refresh (ETA is the point of the tool)
                for fld in ("eta", "etaISO", "flagCode", "flagName", "origin", "dest", "agent", "line"):
                    nv = v.get(fld)
                    if nv not in (None, "", 0):
                        rec[fld] = nv
                rec["lastETA"] = v.get("eta") or rec.get("lastETA", "")
                # static fields: fill only if missing
                for fld in ("gt", "dwt", "built", "loa", "beam", "type"):
                    if v.get(fld) and not rec.get(fld):
                        rec[fld] = v[fld]
                rec["source"] = source_tag
                updated += 1
            else:
                db["vessels"][key] = {
                    "imo": imo, "name": name, "type": v.get("type", ""),
                    "flagCode": v.get("flagCode", ""), "flagName": v.get("flagName", ""),
                    "portId": port_id, "portName": port_name,
                    "firstSeen": now, "lastSeen": now,
                    "eta": v.get("eta", ""), "lastETA": v.get("eta", ""),
                    "etaISO": v.get("etaISO", ""),
                    "gt": v.get("gt", 0), "dwt": v.get("dwt", 0),
                    "built": v.get("built", ""), "loa": v.get("loa", ""), "beam": v.get("beam", ""),
                    "origin": v.get("origin", ""), "dest": v.get("dest", ""),
                    "agent": v.get("agent", ""), "line": v.get("line", ""),
                    "source": source_tag,
                }
                added += 1
    return added, updated

# --- FIX #1/#3/#5/#8: flag resolution ------------------------------------
def get_flag(imo):
    """FIX #1: pure in-memory lookup. ZERO disk I/O. Never blocks."""
    if not imo: return ""
    with _DB_LOCK:
        return load_db()["flags"].get(imo, "")

def save_flag(imo, fc, flush=True):
    """FIX #12: validate before persisting. FIX #2: locked."""
    if not imo: return False
    fc = XMAP.get(str(fc).upper(), str(fc).upper())
    if not re.match(r"^[A-Z]{2}$", fc):
        return False
    with _DB_LOCK:
        db = load_db()
        db.setdefault("flags", {})
        if db["flags"].get(imo) == fc:
            return True
        db["flags"][imo] = fc
    if flush:
        save_db()
    return True

def fetch_flag_vf(imo):
    """Fetch flag from VesselFinder. Returns '' on any failure (incl. IP block)."""
    if not imo: return ""
    ts = _flag_neg.get(imo)
    if ts and (time.time() - ts) < NEG_TTL:
        return ""                                    # FIX #8: don't retry known failures
    try:
        req = urllib.request.Request(
            f"{VF_BASE}/vessels/details/{imo}",
            headers={"User-Agent": UA_BOT, "Accept": "text/html"})
        html = urllib.request.urlopen(req, timeout=6).read().decode("utf-8", errors="replace")
        if "Radware" in html or "Verifying your browser" in html:
            _flag_neg[imo] = time.time(); return ""
        m = re.search(r"flags/4x3/(\w+)\.svg", html)
        fc = XMAP.get(m.group(1).upper(), m.group(1).upper()) if m else ""
        if fc:
            return fc
        _flag_neg[imo] = time.time()
        return ""
    except Exception as e:                            # FIX #7: no bare except
        _flag_neg[imo] = time.time()
        log(f"flag {imo}: {type(e).__name__}")
        return ""

# FIX #5: background resolver - requests never block on VesselFinder
_resolve_q = []
_resolve_seen = {}     # imo -> last time it was queued (BUG FIX: was a set that
                        # never expired, so any IMO that failed once via VF was
                        # permanently excluded from retry, defeating NEG_TTL below)
_resolve_lock = threading.Lock()
_resolver_started = False

def queue_flags(imos):
    now = time.time()
    with _resolve_lock:
        for i in imos:
            if not i or get_flag(i):
                continue
            last = _resolve_seen.get(i)
            if last is None or (now - last) > NEG_TTL:
                _resolve_seen[i] = now
                _resolve_q.append(i)

def _resolver_loop():
    while True:
        try:
            with _resolve_lock:
                batch = _resolve_q[:12]; del _resolve_q[:12]
            if not batch:
                time.sleep(3); continue
            found = 0
            for imo in batch:
                fc = fetch_flag_vf(imo)
                if fc and save_flag(imo, fc, flush=False):
                    found += 1
                time.sleep(0.4)                        # be gentle with VF
            if found:
                save_db()                              # FIX #1: one write per batch
                log(f"resolver: +{found} flags (queue {len(_resolve_q)})")
        except Exception as e:
            log(f"resolver error: {type(e).__name__}: {e}")
            time.sleep(5)

def start_resolver():
    global _resolver_started
    if _resolver_started: return
    _resolver_started = True
    threading.Thread(target=_resolver_loop, daemon=True, name="flag-resolver").start()
    log("background flag resolver started")

# --- ShipNext -------------------------------------------------------------
def fetch_shipnext(port_id):
    """FIX #5: returns immediately with CACHED flags. Unknowns go to background queue."""
    sn_id = SN_PORTS.get(port_id)
    if not sn_id: return []
    req = urllib.request.Request(f"{SN_BASE}/{sn_id}/planned-vessels",
                                 headers={"User-Agent": UA})
    data = json.loads(urllib.request.urlopen(req, timeout=15).read())
    out = []
    for v in data.get("data", []):
        name = clean_name(v.get("name", ""))
        if not name: continue
        imo = (v.get("imo") or "").strip()
        det = v.get("details", {}) or {}
        rt  = v.get("route", {}) or {}
        iso, disp = parse_eta((rt.get("to") or {}).get("date", ""))
        out.append({
            "name": name, "imo": imo, "type": det.get("type", ""),
            "eta": disp, "etaISO": iso,
            "flagCode": get_flag(imo), "flagName": "",
            "gt": 0, "dwt": int(det.get("dwt") or 0),
            "built": str(det.get("blt") or ""), "loa": "", "beam": "",
            "origin": (rt.get("from") or {}).get("name", ""),
            "dest": "", "agent": "", "line": "",
        })
    queue_flags([v["imo"] for v in out if v["imo"] and not v["flagCode"]])
    return out

# --- VesselFinder expected ------------------------------------------------
def fetch_vf_expected(vf_code):
    req = urllib.request.Request(
        f"{VF_BASE}/ports/{vf_code}",
        headers={"User-Agent": UA_BOT, "Accept": "text/html", "Accept-Language": "en-US,en;q=0.9"})
    html = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="replace")
    vessels = []
    tables = re.findall(r"<table[^>]*>(.+?)</table>", html, re.DOTALL)
    if not tables: return vessels
    tbody = re.search(r"<tbody>(.*)</tbody>", tables[0], re.DOTALL)
    if not tbody: return vessels
    for row in tbody.group(1).split("<tr>"):
        if "vessels/details" not in row: continue
        name = clean_name((re.search(r'named-title["\s>]+([^<]+)', row) or [None, ""])[1]
                          if re.search(r'named-title["\s>]+([^<]+)', row) else "")
        if not name: continue
        imo_m  = re.search(r"vessels/details/(\d+)", row)
        flag_m = re.search(r'flags/4x3/(\w+)\.svg.*?title="([^"]+)"', row)
        type_m = re.search(r'named-subtitle["\s>]+([^<]+)', row)
        time_m = re.search(r"<td>([^<]+)</td>", row)
        gt_m   = re.search(r"col-gt[^>]*>(\d[\d,]*)<", row)
        dwt_m  = re.search(r"col-dwt[^>]*>(\d[\d,]*)<", row)
        size_m = re.search(r"(\d{2,4})\s*x\s*(\d{2,4})", row)
        fc = XMAP.get(flag_m.group(1).upper(), flag_m.group(1).upper()) if flag_m else ""
        imo = imo_m.group(1) if imo_m else ""
        iso, disp = parse_eta(time_m.group(1).strip() if time_m else "")
        gt_v  = gt_m.group(1).replace(",", "") if gt_m else ""
        dwt_v = dwt_m.group(1).replace(",", "") if dwt_m else ""
        if fc and imo:
            save_flag(imo, fc, flush=False)          # VF port page is a free flag source
        vessels.append({
            "name": name, "imo": imo,
            "type": type_m.group(1).strip() if type_m else "",
            "eta": disp, "etaISO": iso,
            "flagCode": fc, "flagName": flag_m.group(2) if flag_m else "",
            "gt": int(gt_v) if gt_v.isdigit() else 0,
            "dwt": int(dwt_v) if dwt_v.isdigit() else 0,
            "loa": size_m.group(1) if size_m else "", "beam": size_m.group(2) if size_m else "",
            "origin": "", "dest": "", "agent": "", "line": "", "built": "",
        })
    if vessels: save_db()
    return vessels

# --- Bilbao Port Authority ------------------------------------------------
def fetch_bilbao():
    html = None
    for ua in (UA_BOT, UA, "Mozilla/5.0 (compatible; bingbot/2.0)", "curl/7.81.0"):
        try:
            req = urllib.request.Request(BILBAO_URL, headers={
                "User-Agent": ua, "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "identity"})
            text = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", errors="replace")
            if "flags/" in text and re.search(r"<td[^>]*>", text):
                html = text
                log(f"Bilbao OK: {len(html)}b (UA={ua[:22]})")
                break
            log(f"Bilbao: {len(text)}b no table (UA={ua[:22]})")
        except Exception as e:
            log(f"Bilbao {type(e).__name__} (UA={ua[:22]})")
    if not html:
        log("Bilbao: all strategies failed")
        return []
    vessels = []
    for row in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", html):
        flag_m = re.search(r"flags/(\w{2})\.png", row)
        if not flag_m: continue
        cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", row)
        if len(cells) < 7: continue
        cl = lambda c: re.sub(r"<[^>]+>", "", c).replace("\xa0", " ").strip()
        name = clean_name(cells[2])                   # FIX #20: strips trailing '*'
        if not name: continue
        fc = BILBAO_FLAGS.get(flag_m.group(1).lower(), flag_m.group(1).upper())
        gt_raw = cl(cells[4]).replace(",", "").replace(".", "")
        iso, disp = parse_eta(cl(cells[5]))           # FIX #9: 'Ago' -> August
        vessels.append({
            "name": name, "imo": "", "type": "",
            "eta": disp or cl(cells[5]), "etaISO": iso,
            "flagCode": fc, "flagName": "",
            "gt": int(gt_raw) if gt_raw.isdigit() else 0, "dwt": 0,
            "loa": cl(cells[3]), "beam": "", "built": "",
            "origin": cl(cells[6]) if len(cells) > 6 else "",
            "dest": cl(cells[7]) if len(cells) > 7 else "",
            "agent": "", "line": "",
        })
    # FIX #20: collapse duplicates created by provisional '*' rows
    seen, uniq = {}, []
    for v in vessels:
        k = norm_key(v["name"])
        if k in seen:
            prev = uniq[seen[k]]
            if v.get("etaISO") and (not prev.get("etaISO") or v["etaISO"] < prev["etaISO"]):
                uniq[seen[k]] = v                     # keep earliest ETA
            continue
        seen[k] = len(uniq); uniq.append(v)
    if len(uniq) != len(vessels):
        log(f"Bilbao: collapsed {len(vessels)-len(uniq)} duplicate rows")
    log(f"Bilbao: {len(uniq)} vessels parsed")
    return uniq

# --- Marin Port Authority -------------------------------------------------
def fetch_marin():
    req = urllib.request.Request(MARIN_URL, headers={
        "User-Agent": UA_BOT, "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8"})
    html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", errors="replace")
    vessels = []
    tables = re.findall(r"<table[^>]*>([\s\S]{10,20000}?)</table>", html)
    if not tables: return vessels
    for row in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", tables[0]):
        cells = re.findall(r"<td[^>]*>([\s\S]*?)</td>", row)
        if len(cells) < 4: continue
        cl = lambda c: re.sub(r"<[^>]+>", "", c).replace("\xa0", " ").strip()
        name = clean_name(cells[0])
        if not name: continue
        iso, disp = parse_eta(cl(cells[8]) if len(cells) > 8 else "")
        vessels.append({
            "name": name, "imo": "",
            "type": cl(cells[7]) if len(cells) > 7 else "",
            "eta": disp or (cl(cells[8]) if len(cells) > 8 else ""), "etaISO": iso,
            "flagCode": "", "flagName": "",
            "gt": 0, "dwt": 0, "loa": "", "beam": "", "built": "",
            "origin": cl(cells[1]) if len(cells) > 1 else "",
            "dest": cl(cells[2]) if len(cells) > 2 else "",
            "agent": cl(cells[4]) if len(cells) > 4 else "", "line": "",
        })
    log(f"Marin: {len(vessels)} vessels parsed")
    return vessels


# --- Spanish country name -> ISO code (Avilés / Vilagarcía PA feeds) -------
ES_FLAGS = {
 "ESPANA":"ES","ESPAÑA":"ES","PORTUGAL":"PT","MADEIRA":"PT","MALTA":"MT",
 "LIBERIA":"LR","ISLAS MARSHALL":"MH","ISLAS MARSHALL (REP)":"MH","HONG KONG":"HK",
 "PANAMA":"PA","PANAMÁ":"PA","CHIPRE":"CY","PAISES BAJOS":"NL","PAÍSES BAJOS":"NL",
 "HOLANDA":"NL","BARBADOS":"BB","GIBRALTAR":"GI","LITUANIA":"LT","ITALIA":"IT",
 "ALEMANIA":"DE","FRANCIA":"FR","REINO UNIDO":"GB","GRAN BRETANA":"GB","GRAN BRETAÑA":"GB",
 "NORUEGA":"NO","DINAMARCA":"DK","SUECIA":"SE","FINLANDIA":"FI","IRLANDA":"IE",
 "BELGICA":"BE","BÉLGICA":"BE","GRECIA":"GR","TURQUIA":"TR","TURQUÍA":"TR",
 "RUSIA":"RU","CHINA":"CN","SINGAPUR":"SG","BAHAMAS":"BS","GRAN BAHAMAS":"BS",
 "BERMUDAS":"BM","ANTIGUA Y BARBUDA":"AG","ANTIGUA":"AG","SAN VICENTE":"VC",
 "SAN VICENTE Y LAS GRANADINAS":"VC","ISLAS CAIMAN":"KY","ISLAS CAIMÁN":"KY",
 "LUXEMBURGO":"LU","SUIZA":"CH","POLONIA":"PL","ESTONIA":"EE","LETONIA":"LV",
 "CROACIA":"HR","TOGO":"TG","SIERRA LEONA":"SL","TANZANIA":"TZ","COMORAS":"KM",
 "MOLDAVIA":"MD","UCRANIA":"UA","JAPON":"JP","JAPÓN":"JP","COREA":"KR",
 "COREA DEL SUR":"KR","INDIA":"IN","VIETNAM":"VN","FILIPINAS":"PH","INDONESIA":"ID",
 "MARRUECOS":"MA","ARGELIA":"DZ","TUNEZ":"TN","TÚNEZ":"TN","EGIPTO":"EG",
 "ISRAEL":"IL","ESTADOS UNIDOS":"US","EEUU":"US","CANADA":"CA","CANADÁ":"CA",
 "BRASIL":"BR","ARGENTINA":"AR","MEXICO":"MX","MÉXICO":"MX","CHILE":"CL",
 "PERU":"PE","PERÚ":"PE","COLOMBIA":"CO","VENEZUELA":"VE","CUBA":"CU",
 "AUSTRALIA":"AU","NUEVA ZELANDA":"NZ","SUDAFRICA":"ZA","SUDÁFRICA":"ZA",
 "TAIWAN":"TW","TAILANDIA":"TH","MALASIA":"MY","EMIRATOS ARABES UNIDOS":"AE",
 "ARABIA SAUDI":"SA","QATAR":"QA","KUWAIT":"KW","IRAN":"IR","BULGARIA":"BG",
 "RUMANIA":"RO","RUMANÍA":"RO","GEORGIA":"GE","BELICE":"BZ","CAMBOYA":"KH",
 "MONGOLIA":"MN","PALAU":"PW","VANUATU":"VU","ISLAS COOK":"CK","NIUE":"NU",
 "SANTO TOME Y PRINCIPE":"ST","GUINEA ECUATORIAL":"GQ","NIGERIA":"NG",
 "ISLAS FEROE":"FO","ISLA DE MAN":"IM","JAMAICA":"JM","REPUBLICA DOMINICANA":"DO",
}
def es_flag(name):
    if not name: return ""
    k = re.sub(r"\s+", " ", str(name)).strip().upper()
    return ES_FLAGS.get(k, "")

AVILES_CSV = "https://www.puertoaviles.es/es-ES/Servicios/Buques-en-el-Puerto/movimientos.csv"
VILAG_URL  = "https://www.portovilagarcia.es/MDB_BARCOS.php"

def _pa_rows(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", errors="replace")
    return [l.split(";") for l in raw.replace("\r", "\n").split("\n") if l.strip()]

def fetch_aviles():
    """Aviles PA CSV - 22 fields, includes IMO + flag + GT + callsign."""
    rows = _pa_rows(AVILES_CSV)
    SKIP = {"ULTIMAS SALIDAS"}                 # already departed
    out = []
    for r in rows:
        if len(r) < 22 or r[0].strip().upper() in SKIP: continue
        name = clean_name(r[5])
        if not name: continue
        imo = re.sub(r"\D", "", r[17] or "")
        fc  = es_flag(r[20])
        if imo and fc: save_flag(imo, fc, flush=False)   # enrich seed for free
        iso, disp = parse_eta(r[3])
        gt = re.sub(r"\D", "", (r[18] or "").split(",")[0])
        out.append({
            "name": name, "imo": imo if len(imo) == 7 else "",
            "type": (r[21] or "").strip().title(),
            "eta": disp or r[3].strip(), "etaISO": iso,
            "flagCode": fc, "flagName": (r[20] or "").strip().title(),
            "gt": int(gt) if gt.isdigit() else 0, "dwt": 0,
            "built": "", "loa": (r[9] or "").split(",")[0], "beam": "",
            "origin": (r[6] or "").strip().title(), "dest": (r[7] or "").strip().title(),
            "agent": (r[10] or "").strip().title(), "line": "",
        })
    if out: save_db()
    log(f"Aviles: {len(out)} vessels parsed")
    return out

def fetch_vilagarcia():
    """Vilagarcia PA feed - 15 fields, name + Spanish flag + ETA (no IMO)."""
    rows = _pa_rows(VILAG_URL)
    out = []
    for r in rows:
        if len(r) < 15 or r[0].strip().upper() == "S": continue   # S = sailed
        name = clean_name(r[1])
        if not name: continue
        iso, disp = parse_eta(r[4])
        qty = re.sub(r"\D", "", r[11] or "")
        out.append({
            "name": name, "imo": "",
            "type": (r[14] or "").strip().title(),
            "eta": disp or r[4].strip(), "etaISO": iso,
            "flagCode": es_flag(r[2]), "flagName": (r[2] or "").strip().title(),
            "gt": 0, "dwt": int(qty) if qty.isdigit() else 0,
            "built": "", "loa": "", "beam": "",
            "origin": (r[12] or r[3] or "").strip().title(), "dest": "",
            "agent": (r[6] or "").strip().title(), "line": (r[13] or "").strip().title(),
        })
    log(f"Vilagarcia: {len(out)} vessels parsed")
    return out


LOCAL_FEED = os.path.join(SCRIPT_DIR, "local_feed.json")

def fetch_localfeed(port_id=None):
    """Vessels collected by local_sync.py from sources that block datacenter IPs
    (Posidonia Gijón, puertogijon.es). Committed to the repo; read-only here."""
    if not os.path.exists(LOCAL_FEED):
        return []
    try:
        with open(LOCAL_FEED, encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        log(f"local_feed read error: {e}")
        return []
    out = []
    for v in payload.get("vessels", []):
        if port_id and v.get("portId") != port_id:
            continue
        name = clean_name(v.get("name", ""))
        if not name:
            continue
        imo = re.sub(r"\D", "", v.get("imo", "") or "")
        imo = imo if len(imo) == 7 else ""
        iso, disp = parse_eta(v.get("eta", ""))
        out.append({
            "name": name, "imo": imo, "type": (v.get("type") or "").strip(),
            "eta": disp or (v.get("eta") or ""), "etaISO": iso,
            "flagCode": v.get("flagCode") or get_flag(imo), "flagName": "",
            "gt": 0, "dwt": 0, "built": "", "loa": "", "beam": "",
            "origin": (v.get("origin") or "").strip(), "dest": "",
            "agent": (v.get("agent") or "").strip(), "line": "",
        })
    age = payload.get("generated", "?")
    log(f"local_feed: {len(out)} vessels (generated {age})")
    return out

# --- HTTP server ----------------------------------------------------------
class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    def log_message(self, fmt, *args): pass

    def _json(self, code, data, cors="*"):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        if cors:                                       # FIX #17: opt-in per endpoint
            self.send_header("Access-Control-Allow-Origin", cors)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try: self.wfile.write(body)
        except Exception: pass

    def _fetch_endpoint(self, fn, pid, pname, tag, **kw):
        """Shared wrapper: FIX #3 (bump_run) + FIX #7 (typed errors)."""
        try:
            vs = fn(**kw)
            db = load_db()
            a, u = merge_into_db(db, vs, pid, pname, tag)
            bump_run(); save_db()
            self._json(200, {"vessels": vs, "count": len(vs), "added": a, "updated": u})
        except urllib.error.HTTPError as e:
            log(f"{tag} {pid}: HTTP {e.code}")
            self._json(200, {"error": f"HTTP {e.code}", "vessels": [], "count": 0})
        except Exception as e:
            log(f"{tag} {pid}: {type(e).__name__}: {e}")
            self._json(200, {"error": f"{type(e).__name__}", "vessels": [], "count": 0})

    def do_GET(self):
        p = urlparse(self.path)
        q = parse_qs(p.query)
        if p.path in ("/", "/index.html"):
            body = HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try: self.wfile.write(body)
            except Exception: pass

        elif p.path == "/api/ping":                    # FIX #16: keep-alive
            self._json(200, {"ok": True, "version": VERSION,
                             "queue": len(_resolve_q),
                             "flags": len(load_db().get("flags", {}))})

        elif p.path == "/api/port":
            vf = q.get("vf", [""])[0]
            if not re.match(r"^[A-Z]{5}\d{3}$", vf):
                return self._json(400, {"error": "Invalid code", "vessels": [], "count": 0})
            self._fetch_endpoint(fetch_vf_expected, q.get("pid", [""])[0],
                                 unquote(q.get("pname", [""])[0]), "VF", vf_code=vf)

        elif p.path == "/api/shipnext":
            pid = q.get("pid", [""])[0]
            if pid not in SN_PORTS:
                return self._json(400, {"error": f"Port {pid} not in ShipNext",
                                        "vessels": [], "count": 0})
            self._fetch_endpoint(fetch_shipnext, pid,
                                 unquote(q.get("pname", [""])[0]), "SN", port_id=pid)

        elif p.path == "/api/bilbao":
            self._fetch_endpoint(fetch_bilbao, "ESBIO", "Bilbao", "BIO-PA")

        elif p.path == "/api/localfeed":
            pid = q.get("pid", [""])[0] or None
            nm  = unquote(q.get("pname", [""])[0]) or "Local"
            self._fetch_endpoint(fetch_localfeed, pid or "ESGIJ", nm, "LOCAL", port_id=pid)

        elif p.path == "/api/aviles":
            self._fetch_endpoint(fetch_aviles, "ESAVS", "Avilés", "AVS-PA")

        elif p.path == "/api/vilagarcia":
            self._fetch_endpoint(fetch_vilagarcia, "ESVIL", "Vilagarcía", "VIL-PA")

        elif p.path == "/api/marin":
            self._fetch_endpoint(fetch_marin, "ESMRN", "Marín", "MRN-PA")

        elif p.path == "/api/saveflag":                # FIX #12/#17: validated, no CORS
            imo = q.get("imo", [""])[0]
            fc  = q.get("fc", [""])[0]
            ok = bool(re.match(r"^\d{7}$", imo)) and save_flag(imo, fc)
            self._json(200, {"imo": imo, "flagCode": fc, "saved": ok}, cors=None)

        elif p.path == "/api/history":
            db = load_db()
            self._json(200, {"vessels": db.get("vessels", {}),
                             "meta": db.get("meta", {}),
                             "flags": len(db.get("flags", {}))})

        elif p.path == "/api/clearold":
            with _DB_LOCK:
                db = load_db()
                cut = (datetime.now() - timedelta(days=30)).isoformat()
                before = len(db["vessels"])
                db["vessels"] = {k: v for k, v in db["vessels"].items()
                                 if v.get("lastSeen", "") >= cut}
                removed = before - len(db["vessels"])
            save_db()
            self._json(200, {"removed": removed, "remaining": len(load_db()["vessels"])})

        elif p.path == "/api/health":                  # FIX #19: source health check
            out = {}
            for pid, sn in SN_PORTS.items():
                try:
                    r = urllib.request.Request(f"{SN_BASE}/{sn}/planned-vessels",
                                               headers={"User-Agent": UA})
                    d = json.loads(urllib.request.urlopen(r, timeout=8).read())
                    out[pid] = {"ok": True, "n": len(d.get("data", []))}
                except Exception as e:
                    out[pid] = {"ok": False, "err": type(e).__name__}
            self._json(200, {"shipnext": out, "flagsCached": len(load_db()["flags"]),
                             "queue": len(_resolve_q)})
        else:
            self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

HTML = r"""<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>FSI Arrival Monitor v3.11.0</title><link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚓</text></svg>"><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet"><style>*{box-sizing:border-box;margin:0;padding:0}:root{--bg:#060b14;--bg2:#0a1220;--brd:#162a42;--brd2:#2a5a8c;--t1:#d8e2ec;--t2:#8899aa;--t3:#4a5a6a;--blue:#5ea8f0;--green:#5cb88a;--amber:#e8b84a;--red:#e06060;--m:'JetBrains Mono',monospace;--s:'DM Sans',system-ui,sans-serif}html{background:var(--bg);color:var(--t1);font-family:var(--s);font-size:13px;line-height:1.5}::-webkit-scrollbar{width:5px;height:5px}::-webkit-scrollbar-track{background:var(--bg2)}::-webkit-scrollbar-thumb{background:var(--brd);border-radius:3px}a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}@keyframes spin{to{transform:rotate(360deg)}}.hdr{background:linear-gradient(180deg,#0c1a2e,var(--bg));border-bottom:1px solid var(--brd);padding:14px 22px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}.hdr-brand{display:flex;align-items:center;gap:10px}.hdr-icon{width:34px;height:34px;border-radius:7px;background:linear-gradient(135deg,#1a4a7c,#0d2a4c);display:flex;align-items:center;justify-content:center;font-size:17px;border:1px solid var(--brd2)}.hdr h1{font-size:15px;font-weight:700;color:#e8f0f8}.hdr p{font-size:10px;color:var(--t3);margin-top:1px}.hdr-actions{display:flex;gap:7px;align-items:center;flex-wrap:wrap}.btn{display:inline-flex;align-items:center;gap:4px;padding:5px 13px;border-radius:5px;font-size:11px;font-weight:600;border:1px solid var(--brd);background:var(--bg2);color:var(--t2);cursor:pointer;transition:all .12s;font-family:var(--s);white-space:nowrap}.btn:hover{border-color:var(--brd2);color:var(--blue)}.btn-green{color:var(--green);border-color:#1a5040}.btn-primary{background:linear-gradient(135deg,#1a4a7c,#0d3060);color:#fff;border-color:var(--brd2)}.btn-amber{color:var(--amber);border-color:#5a4a10}.chip{display:inline-flex;align-items:center;gap:4px;padding:4px 10px;border-radius:5px;font-size:11px;font-weight:500;border:1px solid var(--brd);background:transparent;color:var(--t3);cursor:pointer;transition:all .12s;font-family:var(--s);white-space:nowrap}.chip:hover{border-color:#3a5a7a;color:var(--t2)}.chip.active{background:#132a48;border-color:var(--brd2);color:var(--blue)}.chip .badge{padding:1px 5px;border-radius:8px;font-size:9px;font-weight:700;background:#0e1e30;color:var(--t3);margin-left:2px}.chip.active .badge{background:#1a3a60;color:#8ec8ff}.card{background:var(--bg2);border:1px solid var(--brd);border-radius:7px;padding:13px 16px}.card-label{font-size:9px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.07em}.card-value{font-size:24px;font-weight:700;font-family:var(--m);margin-top:2px}.input{padding:7px 11px;border-radius:5px;background:var(--bg);border:1px solid var(--brd);color:var(--t1);font-size:12px;outline:none;font-family:var(--s);width:100%}.input:focus{border-color:var(--brd2)}select.input{cursor:pointer;width:auto}.table-wrap{background:var(--bg2);border:1px solid var(--brd);border-radius:7px;overflow:auto;max-height:62vh}table{width:100%;border-collapse:collapse;min-width:1050px}thead th{padding:9px 11px;text-align:left;font-size:9px;font-weight:700;color:var(--t3);text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid var(--brd);background:var(--bg);position:sticky;top:0;z-index:2;cursor:pointer;user-select:none;white-space:nowrap}thead th:hover{color:var(--t2)}thead th.sorted{color:var(--blue)}tbody tr{border-bottom:1px solid #0e1a28;transition:background .08s}tbody tr:hover{background:#0b1522}tbody td{padding:9px 11px}tr.stale{opacity:.5}.main{padding:14px 22px;display:flex;flex-direction:column;gap:12px}.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px}.filters-bar{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.section-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}.section-title{font-size:10px;font-weight:700;color:var(--t2);text-transform:uppercase;letter-spacing:.06em}.chips-wrap{display:flex;flex-wrap:wrap;gap:5px}.picker-body{margin-top:9px;border-top:1px solid var(--brd);padding-top:9px}.region-bar{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:7px}.region-btn{padding:2px 9px;border-radius:3px;font-size:9px;font-weight:700;border:1px solid var(--brd);background:var(--bg2);color:var(--t3);cursor:pointer;text-transform:uppercase;letter-spacing:.04em}.region-btn.active{background:#132a48;border-color:var(--brd2);color:var(--blue)}.region-group{margin-bottom:7px}.region-group-label{font-size:8px;color:var(--t3);font-weight:700;text-transform:uppercase;letter-spacing:.08em;margin-bottom:3px;padding-left:2px}.picker-scroll{max-height:200px;overflow-y:auto}.loading{display:none;align-items:center;gap:8px;padding:12px;background:var(--bg2);border:1px solid var(--brd);border-radius:7px;font-size:12px;color:var(--t2)}.spinner{width:16px;height:16px;border:2px solid var(--brd);border-top-color:var(--blue);border-radius:50%;animation:spin .6s linear infinite}.plog{font-size:10px;color:var(--t3);font-family:var(--m);padding:4px 0;min-height:16px}.info{background:var(--bg2);border:1px solid var(--brd);border-radius:7px;padding:13px;font-size:11px;color:var(--t3);line-height:1.7}.db-bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 14px;background:#0c1520;border:1px solid var(--brd);border-radius:7px;font-size:10px;color:var(--t3);font-family:var(--m)}.db-bar b{color:var(--amber)}.live-tag{display:inline-flex;padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700;font-family:var(--m);background:#0c2a1c;color:#6ec090;border:1px solid #1a5a3a}.empty-msg{padding:36px;text-align:center;color:var(--t3);font-style:italic}.sel-bar{display:none;align-items:center;gap:10px;padding:10px 16px;background:#1a2a10;border:1px solid #3a5a20;border-radius:7px;font-size:12px;color:#b0d890}.sel-bar b{color:#e8f0a0}.ck{width:15px;height:15px;accent-color:var(--blue);cursor:pointer}@media(max-width:700px){.hdr{padding:10px 14px}.main{padding:10px 14px}.table-wrap{max-height:45vh}}</style></head><body><div class="hdr"><div class="hdr-brand"><div class="hdr-icon">⚓</div><div><h1>FSI Vessel Arrival Monitor v3.11.0</h1><p>Expected Arrivals — Bilbao PA + Marín PA + ShipNext + VesselFinder</p></div></div><div class="hdr-actions"><span class="live-tag">● LIVE + DB</span><span style="font-size:10px;color:var(--t3);font-family:var(--m)" id="upd"></span><button class="btn btn-primary" onclick="fetchAll()">↻ Refresh</button><button class="btn btn-green" onclick="exportCSV()">↓ CSV</button></div></div><div class="main"><div class="db-bar" id="dbBar">📦 Database: loading...</div><div class="stats-grid" id="stats"></div><div class="loading" id="loadBar"><div class="spinner"></div><span id="loadTxt">Fetching...</span></div><div class="plog" id="plog"></div><div id="errPanel" style="display:none;padding:8px 13px;background:#2a1010;border:1px solid #5a2020;border-radius:7px;font-size:11px;color:#e09090;font-family:var(--m)"></div><div class="sel-bar" id="selBar"><b id="selCount">0</b> vessels selected <button class="btn btn-amber" onclick="genCombinedReq()">📧 Combined Inspection Request</button> <button class="btn" onclick="clearSel()">Clear</button></div><div class="card"><div class="section-head"><span class="section-title">🏗 Ports (<span id="pC">0</span>)</span><button class="btn" onclick="tPicker('port')" id="portPickerBtn">+ Add Ports</button></div><div class="chips-wrap" id="sP"></div><div id="portPicker" style="display:none" class="picker-body"><input class="input" placeholder="Search ports..." oninput="rPP(this.value)" id="pS"><div class="region-bar" id="rBar"></div><div class="picker-scroll" id="pPL"></div></div></div><div class="card"><div class="section-head"><span class="section-title">🏴 Flag Filter (tap to toggle)</span><button class="btn" onclick="S.flags=['MT','LR','MH','HK'];sv();render()">All 4</button></div><div class="chips-wrap" id="sF"></div></div><div class="filters-bar"><input class="input" style="flex:1 1 200px;min-width:170px;width:auto;font-family:var(--m)" placeholder="🔍 Search vessel name or IMO..." oninput="S.q=this.value;render()"><select class="input" onchange="S.ft=this.value;render()"><option value="all">All Types</option><option>Bulk Carrier</option><option>Container Ship</option><option>General Cargo</option><option>Oil Tanker</option><option>Chemical Tanker</option><option>LPG Tanker</option><option>LNG Tanker</option><option>Car-carrier</option><option>Ro-Ro</option><option>Vehicles Carrier</option><option>Reefer</option></select><label class="btn" style="cursor:pointer"><input type="checkbox" id="hpChk" onchange="S.hidePast=this.checked;sv();render()" style="accent-color:var(--blue);margin-right:5px">Hide past ETA</label><select class="input" onchange="S.src=this.value;render()"><option value="all">All Sources</option><option value="live">Live Today</option><option value="db">History Only</option></select></div><div class="table-wrap"><table><thead id="tH"></thead><tbody id="tB"></tbody></table></div><div class="info"><strong style="color:#778899">ℹ️ Data sources:</strong><br>🌟 <b style="color:var(--amber)">Bilbao</b>: Port Authority → <b>~65 vessels, 3 weeks ahead</b> (flag, GT, LOA, origin, dest).<br>🌟 <b style="color:var(--amber)">Marín</b>: Port Authority → <b>~8 vessels, 10 days</b> (name, origin, dest, agent, cargo).<br>🌐 <b style="color:var(--blue)">9 ports</b> (Gijón, Avilés, Santander, Pasajes, Bayonne, San Ciprián, Ferrol, A Coruña, Vigo): ShipNext → all planned vessels.<br>📡 <b style="color:var(--t2)">Marín, Vilagarcía</b>: VesselFinder → 10 per port.<br><span style="color:var(--amber)">📧</span> Tick vessels → <b>combined inspection request</b> per flag.<br>🏢 <b style="color:var(--t2)">Equasis link</b> per vessel (needs login) → ISM manager, owner, PSC/inspection history.</div></div><script>
const PORTS=[{id:"ESGIJ",name:"Gijón",vf:"ESGIJ001",region:"Cantabrian",sn:true,localfeed:true},{id:"ESAVS",name:"Avilés",vf:"ESAVS001",region:"Cantabrian",direct:"aviles",sn:true},{id:"ESTAN",name:"Santander",vf:"ESSDR001",region:"Cantabrian",sn:true},{id:"ESBIO",name:"Bilbao",vf:"ESBIO001",region:"Cantabrian",direct:"bilbao"},{id:"ESPAS",name:"Pasajes",vf:"ESPAS001",region:"Cantabrian",sn:true},{id:"FRBAY",name:"Bayonne",vf:"FRBAY001",region:"Cantabrian",sn:true},{id:"ESSCI",name:"San Ciprián",vf:"ESSCI001",region:"Galicia",sn:true},{id:"ESFER",name:"Ferrol",vf:"ESFRO001",region:"Galicia",sn:true},{id:"ESCOR",name:"A Coruña",vf:"ESLCG001",region:"Galicia",sn:true},{id:"ESMRN",name:"Marín",vf:"ESMRN001",region:"Galicia",direct:"marin"},{id:"ESVIL",name:"Vilagarcía",vf:"ESVIL001",region:"Galicia",direct:"vilagarcia"},{id:"ESVGO",name:"Vigo",vf:"ESVGO001",region:"Galicia",sn:true}];
const FLAGS=[{c:"MT",n:"Malta",e:"🇲🇹"},{c:"LR",n:"Liberia",e:"🇱🇷"},{c:"MH",n:"Marshall Islands",e:"🇲🇭"},{c:"HK",n:"Hong Kong",e:"🇭🇰"}];
const XMAP={XB:"PT",XA:"DK",XI:"NO"};
const flagAdmin={MT:{name:"Transport Malta",email:"maritime.surveys@transport.gov.mt",dept:"Merchant Shipping Directorate"},LR:{name:"LISCR (Liberia)",email:"inspection@liscr.com",dept:"Technical Department"},MH:{name:"RMIRS (Marshall Islands)",email:"inspections@register-iri.com",dept:"Maritime Safety Division"},HK:{name:"Hong Kong Marine Department",email:"mardep@mardep.gov.hk",dept:"Flag State Quality Control (FSQC) / Hong Kong Shipping Registry"}};
function lsMig(nk,oks,dv){let raw=localStorage.getItem(nk);if(raw)return raw;for(const ok of oks){const old=localStorage.getItem(ok);if(old){localStorage.setItem(nk,old);return old}}return dv}
const S={ports:JSON.parse(lsMig("fsi13_p",["fsi12_p","fsi11_p","fsi10_p"],'["ESGIJ","ESAVS","ESTAN","ESBIO","ESPAS","FRBAY","ESSCI","ESFER","ESCOR","ESMRN","ESVIL","ESVGO"]')),flags:JSON.parse(lsMig("fsi13_f",["fsi12_f"],'["MT","LR","MH","HK"]')),live:[],db:[],combined:[],sel:new Set(),q:"",ft:"all",src:"all",sb:"eta",sd:"asc",loading:false,logs:[],errs:[],hidePast:JSON.parse(localStorage.getItem("fsi13_hp")||"true"),po:{port:false,flag:false},today:new Date().toISOString().slice(0,10)};
const sv=()=>{localStorage.setItem("fsi13_p",JSON.stringify(S.ports));localStorage.setItem("fsi13_f",JSON.stringify(S.flags));localStorage.setItem("fsi13_hp",JSON.stringify(S.hidePast))};
const el=id=>document.getElementById(id);
function flagEmoji(c){const f=FLAGS.find(x=>x.c===c);return f?f.e:"🏳️"}
function lg(m){S.logs.push(m);el("plog").innerHTML=S.logs.slice(-3).join(" &nbsp;|&nbsp; ")}
function shortDate(s){if(!s||s==="?"||s==="—")return"—";try{const d=new Date(s);if(!d||isNaN(d.getTime()))return String(s).slice(0,16);return d.toLocaleDateString("en-GB",{day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit"})}catch(e){return s}}
function normKey(n){return (n||"").toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"")}
function vKey(v){return (v.imo||("N_"+normKey(v.name)))+"_"+(v.portId||"")}
function buildCombined(){const map=new Map();S.db.forEach(v=>{map.set(vKey(v),{...v,_src:"db"})});S.live.forEach(v=>{const k=vKey(v);const ex=map.get(k);map.set(k,{...(ex||{}),...v,portId:v.portId||"",portName:v.portName||"",lastSeen:S.today,_src:"live",firstSeen:ex?.firstSeen||S.today})});S.combined=[...map.values()]}
async function loadHistory(){try{const r=await fetch("/api/history");const d=await r.json();if(d.vessels){S.db=Object.values(d.vessels).filter(v=>v.name);lg("📦 DB: "+S.db.length+" vessels");updateDbBar(d.meta||{})}}catch(e){lg("⚠ DB: "+e.message)}}
function updateDbBar(m){const t=S.db.length,r=m?.runs||0,l=m?.lastRun?shortDate(m.lastRun):"never";el("dbBar").innerHTML="📦 DB: <b>"+t+"</b> vessels | Runs: <b>"+r+"</b> | Last: <b>"+l+'</b> | <button class="btn" style="font-size:9px;padding:2px 8px" onclick="clearOld()">🗑 >30d</button>'}
async function clearOld(){if(!confirm("Remove >30 days old?"))return;const r=await fetch("/api/clearold");const d=await r.json();lg("🗑 "+d.removed+" removed");await loadHistory();buildCombined();render()}
async function fetchAll(){if(S.loading)return;S.loading=true;S.live=[];S.logs=[];S.errs=[];
el("loadBar").style.display="flex";el("loadTxt").textContent="Starting...";render();
const sp=PORTS.filter(p=>S.ports.includes(p.id));
const jobs=[];
for(const p of sp){
  if(p.direct){jobs.push({p,url:"/api/"+p.direct,tag:"PA"});if(p.sn)jobs.push({p,url:"/api/shipnext?pid="+p.id+"&pname="+encodeURIComponent(p.name),tag:"SN+"})}
  else if(p.sn)jobs.push({p,url:"/api/shipnext?pid="+p.id+"&pname="+encodeURIComponent(p.name),tag:"SN"});
  else jobs.push({p,url:"/api/port?vf="+p.vf+"&pid="+p.id+"&pname="+encodeURIComponent(p.name),tag:"VF"});
  if(p.localfeed)jobs.push({p,url:"/api/localfeed?pid="+p.id+"&pname="+encodeURIComponent(p.name),tag:"LOC"});
}
let done=0,tA=0;const total=jobs.length;
async function runJob(j){
  try{
    const r=await fetch(j.url,{signal:AbortSignal.timeout(45000)});
    const d=await r.json();
    if(d.error){S.errs.push(j.p.name+" ("+j.tag+"): "+d.error);lg("x "+j.p.name+": "+d.error)}
    if(d.vessels&&d.vessels.length){
      const have=new Set(S.live.filter(v=>v.portId===j.p.id).map(v=>v.imo||("N_"+(v.name||"").toLowerCase())));
      let n=0;
      d.vessels.forEach(v=>{
        const k=v.imo||("N_"+(v.name||"").toLowerCase());
        if((j.tag==="SN+"||j.tag==="LOC")&&have.has(k))return;
        if(XMAP[v.flagCode])v.flagCode=XMAP[v.flagCode];
        v.portId=j.p.id;v.portName=j.p.name;S.live.push(v);n++;
      });
      tA+=d.added||0;lg("* "+j.p.name+": "+n+" ("+j.tag+")");
    }
  }catch(e){S.errs.push(j.p.name+" ("+j.tag+"): "+(e.name||e.message));lg("x "+j.p.name+": "+(e.name||e.message))}
  done++;el("loadTxt").textContent="Loading "+done+"/"+total;buildCombined();render();
}
// concurrency-limited parallel pool (4 at a time)
const queue=[...jobs];
await Promise.all(Array.from({length:Math.min(4,queue.length)},async()=>{
  while(queue.length){const j=queue.shift();await runJob(j)}
}));
await loadHistory();buildCombined();S.loading=false;el("loadBar").style.display="none";
lg("done: "+getF().length+" matched | "+S.live.length+" live | +"+tA+" new");
el("upd").textContent="Updated "+new Date().toLocaleTimeString("en-GB");render()}
function getF(){const cut=new Date(Date.now()-2*864e5).toISOString();return S.combined.filter(v=>{if(S.hidePast&&v.etaISO&&v.etaISO<cut)return false;const fc=v.flagCode||"";if(S.flags.length>0&&!S.flags.includes(fc))return false;const t=v.type||"";if(S.ft!=="all"&&!t.toLowerCase().includes(S.ft.toLowerCase()))return false;if(S.src==="live"&&v._src!=="live")return false;if(S.src==="db"&&v._src!=="db")return false;const pid=v.portId||"";if(S.ports.length>0&&pid&&!S.ports.includes(pid))return false;if(S.q){const s=S.q.toLowerCase();if(!(v.name||"").toLowerCase().includes(s)&&!(v.imo||"").includes(s))return false}return true})}
function getS(a){const s=S.sb,d=S.sd;return[...a].sort((x,y)=>{let c=0;if(s==="eta")c=(x.etaISO||"9999").localeCompare(y.etaISO||"9999");else if(s==="name")c=(x.name||"").localeCompare(y.name||"");else if(s==="flag")c=(x.flagCode||"").localeCompare(y.flagCode||"");else if(s==="type")c=(x.type||"").localeCompare(y.type||"");else if(s==="port")c=(x.portName||"").localeCompare(y.portName||"");else if(s==="gt")c=(x.gt||0)-(y.gt||0);else if(s==="dwt")c=(x.dwt||0)-(y.dwt||0);return d==="asc"?c:-c})}
function render(){const f=getF(),so=getS(f);
const ep=el("errPanel");if(ep){if(S.errs.length){ep.style.display="block";ep.innerHTML="&#9888; Failed: "+S.errs.slice(0,6).join(" | ")+(S.errs.length>6?" (+"+(S.errs.length-6)+" more)":"")}else ep.style.display="none"}
const hc=el("hpChk");if(hc)hc.checked=S.hidePast;el("stats").innerHTML=[{l:"Matched",v:f.length,c:"var(--blue)"},{l:"Live Today",v:f.filter(v=>v._src==="live").length,c:"var(--green)"},{l:"History",v:f.filter(v=>v._src==="db").length,c:"#aa88cc"},{l:"Direct PA",v:f.filter(v=>["ESBIO","ESMRN","ESAVS","ESVIL"].includes(v.portId)&&v._src==="live").length,c:"var(--amber)"},{l:"VesselFinder",v:f.filter(v=>!["ESBIO","ESMRN","ESAVS","ESVIL"].includes(v.portId)&&v._src==="live").length,c:"var(--blue)"}].map(s=>'<div class="card"><div class="card-label">'+s.l+'</div><div class="card-value" style="color:'+s.c+'">'+s.v+'</div></div>').join("");
el("sP").innerHTML=S.ports.map(pid=>{const p=PORTS.find(x=>x.id===pid);if(!p)return"";const c=f.filter(v=>v.portId===pid).length;return '<button class="chip active" onclick="tP(\''+pid+'\')">'+(p.bcn||p.direct?'🌟 ':'')+p.name+' <span class="badge">'+c+'</span></button>'}).join("")||"<em style='font-size:11px;color:var(--t3)'>Select ports</em>";el("pC").textContent=S.ports.length;
  // Flag toggle chips with live counts
  const fc_counts={MT:0,LR:0,MH:0,HK:0};S.combined.forEach(v=>{if(fc_counts[v.flagCode]!==undefined)fc_counts[v.flagCode]++});
  const FL3=FLAGS;
  if(el("sF"))el("sF").innerHTML=FLAGS.map(f=>'<button class="chip '+(S.flags.includes(f.c)?"active":"")+'" onclick="tF(\''+f.c+'\')"><span style="font-size:13px">'+f.e+'</span> '+f.n+' <span class="badge">'+fc_counts[f.c]+'</span></button>').join("");
// flags always MT/LR/MH - no dynamic rendering needed
const selCount=[...S.sel].filter(k=>f.some(v=>vKey(v)===k)).length;el("selBar").style.display=selCount>0?"flex":"none";el("selCount").textContent=selCount;
const cols=[{k:"sel",l:"☐",x:1},{k:"eta",l:"ETA"},{k:"name",l:"Vessel"},{k:"flag",l:"Flag"},{k:"type",l:"Type"},{k:"port",l:"Port"},{k:"origin",l:"From"},{k:"gt",l:"GT"},{k:"dwt",l:"DWT"},{k:"lnk",l:"🔗",x:1}];el("tH").innerHTML="<tr>"+cols.map(c=>{const is=S.sb===c.k,ar=is?(S.sd==="asc"?" ↑":" ↓"):"",oc=c.x?"":'onclick="hs(\''+c.k+'\')"';return '<th class="'+(is?'sorted':'')+'" '+oc+'>'+c.l+ar+'</th>'}).join("")+"</tr>";
if(!so.length){el("tB").innerHTML='<tr><td colspan="10" class="empty-msg">'+(S.loading?"Fetching...":"No vessels match.")+"</td></tr>";return}
el("tB").innerHTML=so.map(v=>{const imo=v.imo||"",nm=v.name||"",fc=v.flagCode||"",fn=v.flagName||"";const eta=v.eta||v.lastETA||"";const isLive=v._src==="live";const vk=vKey(v).replace(/'/g,"\\'");const checked=S.sel.has(vKey(v))?"checked":"";const vfLnk=imo?'<a href="https://www.vesselfinder.com/vessels/details/'+imo+'" target="_blank" title="VesselFinder">🚢</a>':'<a href="https://www.vesselfinder.com/vessels?name='+encodeURIComponent(nm)+'" target="_blank" title="Search on VesselFinder">🔍</a>';const eqLnk=imo?' <a href="https://www.equasis.org/EquasisWeb/restricted/ShipInfo?fs=Search&P_IMO='+imo+'" target="_blank" title="Equasis (login required) — ISM manager, owner, PSC history">🏢</a>':'';const lnk=vfLnk+eqLnk;return '<tr class="'+(isLive?"":"stale")+'"><td><input type="checkbox" class="ck" '+checked+' onchange="toggleSel(\''+vk+'\')"></td><td style="font-size:11px;font-family:var(--m);color:'+(isLive?"var(--amber)":"var(--t3)")+';white-space:nowrap">'+(v.etaISO?shortDate(v.etaISO):(eta||"—"))+'</td><td><div style="font-weight:600;color:var(--t1);font-size:12px">'+nm+"</div>"+(imo?'<div style="font-size:10px;color:var(--t3);font-family:var(--m)">IMO '+imo+"</div>":"")+'</td><td style="white-space:nowrap"><span style="font-size:14px">'+flagEmoji(fc)+'</span> <span style="font-size:11px;color:var(--t2)">'+fc+'</span><div style="font-size:9px;color:var(--t3)">'+fn+'</div></td><td style="font-size:11px;color:var(--t2)">'+(v.type||"—")+'</td><td style="font-size:11px;color:var(--t2);font-weight:600">'+(v.portName||"—")+'</td><td style="font-size:10px;color:var(--t3)">'+(v.origin||"—")+'</td><td style="font-size:11px;font-family:var(--m);color:var(--t2)">'+(v.gt?v.gt.toLocaleString():"—")+'</td><td style="font-size:11px;font-family:var(--m);color:var(--t2)">'+(v.dwt?v.dwt.toLocaleString():"—")+'</td><td>'+lnk+"</td></tr>"}).join("")}
function toggleSel(k){if(S.sel.has(k))S.sel.delete(k);else S.sel.add(k);render()}
function clearSel(){S.sel.clear();render()}
function genCombinedReq(){const f=getF();const selected=f.filter(v=>S.sel.has(vKey(v)));if(!selected.length)return alert("No vessels selected");const byFlag={};selected.forEach(v=>{const fc=v.flagCode||"??";if(!byFlag[fc])byFlag[fc]=[];byFlag[fc].push(v)});let html="";for(const[fc,vessels]of Object.entries(byFlag)){const admin=flagAdmin[fc]||{name:"Flag Admin ("+fc+")",email:"[email]",dept:"Maritime Safety"};const subject="Vessel attendance opportunity — "+fc+" flagged vessels";const vesselList=vessels.map(v=>"* "+v.name.toUpperCase()+(v.imo?" - IMO "+v.imo:"")+" - "+(v.portName||"TBC")+" - ETA "+(v.eta||v.lastETA||"TBC")).join("\n");const body="Good day,\n\nPlease be informed that the following vessels are scheduled to one of ports within my coverage, in case needed it could be a good opportunity to arrange attendance:\n\n"+vesselList+"\n\nBest regards";html+='<div style="margin-bottom:20px;padding:16px;background:var(--bg);border:1px solid var(--brd);border-radius:7px"><h3 style="color:var(--t1);font-size:13px;margin:0 0 8px 0">'+flagEmoji(fc)+" "+admin.name+" — "+vessels.length+' vessel(s)</h3><div style="font-size:10px;color:var(--t3);margin-bottom:4px">To: <span style="color:var(--blue);font-family:var(--m)">'+admin.email+'</span></div><pre id="body_'+fc+'" style="font-size:11px;color:var(--t1);font-family:var(--s);padding:10px;background:#050a12;border:1px solid var(--brd);border-radius:4px;white-space:pre-wrap;line-height:1.6;max-height:250px;overflow-y:auto;user-select:all">'+body+'</pre><div style="display:flex;gap:8px;margin-top:8px"><button class="btn btn-primary" onclick="navigator.clipboard.writeText(document.getElementById(\'body_'+fc+"').textContent);this.textContent='✓ Copied!'\">📋 Copy</button><a class=\"btn\" href=\"mailto:"+admin.email+"?subject="+encodeURIComponent(subject)+"&body="+encodeURIComponent(body)+"\" style=\"text-decoration:none\">📧 Email</a></div></div>"}const modal=document.createElement("div");modal.style.cssText="position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.85);z-index:999;display:flex;align-items:center;justify-content:center;padding:20px";modal.onclick=e=>{if(e.target===modal)modal.remove()};modal.innerHTML='<div style="background:var(--bg2);border:1px solid var(--brd2);border-radius:10px;padding:20px;max-width:750px;width:100%;max-height:90vh;overflow-y:auto"><div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px"><h2 style="color:var(--t1);font-size:15px;margin:0">📧 Inspection Requests — '+selected.length+' vessels</h2><button class="btn" onclick="this.closest(\'div[style*=fixed]\').remove()" style="font-size:16px;padding:2px 8px">✕</button></div>'+html+"</div>";document.body.appendChild(modal)}
function tP(id){const i=S.ports.indexOf(id);if(i>=0)S.ports.splice(i,1);else S.ports.push(id);sv();render();if(S.po.port)rPP(el("pS")?.value||"")}
function tF(c){const i=S.flags.indexOf(c);if(i>=0)S.flags.splice(i,1);else S.flags.push(c);sv();render()}
function tR(r){const ids=PORTS.filter(p=>p.region===r).map(p=>p.id);const all=ids.every(id=>S.ports.includes(id));if(all)S.ports=S.ports.filter(id=>!ids.includes(id));else ids.forEach(id=>{if(!S.ports.includes(id))S.ports.push(id)});sv();render();rPP(el("pS")?.value||"")}
function tPicker(t){S.po[t]=!S.po[t];el(t+"Picker").style.display=S.po[t]?"block":"none";el(t+"PickerBtn").textContent=S.po[t]?"Close ✕":"+ "+(t==="port"?"Add Ports":"Manage Flags");if(S.po[t])t==="port"?rPP():rFP()}
function hs(c){if(S.sb===c)S.sd=S.sd==="asc"?"desc":"asc";else{S.sb=c;S.sd="asc"}render()}
function rPP(s=""){const regs=[...new Set(PORTS.map(p=>p.region))];s=(s||"").toLowerCase();el("rBar").innerHTML='<button class="region-btn" style="color:var(--green)" onclick="S.ports=PORTS.map(p=>p.id);sv();render();rPP()">All</button><button class="region-btn" style="color:var(--red)" onclick="S.ports=[];sv();render();rPP()">None</button>'+regs.map(r=>'<button class="region-btn '+(PORTS.filter(p=>p.region===r).every(p=>S.ports.includes(p.id))?"active":"")+'" onclick="tR(\''+r+'\')">'+r+"</button>").join("");let h="";regs.forEach(r=>{const rp=PORTS.filter(p=>p.region===r&&(!s||p.name.toLowerCase().includes(s)));if(!rp.length)return;h+='<div class="region-group"><div class="region-group-label">'+r+'</div><div class="chips-wrap">'+rp.map(p=>'<button class="chip '+(S.ports.includes(p.id)?"active":"")+'" onclick="tP(\''+p.id+'\')">'+(p.bcn||p.direct?"🌟 ":"")+p.name+"</button>").join("")+"</div></div>"});el("pPL").innerHTML=h}
function rFP(s=""){s=(s||"").toLowerCase();el("fPL").innerHTML=FLAGS.filter(f=>!s||f.n.toLowerCase().includes(s)).map(f=>'<button class="chip '+(S.flags.includes(f.c)?"active":"")+'" onclick="tF(\''+f.c+'\')"><span style="font-size:13px">'+f.e+"</span> "+f.n+"</button>").join("")}
function exportCSV(){const d=getS(getF());const h=["ETA","Vessel","IMO","Flag","Flag Name","Type","Port","From","To","GT","DWT","LOA","Agent","Line","VesselFinder","Equasis"];const rows=d.map(v=>[v.eta||v.lastETA||"",v.name,v.imo,v.flagCode,v.flagName||"",v.type||"",v.portName||"",v.origin||"",v.dest||"",v.gt||"",v.dwt||"",v.loa||"",v.agent||"",v.line||"",v.imo?"https://www.vesselfinder.com/vessels/details/"+v.imo:"",v.imo?"https://www.equasis.org/EquasisWeb/restricted/ShipInfo?fs=Search&P_IMO="+v.imo:""]);const csv_data=[h,...rows].map(r=>r.map(c=>'"'+String(c||"").replace(/"/g,'""')+'"').join(",")).join("\n");const a=document.createElement("a");a.href=URL.createObjectURL(new Blob(["\ufeff"+csv_data],{type:"text/csv;charset=utf-8"}));a.download="fsi-arrivals-"+new Date().toISOString().slice(0,10)+".csv";a.click()}
render();fetchAll();
setInterval(()=>{fetch("/api/ping").catch(()=>{})},600000);
setInterval(()=>{if(!S.loading)fetchAll()},1800000);
</script></body></html>"""


if __name__ == "__main__":
    db = load_db()
    start_resolver()
    server = ThreadedHTTPServer((HOST, PORT), Handler)
    url = f"http://localhost:{PORT}"
    print(f"""
+===========================================================+
   FSI Vessel Arrival Monitor v{VERSION}
   Bilbao PA + Marin PA + ShipNext + VesselFinder
   Flags tracked: {' / '.join(TRACKED_FLAGS)}

   Dashboard : {url}
   Database  : {DB_FILE}
   Tracked   : {len(db.get('vessels', {}))} vessels, {len(db.get('flags', {}))} cached flags
   Binding   : {HOST}:{PORT}
+===========================================================+
""", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("shutting down, flushing DB...")
        save_db()
        server.server_close()
