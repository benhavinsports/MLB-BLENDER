import streamlit as st

from engine.core import run_slate

from services.slate import get_mlb_slate

st.set_page_config(page_title="MLB Blender", layout="wide")

st.title("⚾ BLENDER V4.1 REAL DATA ENGINE")

st.write("Stable MLB pipeline — schedule → engine → elimination system")

# -------------------------
# LOAD SLATE
# -------------------------
st.write("Loading MLB Slate...")

games = get_mlb_slate()

if not games:
    st.error("NO GAMES LOADED")
    st.stop()

st.success(f"Loaded {len(games)} games")

st.write("Games:")
st.write([f"{g.get('away')} vs {g.get('home')}" for g in games])

# -------------------------
# RUN ENGINE
# -------------------------
st.write("Running Blender Engine...")

results = run_slate(games)

st.subheader("⚾ RESULTS")

if not results:
    st.error("NO ENGINE RESULTS (run_slate returned empty)")
else:
    for r in results:
        st.write("GAME:", r.get("game", "UNKNOWN"))
        st.write("SURVIVOR:", r.get("survivor", "NONE"))

        # 🔥 FIXED LINE (THIS WAS BREAKING YOU)
        st.write("WHY:", r.get("why", r.get("gates", "NO DATA")))

        st.write("---")

# -------------------------
# CORE 3
# -------------------------
st.subheader("⚾ CORE 3 FINAL POOL")

core3 = build_core3(results)

if not core3:
    st.error("NO CORE 3 OUTPUT (EMPTY INPUT)")
else:
    for p in core3:
        st.write(f"{p.get('rank', '?')}. {p.get('player', 'UNKNOWN')} ({p.get('game', 'UNKNOWN')})")
        st.write(p.get("reason", "NO REASON"))
        st.write("---")
