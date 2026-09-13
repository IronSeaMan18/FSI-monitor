#!/usr/bin/env python3
"""
refresh_flags.py — rebuild flags.json from your own machine.

WHY THIS EXISTS
    VesselFinder blocks Render's datacenter IP, so the cloud server can never
    resolve flags itself. Your laptop's residential IP is NOT blocked.
    This script collects every currently-planned vessel from ShipNext,
    resolves the missing flags via VesselFinder, and updates flags.json.

USAGE
    python3 refresh_flags.py                      # flags only
    python3 refresh_flags.py --live https://fsi-monitor.onrender.com
                                                  # also pull managers saved via the dashboard
    git add flags.json managers.json && git commit -m "refresh seeds" && git push
    -> Render redeploys with fresh seeds.

Since v3.13.0 this runs automatically every day via
.github/workflows/refresh-seeds.yml. Run it by hand only to force a refresh.
Takes ~3 minutes. Pure stdlib, no dependencies.
"""
import json, os, re, sys, time, urllib.request, urllib.error

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "flags.json")
XMAP = {"XB": "PT", "XA": "DK", "XI": "NO"}
TRACKED = ("MT", "LR", "MH", "HK")

SN_PORTS = {
    "Gijón":       "58238f70821bd20e38598a87",
    "Avilés":      "58206e746c69920ef8543580",
    "Santander":   "5828c5146742c90cc0eb71c7",
    "Pasajes":     "582826581c912f0ebcb63c9e",
    "Bayonne":     "58209fb4f4f7e611988749eb",
    "San Ciprián": "5829003f6742c90cc0eb7296",
    "Ferrol":      "582365a0821bd20e385989d8",
    "A Coruña":    "582303d7821bd20e38598841",
    "Vigo":        "582a46575baa9509b886eeed",
}
# Extra VesselFinder port pages — free flags, catches ships ShipNext misses
VF_PORTS = {"Vilagarcía": "ESVIL001", "Ferrol": "ESFRO001", "Marín": "ESMRN001"}


def load_seed():
    if os.path.exists(SEED):
        try:
            with open(SEED, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  ! existing flags.json unreadable ({e}); starting fresh")
    return {}


def save_seed(flags):
    tmp = SEED + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(flags, f, indent=0, sort_keys=True)
    os.replace(tmp, SEED)


def collect_planned():
    """Every IMO currently planned across the ShipNext ports."""
    found = {}
    for name, pid in SN_PORTS.items():
        try:
            req = urllib.request.Request(
                f"https://shipnext.com/api/v1/ports/{pid}/planned-vessels",
                headers={"User-Agent": UA})
            data = json.loads(urllib.request.urlopen(req, timeout=20).read())
            n = 0
            for v in data.get("data", []):
                if v.get("imo"):
                    found[v["imo"]] = v.get("name", "")
                    n += 1
            print(f"  {name:14s} {n:3d} vessels")
        except Exception as e:
            print(f"  {name:14s} FAILED ({type(e).__name__})")
    return found


def probe_vesselfinder():
    """v3.13.1: one explicit, unambiguous line in every run's log answering the
    question the workflow exists to test - can THIS IP reach VesselFinder?
    A bot-block page still returns HTTP 200 with HTML, so 'harvested' lines
    below prove nothing on their own. This checks a known vessel resolves to
    its known flag (FURNESS VICTORIA 9640621 -> PA)."""
    try:
        req = urllib.request.Request("https://www.vesselfinder.com/vessels/details/9640621",
                                     headers={"User-Agent": UA, "Accept": "text/html"})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
        if "Radware" in html or "Verifying your browser" in html:
            print("VESSELFINDER REACHABILITY: BLOCKED (bot-protection page served to this IP)")
            return False
        m = re.search(r"flags/4x3/(\w+)\.svg", html)
        fc = XMAP.get(m.group(1).upper(), m.group(1).upper()) if m else ""
        if fc == "PA":
            print("VESSELFINDER REACHABILITY: OK (9640621 -> PA as expected)")
            return True
        print(f"VESSELFINDER REACHABILITY: UNEXPECTED (page parsed, flag={fc!r}, expected 'PA') - parser may need attention")
        return False
    except Exception as e:
        print(f"VESSELFINDER REACHABILITY: FAILED ({type(e).__name__}: {e})")
        return False


def harvest_vf_ports(flags):
    """VF port pages list flag + IMO together — free, no per-vessel lookup."""
    got = 0
    for name, code in VF_PORTS.items():
        try:
            req = urllib.request.Request(
                f"https://www.vesselfinder.com/ports/{code}",
                headers={"User-Agent": UA, "Accept": "text/html"})
            html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
            for row in re.split(r"<tr[^>]*>", html):
                if "vessels/details" not in row:
                    continue
                im = re.search(r"vessels/details/(\d+)", row)
                fl = re.search(r"flags/4x3/(\w+)\.svg", row)
                if im and fl:
                    fc = XMAP.get(fl.group(1).upper(), fl.group(1).upper())
                    if re.match(r"^[A-Z]{2}$", fc) and flags.get(im.group(1)) != fc:
                        flags[im.group(1)] = fc
                        got += 1
            print(f"  {name:14s} harvested")
        except Exception as e:
            print(f"  {name:14s} FAILED ({type(e).__name__})")
        time.sleep(2)
    return got


def resolve(imo, tries=3):
    for _ in range(tries):
        try:
            req = urllib.request.Request(
                f"https://www.vesselfinder.com/vessels/details/{imo}",
                headers={"User-Agent": UA, "Accept": "text/html"})
            html = urllib.request.urlopen(req, timeout=14).read().decode("utf-8", "replace")
            m = re.search(r"flags/4x3/(\w+)\.svg", html)
            if m:
                return XMAP.get(m.group(1).upper(), m.group(1).upper())
        except Exception:
            pass
        time.sleep(3.5)
    return ""


MANAGERS = os.path.join(HERE, "managers.json")


def pull_live_managers(base_url):
    """v3.13.0 / B-109: managers saved through the dashboard land on Render's
    disk, which is wiped on every deploy. Pull them from the live server and
    merge into the committed managers.json BEFORE anything is pushed, so the
    redeploy that follows cannot destroy them. Newest `updated` wins."""
    base_url = base_url.rstrip("/")
    try:
        req = urllib.request.Request(base_url + "/api/managers", headers={"User-Agent": UA})
        live = json.loads(urllib.request.urlopen(req, timeout=60).read()).get("managers", {})
    except Exception as e:
        print(f"  ! could not pull live managers from {base_url}: {e} (keeping repo copy)")
        return 0
    repo = {}
    if os.path.exists(MANAGERS):
        try:
            with open(MANAGERS, encoding="utf-8") as f:
                repo = json.load(f)
        except Exception as e:
            print(f"  ! managers.json unreadable ({e}); treating as empty")
    merged, changed = dict(repo), 0
    for imo, m in (live or {}).items():
        if not (isinstance(m, dict) and re.match(r"^\d{7}$", imo) and m.get("ism")):
            continue
        if imo not in merged or (m.get("updated", "") > merged[imo].get("updated", "")):
            if merged.get(imo) != m:
                merged[imo] = m; changed += 1
    if changed:
        tmp = MANAGERS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=1, ensure_ascii=False, sort_keys=True)
        os.replace(tmp, MANAGERS)
    print(f"  live managers: {len(live)} | repo: {len(repo)} | merged in: {changed} | now: {len(merged)}")
    return changed


def main():
    print("FSI flag seed refresher\n")
    live = None
    for i, a in enumerate(sys.argv):
        if a == "--live" and i + 1 < len(sys.argv):
            live = sys.argv[i + 1]
    if live:
        print(f"pulling dashboard-saved managers from {live} ...")
        pull_live_managers(live)
        print()
    flags = load_seed()
    print(f"existing seed: {len(flags)} IMOs\n")
    vf_ok = probe_vesselfinder()
    print()

    print("collecting planned vessels from ShipNext...")
    planned = collect_planned()

    print("\nharvesting VesselFinder port pages (free flags)...")
    harvest_vf_ports(flags)
    save_seed(flags)

    todo = [i for i in planned if i not in flags]
    print(f"\nplanned: {len(planned)} | known: {len(planned)-len(todo)} | to resolve: {len(todo)}")
    if not todo:
        print("nothing to do — seed already current.")
    else:
        print("resolving (gentle pacing, ~2.5 s each)...\n")
        ok = 0
        for n, imo in enumerate(todo, 1):
            fc = resolve(imo)
            if fc:
                flags[imo] = fc
                ok += 1
                if fc in TRACKED:
                    print(f"  {fc}  {planned[imo][:32]:32s} IMO {imo}")
            if n % 15 == 0:
                save_seed(flags)
                print(f"  ... {n}/{len(todo)}  (resolved {ok})")
            time.sleep(2.2)
        save_seed(flags)
        print(f"\nresolved {ok}/{len(todo)}")
        if ok < len(todo) * 0.5:
            print("  ! low success rate — VesselFinder may be rate-limiting.")
            print("    Wait ~30 min and run again; already-resolved flags are kept.")

    if not vf_ok:
        print("\n  ! VesselFinder was NOT reachable from this IP - flag resolution could not run.")
        print("    Managers were still synced. Run refresh_flags.py from a residential IP for flags.")
    counts = {f: sum(1 for v in flags.values() if v == f) for f in TRACKED}
    print(f"\nflags.json now: {len(flags)} IMOs")
    print(f"on your flags:  {counts}  (total {sum(counts.values())})")
    print("\nNext:  git add flags.json && git commit -m 'refresh flags' && git push")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\ninterrupted — progress already saved to flags.json")
        sys.exit(1)
