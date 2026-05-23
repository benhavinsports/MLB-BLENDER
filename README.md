# MLB Blender v97 PDF Feed Actual Fix

Fixes the uploaded PDF path:
- Rebuilt feeder.py to actually parse PDFs/tables/text into player rows + metrics.
- Feeder audit + parsed preview included.
- Rebuilt engine so weak/incomplete data does not blank the whole run.
- Owners/tickets commit after run.
- Duplicate Streamlit keys fixed with unique key prefixes.
- Team-color cards preserved; only score >= 78 flashes.
- Live slate is marked as context only unless metrics exist.
