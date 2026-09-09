# FSI Vessel Arrival Monitor — VERSION LOG
Current production version: **v3.11.0**

Semantics: MAJOR = architecture change | MINOR = feature | PATCH = fix
Release entries below are **newest first**; standing reference sections
(data source matrix, standing constraint) are at the end of the file.

## v3.11.0 — Equasis link added per vessel
Requested feature: quick access to ISM manager / owner info per vessel.
Verified Equasis's ship page requires a registered login (no public IMO
lookup) — confirmed via its own support docs. The deep-link pattern
`restricted/ShipInfo?fs=Search&P_IMO=<imo>` resolves (200, not 404) and
honors an existing session if the user is already logged in, dropping
straight to the ship page; otherwise it shows Equasis's own login prompt.
Added as a 🏢 icon next to the existing VesselFinder 🚢 link in the table,
and as a new column in the CSV export. Omitted when no IMO is known (Bilbao
name-only rows), matching the existing VF-link fallback pattern.
## v3.10.3 — Stale seed + permanent-blacklist bug fixed
User reported blank flags on Gijón/Avilés ShipNext vessels (GCL PRAIA MOLE,
FURNESS VICTORIA, MALYOVITSA, GENCO FREEDOM, MARIA, KENNADI, HERBANIA, GFS PEARL).

Two causes, both fixed:
1. `flags.json` hadn't been refreshed since 27 Jul (6+ weeks). Re-ran
   `refresh_flags.py`: 74/74 resolved, seed 145 -> 219 IMOs, 53 on tracked flags
   (up from 39). Confirmed several of the reported vessels are MT/LR/MH:
   GCL PRAIA MOLE (MH), GENCO FREEDOM (MH), MALYOVITSA (MT), KENNADI (LR).
2. Real bug in `queue_flags()`: used a `set()` that permanently excluded any
   IMO once queued, regardless of outcome — so an IMO that failed VF resolution
   (which is guaranteed, VF blocks Render) could never be retried again for the
   life of the process, silently defeating the existing 24h negative-cache TTL.
   Fixed: now a `{imo: timestamp}` dict, re-queues after `NEG_TTL` (24h).

**Verified:** all 8 vessels from the user's screenshots now resolve correctly
end-to-end (GCL PRAIA MOLE=MH, FURNESS VICTORIA=PA, MALYOVITSA=MT,
GENCO FREEDOM=MH, MARIA=CY, KENNADI=LR, HERBANIA=PT, GFS PEARL=CY).

**Standing operational note, restated:** the seed still requires a periodic
manual `refresh_flags.py` run + push — the automatic background resolver
cannot succeed on its own because VesselFinder blocks Render's IP (confirmed
repeatedly since v3.5.1). 6 weeks between refreshes was too long. Consider
automating this via a scheduled GitHub Action (runs on GitHub's IP, not
Render's) if recurring manual upkeep becomes a burden.

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

## v3.10.1 — ETA time fix (found by user verification)
`DD/MM/YYYY HH:MM` and `DD/MM/YY HH:MM` now parse correctly. Previously every
Avilés/Vilagarcía ETA lost its time component and displayed 00:00.

Avilés provenance audited and confirmed against the port authority's own file:
`puertoaviles.es/es-ES/Servicios/Buques-en-el-Puerto/movimientos.csv` — the same
CSV that populates the official "Buques en el Puerto" page. Flags spot-checked
against VesselFinder independently: NQ TULIPA MT, SEA EAGLE LR, TC VICTORY LR,
SOMERSET MT — all match.

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

## DATA SOURCE MATRIX (current, as of v3.11.0)
| Source | Flag included? | Cloud-reachable? | Used for |
|---|---|---|---|
| Bilbao PA (Googlebot UA) | YES | YES | Bilbao (~59, 3 wk horizon) |
| Avilés PA CSV (`movimientos.csv`) | YES (+IMO, GT, callsign) | YES | Avilés, merged with ShipNext; also seeds `flags.json` |
| Vilagarcía PA feed (`MDB_BARCOS.php`) | YES (no IMO) | YES | Vilagarcía |
| Marín PA | no (no IMO either) | YES | Marín (~11) |
| ShipNext planned-vessels | no | YES | 9 ports, all planned arrivals |
| `local_feed.json` (via `local_sync.py`) | YES | n/a — written off-cloud | Gijón supplement; parser unfinished |
| VesselFinder | YES | **IP-BLOCKED from Render** | `refresh_flags.py` only, run off-cloud |

**VesselFinder is no longer usable as a listing source at all** (paywalled name
and IMO since v3.9.0) *and* is unreachable from Render (since v3.5.1). Its only
remaining role is IMO -> flag lookup from an unblocked machine via
`refresh_flags.py`. The historical matrix this replaced is preserved in the
v3.8.0 entry's context; see v3.9.0 and v3.10.2 for why each row changed.

## STANDING CONSTRAINT
VesselFinder blocks Render's datacenter IP (all UAs, all paths — proven v3.5.1).
v3.8.0 makes this **non-fatal**: flags come from the committed `flags.json` seed +
DB cache, and a background thread opportunistically tops up. Requests never block.

