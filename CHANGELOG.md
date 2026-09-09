# Changelog

Newest first. Full root-cause detail for every entry lives in `VERSION.md`;
bug IDs referenced here are tracked in `BUGS.md`.

## v3.12.0 — Manager inquiry drafts
Tick vessels → **🏢 Manager Inquiry** drafts a service proposal (pre-PSC
inspection / ISM internal audit) to the vessel's **ISM manager**, grouped so
several ships under one manager become a single email. Unlike the flag
request, this is **not limited to MT/LR/MH/HK** — a new `🌐 All flags` toggle
shows every arriving vessel (live: 93 across the ShipNext ports, only 22 on
the tracked four).

Manager identity cannot be resolved automatically — free trackers publish the
beneficial owner and mislabel it "manager", and the real ISM-manager field is
paywalled everywhere except login-gated Equasis. So managers are entered once
and kept in `managers.json` forever; because managers recur across ships,
coverage compounds. Vessels with no manager on file show two prefilled lookup
links (the query that works is `<vessel> ISM manager`) plus the Equasis link.

Entries carry a `verified` flag so an aggregator guess is visibly distinct
from something read off Equasis. Every approach is written to an outreach log,
marked `conflict: true` when the vessel flies a flag you hold authority under,
so a later inspection assignment can be declared.
Verified: 34/34 headless JS tests + live endpoint and validation tests.

## v3.11.0 — Equasis link per vessel
Each vessel row (and CSV export) now includes a 🏢 link to Equasis
(`restricted/ShipInfo?fs=Search&P_IMO=<imo>`) alongside the existing
VesselFinder 🚢 link — one click to ISM manager / registered owner / PSC
inspection history for that IMO. Equasis requires a login; the link drops
straight into the ship page if already signed in, otherwise prompts login
first (same as visiting Equasis directly). Shown only when an IMO is known
(Equasis has no public no-login deep link by name).
Verified: 7/7 (link present/absent correctly, CSV column, exact single render).

## v3.10.3 — Stale flag seed + permanent-blacklist bug (B-025)
Blank flags on ShipNext-only vessels had two causes: `flags.json` had gone
6+ weeks without a refresh, and `queue_flags()` used a permanent `set()` that
blacklisted any IMO after one failed lookup, defeating the 24 h negative-cache
retry. Seed refreshed (145 → 219 IMOs, 53 on tracked flags); the set became a
`{imo: timestamp}` dict. All 8 reported vessels now resolve.

## v3.10.2 — Removed the broken VesselFinder supplement (B-023, B-024)
The San Ciprián/Ferrol "VF+" job hung ~60 s on every call (VF has been
IP-blocked from Render since v3.5.1), holding 2 of 4 parallel worker slots
until the browser aborted. That caused both the persistent `AbortError`
banner and the vessel count appearing to change on every reload. Job deleted;
both ports were already fully served by ShipNext. **Do not re-add it.**

## v3.10.1 — ETA times were all 00:00 on Avilés & Vilagarcía (B-022)
`parse_eta` handled `DD/MM HH:MM` but not `DD/MM/YYYY HH:MM` — the year blocked
the optional time group. Found by the user cross-checking a dashboard row
against the port authority's own CSV. 9/9 format regression suite added.

## v3.10.0 — Local-sync channel for Gijón
`gijon.posidoniaport.com` (403) and `www.puertogijon.es` (503) refuse all
datacenter IPs, so neither can be a server-side source. `local_sync.py` runs
on an unblocked machine, writes `local_feed.json`, and the server serves it via
`/api/localfeed`. The Posidonia parser is still written blind — `--discover`
mode exists to capture the real page layout. Verified: 7/7 localfeed tests.

## v3.9.0 — Direct port-authority feeds for Avilés & Vilagarcía
VesselFinder paywalled vessel name and IMO on its port listings, killing it as
a listing source. Two direct PA feeds replaced it: Avilés `movimientos.csv`
(22 fields incl. IMO, flag, GT, callsign) and Vilagarcía `MDB_BARCOS.php`
(15 fields). Both publish Spanish country names → `ES_FLAGS` map. Avilés rows
carrying IMO+flag now auto-enrich `flags.json`.
Avilés 5 → 15 vessels, Vilagarcía 0 → 14, total 144 → 168, coverage 93 % → 94 %.

## v3.8.1 — Follow-up to the hardening pass
v3.8.0's code was correct but the user-visible result was still empty; this
release closed that gap. (Kept for continuity — see `VERSION.md` and
`HANDOFF.md` §9, which cite it as the reason "syntax checks" and "does the
user's actual problem look fixed" are treated as two separate requirements.)

## v3.8.0 — Hardening
### Fixed (all 19 audit points + false vessels)
Backend: in-memory locked DB w/ atomic writes; committed flags.json seed;
background flag resolver (requests never block); negative cache; typed errors;
meta.runs on every endpoint; setdefault guards; ETA -> ISO (Spanish months);
name cleaning + dedupe; merge updates volatile fields; input validation;
CORS scoped to read endpoints; /api/health; /api/ping; threaded HTTP server.

Frontend: parallel fetch (concurrency 4); localStorage migration not wipe;
persistent error panel; keep-alive + 30 min auto-refresh; sort on etaISO;
hide-past-ETA toggle; dead type filters removed; vKey parity with backend.

### Verified
48/48 automated tests (21 unit, 9 integration, 18 frontend).

## v3.7.0 — Hong Kong flag added
MT / LR / MH / **HK**. Flag chips, counts, admin contact, "All 4" reset.
