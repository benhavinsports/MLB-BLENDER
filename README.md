# THE BLENDER MACHINE — SINGLE FILE FINAL

Use this build when the multi-file app keeps breaking.

Files:
- `app.py` — complete Streamlit app, feeder, AI oil, engine, tickets, Game Board, recap, debug
- `requirements.txt`
- `sample_template.csv`

Deploy:
1. Delete old repo files except README if needed.
2. Upload only this `app.py`, `requirements.txt`, and optional `sample_template.csv`.
3. Reboot Streamlit.
4. Open Debug tab and run built-in sample test.
5. Upload your slate and press RUN BLENDER NOW.

Why this build:
- No imports from `engine.py`, `feeder.py`, `ui.py`, or `ai_oil.py`
- No missing module failure
- No empty folder issue
- Game Board and Tickets share the same in-memory result state
