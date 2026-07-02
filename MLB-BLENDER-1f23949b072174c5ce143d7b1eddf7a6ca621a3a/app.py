import streamlit as st
from engine.core import run_slate
from services.slate_stable import get_mlb_slate_stable
from engine.core3 import build_core3


st.set_page_config(page_title="MLB Blender", layout="wide")

st.title("⚾ BLENDER V4.1 REAL DATA ENGINE")

st.write("Stable MLB pipeline — schedule → engine → elimination system")

# -------------------------
# LOAD SLATE
# -------------------------
st.write("Loading MLB Slate...")

games = get_mlb_slate_stable()

st.success(f"Loaded {len(games)} games")

# -------------------------
# RUN ENGINE
# -------------------------
st.write("Running Blender Engine...")

results = run_slate(games)

st.subheader("⚾ RESULTS")

for r in results:
    st.write(r["game"])
    st.write("SURVIVOR:", r["survivor"])
    st.write("WHY:", r["why"])
    st.write("---")

# -------------------------
# CORE 3
# -------------------------
st.subheader("⚾ CORE 3 FINAL POOL")

core3 = build_core3(results)

for p in core3:
    st.write(f"{p['rank']}. {p['player']} ({p['game']})")
    st.write(p["reason"])
    st.write("---")
