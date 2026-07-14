import streamlit as st

from services.slate import get_mlb_slate
from engine.core import run_blender
from services.output import build_core3


# ==========================================================
# MLB HR BLENDER vFINAL
# MAIN APPLICATION
# ==========================================================

st.set_page_config(
    page_title="MLB HR Blender",
    layout="wide"
)

st.title("⚾ MLB HR BLENDER vFINAL")
st.write("True Event Engine — Gates 0–18")


# ==========================================================
# LOAD MLB SLATE
# ==========================================================

st.subheader("📅 Today's Slate")

games = get_mlb_slate()

if not games:
    st.error("No games loaded.")
    st.stop()

st.success(f"{len(games)} games loaded.")

for game in games:

    st.write(
        f"{game['away']} vs {game['home']}"
    )


# ==========================================================
# RUN BLENDER
# ==========================================================

st.subheader("🔥 Running Blender")

results = run_blender(games)

if not results:
    st.error("No Blender results.")
    st.stop()


# ==========================================================
# GAME RESULTS
# ==========================================================

st.subheader("🏆 Final Survivor Per Game")

for result in results:

    st.markdown("---")

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
        result["status"]
    )


# ==========================================================
# CORE 3
# ==========================================================

st.subheader("🔥 CORE 3")

core3 = build_core3(results)

for i, player in enumerate(core3, start=1):

    st.write(
        f"{i}. {player['player']}"
    )

    st.caption(
        player["game"]
    )
