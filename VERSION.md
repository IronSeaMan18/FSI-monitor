# FSI Vessel Arrival Monitor — VERSION LOG

Current production version: **v3.5.0**

Versioning: MAJOR.MINOR.PATCH
- MAJOR = architecture change (data source overhaul)
- MINOR = feature add/remove
- PATCH = bug fix

---

## v3.5.0 (in progress) — Fix cloud flag resolution
**Problem:** VesselFinder blocks Render's datacenter IP (24s timeout → empty flagCode).
All ShipNext-sourced ports show 0 matched because flags never resolve server-side.
**Root cause:** Server-side `resolve_flag()` via VesselFinder vessel-detail page fails from cloud.
**Fix:** Client-side flag resolution — the user's browser (residential IP) reaches
VesselFinder fine. Browser resolves flags after loading vessel list from server.

## v3.4.0 — Flag filter reduced to MT/LR/MH only
- Removed flag picker UI, removed 23 other flags
- Removed Barcelona
- WORKED for Bilbao (direct PA, flags included)
- BROKE for ShipNext ports (flag resolution via VF blocked from cloud)

## v3.3.0 — ShipNext integration
- 9 ports via ShipNext planned-vessels API (breaks VF 10-vessel cap)
- Bilbao kept on direct PA scrape (3-week planning horizon)
- Server-side flag resolution via VesselFinder (parallel threads)
- WORKED at deploy time (VF not yet blocking Render)

## v3.2.0 — Email template simplified
- "Good day... * VESSEL - IMO - PORT - ETA" format

## v3.1.0 — Port code fixes
- Santander ESSAN001 → ESSDR001
- Ferrol ESFER001 → ESFRO001

## v3.0.0 — Multi-source architecture
- Bilbao PA + Barcelona OD + Marín PA + VesselFinder
- Name-based DB keys for vessels without IMO
- Render.com deployment

---

## KNOWN-GOOD DATA SOURCES (verified from cloud)

| Source | Returns flag? | Cloud-reachable? | Vessels |
|--------|--------------|------------------|---------|
| Bilbao PA (Googlebot UA) | ✅ YES | ✅ YES | 68, 3wk |
| Marín PA | ❌ no | ✅ YES | ~8 |
| ShipNext planned-vessels | ❌ no | ✅ YES | all planned |
| VesselFinder (vessel detail) | ✅ YES | ❌ **BLOCKED** | per-IMO |
| VesselFinder (port page) | ✅ YES | ❌ **BLOCKED** | 10/port |

## CRITICAL CONSTRAINT
VesselFinder blocks Render's IP. Any flag resolution via VF MUST happen
client-side (user's browser / residential IP), NOT server-side.

---

## v3.5.0 IMPLEMENTATION COMPLETE

**Solution:** Client-side flag resolution via CORS proxy.

**How it works:**
1. `/api/shipnext` returns vessels with flags filled from DB cache (instant, no VF call)
2. Browser resolves any missing flags by fetching VesselFinder through CORS proxies:
   - api.allorigins.win/raw (primary)
   - api.codetabs.com (fallback 1)
   - corsproxy.io (fallback 2)
3. Each resolved flag is POSTed to `/api/saveflag?imo=X&fc=YY` → persisted to DB
4. All future loads (any user) get flags instantly from cache

**Why this works when server-side failed:**
- VesselFinder blocks Render's datacenter IP (24s timeout)
- CORS proxies fetch VF from THEIR IPs (not blocked) and add CORS headers
- The browser can read proxy responses (CORS=*)
- Server never touches VF — only stores what the browser found

**Endpoints:**
- GET /api/shipnext → vessels + cached flags
- GET /api/saveflag?imo=X&fc=YY → persist browser-resolved flag
- (removed) /api/flag → dead, VF blocks Render

**Performance:**
- First load on fresh DB: ~30-60s (browser resolves ~20 flags, 1 at a time)
- Subsequent loads: instant (DB cache)
- Flags rarely change → cache effectively permanent

**localStorage key:** fsi9 (bumped from fsi8 to force fresh MT/LR/MH defaults)
