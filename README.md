# THE BLENDER v38 Feeder Brain

Smaller build. One feeder brain. No folder/import chaos.

Files:
- app.py
- feeder_brain.py
- blender_engine.py
- ui.py
- config.py
- requirements.txt
- README.md
- sample_template.csv

Purpose:
1. Read entire PDF page-by-page.
2. Keep raw page evidence.
3. Build player blocks with page, team, pitcher, metrics, and raw block.
4. Refuse fake locks only when rows are truly missing team/pitcher.
5. Show Feeder Lab before results so bad data cannot hide.
