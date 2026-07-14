import streamlit as st

from services.slate import get_mlb_slate
from engine.core import run_blender


# ==========================================================
# MLB HR BLENDER vFINAL
# MAIN APPLICATION
# ==========================================================


st.set_page_config(
    page_title="MLB HR Blender",
    layout="wide"
)


st.title(
    "⚾ MLB HR BLENDER vFINAL"
)


st.write(
    "True Event Engine — Gate 0-18"
)



# ==========================================================
# LOAD SLATE
# ==========================================================


st.subheader(
    "📅 MLB SLATE"
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



for game in games:

    st.write(
        f"{game['away']} vs {game['home']}"
    )



# ==========================================================
# RUN BLENDER
# ==========================================================


st.subheader(
    "🔥 RUNNING BLENDER"
)



results = run_blender(
    games
)



if not results:

    st.error(
        "NO BLENDER RESULTS"
    )

    st.stop()



# ==========================================================
# OUTPUT
# ==========================================================


st.subheader(
    "🏆 FINAL HR SURVIVORS"
)



for result in results:

    st.markdown(
        "---"
    )

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



# ==========================================================
# CORE 3
# ==========================================================


st.subheader(
    "🔥 CORE 3"
)


core3 = results[:3]


for i, player in enumerate(core3, 1):

    st.write(
        f"{i}. {player['survivor']}"
    )
