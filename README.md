# THE BLENDER — Locked MLB Home Run Machine

## What this app does

THE BLENDER is a Streamlit app for running the locked MLB Home Run Blender workflow.

The app uses:

1. **PDF hitter pool**
   - Your uploaded Star Tool / slate PDF supplies the hitter rows and hitter metrics.

2. **Official MLB slate pull**
   - MLB schedule context supplies real games, game count, start times, Early/Late slate windows, game status, and probable pitchers.

3. **Locked Blender engine**
   - The engine runs gate-based elimination, not generic ranking.
   - The output should come from surviving gate paths, not alphabetical order or raw score sorting.

## Runtime files

This clean package should contain only:

- `app.py`
- `engine.py`
- `feeder.py`
- `ui.py`
- `official_mlb_slate.py`
- `requirements.txt`
- `README.md`
- `.streamlit/config.toml`
- `data/.gitkeep`

No old repair reports, debug manifests, emergency files, or duplicate engine modules should be included.

## How to run locally

Install requirements:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run app.py
```

## App flow

1. Open the Streamlit app.
2. Upload the slate PDF.
3. Let the feeder read the PDF hitter pool.
4. Let the app pull the official MLB slate.
5. Run the Blender.
6. Review:
   - Core 3
   - Alt 3
   - WHO / Chaos
   - Game Board
   - Pass rows
   - Cut rows
   - Gate trace memory

## Locked Blender behavior

The engine is supposed to behave like an elimination machine:

1. Parse current PDF rows only.
2. Attach official MLB slate context.
3. Build real game environments.
4. Run ordered gates.
5. Cut failed profiles.
6. Isolate one owner per game.
7. Separate role paths:
   - Primary
   - Adjacent / Decoy
   - WHO / Chaos
8. Build Core 3 from surviving role paths.
9. Render the Game Board from the same engine memory.

## What should NOT happen

The app should not:

- force fake picks from name-only rows
- use alphabetical order
- show every score as the same value
- build Core from the same game twice unless unavoidable
- hide pass/cut rows
- use stale locked results
- let the board render a different state than the engine output

## Notes

- Official MLB slate pull is the source of truth for games, times, Early/Late windows, and probable pitchers.
- PDF hitter data is the source of truth for hitter metrics.
- The Game Board should show the same pass/cut memory used to build tickets.
