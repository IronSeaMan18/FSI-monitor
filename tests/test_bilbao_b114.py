"""B-114: Bilbao page has several tables; only 'Expected arrival' rows may be parsed,
columns mapped by header (GT must not be taken from 'Length')."""
import os, sys, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import fsi_monitor as m
html = open(os.path.join(os.path.dirname(__file__), "fixtures", "bilbao_multitable.html"), encoding="utf-8").read()
class R:
    def read(self): return html.encode()
urllib.request.urlopen = lambda *a, **k: R()
m.name_lookup = lambda *a, **k: None
v = m.fetch_bilbao()
fails = 0
def ok(c, msg):
    global fails
    print(("PASS " if c else "FAIL ") + msg); fails += (not c)
ok(len(v) == 3, f"only expected-arrival rows parsed ({len(v)})")
ok(all(x["etaISO"] for x in v), "every row has a real ETA date")
ok(all(not any(ch.isalpha() for ch in x["eta"].split()[0]) for x in v), "ETA column never holds a port name")
ok(all(x["gt"] != int(x["loa"] or 0) for x in v), "GT not copied from Length")
ok(all("00:00" not in x["eta"] for x in v), "no fake 00:00 time")
print(f"{3*0+5-fails}/5"); sys.exit(1 if fails else 0)
