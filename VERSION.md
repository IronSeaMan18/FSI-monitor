# FSI Vessel Arrival Monitor — VERSION LOG
Current production version: **v3.8.0**

Semantics: MAJOR = architecture change | MINOR = feature | PATCH = fix

## v3.8.0 — "Hardening" (all 19 audit points + false-vessel defect)
See PLAN-v3.8.0.md for root-cause analysis and revert procedure.
Verified: 21 unit + 9 integration + 18 frontend = **48/48 passing**.

Headline results:
- `/api/shipnext` **33 s -> 0.7 s** (no longer blocks on VesselFinder)
- Bilbao **65 rows -> 59 unique** (4 false duplicates eliminated)
- ETA parsing **100 %** (was failing on Spanish months)
- 100-thread concurrent flag write: **zero lost writes**

## v3.7.0 — Hong Kong added (4th flag: MT / LR / MH / HK)
## v3.6.0 — Flag toggle chips + VF supplement (Ferrol, San Ciprián)
## v3.5.1 — Googlebot UA on all VF calls (did NOT fix the IP block)
## v3.5.0 — Client-side flag resolution attempt (CORS proxies too flaky)
## v3.4.0 — Flags reduced to MT/LR/MH; Barcelona removed
## v3.3.0 — ShipNext integration (9 ports, breaks VF 10-vessel cap)
## v3.2.0 — Email template simplified
## v3.1.0 — Port code fixes (Santander ESSDR001, Ferrol ESFRO001)
## v3.0.0 — Multi-source architecture, Render deployment

## DATA SOURCE MATRIX (verified from cloud)
| Source | Flag included? | Cloud-reachable? | Vessels |
|---|---|---|---|
| Bilbao PA (Googlebot UA) | YES | YES | ~59, 3 wk |
| Marín PA | no | YES | ~11 |
| ShipNext planned-vessels | no | YES | all planned, 9 ports |
| VesselFinder | YES | **IP-BLOCKED from Render** | 10/port |

## STANDING CONSTRAINT
VesselFinder blocks Render's datacenter IP (all UAs, all paths — proven v3.5.1).
v3.8.0 makes this **non-fatal**: flags come from the committed `flags.json` seed +
DB cache, and a background thread opportunistically tops up. Requests never block.

## v3.9.0 — Direct port-authority feeds for Avilés & Vilagarcía
### Discovery: VesselFinder paywalled its port pages
VF port listings now hide vessel **name and IMO** behind "Available with Basic,
Premium or Satellite plan". Only ETA/flag/type/GT remain. **VF is dead as a
listing source.** (VF *vessel-detail* pages still work -> `refresh_flags.py` is safe.)

### Two new direct PA sources found (both cloud-reachable, no VF dependency)
| Port | Feed | Fields |
|---|---|---|
| Avilés | `puertoaviles.es/es-ES/Servicios/Buques-en-el-Puerto/movimientos.csv` | 22 incl. **IMO, flag, GT, callsign** |
| Vilagarcía | `portovilagarcia.es/MDB_BARCOS.php` | 15 incl. **name, flag, ETA, agent** |

Both publish flags as Spanish country names -> `ES_FLAGS` map (120+ entries).
Avilés rows with IMO+flag auto-enrich `flags.json` via `save_flag()` — free seed growth.

Avilés fetches **PA + ShipNext merged** (dedupe by IMO/name).

### Measured
| | v3.8.1 | v3.9.0 |
|---|---|---|
| Avilés | 5 | **15** (+3 LR found) |
| Vilagarcía | 0 | **14** (100% flagged) |
| Total vessels | 144 | **168** |
| Flag coverage | 93 % | **94 %** |
| On MT/LR/MH/HK | 39 | **43** |

### Still open
- **San Ciprián 0** — Alcoa alumina terminal, very low traffic; ShipNext empty,
  Ferrol PA (apfsc.es) requires login (`comercial@apfsc.es`).
- **Marín 0 flags** — PA feed publishes neither IMO nor flag; nothing to match on.

## v3.10.0 — Local-sync channel (Posidonia Gijón / puertogijon.es)
### Finding: both Gijón sources refuse datacenter IPs
| Host | From cloud | Evidence |
|---|---|---|
| `gijon.posidoniaport.com` | **403 every path** incl. `/robots.txt` | `Server: awselb/2.0` — blocked at the AWS load balancer, before app logic. Not bot detection; no User-Agent helps. |
| `www.puertogijon.es` | **503 every path** | same for `/`, csv/php probes, Googlebot UA |

Render would be refused identically, so these cannot be server-side sources.

### Architecture: local sync channel
`local_sync.py` runs on the inspector's own machine (unblocked), collects the
arrivals, resolves flags via VesselFinder, and writes `local_feed.json`.
Committed to the repo; the server reads it via `/api/localfeed?pid=…`.
Gijón is flagged `localfeed:true` so the dashboard merges it (dedupe by IMO/name).

`local_sync.py --discover` dumps raw pages to `_discovery/` so the Posidonia
parser can be matched to the real layout — needed because the page cannot be
inspected from a datacenter.

Verified: 7/7 localfeed tests (port filtering, `*` cleaning, DD/MM/YY + Spanish
month ETA -> ISO, flag preservation, cross-port isolation).

### Source map after v3.10.0
| Port | Source | Server-side? |
|---|---|---|
| Bilbao | PA scrape (Googlebot UA) | yes |
| Avilés | PA CSV + ShipNext | yes |
| Vilagarcía | PA feed (MDB_BARCOS.php) | yes |
| Marín | PA scrape | yes |
| Gijón | ShipNext + **local_feed** | partly |
| Santander, Pasajes, Bayonne, Ferrol, A Coruña, Vigo | ShipNext | yes |
| San Ciprián | none working | — |

## v3.10.1 — ETA time fix (found by user verification)
`DD/MM/YYYY HH:MM` and `DD/MM/YY HH:MM` now parse correctly. Previously every
Avilés/Vilagarcía ETA lost its time component and displayed 00:00.

Avilés provenance audited and confirmed against the port authority's own file:
`puertoaviles.es/es-ES/Servicios/Buques-en-el-Puerto/movimientos.csv` — the same
CSV that populates the official "Buques en el Puerto" page. Flags spot-checked
against VesselFinder independently: NQ TULIPA MT, SEA EAGLE LR, TC VICTORY LR,
SOMERSET MT — all match.

## v3.10.2 — Removed broken VF supplement (root cause of AbortError + count drift)
Both reported issues traced to one cause: the San Ciprián/Ferrol "VF+" supplement
job called VesselFinder's port page, which has been unreachable from Render since
v3.5.1. Live-tested 3x: consistent ~60.6s hang, 0/3 success.

That single doomed job, sitting in a 4-worker pool for 45s before the browser's
own abort fired, delayed every other queued fetch behind it — which is why the
vessel count on screen depended on exactly when you looked during that long tail.

Fix: removed the VF+ job. San Ciprián (4) and Ferrol (5) were already fully
served by ShipNext with no VF dependency.

**Verified:**
- Two consecutive full runs against the live deployment, all 12 real sources:
  identical per-port and total counts (179 / 179)
- San Ciprián and Ferrol confirmed to still return complete data (4, 5) with
  zero dependency on VesselFinder
- No AbortError possible — the request that produced it no longer exists
