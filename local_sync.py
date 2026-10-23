#!/usr/bin/env python3
"""
local_sync.py v2 — Gijón "future port calls" from gijon.posidoniaport.com

WHY IT RUNS LOCALLY
    gijon.posidoniaport.com answers 403 to every datacenter IP (AWS load balancer,
    even /robots.txt), so the Render server can never fetch it. Your own connection
    can. This script fetches the MOVEMENTS page, keeps ONLY the "future port calls"
    table (vessels not yet showing Gijón as AIS destination), resolves each vessel's
    IMO + flag, and writes local_feed.json for the dashboard.

PAGE LAYOUT (from the live page)
    Three tables: arrivals / departures / future port calls.
    Columns: Port Call Nº | Vessel | Berth | Arrival | Departure | Ship's Agent |
             LOA | Type | Cargo | Tn | Terminal Op.
    There is NO IMO and NO flag on the page.

IMO / FLAG RESOLUTION (never guesses)
    VesselFinder name search -> candidates. A candidate is accepted only if
      * name matches exactly,
      * it has a real 7-digit IMO (rejects pleasure craft with MMSI-style ids),
      * length is within +-2 m of the Posidonia LOA.
    Several hits after that -> tie-break on DWT >= cargo tonnage, else left BLANK.
    Blank flag is always preferable to a wrong flag.

USAGE
    python3 local_sync.py                   # fetch page, resolve, write feed
    python3 local_sync.py --file page.html  # parse a saved page (File > Save As > Page Source)
    python3 local_sync.py --paste page.txt  # parse text copied from the browser table
    python3 local_sync.py --discover        # also dump raw responses to _discovery/
    python3 local_sync.py --no-resolve      # parse only, skip VesselFinder

    then:  git add local_feed.json flags.json local_name_cache.json
           git commit -m "gijon sync" && git push

If the page is rendered by JavaScript the fetched HTML has no table; the script
says so and lists any data endpoints it saw. Use --file or --paste in that case.
"""
import argparse, html as htmllib, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime

HERE  = os.path.dirname(os.path.abspath(__file__))
FEED  = os.path.join(HERE, "local_feed.json")
SEED  = os.path.join(HERE, "flags.json")
NAMES = os.path.join(HERE, "local_name_cache.json")
DISCO = os.path.join(HERE, "_discovery")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HDRS = {"User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8"}
XMAP = {"XB": "PT", "XA": "DK", "XI": "NO"}
TRACKED = ("MT", "LR", "MH", "HK")
DELAY = 2.5          # seconds between VesselFinder requests (be gentle)
MAX_PAGES = 6        # VF result pages scanned per name
LOA_TOL = 2          # metres

POSIDONIA = "https://gijon.posidoniaport.com"
PATHS = ["/", "/movements", "/Movements", "/portcalls"]      # "/" is the URL you use in the browser

# --- section markers (visible text only) ---------------------------------
SECTION_RE = {
    "future":     re.compile(r"future\s+port\s+calls?|pr[oó]ximas?\s+escalas|escalas\s+(?:futuras|previstas)", re.I),
    "arrivals":   re.compile(r"\barrivals\b|\bllegadas\b", re.I),
    "departures": re.compile(r"\bdepartures\b|\bsalidas\b", re.I),
}

# header text -> field
FIELD_KEYS = [
    ("callNo",    r"^port\s*call"),
    ("vessel",    r"^(vessel|buque|barco)"),
    ("berth",     r"^(berth|muelle|atraque)"),
    ("arrival",   r"^(arrival|llegada|eta\b|entrada)"),
    ("departure", r"^(departure|salida|etd\b)"),
    ("agent",     r"^(ship.{0,2}s?\s*agent|agent|consignatario)"),
    ("loa",       r"^(loa|eslora)"),
    ("type",      r"^(type|tipo)"),
    ("cargo",     r"^(cargo|mercanc)"),
    ("tn",        r"^(tn|tons?|tonn)"),
    ("terminal",  r"^terminal"),
]
# fallback: column order on the live page, anchored on the numeric Port Call Nº
POSITIONAL = ["callNo", "vessel", "berth", "arrival", "departure", "agent",
              "loa", "type", "cargo", "tn", "terminal"]
DATE_RE = re.compile(r"\d{1,2}/\d{1,2}/\d{2,4}")


# =========================================================================
# HTTP + dumping
# =========================================================================
def fetch(url, timeout=25):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=HDRS), timeout=timeout)
        return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return None, f"__{type(e).__name__}"


def dump(name, text, force=False):
    if not (ARGS.discover or force):
        return
    os.makedirs(DISCO, exist_ok=True)
    p = os.path.join(DISCO, re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:80])
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"      saved -> _discovery/{os.path.basename(p)}")


def find_endpoints(html):
    found = set()
    for p in (r'fetch\(\s*["\']([^"\']+)', r'url\s*:\s*["\']([^"\']+)',
              r'["\']([^"\']*\.(?:json|csv|php|ashx|aspx)(?:\?[^"\']*)?)["\']',
              r'["\'](/[A-Za-z0-9\-_/\.]*(?:api|rest|service)[^"\']*)'):
        for m in re.findall(p, html, re.I):
            if 6 < len(m) < 160 and not re.search(r"google|recaptcha|gtag|jquery|bootstrap|analytics", m, re.I):
                found.add(m)
    return sorted(found)[:20]


# =========================================================================
# Parsing
# =========================================================================
def cell_text(c):
    c = re.sub(r"<br\s*/?>", " ", c, flags=re.I)
    c = re.sub(r"<[^>]+>", " ", c)
    return re.sub(r"\s+", " ", htmllib.unescape(c)).strip()


def to_int(s):
    m = re.search(r"\d+", re.split(r"[,.]", str(s or ""))[0])
    return int(m.group()) if m else None


def clean_vessel(s):
    s = re.sub(r"[\*\u2020]+\s*$", "", s or "").strip(" -–.")
    return re.sub(r"\s+", " ", s)


def header_map(cells):
    m = {}
    for i, c in enumerate(cells):
        t = c.strip().lower()
        for field, rx in FIELD_KEYS:
            if field not in m and re.search(rx, t):
                m[field] = i
                break
    return m if "vessel" in m and "arrival" in m else None


def call_from_cells(cells, hmap=None):
    """One table row -> call dict, or None if it is not a vessel row."""
    idx = {}
    if hmap and max(hmap.values()) < len(cells):
        idx = hmap
    else:
        # anchor on the numeric Port Call Nº (icon column may or may not be present)
        a = next((i for i, c in enumerate(cells[:3]) if re.fullmatch(r"\d{2,7}", c.strip())), None)
        if a is None:
            return None
        idx = {f: a + k for k, f in enumerate(POSITIONAL)}

    def g(f):
        i = idx.get(f)
        return cells[i].strip() if i is not None and i < len(cells) else ""

    name = clean_vessel(g("vessel"))
    if not name or len(name) < 2 or name.lower() in ("vessel", "buque", "total"):
        return None
    if not (re.fullmatch(r"\d{2,7}", g("callNo")) or DATE_RE.search(g("arrival"))):
        return None
    return {"callNo": g("callNo"), "name": name, "berth": g("berth"),
            "arrival": g("arrival"), "departure": g("departure"), "agent": g("agent"),
            "loa": to_int(g("loa")), "operation": g("type"), "cargo": g("cargo"),
            "tn": to_int(g("tn")), "terminal": g("terminal")}


def table_rows(tb):
    rows = []
    for chunk in re.split(r"<tr[^>]*>", tb, flags=re.I)[1:]:
        cells = [cell_text(c) for c in re.findall(r"<t[hd][^>]*>([\s\S]*?)</t[hd]>", chunk, re.I)]
        if cells:
            rows.append(cells)
    return rows


def calls_from_rows(rows):
    hmap, out = None, []
    for cells in rows:
        if hmap is None:
            hm = header_map(cells)
            if hm:
                hmap = (hm, len(cells))
                continue
        call = call_from_cells(cells, hmap[0] if hmap and len(cells) == hmap[1] else None)
        if call:
            out.append(call)
    return out


def parse_html(html):
    """-> {"arrivals": [...], "departures": [...], "future": [...]} using section headings."""
    h = re.sub(r"<(script|style)[\s\S]*?</\1>", " ", html, flags=re.I)
    masked = re.sub(r"<[^>]*>", lambda m: " " * len(m.group()), h)     # positions kept, tags blanked
    marks = sorted((m.start(), name) for name, rx in SECTION_RE.items() for m in rx.finditer(masked))
    found = []
    for m in re.finditer(r"<table[\s\S]*?</table>", h, re.I):
        calls = calls_from_rows(table_rows(m.group()))
        if calls:
            sec = None
            for pos, name in marks:
                if pos < m.start():
                    sec = name
            found.append((sec, calls))
    out = {"arrivals": [], "departures": [], "future": []}
    for sec, calls in found:
        if sec in out:
            out[sec].extend(calls)
    if not out["future"] and not any(s for s, _ in found) and len(found) == 3:
        print("   ! no section headings found in the HTML; using table ORDER "
              "(arrivals, departures, future)")
        out["arrivals"], out["departures"], out["future"] = (found[0][1], found[1][1], found[2][1])
    return out


def parse_paste(text):
    out = {"arrivals": [], "departures": [], "future": []}
    sec = None
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        cells = [c.strip() for c in line.split("\t")]
        if len(cells) >= 6:
            call = call_from_cells(cells)
            if call and sec:
                out[sec].append(call)
            continue
        if len(s) < 90:
            for name, rx in SECTION_RE.items():
                if rx.search(s):
                    sec = name
    return out


# =========================================================================
# IMO / flag resolution via VesselFinder name search
# =========================================================================
def norm(s):
    return re.sub(r"[^A-Z0-9]+", " ", (s or "").upper()).strip()


def vf_search(name, page=1):
    url = "https://www.vesselfinder.com/vessels?name=" + urllib.parse.quote_plus(name)
    if page > 1:
        url += f"&page={page}"
    r = urllib.request.urlopen(urllib.request.Request(url, headers=HDRS), timeout=25)
    h = r.read().decode("utf-8", "replace")
    pages = 1
    pm = re.search(r"page\s*\d+\s*/\s*(\d+)", h)
    if pm:
        pages = int(pm.group(1))
    rows = []
    for chunk in re.split(r"<tr[^>]*>", h):
        im = re.search(r"/vessels/details/(\d+)", chunk)
        fl = re.search(r"flags/4x3/(\w+)\.svg", chunk)
        nm = re.search(r'class="slna">([^<]+)<', chunk)
        if not (im and fl and nm):
            continue
        vals = dict(re.findall(r'<td class="v([3-6])[^>]*>([^<]*)</td>', chunk))
        lm = re.match(r"\s*(\d+)\s*/\s*\d+", vals.get("6", ""))
        ty = re.search(r'class="slty">([^<]+)<', chunk)
        fc = fl.group(1).upper()
        rows.append({"imo": im.group(1), "flag": XMAP.get(fc, fc),
                     "name": htmllib.unescape(nm.group(1)).strip(),
                     "vtype": htmllib.unescape(ty.group(1)).strip() if ty else "",
                     "built": vals.get("3", "").strip(), "gt": to_int(vals.get("4")),
                     "dwt": to_int(vals.get("5")), "loa": int(lm.group(1)) if lm else None})
    if not rows and "/vessels/details/" in h:
        print("      ! VesselFinder markup changed (links found, no rows parsed)")
    return rows, pages


def resolve(call, cache):
    name, loa, tn = call["name"], call["loa"], call["tn"]
    key = f"{norm(name)}|{loa or ''}"
    c = cache.get(key)
    if c and c.get("status") == "ok":
        return c
    if c and c.get("status") in ("none", "ambiguous") and time.time() - c.get("ts", 0) < 3 * 86400:
        return c
    cands, pages, p, err = [], 1, 1, None
    while p <= min(pages, MAX_PAGES):
        try:
            rows, pages = vf_search(name, p)
        except Exception as e:
            err = type(e).__name__
            break
        cands += [r for r in rows if len(r["imo"]) == 7 and norm(r["name"]) == norm(name)]
        p += 1
        time.sleep(DELAY)
    if err and not cands:
        return {"status": "error", "note": err}                  # transient - not cached
    near = [r for r in cands if r["loa"] and abs(r["loa"] - loa) <= LOA_TOL] if loa else cands
    note = (f"{len(cands)} exact-name IMO hit(s), {len(near)} within ±{LOA_TOL} m" if loa
            else f"{len(cands)} exact-name IMO hit(s), no LOA")
    if len(near) > 1 and tn:
        by_dwt = [r for r in near if r["dwt"] and r["dwt"] >= tn * 0.9]
        if len(by_dwt) == 1:
            near, note = by_dwt, note + ", tie-broken on DWT ≥ cargo"
    if len(near) == 1 and (loa or len(cands) == 1):
        r = near[0]
        res = {"status": "ok", "imo": r["imo"], "flag": r["flag"], "vtype": r["vtype"],
               "gt": r["gt"], "dwt": r["dwt"], "built": r["built"], "loaVF": r["loa"],
               "note": note, "ts": time.time()}
    elif len(near) > 1:
        res = {"status": "ambiguous", "note": note + " -> " + ", ".join(r["imo"] for r in near[:5]),
               "ts": time.time()}
    else:
        res = {"status": "none", "note": note, "ts": time.time()}
    cache[key] = res
    return res


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=1, ensure_ascii=False, sort_keys=(path == SEED))
    os.replace(tmp, path)


# =========================================================================
# Fetch the page
# =========================================================================
def get_page():
    for path in PATHS:
        s, body = fetch(POSIDONIA + path)
        print(f"   {s if s else body:>6}  {path}")
        if s == 200 and len(body) > 500:
            dump("posidonia" + (path.replace("/", "_") or "_root") + ".html", body)
            if re.search(r"<table", body, re.I) and re.search(r"vessel|buque", body, re.I):
                return body
            print("   page loaded but contains no table -> probably rendered by JavaScript")
            for e in find_endpoints(body):
                print("      endpoint hint:", e)
        time.sleep(0.6)
    return None


# =========================================================================
# Main
# =========================================================================
def build_feed(calls, cache, resolve_on):
    vessels, flags = [], load_json(SEED, {})
    for call in calls:
        res = resolve(call, cache) if resolve_on else {"status": "skipped"}
        ok = res.get("status") == "ok"
        tag = (f"{res['flag']}  IMO {res['imo']}" if ok
               else f"-- ({res.get('status')}: {res.get('note', '')})")
        print(f"   {call['arrival']:17s} {call['name'][:24]:24s} LOA {str(call['loa'] or '-'):>3}  {tag}")
        if ok:
            flags[res["imo"]] = res["flag"]
        vessels.append({
            "name": call["name"], "imo": res["imo"] if ok else "",
            "flagCode": res["flag"] if ok else "",
            "eta": call["arrival"], "etd": call["departure"],
            "type": (res.get("vtype") if ok else "") or call["cargo"],
            "loa": call["loa"] or "", "gt": (res.get("gt") or 0) if ok else 0,
            "dwt": (res.get("dwt") or 0) if ok else 0, "built": res.get("built", "") if ok else "",
            "origin": "", "berth": call["berth"], "agent": call["agent"],
            "line": " · ".join(x for x in (call["operation"], call["cargo"]) if x),
            "cargo": call["cargo"], "tn": call["tn"] or "", "terminal": call["terminal"],
            "callNo": call["callNo"], "portId": "ESGIJ", "portName": "Gijón",
            "source": "GIJ-PCS", "match": res.get("note", "")})
    return vessels, flags


def main():
    print(f"FSI Gijón PCS sync{'  [DISCOVERY]' if ARGS.discover else ''}\n")
    if ARGS.paste:
        with open(ARGS.paste, encoding="utf-8") as f:
            sections = parse_paste(f.read())
        print(f"[1/3] parsed pasted text: {ARGS.paste}")
    else:
        if ARGS.file:
            with open(ARGS.file, encoding="utf-8", errors="replace") as f:
                html = f.read()
            print(f"[1/3] parsing saved page: {ARGS.file}")
        else:
            print(f"[1/3] fetching {POSIDONIA}")
            html = get_page()
            if not html:
                print("\nNo usable page. If it opens in your browser but not here, it may need a")
                print("session or render via JavaScript. Save it (File > Save As > Page Source) and run:")
                print("   python3 local_sync.py --file page.html")
                print("or copy the tables from the browser into a text file and run:")
                print("   python3 local_sync.py --paste page.txt")
                return 1
        sections = parse_html(html)

    print(f"      arrivals={len(sections['arrivals'])}  departures={len(sections['departures'])}  "
          f"future port calls={len(sections['future'])}")
    if not sections["future"]:
        print("\nNo 'future port calls' rows found.")
        if sum(len(v) for v in sections.values()) == 0:
            print("Nothing parsed at all — run with --discover and send _discovery/ for a parser fix.")
        else:
            print("Other tables parsed fine, so the layout is understood; the list may simply be empty today.")
        return 1

    print(f"\n[2/3] resolving IMO + flag ({'off' if ARGS.no_resolve else 'VesselFinder name search'})")
    cache = load_json(NAMES, {})
    vessels, flags = build_feed(sections["future"], cache, not ARGS.no_resolve)
    save_json(NAMES, cache)
    save_json(SEED, flags)

    print("\n[3/3] writing local_feed.json")
    payload = {"generated": datetime.now().isoformat(timespec="seconds"), "generatedEpoch": time.time(),
               "source": "local_sync.py v2 / gijon.posidoniaport.com future port calls",
               "vessels": vessels}
    save_json(FEED, payload)
    res_ok = sum(1 for v in vessels if v["imo"])
    tr = [v for v in vessels if v["flagCode"] in TRACKED]
    print(f"      {len(vessels)} future calls | {res_ok} resolved to IMO+flag | {len(tr)} on your flags")
    for v in sorted(tr, key=lambda x: x["eta"]):
        print(f"      {v['flagCode']}  {v['name']:26s} {v['eta']}")
    unresolved = [v["name"] for v in vessels if not v["imo"]]
    if unresolved:
        print(f"      flag unknown (left blank, never guessed): {', '.join(unresolved)}")
    print("\nNext:  git add local_feed.json flags.json local_name_cache.json "
          "&& git commit -m 'gijon sync' && git push")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gijón PCS future port calls -> local_feed.json")
    ap.add_argument("--file", help="parse a saved HTML page instead of fetching")
    ap.add_argument("--paste", help="parse tab-separated text copied from the browser")
    ap.add_argument("--discover", action="store_true", help="dump raw responses to _discovery/")
    ap.add_argument("--no-resolve", action="store_true", help="skip VesselFinder IMO/flag lookup")
    ARGS = ap.parse_args()
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\ninterrupted (name cache and flags already saved where completed)")
        sys.exit(1)
