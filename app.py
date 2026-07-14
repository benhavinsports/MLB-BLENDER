import streamlit as st

from engine.core import run_slate
from services.slate import get_mlb_slate


st.set_page_config(
    page_title="MLB Blender",
    layout="wide"
)


st.title(
    "⚾ MLB HR BLENDER vFINAL"
)


games = get_mlb_slate()


if not games:

    st.error(
        "NO GAMES LOADED"
    )

    st.stop()



st.success(
    f"{len(games)} games loaded"
)


results = run_slate(games)



st.header(
    "🔥 FINAL HR SURVIVORS"
)


for result in results:

    st.write(
        "GAME:",
        result["game"]
    )


    st.write(
        "FINAL SURVIVOR:",
        result["survivor"]
    )


    st.write(
        "STATUS:",
        "LOCKED"
    )


    st.divider()
