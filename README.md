## v1.26 — empty-slate and date-boundary integrity

- A successful but empty schedule response is no longer misreported as a complete slate retrieval. The run is explicitly marked `NOT VALIDATED`, with no Core output, until the requested date/feed is verified.
- The CLI default date now uses the America/New_York calendar, matching the NHL slate's expected local date rather than UTC near midnight. An explicit `--date YYYY-MM-DD` still takes precedence.
- Added a regression test for empty schedule responses.

## v1.25 — projected-to-confirmed phase comparison

When run with `--mode both`, the CLI now writes a separate `phase_comparison.json` report comparing exact player IDs across the projected and confirmed retrieval passes. It surfaces assignment changes, players missing from either phase, evidence changes, and any unsupported `CONFIRMED` labels. A second pass is explicitly not confirmation; configured projected sources remain labelled as such.

## v1.24 — historical goal context × deployment audit

- For each skater, the report now compares joined historical goal-shift events with exact shared current line / power-play assignment labels where both players have explicit deployment rows.
- The output preserves matched game/event IDs and which assignment label matched. Missing assignment is `UNRESOLVED`; no matches in a retrieved sample are reported separately from missing sample data.
- This is descriptive historical context only. It does not certify a line/PP assignment, prove scoring causality, clear a gate, or force a G18 lock.

## v1.19 — G15/G16 decision integrity

Only the explicit `DISTINCT EVIDENCE ADVANTAGE` result clears G15 and G16. Generic “comparison complete”, equivalent observed evidence, dominated candidates, mixed evidence, or missing decisions remain blockers. Added regression tests for both blocked and clearing cases.

# NHL Blender — automated full-slate analysis and audit

## v1.20 — historical sample integrity

The player-level audit now distinguishes **no historical play-by-play sample retrieved** from **a retrieved sample with zero observed goals**. When the event sample is missing, G4/G10 remain pending and the final blocker identifies the missing sample; the app no longer presents missing data as if it were observed zero production. The report records historical games and play-by-play event counts per player. Regression tests cover both missing-sample and observed-zero cases. Validation: 55 automated tests passed in the build environment.


## v1.18 reliability update

- The Streamlit app and command-line runner use the same retrieval-completeness audit.
- A failed schedule, per-game bundle/deployment step, or required gamecenter feed is preserved in `retrievalAudit`.
- Partial slate retrieval suppresses Core picks and marks the run `NOT VALIDATED`; successful game bundles remain available for investigation rather than being discarded.

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
# One pass
python run_daily.py --date 2026-10-12 --mode projected --history 8

# Separate fresh projected pass followed by separate fresh confirmed pass
python run_daily.py --date 2026-10-12 --mode both --history 8
```

## Optional G8 player-market evidence

The app can retrieve NHL anytime-goal-scorer market outcomes from The Odds API. Configure `ODDS_API_KEY` in the environment where Streamlit/CLI runs, using an account tier that includes NHL player props. For example:

```bash
# macOS/Linux, for this terminal session only
export ODDS_API_KEY="your_api_key_here"
streamlit run app.py

# Windows PowerShell, for this terminal session only
$env:ODDS_API_KEY="your_api_key_here"
streamlit run app.py
```

The app matches the scheduled event by exact home/away team names and joins market outcomes to the player pool by exact normalized full name. Ambiguous events, unsupported plans, missing markets, and unmatched players remain pending. It preserves bookmaker, American price, and market update timestamp. It does not calculate probabilities, rank players by odds, or treat market presence as proof of a scoring path. Without the key or eligible API access, G8 stays pending and no key is stored in the project.

## Included automated work
- Fetches the NHL schedule for the selected date and processes every eligible pregame game. Live, completed, and unknown-state games are excluded from pregame analysis and listed in the report rather than back-solved.
- Fetches landing, boxscore, and play-by-play payloads for each game.
- Retains the available complete skater pool; when the game boxscore has not populated yet, falls back to the official current team roster instead of returning an empty slate. Does not pre-filter to stars, chalk, or PP1.
- Retrieves recent completed team games and their play-by-play, then builds per-player shot/goal history and goalie shot-type / goals-against samples.
- Matches shooter player IDs to opposing goalie IDs only when the same historical event feed contains both IDs. A Main path requires a source-explicitly-marked starter plus a direct goal and shared damage lane; a listed backup cannot inherit the starter label.
- Runs and records the complete active gate sequence, exposing gate evidence, limitations, data errors, player route history, goalie shot-type/zone outcomes, exact direct matchup records, and JSON/CSV exports.
- Keeps projected and confirmed passes separate. The app's **Run projected → confirmed** action and CLI `--mode both` each perform fresh retrievals for the projected pass first and confirmed pass second, and save the two JSON reports separately. The included GitHub Actions workflow supports daily automated JSON runs.
- Includes retry handling for transient NHL API errors and a categorical path board that compares player goal-shot types/zones with observed opposing-goalie goals allowed by shot type/zone. Each player receives an individual ordered gate trace. G10.5 exposes recorded finishers separately from recorded facilitators using event IDs; G14–G17 expose categorical path and contradiction findings without numeric weights.

## Live-data boundary

The official NHL feed remains the schedule, player identity, boxscore, and play-by-play source. If it does not contain projected lines or PP units, the app searches the additional public sources described below and records each attempt. It only attaches rows to player IDs after an exact normalized full-name join to the official roster. Projected lines never become confirmed lines merely because the user selected the Confirmed pass. Source data may be unavailable or change format; when that happens, G2/G6 remain unresolved and the source audit shows why. G6 cannot be completed from historical TOI alone, and final path certification remains withheld until comparative finisher and contradiction checks are supported.

## Evidence integrity

This is an analysis/audit workflow, not a prediction engine. It does not force a winner, invent a numeric prediction score, use odds as a shortcut, or fabricate player/evidence values. Missing data stays pending. Official line/PP assignments, injuries, confirmed starters, market data, and full environment/rest/travel context are shown only when supported by source data; otherwise they remain unresolved.

## API
Uses NHL public Web API endpoints for schedule, gamecenter landing, boxscore, play-by-play, and club-schedule-season. The NHL may change payload schemas; failures are recorded in the report. Not affiliated with the NHL.


## Line / power-play source fallback (v4)

When the official NHL game payload does not contain projected line or power-play deployment, the app now searches additional public sources instead of stopping at the roster: (1) Hockey Insights' published lineup snapshot (its source notes credit PuckPedia first, Daily Faceoff second, and same-day NHL.com third), (2) the current NHL.com projected-lineup article, then (3) Daily Faceoff's team line-combinations page. Source attempts, errors, freshness/date where available, unmatched names, and exact roster-ID join counts are saved in the run report and displayed in **Deployment source audit**.

Important distinctions: an article that only publishes even-strength lines does not establish PP1/PP2; no PP unit is inferred. Exact normalized full-name matching to the official NHL roster is required before attaching deployment to a player ID. Projected-source rows remain labelled `PROJECTED` even in a Confirmed pass; they cannot masquerade as confirmation. If all sources fail or the schema changes, the app reports that search result as unresolved rather than converting missing data to a negative finding.


## General web-search fallback (v1.5)

If the first three lineup sources do not establish both a forward-line assignment and a PP unit, the deployment layer searches DuckDuckGo and Bing for the club's projected combinations and power-play units. Search snippets are discovery only. Both search indexes are attempted when parseable coverage is limited. Candidate pages are opened and accepted only when structured page data contains explicit line/PP assignments; a headline or snippet never becomes player-level evidence. Candidate URLs and parsing outcomes are retained in the source audit. Exact normalized full-name joins to official roster IDs remain mandatory, conflicting assignments remain unresolved, and projected rows never become confirmed rows.


## Core output enforcement (v1.7)

The report now includes `coreOutput`. Only a player whose path disposition is explicitly `LOCKED — ...` and whose final candidate gate is explicitly `LOCKED...` can enter the output. A Core 3 requires exactly three such survivors from distinct games; a two-game slate can return Core 2 only when both games produce one lock each. The app will not fill missing slots with unresolved players. If more than three game-level locks exist, the run reports cross-game competition as unresolved rather than silently choosing the first three. This enforces output integrity; it does not manufacture missing gate evidence or make the current evidence pipeline fully validated.

## Per-player G18 blocker audit (v1.8)

Each candidate now carries `gateBlockers`, `gateBlockerCount`, `g18Eligible`, and `g18Decision`. The run-level `gateBlockerSummary` groups missing requirements by gate. This is an actionable diagnostic, not a scoring system: a populated trace cannot become a lock just because the code reached G18. Confirmed mode requires an explicit confirmed deployment status, and unresolved finisher/candidate/contradiction audits remain blockers.


## G17 source contradiction audit (v1.10)

The structural audit now separately reports conflicting line/PP assignments for the same exact player ID, duplicate deployment records, multiple goalies explicitly marked as starters for one team, duplicate current-roster IDs, and retrieval errors. Conflicts are preserved as findings; the app does not choose a source by order or treat the absence of a conflict as proof that tactical review is complete.


## G18 blocker integrity (v1.11)

G18 now explicitly carries unresolved G8 market-fingerprint evidence and G9 player-specific environment splits as blockers; team rest/venue context alone cannot pass the player-environment gate. G17 blocker handling also includes conflicting deployment assignments, duplicate deployment records, multiple marked starters, and source retrieval errors. These are conservative integrity controls, not evidence that a player is a pick.


## CLI retrieval fault isolation (v1.12)

The daily CLI now isolates failures per game and writes `retrievalAudit` into each report. A schedule-fetch failure or any failed game/deployment bundle marks the slate `NOT VALIDATED — SOURCE RETRIEVAL INCOMPLETE` and clears Core output rather than allowing a partial slate to appear complete. Successful game bundles can still be inspected in the same report. The script is import-safe for tests, and `pytest.ini` makes both `pytest` and `python -m pytest` resolve the project modules consistently.


## Official game-specific roster evidence (v1.13)

The deployment audit now separately surfaces the official NHL Gamecenter boxscore's game-specific player rows, explicit goalie-starter markers, and scratches when those fields are present. This is deliberately not treated as proof of forward-line or power-play deployment: both remain false unless a dedicated source explicitly establishes them. If the boxscore has not populated its game-specific roster yet, the report says it is unavailable rather than interpreting that absence as a scratch or inactive status.


## v1.14 — Player-specific environment evidence

G9 now includes each skater’s historical home/away game counts, shots on goal, goals, and per-game rates, joined by official game IDs and NHL play-by-play. G9 remains pending unless both home and away samples exist. This is descriptive evidence only: no invented cutoff, weighting, or causal claim is used. G8 remains blocked because player-level market-fingerprint evidence is still not implemented.


## v1.16 — G8 market source integrity

Player-level anytime-goal market rows now need both a numeric non-zero American price and a parseable provider update timestamp to count as usable G8 evidence. The report records the latest update timestamp and age in seconds, but does not invent a stale-data threshold. Missing or malformed timestamp/price pairs remain blockers; market presence is not a pick or a probability estimate. The market audit table also displays per-player source-field integrity and the latest provider-update age where valid timestamps exist.


## v1.17 — official slate endpoint fallback

The slate loader now attempts three official NHL routes in order: `schedule/{date}`, `score/{date}`, and `schedule-calendar/{date}`. It filters records to the requested date, deduplicates game IDs, and preserves retrieval errors. If all three routes fail, it raises an explicit `NHLDataError` so the CLI records an incomplete source retrieval instead of treating a DNS/HTTP outage as a legitimate zero-game slate.

Regression coverage includes scoreboard fallback after schedule failure, schedule-calendar fallback after an empty preferred response, and an explicit error when all three endpoints fail. This does not solve the environment's external network restrictions or certify a Core 3; it makes the application safer when one official endpoint is unavailable.

## v1.21 — historical shift-chart evidence

The engine now retrieves up to the three most recent completed-game shift charts per team from the NHL Stats API and exposes player-level shift counts and observed shift duration by game. Each team retains the source URL, retrieval timestamp, row count, and any retrieval error in `historicalByTeam.shiftChartAudit`. This is historical deployment context only: it does not infer a player's line, PP unit, or confirmed role for the upcoming game. If the feed is missing or unparseable, the audit says unavailable rather than interpreting it as zero usage. The G6 audit now surfaces shift-chart coverage while preserving the rule that current line/PP evidence is still required for opportunity/access. Five regression tests cover parsing, summaries, and source failure handling.


## v1.22 — historical teammate overlap

The shift-chart audit now derives pairwise teammate overlap from observed shift intervals, grouped by game and period. Player records expose `historicalShiftOverlap`; team-level records expose `historicalByTeam[team].historicalShiftOverlap`. Pair summaries include observed games, overlap seconds, and per-game details. This can support historical line-combination context but is not evidence of tonight's confirmed line or PP unit. Missing shift charts remain unavailable rather than zero. Regression coverage includes overlap aggregation, player filtering, and prevention of cross-team/cross-period false overlap.


## v1.23 — historical goal-to-shift context

Historical play-by-play goal events are now joined to shift-chart intervals using the same game, period, team ID, and the event's remaining-period clock. For successfully joined goals, the report records the scorer, teammates observed on ice, assists, and event identity. Events with missing clock/identity or where the scorer is not covered by a matching shift interval are kept in an explicit unjoined list rather than guessed. Player records receive a compact historical teammate-at-goal context, and the team audit includes the full join details. This remains retrospective evidence only; it cannot confirm today's lines or power-play units. Regression tests cover correct joins and missing/mismatched event evidence.


## v1.27 — exact-date scoreboard fallback integrity

The official scoreboard fallback now accepts a game only when its explicit `gameDate` exactly matches the requested local slate date. Records with a missing date or a different date are not silently imported into the slate; the independent schedule-calendar fallback is attempted instead. This closes a cross-date contamination path at midnight and prevents a partially shaped scoreboard record from being treated as evidence for the requested day. Regression coverage verifies that wrong-date and date-less records are rejected while a matching calendar record is retained.


### v1.28 — schedule integrity before analysis

Before fetching game bundles, the CLI now validates every scheduled record against the requested local slate date, requires a game ID and both team abbreviations, and flags duplicate game IDs. Invalid rows are excluded from player analysis and recorded in `retrievalAudit`; any such row blocks complete-slate validation and suppresses Core output. This prevents a cross-date or malformed schedule record from contaminating downstream gate analysis.


## v1.29 — live source preflight

Added `python run_daily.py --preflight` to probe the official `schedule/{date}`, `score/{date}`, and `schedule-calendar/{date}` endpoints independently in the runtime where the app is launched. The JSON report records HTTP status, latency, JSON validity, top-level keys, schema checks, exact-date game counts, and exception details. It distinguishes network/DNS failures from reachable endpoints that return no records for the requested date. This mode is diagnostic only: it does not run player analysis, does not treat preflight as a complete slate validation, and cannot certify G18 locks.

Example: `python run_daily.py --date 2026-10-19 --preflight --out runs`. Three regression tests cover successful endpoints, network failure, and cross-date-only payloads.


## v1.29 — live source preflight

Added `python run_daily.py --preflight` to probe the official `schedule/{date}`, `score/{date}`, and `schedule-calendar/{date}` endpoints independently in the runtime where the app is launched. The JSON report records HTTP status, latency, JSON validity, top-level keys, schema checks, exact-date game counts, and exception details. It distinguishes network/DNS failures from reachable endpoints that return no records for the requested date. Probes use direct requests without the main data client's retry policy, so diagnostics finish quickly when networking is blocked. This mode is diagnostic only: it does not run player analysis, does not treat preflight as a complete slate validation, and cannot certify G18 locks.

Example: `python run_daily.py --date 2026-10-19 --preflight --out runs`. Three regression tests cover successful endpoints, network failure, and cross-date-only payloads. The build environment's live probe for 2026-10-19 returned `NO_ENDPOINT_REACHABLE` (0/3), which is retained as a limitation rather than interpreted as an empty slate.
