
# v135 Engine Import Compatibility + Results System

This fixes the Streamlit startup ImportError without changing upload behavior.

Purpose:
- Keep the clean results engine focused on:
  1. correct PDF rows only
  2. no stale/yesterday owners
  3. one clean engine path
  4. Primary / Adjacent / WHO no overlap
  5. repeat names rotate/cut/refill
  6. Core 3 always structured
  7. Game Board true role outcome

Fix:
- app.py was importing old function names that the clean engine removed.
- v135 restores those names as wrappers so the app starts.
