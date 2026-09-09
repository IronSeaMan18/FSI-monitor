#!/usr/bin/env python3
"""
local_sync.py — pull the sources that block cloud servers, from YOUR machine.

WHY THIS EXISTS
    Some sources refuse datacenter IPs outright:
      * gijon.posidoniaport.com  -> 403 at the AWS load balancer, every path
      * www.puertogijon.es       -> 503 for all requests
      * www.vesselfinder.com     -> blocks Render (flag lookups)
    Your own connection is not blocked. So this script runs locally, collects
    what the server cannot reach, and writes two files the app consumes:

      local_feed.json   extra vessel arrivals (merged into the dashboard)
      flags.json        IMO -> flag cache (same file refresh_flags.py maintains)

USAGE
    python3 local_sync.py                 # normal run
    python3 local_sync.py --discover      # ALSO dump raw pages to _discovery/

    git add local_feed.json flags.json
    git commit -m "local sync" && git push

FIRST RUN
    Use --discover and send the contents of _discovery/ so the Posidonia
    parser can be tuned to the exact page layout. Until then the script uses
    a generic table/JSON detector, which may or may not find the arrivals.
"""
import json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
FEED  = os.path.join(HERE, "local_feed.json")
SEED  = os.path.join(HERE, "flags.json")
DISCO = os.path.join(HERE, "_discovery")
DISCOVER = "--discover" in sys.argv

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HDRS = {"User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
XMAP = {"XB": "PT", "XA": "DK", "XI": "NO"}
TRACKED = ("MT", "LR", "MH", "HK")

# Candidate Posidonia endpoints — the real one gets confirmed on first success
POSIDONIA_HOST = "https://gijon.posidoniaport.com"
POSIDONIA_PATHS = [
    "/", "/portcalls", "/portcall-summary", "/summary",
    "/api/portcalls", "/api/v1/portcalls", "/api/portcall/summary",
    "/rest/portcalls", "/services/portcalls", "/escalas",
]
GIJON_PA = [
    "https://www.puertogijon.es/servicios/escalas/",
    "https://www.puertogijon.es/es/servicios/escalas/",
    "https://www.puertogijon.es/",
]


def fetch(url, timeout=25):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=HDRS), timeout=timeout)
        return r.status, r.read().decode("utf-8", "replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", dict(e.headers)
    except Exception as e:
        return None, f"__{type(e).__name__}", {}


def dump(name, text):
    if not DISCOVER:
        return
    os.makedirs(DISCO, exist_ok=True)
    p = os.path.join(DISCO, re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:80])
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"      dumped -> _discovery/{os.path.basename(p)}")


def strip(h):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", h)).strip()


def find_tables(html):
    """Return [(headers, rows)] for every table that looks like vessel data."""
    out = []
    for tb in re.findall(r"<table[\s\S]*?</table>", html, re.I):
        heads = [strip(x) for x in re.findall(r"<th[^>]*>([\s\S]*?)</th>", tb, re.I)]
        rows = []
        for tr in re.findall(r"<tr[^>]*>([\s\S]*?)</tr>", tb, re.I):
            cells = [strip(c) for c in re.findall(r"<td[^>]*>([\s\S]*?)</td>", tr, re.I)]
            if cells and any(c for c in cells):
                rows.append(cells)
        blob = (" ".join(heads) + " " + " ".join(" ".join(r) for r in rows[:3])).lower()
        if rows and re.search(r"buque|vessel|escala|eta|barco|arrival|llegada|imo", blob):
            out.append((heads, rows))
    return out


def find_endpoints(html):
    pats = [r'fetch\(\s*["\']([^"\']+)', r'url\s*:\s*["\']([^"\']+)',
            r'["\'](/[A-Za-z0-9\-_/\.]*(?:api|rest|json|php|ashx|asmx)[^"\']*)',
            r'["\']([^"\']*\.(?:json|csv|php)(?:\?[^"\']*)?)["\']']
    found = set()
    for p in pats:
        for m in re.findall(p, html, re.I):
            if 8 < len(m) < 160 and not re.search(r"google|recaptcha|gtag|jquery|bootstrap", m, re.I):
                found.add(m)
    return sorted(found)[:25]


def probe_posidonia():
    print("\n[1/3] Posidonia Gijón")
    hits = []
    for path in POSIDONIA_PATHS:
        url = POSIDONIA_HOST + path
        s, body, _ = fetch(url, 20)
        mark = "OK " if s == 200 and len(body) > 500 else "   "
        print(f"   {mark}{s if s else body:>6}  {path}")
        if s == 200 and len(body) > 500:
            dump(f"posidonia{path.replace('/','_') or '_root'}.html", body)
            hits.append((url, body))
        time.sleep(0.6)
    if not hits:
        print("   -> no path returned data. If the site works in your browser it may")
        print("      need a login session; open DevTools > Network, reload the port")
        print("      call summary, and note the request that returns the arrivals.")
        return []
    vessels = []
    for url, body in hits:
        eps = find_endpoints(body)
        if eps:
            print(f"   endpoints referenced by {url}:")
            for e in eps[:12]:
                print(f"      {e}")
        try:
            j = json.loads(body)
            dump("posidonia_response.json", json.dumps(j, indent=1)[:200000])
            print("   JSON response captured -> _discovery/ (parser can be tuned)")
            continue
        except Exception:
            pass
        for heads, rows in find_tables(body):
            print(f"   table: {len(rows)} rows | headers={heads[:8]}")
            vessels += rows_to_vessels(heads, rows)
    return vessels


def rows_to_vessels(heads, rows):
    """Generic table -> vessel records using header names (ES/EN)."""
    hl = [h.lower() for h in heads]

    def col(*words):
        for i, h in enumerate(hl):
            if any(w in h for w in words):
                return i
        return None

    ci = {"name": col("buque", "vessel", "barco", "ship", "nombre"),
          "eta":  col("eta", "llegada", "entrada", "arrival", "fecha"),
          "imo":  col("imo"),
          "type": col("tipo", "type"),
          "orig": col("origen", "procedencia", "origin", "from"),
          "agent": col("consignatario", "agente", "agent")}
    if ci["name"] is None:
        return []
    out = []
    for r in rows:
        def g(k):
            i = ci[k]
            return r[i].strip() if i is not None and i < len(r) else ""
        nm = g("name")
        if not nm or len(nm) < 2 or nm.lower() in ("buque", "vessel", "total"):
            continue
        imo = re.sub(r"\D", "", g("imo"))
        out.append({"name": nm, "imo": imo if len(imo) == 7 else "",
                    "eta": g("eta"), "type": g("type"),
                    "origin": g("orig"), "agent": g("agent"),
                    "portId": "ESGIJ", "portName": "Gijón", "source": "GIJ-LOCAL"})
    return out


def probe_gijon_pa():
    print("\n[2/3] puertogijon.es")
    vessels = []
    for url in GIJON_PA:
        s, body, _ = fetch(url, 20)
        print(f"   {s if s else body:>6}  {url}")
        if s == 200 and len(body) > 2000:
            dump("puertogijon_" + re.sub(r"\W+", "_", url[-30:]) + ".html", body)
            for heads, rows in find_tables(body):
                print(f"   table: {len(rows)} rows | headers={heads[:8]}")
                vessels += rows_to_vessels(heads, rows)
            if DISCOVER:
                eps = find_endpoints(body)
                if eps:
                    print("   endpoints:", eps[:10])
            if vessels:
                break
        time.sleep(0.6)
    return vessels


def resolve_flags(vessels):
    print("\n[3/3] resolving flags via VesselFinder")
    flags = {}
    if os.path.exists(SEED):
        try:
            flags = json.load(open(SEED, encoding="utf-8"))
        except Exception:
            pass
    todo = [v["imo"] for v in vessels if v.get("imo") and v["imo"] not in flags]
    print(f"   {len(vessels)} vessels | {len(todo)} flags to resolve")
    got = 0
    for n, imo in enumerate(dict.fromkeys(todo), 1):
        fc = ""
        for _ in range(3):
            try:
                h = urllib.request.urlopen(urllib.request.Request(
                    f"https://www.vesselfinder.com/vessels/details/{imo}",
                    headers=HDRS), timeout=14).read().decode("utf-8", "replace")
                m = re.search(r"flags/4x3/(\w+)\.svg", h)
                if m:
                    fc = XMAP.get(m.group(1).upper(), m.group(1).upper())
                    break
            except Exception:
                pass
            time.sleep(3)
        if fc:
            flags[imo] = fc
            got += 1
            if fc in TRACKED:
                print(f"      {fc}  IMO {imo}")
        if n % 10 == 0:
            json.dump(flags, open(SEED, "w"), indent=0, sort_keys=True)
        time.sleep(2.2)
    json.dump(flags, open(SEED, "w"), indent=0, sort_keys=True)
    for v in vessels:
        v["flagCode"] = flags.get(v.get("imo", ""), "")
    print(f"   resolved {got}; flags.json now {len(flags)} IMOs")
    return vessels


def main():
    print(f"FSI local sync  ({'DISCOVERY MODE' if DISCOVER else 'normal'})")
    vessels = probe_posidonia() + probe_gijon_pa()

    # dedupe by name within Gijón
    seen, uniq = set(), []
    for v in vessels:
        k = re.sub(r"[^a-z0-9]+", "", v["name"].lower())
        if k and k not in seen:
            seen.add(k)
            uniq.append(v)

    if uniq:
        uniq = resolve_flags(uniq)
        payload = {"generated": datetime.now().isoformat(timespec="seconds"),
                   "source": "local_sync.py", "vessels": uniq}
        json.dump(payload, open(FEED, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        tr = [v for v in uniq if v.get("flagCode") in TRACKED]
        print(f"\nlocal_feed.json written: {len(uniq)} vessels, {len(tr)} on your flags")
        for v in sorted(tr, key=lambda x: x.get("eta", "")):
            print(f"   {v['flagCode']}  {v['name'][:30]:30s} {v.get('eta','')}")
        print("\nNext:  git add local_feed.json flags.json && git commit -m 'local sync' && git push")
    else:
        print("\nNo arrivals extracted.")
        if not DISCOVER:
            print("Run again with --discover, then share the _discovery/ folder")
            print("so the parser can be matched to the real page layout.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted")
        sys.exit(1)
