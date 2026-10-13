# NHL Blender — automated full-slate analysis and audit

## Start the app

- **Windows:** double-click `start_windows.bat`
- **macOS/Linux:** run `./start_unix.sh`

Or start manually:
```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Scheduled/command-line run
```bash
python run_daily.py --date 2026-10-12 --mode projected --history 8
python run_daily.py --date 2026-10-12 --mode confirmed --history 8
```

## Included automated work
- Fetches the NHL schedule for the selected date and processes every listed game.
- Fetches landing, boxscore, and play-by-play payloads for each game.
- Retains the available complete skater pool; when the game boxscore has not populated yet, falls back to the official current team roster instead of returning an empty slate. Does not pre-filter to stars, chalk, or PP1.
- Retrieves recent completed team games and their play-by-play, then builds per-player shot/goal history and goalie shot-type / goals-against samples.
- Matches shooter player IDs to opposing goalie IDs only when the same historical event feed contains both IDs. A Main path requires a source-explicitly-marked starter plus a direct goal and shared damage lane; a listed backup cannot inherit the starter label.
- Runs and records the complete active gate sequence, exposing gate evidence, limitations, data errors, player route history, goalie shot-type/zone outcomes, exact direct matchup records, and JSON/CSV exports.
- Keeps projected and confirmed passes separate. The included GitHub Actions workflow supports daily automated JSON runs.
- Includes retry handling for transient NHL API errors and a categorical path board that compares player goal-shot types/zones with observed opposing-goalie goals allowed by shot type/zone. Each player receives an individual ordered gate trace. G10.5 exposes recorded finishers separately from recorded facilitators using event IDs; G14–G17 expose categorical path and contradiction findings without numeric weights.

## Evidence integrity

This is an analysis/audit workflow, not a prediction engine. It does not force a winner, invent a numeric prediction score, use odds as a shortcut, or fabricate player/evidence values. Missing data stays pending. Official line/PP assignments, injuries, confirmed starters, market data, and full environment/rest/travel context are shown only when supported by source data; otherwise they remain unresolved.

## API
Uses NHL public Web API endpoints for schedule, gamecenter landing, boxscore, play-by-play, and club-schedule-season. The NHL may change payload schemas; failures are recorded in the report. Not affiliated with the NHL.
