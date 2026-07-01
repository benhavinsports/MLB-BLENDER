import streamlit as st
from services.mlb_api import get_todays_games
from engine.core import run_slate

st.title("⚾ BLENDER V4.1 REAL-DATA LOCKED")

st.caption("MLB API only | No placeholders | Deterministic gates")

if st.button("RUN TODAY SLATE"):
    games = get_todays_games()

    if not games:
        st.error("NO MLB DATA AVAILABLE")
    else:
        results = run_slate(games)

        for r in results:
            st.subheader(r["game"])
            st.write("SURVIVOR:", r["survivor"])
            st.write("WHY:", r["why"])
