import streamlit as st

from engine.core import run_slate
from engine.core3 import build_core3
from services.slate_projection import get_mlb_pregame_slate


st.set_page_config(page_title="MLB Blender", layout="wide")

st.title("⚾ BLENDER V4.1 REAL DATA ENGINE")

st.write("Stable MLB pipeline — schedule → engine → elimination system")

# LOAD SLATE
st.write("Loading MLB Slate...")

games = get_mlb_pregame_slate()

st.success(f"Loaded {len(games)} games")

st.write([g["game"] for g in games])

# RUN ENGINE (UNCHANGED)
results = run_slate(games)

st.subheader("RESULTS")

for r in results:
    st.write(r["game"])
    st.write("SURVIVOR:", r["survivor"])
    st.write("WHY:", r["why"])
    st.write("---")

# CORE 3 (UNCHANGED)
st.subheader("CORE 3")

core3 = build_core3(results)

for p in core3:
    st.write(p)
