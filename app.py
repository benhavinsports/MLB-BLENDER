import streamlit as st

from engine.core import run_slate
from engine.core3 import build_core3
from services.slate_projection import get_mlb_pregame_slate


st.set_page_config(page_title="MLB Blender", layout="wide")

st.title("⚾ BLENDER REAL INTELLIGENCE ENGINE")

games = get_mlb_pregame_slate()

st.write("Loaded games:", len(games))

results = run_slate(games)

st.subheader("RESULTS")

for r in results:
    st.write(r)

core3 = build_core3(results)

st.subheader("CORE 3")

for p in core3:
    st.write(p)
