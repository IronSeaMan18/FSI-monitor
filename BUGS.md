# FSI Monitor — Bug Tracker

## Fixed in v3.8.0
| ID | Sev | Description | Root cause | Fix |
|---|---|---|---|---|
| B-020 | HIGH | **False/duplicate vessels** | Bilbao names carry trailing `*` (provisional) + padding -> 2nd DB key for same ship | `clean_name()` strips markers; `norm_key()` dedupes; earliest ETA kept |
| B-021 | HIGH | "string did not match the expected pattern" | Bilbao ETAs are Spanish (`5 Ago`) -> JS `new Date()` Invalid Date | `parse_eta()` with ES+EN month maps -> ISO |
| B-001 | CRIT | `/api/shipnext` 33 s, returns empty flags | `resolve_flag()` did full DB read per IMO; VF blocked | in-memory cache + background resolver |
| B-002 | CRIT | Lost flag writes / corrupt JSON risk | 25 threads read-modify-write same file, no lock | `RLock` + atomic `tmp`+`os.replace` |
| B-003 | MED | UI shows "Runs: 0 / Last: never" | `/api/shipnext` never bumped `meta.runs` | shared `_fetch_endpoint()` calls `bump_run()` |
| B-004 | MED | KeyError on DB without `meta` | direct `db["meta"]["runs"]` | `setdefault` guards |
| B-005 | MED | Flag cache lost every restart | gitignored DB on ephemeral disk | committed `flags.json` seed (82 IMOs) |
| B-006 | MED | Cannot diagnose failures | bare `except:` in 8 places | typed `except Exception as e` + `log()` |
| B-007 | LOW | Dead IMOs retried every refresh | no negative cache | 24 h TTL negative cache |
| B-008 | HIGH | **Changed ETA never updated** | `merge_into_db` only filled empty fields | volatile fields always refresh |
| B-009 | MED | ETA sort wrong across sources | display strings sorted as text | `etaISO` field, sort on it |
| B-010 | LOW | Stale past arrivals shown as current | no ETA expiry | `hidePast` filter (default ON, toggleable) |
| B-011 | LOW | Port selection wiped each release | localStorage key bump | `lsMig()` migrates fsi12->fsi13 |
| B-012 | LOW | Errors scrolled away unseen | 3-line log only | persistent red error panel |
| B-013 | LOW | 12 ports fetched serially | sequential await loop | concurrency-4 parallel pool |
| B-014 | LOW | Cold start every visit | Render sleeps at 15 min | `/api/ping` keep-alive every 10 min |
| B-015 | LOW | Dead type filters | Catalan leftovers from Barcelona | removed |
| B-016 | MED | Anyone could poison flag cache | `CORS *` on `/api/saveflag` | CORS removed on write endpoint |
| B-017 | MED | Arbitrary strings written as flags | no validation | `^[A-Z]{2}$` + `^\d{7}$` IMO |
| B-018 | LOW | Silent breakage if ShipNext rotates IDs | no monitoring | `/api/health` probes all 9 ports |

## Open / known limitations
| ID | Description | Mitigation |
|---|---|---|
| B-100 | VesselFinder blocks Render IP | `flags.json` seed + background top-up; non-fatal |
| B-101 | Vilagarcía absent from ShipNext (VF-only) | needs alternate source |
| B-102 | ShipNext under-covers Ferrol (missed ANJI FOREVER, new 7-digit IMO) | VF supplement configured |
| B-103 | Bilbao publishes no IMO -> name keys | flags come inline from PA, so acceptable |
| B-104 | Render free tier: DB resets on redeploy | flags.json survives; vessel history does not |

## v3.10.1
| ID | Sev | Description | Root cause | Fix |
|---|---|---|---|---|
| B-022 | **HIGH** | **ETA time wrong on every Avilés & Vilagarcía record** — all showed 00:00 | `parse_eta` regex `^(\d{1,2})/(\d{1,2})(?:[ T]+...)` handled `DD/MM HH:MM` but not `DD/MM/YYYY HH:MM`. The `/2026` blocked the optional time group, so hh/mi defaulted to 0. Found by user cross-checking NQ TULIPA (CSV `03/08/2026 22:00` vs dashboard `03 Aug 00:00`). | Regex now `^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?:[ T]+(\d{1,2}):(\d{2}))?`; explicit year trusted (2-digit -> +2000), rollover inference only when absent. 9/9 format regression suite. |

## v3.10.2
| ID | Sev | Description | Root cause | Fix |
|---|---|---|---|---|
| B-023 | **HIGH** | Persistent red error banner "Ferrol (VF+): AbortError \| San Ciprián (VF+): AbortError" on every load | Live-tested against Render 3x: `/api/port` (VesselFinder) hangs **~60.6s every single time**, consistent to the tenth of a second — VF never responds; something (likely Render's own platform proxy timeout) eventually kills the connection at ~60s. Browser's own `AbortSignal.timeout(45000)` always loses that race first. VF confirmed permanently unreachable from Render (documented since v3.5.1). | Removed `vfsupp:true` from San Ciprián/Ferrol; deleted the VF+ job push entirely. Both ports were already fully covered by ShipNext (4 and 5 vessels respectively, verified stable across repeated live calls) — the VF+ job was contributing zero data and only cost time. |
| B-024 | MED | "Different quantity of vessels each reload" | Direct consequence of B-023: the two doomed VF+ jobs occupied 2 of the 4 parallel worker slots for the full 45s before aborting, starving/delaying the queue behind them. Total load time stretched to 45-60s+; anyone viewing the dashboard before that tail completed saw whichever partial subset had loaded so far — different every time depending on timing. | Same fix as B-023. Verified: two full back-to-back runs of all 12 real sources against the live deployment returned **identical results, port-by-port** (179/179 total, e.g. Bilbao 50/50, Vigo 23/23, Marín 8/8) — confirming the underlying data sources were never the source of the nondeterminism. |

## v3.10.3
| ID | Sev | Description | Root cause | Fix |
|---|---|---|---|---|
| B-025 | **HIGH** | ShipNext-only vessels showing blank/white flag (e.g. GCL PRAIA MOLE, GENCO FREEDOM, MALYOVITSA, KENNADI at Gijón/Avilés) | Two compounding causes: (1) `flags.json` seed hadn't been refreshed since **27 Jul** — 6+ weeks stale, so none of the currently-planned Sep/Oct vessels were in it. (2) Genuine code bug: `queue_flags()` used a permanent `set()` to track queued IMOs, so any IMO that failed VF resolution once (guaranteed, since VF blocks Render) was excluded from ever being retried again for the life of the server process — silently defeating the 24h negative-cache TTL that was supposed to allow retries. | (1) Ran `refresh_flags.py` — resolved 74/74 new IMOs, seed grew 145 -> 219, tracked-flag total 53. (2) Replaced `_resolve_seen` set with a `{imo: last_queued_ts}` dict; an IMO is only skipped if it was queued within the last `NEG_TTL` (24h), restoring real retry capability. |
