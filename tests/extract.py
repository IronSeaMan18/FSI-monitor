#!/usr/bin/env python3
"""Extract the inline <script> from fsi_monitor.py for headless node tests.
usage: python3 tests/extract.py full  > /tmp/full.js
       python3 tests/extract.py mi    > /tmp/mi.js   (the v3.12.0 manager-inquiry block only)"""
import sys, os
c = open(os.path.join(os.path.dirname(__file__), "..", "fsi_monitor.py"), encoding="utf-8").read()
js = c[c.find("<script>") + 8 : c.rfind("</script>")]
if sys.argv[1:] == ["mi"]:
    js = js[js.find("// --- v3.12.0") : js.find("function exportCSV")]
sys.stdout.write(js)
