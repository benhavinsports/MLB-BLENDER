# MLB Blender v97 PDF Feed Actual Fix

Fixes the uploaded PDF path:
- Rebuilt feeder.py to actually parse PDFs/tables/text into player rows + metrics.
- Feeder audit + parsed preview included.
- Rebuilt engine so weak/incomplete data does not blank the whole run.
- Owners/tickets commit after run.
- Duplicate Streamlit keys fixed with unique key prefixes.
- Team-color cards preserved; only score >= 78 flashes.
- Live slate is marked as context only unless metrics exist.


# v98 Godmode PDF Ingestion

Includes the required 1–5:
1. Multi-layer OCR/extraction fallback: pypdf, pdfplumber, PyMuPDF, optional pytesseract OCR.
2. Semantic table reconstruction: detects headers and maps them into Blender schema.
3. Cross-page context memory: carries team/game/pitcher/page context across pages.
4. Adaptive schema detection: detects player column and metric aliases.
5. Confidence + recovery layer: ingestion_confidence + needs_recovery; weak rows stay alive for capped audit instead of blanking.


# v99 Fast PDF No-Hang Patch

Fixes the freeze on `Reading feed...`:
- OCR is no longer run during normal upload.
- PDF extraction is staged and page-capped.
- pypdf runs first.
- pdfplumber table/text runs second with caps.
- PyMuPDF text runs only if needed.
- OCR is skipped by default to prevent Streamlit Cloud lockups.
- Parsed rows capped to prevent UI render crashes.


# v100 Row Anchor Fix
- Team names are hard-rejected as player names.
- Player anchor uses last valid human name before metrics.
- Matchup/team header rows are no longer promoted into tickets.
- 0-score malformed parse rows stay in audit, not Core 3.


# v101 PDF Rebuild Not Block
This version does NOT just block bad rows.
It rebuilds broken sportsbook PDF rows:
- team/header rows are used as context
- player-only rows become pending anchors
- metric-only rows are stitched back to the pending player
- joined player+metric rows use the last valid player anchor before numbers
- parse_note and raw_line_no are exposed for audit

# v104 StarTool Sequential Parser
Directly parses pypdf text where name and handedness split onto separate lines. Daily-run mode: upload the slate PDF for whatever date you are running. No date-specific feed is bundled.


# v105 Public Blender Unblocked
Public Blender no longer runs 30/32 slate-context rows through the engine.
It now:
- loads MLB schedule/pitchers
- pulls active roster hitters from MLB Stats API
- pulls public season hitting stats per hitter
- creates public proxy metrics: HR/PA, HPI, DMG, pull/sweet/barrel/hard proxies
- attaches opponent pitcher/game context
- runs the same 0–19 gate engine
Important: public mode is PUBLIC PROXY MODE. Uploaded StarTool PDF remains strongest/cleanest mode.


# v106 Ticket Structure Lock
Fixes official ticket structure:
- CORE 3 must be 1 Primary + 1 Adjacent/Transfer + 1 WHO/Chaos.
- Adjacent ticket requires 10.5 Adjacent: PASS.
- Chaos ticket requires 11 WHO/Chaos: PASS.
- Soft/weak gate players cannot enter that bucket.
- Recovery/Data-Recovery players stay in Game Board only, not official tickets.
- ALT 3 uses clean pass candidates only.


# v107 Blender Visual + Compact Game Board UI
- Main tab is now Blender Visual cockpit + upload/run area.
- Tab order: Blender Visual → Tickets → Game Board.
- Game Board is compact/table oriented to reduce scrolling.
- Full gate paths moved into expandable audit section.
- v106 ticket structure lock is preserved.


# v108 True Visual Game Board Layout
- Main Blender Visual page no longer stacks Tickets/Game Board underneath it.
- Main page is cockpit + upload/run/current feed only.
- Tickets tab remains tickets only.
- Game Board tab is now square/card game-board style, not a spreadsheet first.
- Spreadsheet/audit view is moved into an expander.
- Ticket card metric overflow fixed with rounded values.


# v109 Today Test Run Ready
Merged final requests:
- Main page is only Blender Visual cockpit + upload/run/current feed.
- Tickets tab only.
- Game Board tab is square/card board, not spreadsheet-first.
- Core 3 = 1 Primary + 1 Adjacent/Transfer + 1 WHO/Chaos.
- Alt 3 remains intact.
- Chaos 3 requires WHO/Chaos PASS.
- Recovery/soft-gate players cannot leak into official tickets.
- v105 public hitter proxy and v104 PDF StarTool parser remain included.


# v110 Game Count Dedupe Fix
- Canonical game_key now uses team + opposing pitcher for StarTool attack rows.
- Dedupes repeated player/team/pitcher rows after PDF/public merge.
- Owners are enforced one per canonical game_key.
- Current Feed uses actual_game_count().
- Fixes inflated 26-game count when today should be 16.


# v111 True Slate Game Count Fix
Fixes the remaining 26-games display issue:
- StarTool PDFs have "attack pools" (team vs opposing pitcher), not full games.
- Current Feed now separates:
  - Slate Games = true MLB schedule count from public slate
  - Attack Pools = parsed PDF team/pitcher targets
- Uploading a PDF auto-loads public slate context for true game count.
- Run messages now say slate games + attack pools separately.


# v112 Attack Pool Cockpit Fix
- Cockpit no longer labels attack pools as "Games".
- Cockpit now shows: Players Read, Slate Games, Attack Pools, Owners, Core Legs.
- Reset button now clears state and immediately reruns.
- Run message says owners from attack pools, with slate games separate.


# v113 True Game Board Grid
- Game Board is now a real board: one square tile per attack pool/game key.
- Each tile shows owner, team vs pitcher, score, and lane statuses:
  - Primary PASS/CUT
  - Adjacent PASS/CUT
  - WHO PASS/CUT
- Full spreadsheet audit remains tucked inside an expander.


# v114 Unique Ticket Buckets + No Code Leak
- A player can appear in only ONE official bucket:
  1. Core first
  2. ALT second
  3. Chaos third
- Prevents examples like Buxton / James Wood showing in both ALT and WHO/Chaos.
- Internal duplicate player rows are removed from each ticket bucket.
- Raw Python/Streamlit traceback/code no longer displays on run page.
- Errors are hidden behind the existing Last Error expander only.


# v115 PDF Truth + Bucket Assignment
Fixes the user's latest issues:
- PDF player/team/pitcher rows are now authoritative.
- Public slate/context cannot overwrite or mix PDF players/teams/pitchers.
- Uploaded PDF display is always Team vs Pitcher from the PDF.
- Ticket duplicate fix is assignment/refill, not blocking:
  Core first, ALT next, Chaos next; no duplicate player across buckets.
- Blender picks are not silently removed just because a duplicate appeared in another bucket.


# v116 Run Button Reads Upload Fix
- Fixes uploaded PDF visible but RUN says "No usable feed rows loaded yet."
- RUN BLENDER NOW now parses the uploaded PDF immediately if feed_df is empty.
- PDF remains source of truth.
- v115 bucket assignment preserved.


# v117 Player / Team Integrity Guard
- Adds pre-score player/team sanity guard.
- Prevents impossible output like Byron Buxton on Kansas City.
- Known correction map locks common players to current MLB team.
- Rebuilds display game after correction so cards show Player's team vs pitcher.
- Applies guard to feed, owners, Core, ALT, Chaos, and Game Board outputs.
- Does not change hitter metrics from the PDF.


# v119 REAL Event Isolation Engine
This build actually changes ranking and rebuilds tickets after event isolation.
Visible output columns in result data include: pre_event_score, conversion_dna, adjacent_transfer_score, chaos_recipient_score, mistake_pitch_recipient_score, pressure_release_score, event_isolation_score, event_note.


# v120 Forced Event Rerank Core
This version forces event isolation as the final scoring layer.

If results do not change after deploying this version, the deployed app is still using cached/old files.

Visible output columns:
- raw_blender_score
- conversion_dna
- adjacent_transfer_score
- chaos_recipient_score
- mistake_pitch_score
- pressure_release_score
- event_isolation_score
- event_note


# v121 No Date-Patched Feed
- Removed bundled May 23 cleaned feed/test CSV.
- App is daily-upload based: upload the PDF for the slate date you are running.
- No hardcoded May 23 player pool is used by the Blender.
- v120 forced event rerank core is preserved.


# v122 Daily Clean Event Engine
Fixes the exact complaint:
- New upload clears yesterday's old results immediately.
- New run clears old results before scoring.
- Event Isolation is the final scoring layer and rebuilds Core/ALT/Chaos.
- Visible event columns are added:
  raw_blender_score, conversion_dna, adjacent_transfer_score, who_chaos_score,
  mistake_pitch_score, pressure_release_score, event_isolation_score, event_note.

# v123 Role-Locked Event Engine
Primary/Adjacent/WHO are separated before ticket build. Stars cannot be labeled WHO by score alone.


# v125 No Stale Results / Daily Only
This fixes yesterday's picks reappearing:
- load_locked_results() now returns empty results only.
- save_locked_results() is disabled.
- old locked/result/cache/history files removed from the package.
- app startup uses empty_results(), not saved old outputs.
- uploading a PDF immediately clears all previous tickets/owners.
- running the Blender clears results before scoring.
- results now only come from the current uploaded PDF/current live feed.

# v126 Fresh Slate Anti-Repeat Layer
- Suppresses recent failed owners unless they pass a strict repeat-exception gate.
- Prevents same star/surface profiles from auto-repeating on the next slate.
- Boosts fresh lower-attention event-owner profiles.
- Same player can still repeat only if today's event evidence is strong.

# v127 Hard Role Lock + Score Caps
Primary/Adjacent/WHO are mutually exclusive. Weak gates cap scores: 1=88, 2=74, 3+=59. No Primary can also be WHO.

---

## v140 / v141 — Board Memory Results Sync + README Preservation

### What changed
- Restored the Game Board/results sync layer without replacing the README structure.
- Engine now writes board-memory fields directly into result frames:
  - `gate_trace_full`
  - `pass_gates`
  - `soft_gates`
  - `cut_gates`
  - `pass_count`
  - `soft_count`
  - `cut_count`
  - `board_lane_label`
- Game Board renderer now has board-game style tile support.
- Universal fallback text like `Clean / pass lane` is replaced by per-player lane memory.
- Each hitter can now show different PASS / SOFT / CUT gate paths.
- Primary / Adjacent / WHO lanes stay separated.
- No hot-bat tuning was added in this version.
- README/version-history format is preserved from the uploaded master README.

### Purpose
This version focuses only on the root issue:
- detailed gate memory was being flattened;
- lane identity was being lost;
- event-path rendering was being replaced by generic fallback text;
- board UI was not showing the same gate-state memory the engine calculated.

### Game Board target behavior
The board should act like a progression path:

`START → Pool → Weak Slot → Adjacent Pressure → WHO Trigger → Finisher → Event Isolation → OWNER`

Each player tile should show:
- PASS gates
- SOFT gates
- CUT gates
- role path
- event owner status
- full gate trace

### Files touched
- `engine.py`
- `ui.py`
- `app.py` version stamp only
- `README.md` appended with this section only



---

## v142 — Clean Production Strengthened

### What changed
- Consolidated the actual runtime files instead of stacking temporary patch blocks.
- Rebuilt `engine.py` as one clean authority for:
  - PDF/feed source of truth
  - real-player filtering
  - repeat rotation/cut
  - Primary / Adjacent / WHO role separation
  - score caps from weak gates
  - Core 3 construction
  - Game Board gate memory
- Strengthened `ui.py` Game Board renderer to read engine-produced gate memory.
- Kept only production files in the package.

### Production files
- `app.py`
- `engine.py`
- `ui.py`
- `feeder.py`
- `ai_oil.py`
- `requirements.txt`
- `README.md`
- `VERSION_HISTORY.md`

### Removed from production package
- proof JSON clutter
- temporary restore notes
- duplicated patch reports
- debug-only artifacts

### Results-system target
- Core 3 = Primary / Adjacent / WHO
- No Primary also being WHO
- Repeat names rotate/cut/refill instead of owning by default
- Game Board shows PASS / SOFT / CUT gates
- No universal `Clean / pass lane` fallback


---

## v143 — Board Renderer + Team Count Fix

### What changed
- Fixed literal `{board_lane_summary(row)}` showing on player cards.
- Added hard override Game Board renderer at bottom of `ui.py` so old renderer cannot leak placeholder text.
- Strengthened feed/result summary counts so dashboard reads:
  - players
  - games
  - teams
  - pitchers
  - attack pools
- Preserved production-file-only structure from v142.

### Purpose
Fix the exact issues shown in screenshot:
- Game Board card printed code text instead of lane summary.
- Dashboard showed players but 0 games / 0 attack pools.

---

## v144 — Ticket Timeframe + SGP Environment Finder

- Added Blender-only ticket filters: Full slate, Early games, Late games, Custom window.
- Ticket Core/Alt/Chaos rebuild from selected window only.
- Added SGP Environment Finder when Blender identifies same-game environment strength.
- No stat-site bias, no hot-bat tuning, no forced SGP.


---

## v145 — Startup Feeder Fix

### What changed
- Fixed startup crash:
  - `app.py` imports `read_feed`
  - `feeder.py` now exposes stable `read_feed(filename, data)`
- This keeps the app starting normally.
- No Blender results logic was changed in this version.

---

## v146 — Startup + Ticket Import Fix

### What changed
- Fixed startup crash from `from feeder import read_feed`.
- Added a stable `read_feed(filename, data)` function in `feeder.py`.
- Added safe app fallback if feeder import fails.
- Ensured `run_ticket_view` is exported from `engine.py`.
- Ensured `ui.py` can access `run_ticket_view`.

### Purpose
Stop the app from crashing on startup and stop the Tickets tab from crashing when the time-window selector is used.


---

## v148 — Correct Clean Runtime
- Replaced feeder.py and engine.py cleanly instead of stacking patch blocks.
- PDF feeds extract hitter rows only.
- Engine creates owners from structured hitter metrics and produces board gate memory.


---

## v149 — Restored Blender Experience
- Restored board-game visual renderer on top of v148 clean engine.
- Game Board tiles now show progression path, PASS/SOFT/CUT chips, and audit table.
- Ticket display restored for Full/Early/Late/Custom + SGP finder.


---

## v150 — Startup Import Restore

### What changed
- Fixed the startup ImportError at `from engine import ...`.
- Added stable compatibility exports in `engine.py`.
- Added a final `__getattr__` safety net for older app/ui imports.
- Did not change v148 feed parsing.
- Did not change v149 visual Game Board renderer.
