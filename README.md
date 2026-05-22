# THE BLENDER — Complete Fixed Streamlit App

Run with:

```bash
pip install -r requirements.txt
streamlit run app.py
```

What was fixed/added:
- Restored the missing Blender engine constants/cache paths that caused runtime engine failure.
- Fixed locked owner + recap files to save inside `/data` instead of unsafe working-directory strings.
- Included the full 18-gate + Gate 19 HR model confirmation flow.
- Added owner locking, Game Board survivors/KILL reasons, Core 3 / Alt 3 / Chaos 3 ticket building, recap logging, public slate/live pool fallback, and adaptive weight recalibration.
- Replaced the empty sample CSV with readable rows that prove the engine spins and locks owners.

Use your Star Tool/PDF/CSV as the main feed. The public slate buttons are fallback/context only.
