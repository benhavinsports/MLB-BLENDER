# Master MLB Blender Machine V50 — Multi-File Feeder

Fix:
- Feeder now accepts multiple files at once.
- You can upload all 4 split CSV files together.
- It merges every uploaded file into one slate before running the blender.
- It de-dupes same game/player rows across files.
- Same tabs only:
  - Blender Machine
  - Tickets
  - Core 3
  - Alt 3
  - Chaos 3
  - Game Board

Deploy:
- app.py
- requirements.txt
- packages.txt
- sample_template.csv

Run:
streamlit run app.py
