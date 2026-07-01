import streamlit as st

from services.slate import get_mlb_slate
from engine.core import run_slate


# -----------------------------
# ⚾ APP CONFIG
# -----------------------------
st.set_page_config(
    page_title="MLB BLENDER V4.1",
    layout="wide"
)

st.title("⚾ BLENDER V4.1 REAL DATA ENGINE")
st.write("Stable MLB pipeline — schedule → engine → elimination system")


# -----------------------------
# 🧭 LOAD SLATE
# -----------------------------
st.header("Loading MLB Slate...")

games = get_mlb_slate()

if not games:
    st.error("❌ NO MLB GAMES FOUND — SLATE PIPELINE FAILED")
    st.stop()

st.success(f"✅ Loaded {len(games)} games")


# -----------------------------
# ⚙️ RUN ENGINE
# -----------------------------
st.header("Running Blender Engine...")

results = run_slate(games)


# -----------------------------
# 📊 OUTPUT
# -----------------------------
st.header("⚾ RESULTS")

for r in results:

    st.markdown("---")

    st.subheader(r.get("game", "UNKNOWN GAME"))

    st.write(f"**SURVIVOR:** {r.get('survivor')}")

    st.write(f"**WHY:** {r.get('why')}")
