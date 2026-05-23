# MLB Blender v97 PDF Feed Actual Fix

Fixes the uploaded PDF path:
- Rebuilt feeder.py to actually parse PDFs/tables/text into player rows + metrics.
- Feeder audit + parsed preview included.
- Rebuilt engine so weak/incomplete data does not blank the whole run.
- Owners/tickets commit after run.
- Duplicate Streamlit keys fixed with unique key prefixes.
- Team-color cards preserved; only score >= 78 flashes.
- Live slate is marked as context only unless metrics exist.


# v98 Godmode PDF Ingestion

Includes the required 1–5:
1. Multi-layer OCR/extraction fallback: pypdf, pdfplumber, PyMuPDF, optional pytesseract OCR.
2. Semantic table reconstruction: detects headers and maps them into Blender schema.
3. Cross-page context memory: carries team/game/pitcher/page context across pages.
4. Adaptive schema detection: detects player column and metric aliases.
5. Confidence + recovery layer: ingestion_confidence + needs_recovery; weak rows stay alive for capped audit instead of blanking.
