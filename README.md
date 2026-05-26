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
