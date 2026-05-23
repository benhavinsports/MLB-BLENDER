# MLB Blender v90 Strongest AI Oil Blender

This version fixes the remaining core issue:
- Adds the AI Oil layer from ai_oil.py into the feed rebuild path.
- AI Oil repairs fields, validates feed, detects WHO/chaos signals, but does NOT freestyle picks.
- Replaces fake 99 scoring with calibrated true HR-event scoring.
- Missing pitch edge no longer blocks the Blender, but it also cannot create elite 99s.
- Recovery/audit owners are capped and labeled.
- Clean owners, recovery owners, Core/Alt/Chaos are separated correctly.
- No st.rerun after run; output stays visible.
- Uploaded feed runs immediately through the 19-gate system.
