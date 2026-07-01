import streamlit as st
from services.mlb_api import get_todays_games
from engine.core import run_slate

st.title("⚾ BLENDER V4.1 REAL DATA STABLE ENGINE")

st.caption("Stable MLB engine — no placeholders, no wipeouts")

if st.button("RUN TODAY SLATE"):
    games = get_todays_games()

    if not games:
        st.error("NO MLB GAMES FOUND")
    else:
        results = run_slate(games)

        for r in results:
            st.subheader(r["game"])
            st.write("SURVIVOR:", r["survivor"])
            st.write("WHY:", r["why"])
