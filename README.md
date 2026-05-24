# MLB Blender App — v135 Restore Package

Current runtime target:
- Keep the Blender results system intact
- Fix the Streamlit import/startup crash
- Do not change upload behavior
- Do not hot-bat tune right now

Locked results-system requirements:
1. Correct PDF rows only
2. No stale/yesterday owners
3. One clean engine path
4. Primary / Adjacent / WHO cannot overlap
5. Repeat names rotate/cut/refill correctly
6. Core 3 always structured
7. Game Board shows true role outcome, not fake tags

What v135 does:
- Restores old function names that app.py imports
- Keeps the results engine available through run_true_blender
- Prevents the ImportError crash from app.py importing missing names

Important:
- This package should replace the live app files.
- It does NOT mean old work is intentionally deleted.
- The version history is documented in VERSION_HISTORY.md.
