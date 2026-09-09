# FSI Vessel Arrival Monitor v3.8.0

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
| `/api/ping` | Keep-alive + version/queue |
| `/api/health` | Probes all 9 ShipNext ports, reports flag cache size |
| `/api/history` | Full DB |
| `/api/clearold` | Purge records unseen > 30 days |

## Docs
`refresh_flags.py` (weekly seed refresh) · `PLAN-v3.8.0.md` (root causes + revert) · `BUGS.md` · `CHANGELOG.md` · `VERSION.md`
