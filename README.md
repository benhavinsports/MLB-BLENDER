# Master MLB Blender Machine V48

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Layout
Only six tabs:
1. Blender Machine
2. Tickets
3. Core 3
4. Alt 3
5. Chaos 3
6. Game Board

## Feeder
Upload one file only:
- CSV
- Excel
- PDF
- PNG/JPG/WebP screenshot

The feeder recovers rows and never blocks the machine. If OCR dependencies are available, it reads image PDFs and screenshots.
