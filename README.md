# BenHavin TRUE Blender Full App v135

This is a full Streamlit app folder, not a 5-file patch.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Engine logic
1. Read slate file.
2. Lock the pitcher weakness archetype for each side/game first.
3. Only hitters matching that pitcher weakness lane enter survival gates.
4. Run ordered gate pressure.
5. Apply Step 10.5 adjacent/decoy transfer only after lane-match survives.
6. Apply WHO/chaos only after validation pressure, not as random injection.
7. Lock one owner per game, then build Core 3 / Alt 3 / Chaos 3.

## Important
Upload the Star Tool PDF/CSV/XLSX directly in the app.
Projected lineups should still be final-checked before betting.
