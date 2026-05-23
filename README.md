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
