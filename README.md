# FSI Vessel Arrival Monitor v3.11.0

Expected-arrival monitor for a Flag State Inspector covering 12 ports in
northern Spain + Bayonne. Filters to **Malta / Liberia / Marshall Islands / Hong Kong**.

## Deploy (Render.com)
Start command: `python fsi_monitor.py` — no build step, no dependencies.

## IMPORTANT: commit `flags.json`
It is the IMO->flag cache seed and is what makes flags survive Render restarts.
It is deliberately **not** gitignored. `fsi_vessels_db.json` IS gitignored.

## Endpoints
| Path | Purpose |
|---|---|
| `/` | Dashboard |
| `/api/bilbao` | Bilbao PA scrape (flags inline; Googlebot UA bypasses Radware) |
| `/api/aviles` | Avilés PA CSV + ShipNext, merged/deduped (has IMO + flag) |
| `/api/vilagarcia` | Vilagarcía PA feed (has flag, no IMO) |
| `/api/marin` | Marín PA scrape (no IMO, no flag in source) |
| `/api/shipnext?pid=&pname=` | ShipNext planned vessels, 9 ports (no flag field) |
| `/api/localfeed?pid=&pname=` | Serves `local_feed.json` if present (Gijón; see HANDOFF §5) |
| `/api/saveflag?imo=&fc=` | Persist a resolved flag (validated, no CORS) |
| `/api/port?vf=&pid=&pname=` | VesselFinder listing — **dead path**, see B-105 |
| `/api/ping` | Keep-alive + version/queue |
| `/api/health` | Probes all 9 ShipNext ports, reports flag cache size |
| `/api/history` | Full DB |
| `/api/clearold` | Purge records unseen > 30 days |

## Docs
**Start with `HANDOFF.md`** — it covers the constraints that cost real debugging
time (VesselFinder's IP block, the Gijón datacenter block, working conventions).

`VERSION.md` (full history + root causes) · `BUGS.md` (B-001…B-025) ·
`CHANGELOG.md` (user-facing summary) · `PLAN-v3.8.0.md` (historical SDD plan) ·
`refresh_flags.py` (periodic seed refresh, run off-cloud) ·
`local_sync.py` (Gijón local sync, unfinished — see HANDOFF §5)
