# THE BLENDER MACHINE — COMPLETE REAL FIX

This build keeps the real app pieces:
- Streamlit UI
- Feeder for PDF/CSV/XLSX/images/text
- Live public slate buttons
- 2AM/manual recap logic
- Tickets tab
- Game Board tab
- Complete 0–19 gate Blender engine

Important fix:
The engine no longer returns a dead app state after reading a slate. If a game lacks enough clean metrics, it locks a clearly marked Recovery Owner so Game Board and Tickets still populate for audit instead of saying “Run the Blender first.”

Deploy:
1. Replace every file in your Streamlit repo with these files.
2. Commit changes.
3. Reboot Streamlit app.
4. Upload slate.
5. Click RUN BLENDER NOW.


## Smart AI Oil Layer

Added `ai_oil.py`.

It gives the Blender:
- AI field mapper for messy files
- AI feed validator
- AI chaos/WHO detector
- AI explanation layer
- AI recap calibration layer
- optional OpenAI API parser support

The AI layer does **not** override locked Blender gates. It cleans, validates, audits, explains, and calibrates around the engine.

Optional OpenAI:
Set Streamlit Secret:
```toml
OPENAI_API_KEY="your_key_here"
```
