# MLB Home Run Blender — Streamlit Gate Machine

This is a deterministic version of the MLB HR Blender so the run happens outside chat.

## Run it
```bash
pip install streamlit pandas openpyxl numpy
streamlit run app.py
```

## Input
Upload a CSV or Excel file with the columns shown in `sample_template.csv`.

Important rules enforced by the app:
- No revived players: once a hitter is cut, he cannot return.
- Step 10.5 only audits hitters alive after Step 10.
- No Core 3 until the selected games are processed.
- Role-balanced Core Builder tries to include Primary/Clean, Transfer/Adjacent, and Chaos/WHO roles.
- If no player survives a game, that game becomes NO PLAY.

## Workflow
1. Export or manually enter Star Tool rows into the template.
2. Upload the file.
3. Adjust thresholds in the sidebar.
4. Expand each game to inspect the gate-by-gate logs.
5. Use the Survivor Board and Role-balanced Core Builder.

## Notes
PDF screenshots are not reliable for deterministic parsing. The safest workflow is CSV/XLSX rows copied from the Star Tool.
