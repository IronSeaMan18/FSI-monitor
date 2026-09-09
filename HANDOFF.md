# HANDOFF.md — Read this file first

You are picking up **FSI Vessel Arrival Monitor**, currently **v3.11.0**, from a
long-running Claude.ai chat session. This document exists so you don't have to
rediscover things that were already found the hard way — several of them cost
real debugging time. Read this fully before touching code.

---

## 1. What this is, in one paragraph

A single-file Python web dashboard for a Flag State Inspector (Illya) based in
Gijón, Spain, authorized under Malta, Liberia, Marshall Islands, and Hong Kong.
It aggregates **expected vessel arrivals** across 12 ports on Spain's northern
coast + Bayonne (France), filters to his four flags, and lets him generate
inspection-request emails to the flag administrations. It is deployed on
Render.com and is genuinely in daily use — treat bugs as production bugs.

---

## 2. Where everything is

All files in this delivery go at the **repo root** (no subfolders):

| File | Purpose |
|---|---|
| `fsi_monitor.py` | The entire application — Python stdlib HTTP server + inline HTML/CSS/JS dashboard. One file, no framework, no build step. |
| `flags.json` | **Committed, not gitignored.** IMO → flag-code cache. This is load-bearing — see §4. |
| `refresh_flags.py` | Standalone script, run manually/periodically from a non-Render machine. Rebuilds `flags.json`. See §4. |
| `local_sync.py` | Standalone script for sources that block *all* datacenter IPs outright (not just Render) — currently targets Gijón's Posidonia port-call system. See §5. |
| `Procfile`, `requirements.txt`, `runtime.txt` | Render deploy config. `requirements.txt` is intentionally near-empty — stdlib only. |
| `.gitignore` | Excludes `fsi_vessels_db.json` (runtime DB, regenerated) and `_discovery/` (local_sync.py debug dumps). **Does not** exclude `flags.json`. |
| `VERSION.md` | Full version history, v3.0.0 → v3.11.0, with root-cause analysis for every fix. Read this before assuming something is a fresh bug — it may be documented already. |
| `BUGS.md` | Bug tracker, IDs B-001 through B-025, fixed and open. |
| `CHANGELOG.md` | Shorter, user-facing changes per version. |
| `PLAN-v3.8.0.md` | The SDD plan document from the v3.8.0 "hardening" pass (19-point audit). Historical, kept for reference. |
| `README.md` | Short pointer doc. |

**Live deployment:** Render.com, auto-deploys from the connected GitHub repo's
default branch. Free tier: spins down after ~15 min idle, ~30s cold start on
next request. `/api/ping` exists as a keep-alive target if that becomes worth
automating (e.g. external cron hitting it every 10 min).

---

## 3. Architecture in 90 seconds

```
GET /                    -> serves the whole dashboard (inline HTML/JS)
GET /api/bilbao          -> Bilbao Port Authority scrape (has flags inline)
GET /api/marin           -> Marín Port Authority scrape (no flags)
GET /api/aviles          -> Avilés Port Authority CSV (has IMO + flag)
GET /api/vilagarcia      -> Vilagarcía Port Authority feed (has flag, no IMO)
GET /api/shipnext?pid=&pname=  -> ShipNext planned-vessels API (9 ports, no flag)
GET /api/localfeed?pid=&pname= -> reads local_feed.json if present (see §5)
GET /api/saveflag?imo=&fc=     -> persist a resolved flag to the DB cache
GET /api/history         -> full DB dump (vessels + meta + flag count)
GET /api/clearold        -> purge vessels unseen >30 days
GET /api/health          -> probes all 9 ShipNext ports, reports flag cache size
GET /api/ping            -> keep-alive + version + resolver queue length
```

The browser's `fetchAll()` (in the inline `<script>`) fans out to whichever of
these apply to the 12 configured ports, in parallel (concurrency 4), merges
results into `S.combined`, and renders the table. Each port object in the JS
`PORTS` array declares its own sourcing (`direct:`, `sn:`, `vfsupp:`,
`localfeed:`) — read that array first when asking "where does port X's data
come from."

The Python side keeps an **in-memory DB** (`_DB`, guarded by `_DB_LOCK`),
flushed to `fsi_vessels_db.json` atomically (`tmp` + `os.replace`). It is
NOT re-read from disk after the first `load_db()` call in a process's life —
this was a deliberate fix for I/O thrashing (see B-001 in BUGS.md). If you add
a new endpoint that needs the DB, call `load_db()`, don't read the file
yourself.

---

## 4. THE central constraint — read this before "fixing" flag resolution

**VesselFinder blocks Render's datacenter IP.** This has been re-confirmed
independently at least four times across the project's life (v3.5.1, v3.8.0,
v3.10.2 — see VERSION.md for each). It is not a User-Agent issue (Googlebot UA
does not help, unlike Bilbao's Radware block which *is* UA-based and *is*
bypassed by Googlebot UA — don't conflate the two). It is not intermittent —
live-tested 3x back to back, ~60.6s hang every time, 0% success.

**Consequence:** ShipNext (used for 9 of the 12 ports) returns vessel lists
with IMO but **no flag field at all** — ShipNext's API has never had one, at
any point in this project. VesselFinder is the only free source that maps
IMO → flag, and the server literally cannot reach it.

**The working solution:** `flags.json` is a seed cache, resolved from a
non-Render machine (this sandbox during the chat session, or the user's own
laptop) and committed to the repo. `refresh_flags.py`:
1. collects every currently-planned IMO across the 9 ShipNext ports,
2. harvests flags for free where possible (Avilés CSV and Vilagarcía's PA
   feed both carry flag alongside IMO/name — see their fetch functions),
3. resolves whatever's left via VesselFinder directly (works fine from a
   normal residential/sandbox IP), with gentle pacing (~2.5s/vessel) to avoid
   rate-limiting,
4. writes the result back to `flags.json`.

Run it, then `git add flags.json && git commit && git push`. Render redeploys
and the new seed is loaded at next boot.

**This needs to happen periodically.** It went 6 weeks without a refresh once
(late July → early Sept) and the user noticed blank flags on vessels that
mattered to him (B-025 in BUGS.md). There is also a background resolver
thread server-side (`_resolver_loop`) that opportunistically tries VF via a
queue — but since VF is blocked from Render, it will essentially never
succeed on its own; it exists mainly so that IF the block is ever lifted,
resolution starts working automatically with no code change.

**If asked to "fix" flag resolution being incomplete:** the fix is almost
certainly "run `refresh_flags.py` and push," not a code change. Check
`VERSION.md` v3.10.3 and B-025 for the exact prior instance of this.

**A real bug already found and fixed here (v3.10.3):** the resolver's
"already tried" tracking used to be a `set()` that never expired, permanently
blacklisting any IMO that failed once (i.e. every IMO, since VF always
fails from Render) from ever being retried, defeating the 24h negative-cache
TTL that was supposed to allow retries. Now a `{imo: timestamp}` dict. If you
see similar "tracked forever, never retried" patterns elsewhere, they're
worth a second look.

**Possible future improvement, not yet built:** a scheduled GitHub Action
that runs `refresh_flags.py` on GitHub's own IP (not blocked, not the user's
laptop) and commits automatically. This was proposed to the user but not
built — mentioning it here in case they ask for it, since it would close this
operational gap permanently.

---

## 5. The other blocked source: Gijón's own systems

Two more sources refuse **all** datacenter IPs (not just Render's — confirmed
from this project's own sandbox too, so it's a genuine IP-tier block, not
Render-specific):

| Host | Symptom |
|---|---|
| `gijon.posidoniaport.com` | 403 on every path, including `/robots.txt`. `Server: awselb/2.0` — blocked at the AWS load balancer, before any app logic runs. |
| `www.puertogijon.es` | 503 on every path, every User-Agent. |

`local_sync.py` exists for this: run from a machine that isn't blocked (the
user's laptop works, since they can see these pages in a normal browser),
writes `local_feed.json`, commit + push, server reads it via
`/api/localfeed?pid=ESGIJ`.

**Status: unfinished.** The Posidonia parser in `local_sync.py` was written
**blind** — nobody has actually seen the page's real structure, since it
can't be inspected from any datacenter context available in this project.
It uses a generic table/JSON-endpoint detector and a `--discover` mode that
dumps raw pages to `_discovery/` for manual inspection. If the user runs
`local_sync.py --discover` and shares the output, the parser can be tuned to
the actual layout. As of this handoff, that loop has not been closed — this
is genuinely open work, not a "should already work" item.

---

## 6. Port-by-port source map (current, v3.11.0)

| Port ID | Name | Source(s) | Notes |
|---|---|---|---|
| ESGIJ | Gijón | ShipNext + local_feed (unfinished, see §5) | |
| ESAVS | Avilés | PA CSV (`movimientos.csv`) + ShipNext, merged/deduped | CSV has IMO+flag+GT+callsign |
| ESTAN | Santander | ShipNext | |
| ESBIO | Bilbao | Direct PA scrape (Googlebot UA bypasses Radware) | Has flags inline; ~65 vessels, 3wk horizon — deliberately NOT on ShipNext, PA gives more/better data |
| ESPAS | Pasajes | ShipNext | |
| FRBAY | Bayonne (France) | ShipNext | Only non-Spanish port |
| ESSCI | San Ciprián | ShipNext only | VF supplement was tried and removed in v3.10.2 — see below |
| ESFER | Ferrol | ShipNext only | Same as above. Ferrol PA (apfsc.es) requires a login (comercial@apfsc.es) for vessel data — never obtained, would let San Ciprián+Ferrol move to a real PA source if pursued |
| ESCOR | A Coruña | ShipNext | |
| ESMRN | Marín | Direct PA scrape | No IMO, no flag in source — genuinely nothing to match against; open limitation |
| ESVIL | Vilagarcía | Direct PA feed (`MDB_BARCOS.php`) | Has flag (Spanish country names, see `ES_FLAGS` map), no IMO |
| ESVGO | Vigo | ShipNext | |

**Do not re-add a VF-based "supplement" job for San Ciprián/Ferrol.** This was
tried (`vfsupp: true`) and definitively removed in v3.10.2 after live-testing
proved it *always* hung ~60s against Render before the browser's own 45s
abort fired — it contributed zero data and, worse, occupied 2 of 4 parallel
worker slots for the full 45s, delaying every other port's load and causing
the total vessel count to appear to change on every reload depending on
timing. Full root-cause writeup: VERSION.md v3.10.2, BUGS.md B-023/B-024.

---

## 7. Spanish flag-name mapping

Avilés and Vilagarcía publish flags as Spanish-language country names
(`ISLAS MARSHALL`, `LIBERIA`, `GRAN BAHAMAS`, etc.), not ISO codes. The
`ES_FLAGS` dict in `fsi_monitor.py` (~120 entries) handles this. If a new
Spanish-language source is added, reuse `es_flag()` rather than writing a
new mapping.

---

## 8. Known open items (not yet done, not forgotten)

- **Gijón/Posidonia parser** — see §5, needs `--discover` output from the user.
- **Marín has no IMO or flag in its source** — genuinely no matching key
  available from the current feed; would need a different source entirely.
- **San Ciprián / Ferrol** — could move off ShipNext-only to a real PA feed
  if the user gets Ferrol PA login credentials (comercial@apfsc.es). Not
  pursued because it needs the user to make contact.
- **`flags.json` staleness** — needs periodic `refresh_flags.py` runs. A
  GitHub Action to automate this was discussed but not built (see §4).
- **Equasis integration is link-only** (v3.11.0) — each vessel row has a
  link into Equasis's ISM-manager/owner page, but it requires the user's own
  login and nothing is scraped automatically. A fuller "vessel manager
  lookup with cached company contacts" feature was discussed (grouping
  vessels by manager, since managers recur far more than individual ships)
  but never built — flagged to the user as a COI consideration (he holds FSI
  authority for MT/LR/MH/HK; marketing ISM audit services to companies whose
  ships he might inspect under that authority is a real conflict worth
  resolving deliberately before building outreach tooling). If this comes up
  again, start from that conversation rather than re-deriving it.

---

## 9. Working conventions established over this project (please continue them)

- **SDD approach, explicitly requested by the user.** Every change gets: a
  version bump (semver: MAJOR = architecture change, MINOR = feature,
  PATCH = fix), an entry in `VERSION.md` with root-cause reasoning (not just
  "fixed X"), and a `BUGS.md` entry with an ID if it's a bug. Don't skip this
  even for small fixes — the user reads these to build trust in changes he
  can't personally verify against live sources.
- **Verify against the live deployment or a local run before claiming
  something is fixed.** Multiple entries in VERSION.md exist specifically
  because an earlier fix was declared done after only a syntax check, and
  the underlying behavior was still broken (see v3.8.0 → v3.8.1 for the
  clearest example: code was correct, but the actual user-visible outcome
  was still empty, and it took a second pass to notice). The user has
  explicitly called this out once already ("why you didnt finish") — treat
  "does the JSON compile" and "does the user's actual problem look fixed
  when you fetch the real data" as two separate, both-required checks.
- **The user cross-checks your claims against source data** — he caught a
  real ETA-parsing bug (B-022) by comparing a dashboard timestamp against
  the raw CSV himself. Assume he will do this again. Don't state a flag or
  a data point with confidence unless you've actually resolved/verified it
  in this session.
- **No Chrome/browser automation for this user.** Long-running browser tool
  use has caused his laptop to freeze in the past. Use direct HTTP
  requests/`curl`-equivalents instead. If you have a headless browser tool
  available in Claude Code, prefer not to reach for it here unless nothing
  else works.
- **Localize dates/times with care.** Multiple sources use different date
  formats (Spanish month abbreviations like "Ago" for August, `DD/MM/YYYY
  HH:MM`, `DD/MM HH:MM` with year inferred, ISO8601 from ShipNext). All of
  it funnels through `parse_eta()` — extend that function rather than
  parsing dates elsewhere.
- **Test node/JS logic headlessly rather than assuming it's correct** — this
  project's JS has been verified multiple times by extracting the `<script>`
  block and running it under `node` with stubbed `document`/`localStorage`/
  `fetch`. That pattern is fast and has caught real bugs (e.g. a missing
  closing brace that silently broke the entire frontend). Reuse it.

---

## 10. Quick start for your first session

```bash
# 1. Read this file (done). Skim VERSION.md top-to-bottom for full history.
# 2. Run locally:
python3 fsi_monitor.py            # http://localhost:8090
# 3. Confirm flags.json isn't stale:
python3 refresh_flags.py          # safe to run anytime; no-ops if current
# 4. If asked to change frontend JS, verify headlessly before claiming done:
python3 -c "
c=open('fsi_monitor.py').read()
open('/tmp/app.js','w').write(c[c.find('<script>')+8:c.rfind('</script>')])
"
node --check /tmp/app.js
```
