# MLB HR Blender V5

Run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app uses MLB Stats API for schedules, game feeds, lineups, identities, and season totals. It also attempts to load Baseball Savant custom and bat-tracking leaderboard CSV data. Missing advanced fields pass through rather than being fabricated.
