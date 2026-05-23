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
Directly parses pypdf text where name and handedness split onto separate lines. Tested on May 23.pdf and exports May_23_cleaned_startool_feed.csv.


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
