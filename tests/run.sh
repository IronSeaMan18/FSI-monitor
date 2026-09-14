#!/bin/sh
# Headless regression suites (node + stubbed DOM). No browser, no network.
set -e
cd "$(dirname "$0")/.."
python3 -m py_compile fsi_monitor.py refresh_flags.py local_sync.py && echo "py_compile: OK"
python3 tests/extract.py full > /tmp/fsi_full.js
python3 tests/extract.py mi   > /tmp/fsi_mi.js
node --check /tmp/fsi_full.js && echo "node --check: OK"
echo "== manager inquiry =="; node tests/test_manager_inquiry.js /tmp/fsi_mi.js | tail -1
echo "== ports / B-106   =="; node tests/test_ports_b106.js /tmp/fsi_full.js | tail -1
