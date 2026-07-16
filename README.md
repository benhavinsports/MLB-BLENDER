# MLB HR Blender V5.2

Run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

V5.2 repairs Baseball Savant ingestion by using the actual `custom.csv`
download route, adds name fallback matching when Savant omits player IDs, adds
multiple bat-tracking CSV parameter fallbacks, exposes pipeline health in debug
mode, and makes Gate 18's audit count reflect the final one-player lock.
