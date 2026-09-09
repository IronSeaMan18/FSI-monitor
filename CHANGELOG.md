# Changelog

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

## v3.11.0 — Equasis link per vessel
Each vessel row (and CSV export) now includes a 🏢 link to Equasis
(`restricted/ShipInfo?fs=Search&P_IMO=<imo>`) alongside the existing
VesselFinder 🚢 link — one click to ISM manager / registered owner / PSC
inspection history for that IMO. Equasis requires a login; the link drops
straight into the ship page if already signed in, otherwise prompts login
first (same as visiting Equasis directly). Shown only when an IMO is known
(Equasis has no public no-login deep link by name).
Verified: 7/7 (link present/absent correctly, CSV column, exact single render).
