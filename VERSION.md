# FSI Vessel Arrival Monitor — VERSION LOG
Current production version: **v3.14.0**

Semantics: MAJOR = architecture change | MINOR = feature | PATCH = fix
Release entries below are **newest first**; standing reference sections
(data source matrix, standing constraint) are at the end of the file.

## v3.14.0 — The manager directory maintains itself; keep-alive; tests in-repo
User: "keep always info about managers for the vessels arriving into Gijón
and Avilés. Today we have new ones and info is empty." Six new vessels had
appeared overnight; the v3.13.0 directory was a snapshot, not a process.

### 1. ISM manager auto-resolution (MagicPort), daily
MagicPort's vessel pages carry a JSON-LD sentence — `"ISM Manager of NAME
(IMO 1234567) is COMPANY."` — and `magicport.ai/vessels?search=<IMO>` returns
the vessel's page slug. Two plain fetches, no login, no API key. Wrapped as
`resolve_manager(imo)` in `refresh_flags.py`; the daily workflow runs it for
every IMO planned at Gijón and Avilés (ShipNext + Avilés PA CSV, cp1252-safe)
that has no manager on file, writing `verified: false, source:
magicport-auto`. Politeness cap 40/run, 2 s pacing. The page's own IMO is
checked against the query — a name collision in search results is refused
rather than mis-attributed.

**Validation:** 3/3 hand-verified entries (BBC BAHRAIN, PEAK BELFAST, GCL
PRAIA MOLE) reproduced exactly. Of the first 5 new vessels resolved, 3 would
have gone to the wrong company by name-guessing: GCL KRISHNA → Anglo-Eastern
(its sister GCL PRAIA MOLE is Kobe); NORD PLATINUM → Donnelly Tanker
Management (not Norden); COMBI DOCK I → HG Dry (Harren Group).

### 2. Contacts propagate between sister vessels
Managers recur across ships far more than ships recur. `propagate_contacts()`
copies email / contact / phone / notes from the freshest entry under the
same ISM company into siblings whose fields are empty — never overwriting.
Company matching folds legal-form suffixes and diacritics, because MagicPort
writes `VERTOM BEREEDERUNGS GMBH` where a human wrote `Vertom Bereederungs
GmbH & Co. KG`, and `GRONBERG` for `Grönberg`; the first attempt matched 0
until this was fixed. Live result: BBC BRISBANE inherited Briese's contact,
VERTOM ANETTE inherited Vertom's Group QHSE Manager. Only genuinely new
companies need a human.

### 3. Today's six, filled by hand
| Vessel | ISM manager | Contact |
|---|---|---|
| COMBI DOCK I | HG Dry (Harren Group) | **Capt. Jacek Hausler, Director QHSE & DPA**, `dpa@harren-group.com` |
| BBC BRISBANE | Briese Heavylift | inherited `info@briese.de` |
| GCL KRISHNA | Anglo-Eastern | HQ phone only; site hides emails |
| NORD PLATINUM | Donnelly Tanker Mgmt (Hartmann Group) | `mail@donnellytanker.com.cy` (directory) |
| RUMA | Ership SAU | `adm.mad@ership.com` (directory) — **has a Gijón delegation** |
| GAS AEGEAN | Benelux Overseas | `info@benelux-ship.com` (verified) |
| HERBEIRA | Navigasa (A Coruña) | `navigasa@navigasa.com` (directory) |

FRANCISCO DE PAULA NAVARRO (9098581) added as an explicit non-target — a
30 m IEO research vessel — so the dashboard stops asking for a manager.

### 4. UI: known manager, no email
The card now offers one-click "find contact" and "LinkedIn" searches for the
company, so the only manual step left is one click and a paste.

### 5. `.github/workflows/keep-alive.yml`
Hits `/api/ping` every 5 min from GitHub so the Render free instance does not
spin down; the dashboard's own ping (B-014) only runs while a tab is open.
GitHub's scheduler drifts, so this is "almost always awake"; Render Starter
is the hard fix. Side effect: the in-memory DB (B-104) survives, so Runs /
History accumulate.

### 6. `tests/` — headless suites now live in the repo
The 34-test manager-inquiry suite existed only in a scratch directory and was
lost between sessions. Both suites (`test_manager_inquiry.js`,
`test_ports_b106.js`) plus `extract.py` and `run.sh` are now committed.
`tests/run.sh` = py_compile + node --check + both suites. 38/38 + 12/12.

### Verified
- `resolve_manager`: 3/3 controls exact; 8/8 new IMOs resolved; research
  vessel correctly not found.
- Company matching: 8/8 cases incl. suffix and diacritic differences and
  three deliberate non-matches (Kobe Shipmanagement ≠ Kobe Shipping, Star
  Bulk Hellas ≠ Starbulk SA).
- Clean boot on 3.14.0, 29 managers; all four of today's new vessels render
  complete cards from real data.

## v3.13.1 — Workflow run #1 was inconclusive; made every run self-diagnosing
Run #1 (13 Sep, `workflow_dispatch`) went green in 27 s and pushed nothing.
Green here means only "the script exited 0": the seed had been refreshed by
hand that morning, so `to resolve: 0` and VesselFinder was never exercised.
Worse, the existing "harvested" lines cannot settle it either — a bot-block
page comes back HTTP 200 with HTML and simply parses to zero rows.

Added `probe_vesselfinder()`: fetches a known vessel (FURNESS VICTORIA
9640621) and prints exactly one of
`VESSELFINDER REACHABILITY: OK | BLOCKED | FAILED | UNEXPECTED` at the top of
every run, and the end-of-run summary says plainly when flags could not be
resolved. Verified from a residential IP: `OK (9640621 -> PA as expected)`.

Also bumped `actions/checkout` v4→v5 and `actions/setup-python` v5→v6 to
clear the "Node.js 20 is deprecated" annotation before it becomes a failure.

**Resolved by run #2 (13 Sep 2026, 14:5x UTC):**
`VESSELFINDER REACHABILITY: OK (9640621 -> PA as expected)` — **GitHub's
runner IPs are not blocked.** The daily flags refresh will work. Same run:
managers pull `live 20 | repo 20 | merged 0`, ShipNext 77 planned / 77 known /
0 to resolve (seed had been hand-refreshed that morning). The legacy
VesselFinder port-page harvest reported `Marín FAILED (HTTPError)`; those
listings have been paywalled since v3.9.0 and the step contributes nothing
either way — left in place, noted here.

The standing operational note repeated in v3.8.0, v3.10.3 and v3.12.2 —
"the seed still requires a periodic manual `refresh_flags.py` run" — no
longer applies.

## v3.13.0 — Daily automated seed refresh + manager directory for Gijón/Avilés
Two things that were "next" for the whole life of the project, done.

### 1. `.github/workflows/refresh-seeds.yml` — daily, 05:00 UTC, plus a manual button
Closes the operational gap first described in HANDOFF §4 and hit again in
B-025 and v3.12.2 (94% -> 50% coverage in four days). Steps:
1. **Pull dashboard-saved managers from the live server first** (`refresh_flags.py
   --live URL` -> `GET /api/managers`, merged newest-`updated`-wins) — see B-109.
2. Run `refresh_flags.py` — VesselFinder from GitHub's runner IP, not Render's.
3. Sanity-check both seeds (7-digit keys, 2-letter flags, non-empty ISM,
   `flags.json` ≥ 100 entries) and **refuse to commit** if anything is off.
4. Commit + push only if a seed changed -> Render redeploys with current seeds.

`permissions: contents: write`, no secrets. Concurrency-guarded so two runs
never race. **Known risk, unproven until the first run:** nobody has shown
VesselFinder accepts GitHub's IPs. If it does not, the flags step resolves 0
and says so; the managers step still works. The first `workflow_dispatch`
run is the test.

Merge logic verified in four cases against the real live server and a
stubbed one: identical (0 merged), newer live entry wins, new entry added,
junk keys (`bad`, entry without `ism`) rejected, older live entry ignored.

### 2. B-109 — managers saved through the dashboard were being lost
`save_managers()` writes `managers.json` on Render's disk, which is ephemeral
and wiped by every deploy. So anything entered via **Save manager** on the
live site survived only until the next push — including every push this
workflow makes. The v3.12.0 seed entry survived only because it was
committed by hand. Fixed by step 1 above: the live directory is pulled and
committed before any push. Race window: an entry saved between the 05:00
pull and the redeploy a minute later is lost; documented, tolerated.

`save_manager()` now also preserves fields it does not own (`phone`,
`notes`) so a re-save from the UI cannot wipe research done offline.
Verified live: re-saving 9440253 through `/api/savemanager` kept both.

### 3. `managers.json` — every vessel currently calling Gijón and Avilés
20 vessels researched (1 -> 20 entries). Method per vessel: MagicPort's
vessel page for the ISM manager (the only free source that states the DOC
holder as a distinct field), then the company's own site for contacts.
`verified: true` only where the ISM identity came from MagicPort's vessel
page or the company's own fleet list; 17/20. 14 have an email, 7 a named
DPA/QHSE contact for the salutation, 6 are phone/contact-form only.

Why the method matters — three of the 20 would have gone to the wrong
company from a tracker's "manager" field:
| Vessel | Tracker says | DOC holder actually |
|---|---|---|
| PEAK BELFAST | Peak Project Carriers (Norway) | **Grönberg Ship Management BV** (Delfzijl) |
| GCL PRAIA MOLE | (nothing useful) | **Kobe Shipmanagement Co Ltd** — not "GCL" |
| FURNESS VICTORIA | Fukunaga Kaiun (owner) | **Viridian Maritime** (v3.12.0) |

Best-case contacts found: Navibulgar `head-sepqm@navbul.com` (Manager
DPA/MR/CSO), Wijnne & Barends `qhsse@` ("ISO and ISM related issues, audits,
flag state, port state" — their words), Arklow `technical@asl.ie` with John
Conlon named as Marine Superintendent/DPA, Naviera Murueta's DPA named on
their contacts page, Vertom's Group QHSE Manager by name and direct line,
Wilson's SHEQ Manager, Director Ship Management and Technical Manager all
with direct emails. Worst case: Japanese and Chinese managers (Misuga, COSCO
Asphalt) and the big Greek/US listed owners (Star Bulk, Diana, Safe Bulkers,
Genco) publish phone numbers or contact forms only.

Out of scope: FRANCISCO DE PAULA NAVARRO (9098581) is a 30 m Spanish
government research vessel, not a commercial target. Left out of the
directory deliberately so it keeps prompting as unknown rather than
carrying a fake manager.

Two entries are `verified: false` and say so in their notes: AVILA (vessel ->
Tom Wörden link is from a tracker; the company itself is an ISM manager and
published a named DPA) and EEMS DOLLARD (Amasus, from a tracker summary).

### Verified
- 34/34 manager suite, 12/12 B-106 suite, clean boot on 3.13.0 with 20
  managers loaded; modal renders "Dear Mr Conlon," with the DPA note and
  Wilson's phone from real directory data; the research vessel still prompts
  as unknown.
- Workflow file structure checked; the sanity-check step run locally against
  the committed seeds: 258 flags / 20 managers, 0 malformed.

## v3.12.2 — Blank flags: stale seed + cp1252 decode bug + emoji for non-tracked flags
Reported as "a lot of vessels without flag identified" the day after the
`🌐 All flags` toggle shipped. Three distinct causes; only one was "unknown".

### 1. Seed staleness (most of it) — operational, B-025 pattern
`flags.json` covered 94% of planned ShipNext IMOs on 9 Sep and **50% (39 of
77 missing) on 13 Sep**. ShipNext's planned lists roll forward every few
days; the seed does not. Ran `refresh_flags.py` from a residential IP:
**39/39 resolved, seed 219 -> 258**, 0 changed, 0 lost.

**12 of the 39 were on tracked flags** (MT 5, LR 3, MH 4) — e.g. FU ZHOU
WAN (MT), DSI PYXIS (MH), SEAHORSE (MH), SONGA PANTHER (LR), CONTSHIP SKY
(LR). Under the default filter these vessels were absent from the dashboard
entirely. A stale seed is not a cosmetic problem; it hides inspectable
ships. Tracked total 53 -> 65.

Four days from 94% to 50% means a weekly manual run is not enough. The
scheduled GitHub Action (HANDOFF §4, still unbuilt) is the durable fix.

### 2. B-107 — Avilés CSV decoded as UTF-8, served as cp1252 (code)
`_pa_rows()` decoded with `utf-8, errors="replace"`. The Avilés feed sends
`ESPA\xd1A` (cp1252), so every accented flag name became `ESPA\ufffdA`,
`es_flag()` never matched, and **every Spanish-flagged vessel at Avilés
came out with a blank flag code** (3 rows on the day). Accented vessel
names corrupted the same way. Present since v3.9.0; invisible until All
flags made ES rows visible. Fix: strict UTF-8, cp1252 fallback on
`UnicodeDecodeError`. Vilagarcía goes through the same helper and is
covered if it ever does the same.

### 3. B-108 — resolved flags rendered as unresolved (code)
`flagEmoji()` knew only the four tracked flags and returned 🏳️ for every
other code, so a resolved `PA` / `CY` / `AG` looked identical to a missing
flag. Never visible before All flags. Fix: derive the emoji from the ISO
code (regional-indicator pair); unchanged for the tracked four; still 🏳️
for empty / `??` / malformed.

### Verified
- Live Avilés through the real code path: 12 rows, 0 U+FFFD, all 3
  Spanish rows `flagName='España' flagCode='ES'`, 0 rows with a name but
  no code.
- Emoji: 13 cases — the tracked four, PA/CY/AG/ES, and empty/undefined/
  `??`/3-letter/lowercase all correct.
- Seed diff validated: +39, 0 changed, 0 lost, 0 malformed entries.
- Clean boot on 3.12.2, `/api/ping` reports 258 flags.

## v3.12.1 — Empty port selection no longer kills the dashboard (B-106)
Reported as "showing 0 vessels at all, no searching" on the live deployment
the day after v3.12.0 shipped. Not a regression — v3.12.0 touches nothing
in port selection — but it surfaced now and it was a real defect.

### Root cause
The port picker has a red **None** button (`S.ports=[]`), and region buttons
that *deselect* a region when it is already fully selected. Either path can
leave zero ports selected. That state is then persisted to `localStorage`
(`fsi13_p = "[]"`) and restored on every reload, where `lsMig()` treats the
truthy string `"[]"` as a valid saved value rather than falling back to the
default. `fetchAll()` then filters `PORTS` down to nothing, builds zero
jobs, and returns — no loading bar, no requests, no error panel. `render()`
shows "No vessels match.", which reads as a data problem. The only clue was
`PORTS (0)` in the picker header.

Diagnosed by elimination: the live server was healthy (every endpoint
returned data, and in a clean browser the page showed 176 vessels), but its
`meta.runs` was 0 — the user's browser had loaded the page and never sent a
single data request. Reproduced headlessly with `fsi13_p="[]"`: 0 fetches.

### Fix
- **Heal at page load only.** If the saved selection is empty when the page
  opens, restore all 12 ports, persist, and log "No ports were selected —
  restored all 12". Not mid-session: after clicking None to pick a subset
  the user must not be fought.
- **Never silent.** `fetchAll()` with zero ports now logs "No ports selected
  — open + Add Ports and choose ports, or All", clears the loading state,
  rebuilds the table (dropping stale live rows), and returns. The empty
  table says the same instead of "No vessels match."
- **None** stays — it is the right way to pick two or three ports.

Also repaired the module docstring, which had been silently corrupted by
successive global version bumps into "v3.11.0 fixes all 19 audited weak
points. See PLAN-v3.11.0.md" — a file that does not exist; the hardening
was v3.8.0. Rewritten to list the actual sources with no version-pinned
sentence to rot again.

### Verified
- 12/12 headless (node, stubbed DOM + localStorage): load with `[]` restores
  12 ports and persists them, 14 fetches issued, restore message survives
  `fetchAll`'s log reset, rows render; mid-session None does not
  auto-restore, Refresh with 0 ports issues no fetches and leaves no stuck
  spinner, status line and table both explain; picking Vigo resumes fetching.
- Regression: 34/34 manager-inquiry suite, normal 12-port load issues 16
  fetches with no exception, all-flags state renders.
- One assertion initially failed and exposed a real gap: the early return
  skipped `buildCombined()`, so stale live rows outlived the port
  deselection. Fixed.

## v3.12.0 — ISM manager inquiry + manager directory
Requested feature: send service proposals (pre-PSC inspection / ISM internal
audit) to the **managers** of vessels calling at the covered ports, alongside
the existing inspection requests to flag administrations.

### Root cause of the hard part: manager identity cannot be automated
The obvious design — resolve IMO -> ISM manager server-side — does not work,
and the reason is worth recording because it looks solvable and is not.

**Free trackers publish the beneficial owner and label it "manager".** Live
test on FURNESS VICTORIA (9640621): MarineTraffic and others report
`FUKUNAGA KAIUN KK`, and Fukunaga's own site corroborates it — they had her
built at Kawasaki in 2012 and list her in their fleet. All true, and all the
wrong company. The real chain is:

| Role | Company |
|---|---|
| Beneficial owner / had her built | Fukunaga Kaiun (Japan) |
| Registered owner | East Blue Line SA (Panama SPV) |
| **ISM manager** (DOC holder, has the DPA) | Viridian Maritime Pte Ltd (Singapore) |

Only the ISM manager holds the DOC and employs the DPA, so only the ISM
manager is a valid recipient. Sending to the beneficial owner reaches a
company with no safety-management role in the ship.

**The ISM-manager field is a paid data product industry-wide.** Verified by
probing: vesseltracker renders `ISM Manager Name / Email / Phone / Website`
as distinct fields and blanks every one without a subscription; ClassNK's
register returns 403; marinevesseltraffic's owner/manager/ISM page returns
403; balticshipping serves no company data at all. Equasis is the free
exception and is login-gated — same wall as VesselFinder (B-100) and Gijón
(v3.10.0). MagicPort does expose the ISM-manager role and is reachable, but
is a single unconfirmed source.

**Consequence:** manager identity is hand-entered, once per vessel, and kept
forever. Since managers recur across ships far more than ships recur,
coverage compounds — the tenth vessel under a known manager costs nothing.
This is the same shape as the `flags.json` seed: a committed cache that
exists because the automatic path is blocked.

### Search procedure that actually works (2 queries)
Recorded because the first attempt wasted a dozen calls on vague queries and
paywalled fetches:
1. `<vessel name> ISM manager` — the exact field name; routes to MagicPort /
   the Google overview, which return the ISM company rather than the owner.
2. `<company> contact` — the company's own site for the address.

Built into the UI: a vessel with no manager on file shows both prefilled
links plus the Equasis deep link, so the lookup is two clicks and the answer
is stored permanently.

### Realistic contact target
Named DPAs are rarely published. Viridian Maritime lists only
`enquiries@viridianmaritime.com` (verified on their own site); Fukunaga
publishes only a contact form. A monitored role address is the practical
target and is more durable than a named person — it survives staff changes.

### Scope: all flags, not the tracked four
Manager inquiries are commercial work and are not limited to flags under
which FSI authority is held. `getF()` already skipped flag filtering when
`S.flags` is empty, but nothing surfaced that — a `🌐 All flags` toggle now
does. Measured live: 93 vessels across the 9 ShipNext ports, of which only
22 are MT/LR/MH/HK. **71 vessels (76%) were previously unreachable.**

### Conflict of interest — handled, not designed away
Soliciting audit work from managers of ships that may later be inspected
under held flag authority is a real conflict (raised in HANDOFF §8 and never
resolved). It applies only to MT/LR/MH/HK; for other flags no authority
exists and there is no conflict. The tool now records every approach in an
outreach log with `conflict: true` on vessels under held authority, and the
inquiry modal warns before sending. The log is a memory aid so a later
inspection assignment can be recognised and declared — it does not decide
anything.

### Added
- `managers.json` — committed seed, IMO -> `{ism, ismEmail, contact, owner,
  source, verified, updated}`. Atomic write, boot-loaded, survives restarts.
  `verified` separates "read off Equasis" from "inferred from an aggregator";
  the UI renders unverified entries in amber so a guess is never mistaken
  for a fact.
- `outreach.json` — recusal log (gitignored; runtime state).
- `GET /api/savemanager` — validated (`^\d{7}$` IMO, RFC-ish email, company
  name 2-90 chars, markup stripped), no CORS, mirroring `/api/saveflag`.
- `GET /api/managers`, `GET /api/outreach` — read-only.
- `GET /api/logoutreach` — appends one approach, no CORS.
- Frontend: `🏢 Manager Inquiry` button, manager-grouped modal, `🌐 All flags`
  toggle, per-vessel save form with lookup links.

### Verified
- 34/34 headless JS tests (`node`, stubbed DOM): ETA -> "18 September" incl.
  Jan/Dec boundaries and invalid input, singular/plural body ("while she's" vs
  "while they are"), salutation with and without a named contact, multi-vessel
  grouping, subject lines, conflict warnings naming the LR and MT vessels but
  not the PA one, mailto construction, save-form rendering.
- Live endpoint tests: valid save persists to disk and survives reload;
  malformed email, 2-digit IMO and empty company all rejected **without
  corrupting the existing entry**; outreach log sets `conflict` true for LR
  and false for PA; `/api/health` reports 9/9 ShipNext ports, 219 flags,
  managers cached.
- Dashboard served and confirmed to contain the new controls (37.3 KB).

### Known limitation
The seeded `managers.json` entry for 9640621 is marked `verified: false` —
the Viridian link comes from MagicPort and the Google overview, and could not
be independently confirmed without an Equasis login. Confirm in Equasis and
re-save to clear the flag.

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

