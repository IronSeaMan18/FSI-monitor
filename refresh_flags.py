#!/usr/bin/env python3
"""
refresh_flags.py — rebuild flags.json from your own machine.

WHY THIS EXISTS
    VesselFinder blocks Render's datacenter IP, so the cloud server can never
    resolve flags itself. Your laptop's residential IP is NOT blocked.
    This script collects every currently-planned vessel from ShipNext,
    resolves the missing flags via VesselFinder, and updates flags.json.

USAGE
    python3 refresh_flags.py
    git add flags.json && git commit -m "refresh flags" && git push
    -> Render redeploys with fresh flags.

Run it roughly weekly. Takes ~3 minutes. Pure stdlib, no dependencies.
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


def main():
    print("FSI flag seed refresher\n")
    flags = load_seed()
    print(f"existing seed: {len(flags)} IMOs\n")

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
