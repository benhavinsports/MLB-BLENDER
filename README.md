# THE BLENDER — Locked MLB Home Run Machine

This is the locked MLB Home Run Blender Streamlit app.

## Runtime files

- `app.py` — Streamlit app entry point
- `engine.py` — locked Blender engine
- `feeder.py` — PDF/CSV/XLSX feeder
- `ui.py` — tickets and game board renderer
- `official_mlb_slate.py` — official MLB schedule/probable pitcher pull
- `requirements.txt`
- `.streamlit/config.toml`
- `data/.gitkeep`

## Correct app flow

1. Upload PDF hitter pool.
2. Pull official MLB slate.
3. Attach official game context to PDF rows.
4. Lock one attack side per game.
5. Run ordered pass/cut gates.
6. Resolve one owner per game.
7. Separate role paths:
   - PRIMARY
   - ADJACENT
   - WHO
8. Build Core only from surviving role paths.
9. Render Game Board from the same engine state.

## No-drift rules

The app must not:

- use alphabetical ordering
- force generic score-ranking picks
- create fake equal scores
- refill Core with unrelated best-score names
- hide pass/cut lineage
- render a different board than the engine state
- use stale/yesterday locked owners

## Output sections

- Core 3
- Alt 3
- Chaos / WHO 3
- Locked Attack Sides
- Owners by Game
- Gate Path Board
- Pass Rows
- Cut Rows
- Raw role memory
- Raw gate trace table

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```


## v159 — True Ownership State Machine
- Removed duplicate role recycling.
- Disabled fallback sorting.
- Disabled refill assignment logic.
- Added frozen role assignment enforcement.
- Core now preserves unique ownership paths only.
- Same player cannot occupy multiple Blender paths.


## v160 — Elimination Engine Rewrite
- Ownership now resolves from elimination depth.
- Core builder rewritten.
- Duplicate player recycling removed.
- No refill architecture.
- One player per role path globally.
- One owner per game enforced.


## v161 — TRUE BLENDER MACHINE FULL FIX

This is the full engine-authority rebuild.

Hard rules:
- No generic Core refill.
- No fallback sorting.
- No role recycling.
- One player can occupy only one official path.
- One owner per game.
- Core is built only from surviving PRIMARY / ADJACENT / WHO role lanes.
- Scores come from elimination survival depth + gate quality, not projection normalization.
- Game Board reads the same gate memory used by tickets.
