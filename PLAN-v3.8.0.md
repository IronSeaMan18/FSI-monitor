# PLAN — v3.8.0 "Hardening"

## Goal (unchanged, restated)
Illya needs reliable information about expected vessel arrivals in his region,
filtered to MT / LR / MH / **HK** flags, to plan Flag State Inspections.

## Scope
Fix all 19 audited weak points + false-vessel defect (#20). No new data sources.

## ROOT CAUSES FOUND (investigation before code)

| # | Finding | Evidence |
|---|---------|----------|
| A | `resolve_flag()` calls `load_db()` per IMO; `save_flag()` does full load+save per flag | 80 vessels = 160+ whole-file JSON ops → the 33 s `/api/shipnext` |
| B | 25 threads read-modify-write the same file, no lock | lost writes, corrupt-JSON risk |
| C | **Bilbao names carry a trailing `*` + padding** — `'containerships nord          *'` | 4/65 rows. Creates a 2nd DB key for a vessel already stored as `containerships nord` → **duplicate/false vessel** |
| D | **Bilbao ETAs are Spanish** — `'5 Ago'` (agosto) | `new Date('5 Ago')` → Invalid Date → the "string did not match the expected pattern" JS error, and broken sort |
| E | DB never expires by ETA, only by `lastSeen` (30 d) | past arrivals resurface in History view = "false vessels" |
| F | `merge_into_db` only fills *empty* fields | changed ETA never updates — the core purpose of the tool |
| G | `/api/shipnext` never increments `meta.runs` | UI shows "Runs: 0 / Last: never" |

Marín parser verified CLEAN (11/11 valid). VF parser structurally OK.

## RECTIFICATION ACTIONS

### Backend
1. In-memory `_DB` + `threading.RLock`; disk read once at boot, atomic write (tmp+rename)
2. `flags.json` committed seed loaded at boot → cache survives Render restarts
3. `resolve_flag()` = pure memory lookup, zero disk I/O
4. Background resolver thread + queue; `/api/shipnext` returns immediately
5. Negative cache, 24 h TTL — stop retrying dead IMOs every refresh
6. `except Exception as e` + logged everywhere; no bare except
7. `meta.runs` / `meta.lastRun` on every fetch endpoint; `setdefault` guards
8. `clean_name()` — strip `*`, collapse whitespace, drop junk rows
9. `parse_eta()` → ISO 8601, Spanish + English month maps
10. `merge_into_db` updates changed ETA/flag; preserves `firstSeen`
11. `norm_key()` for name-based keys (dedupe `nord *` vs `nord`)
12. Validate `fc` as `^[A-Z]{2}$`; CORS `*` only on read endpoints

### Frontend
13. Parallel fetch, concurrency 4
14. localStorage migration (fsi11→fsi13) instead of wipe
15. Persistent failed-ports panel
16. Keep-alive ping /api/ping every 10 min
17. Sort on `etaISO`, not display string
18. Hide vessels whose ETA is >2 days past (toggle)
19. Dead type-filter options removed (Portacontenidors/Tancs)
20. HK added to flag counts/admin (done v3.7.0, retained)

## REVERT PROCEDURE
- Previous good artefact: `fsi-monitor-v3.7.0.zip` (HK added, pre-hardening)
- `git revert <sha>` → Render auto-redeploys previous build
- `flags.json` is additive-only; safe to keep across revert
- localStorage: v3.8.0 migrates, does not destroy. Reverting leaves `fsi13_*`
  keys unused and `fsi12_*` intact.

## ACCEPTANCE CRITERIA
- [ ] `/api/shipnext` responds < 5 s cold
- [ ] No duplicate vessel names differing only by `*`/whitespace
- [ ] All ETAs parse to valid ISO; no Invalid Date
- [ ] `meta.runs` increments
- [ ] Concurrent flag writes lose nothing (100-thread test)
- [ ] 4 flags MT/LR/MH/HK filter correctly
- [ ] Full syntax + brace-balance clean
