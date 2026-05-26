# THE BLENDER — V0207 Locked Owner Engine

Minimal Streamlit build.

Files included:
- app.py
- engine.py
- feeder.py
- ui.py
- official_mlb_slate.py
- requirements.txt
- README.md

Fixed flow:
1. Lock attack side
2. Eliminate within locked side only
3. Resolve ONE owner per game before roles
4. Build role identity from isolated survivor behavior
5. Build Core 3 from final isolated owners only
6. Render raw gate memory directly
7. Zero projection fallback
8. Zero “best remaining hitter” refill logic

Run:
```bash
pip install -r requirements.txt
streamlit run app.py
```
