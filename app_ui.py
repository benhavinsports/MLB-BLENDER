import streamlit as st

# import your engine (DO NOT CHANGE ENGINE)
from core import run_slate
from core3 import build_core3


# ----------------------------
# PAGE CONFIG
# ----------------------------
st.set_page_config(
    page_title="MLB HR BLENDER",
    layout="wide"
)

st.title("⚾ MLB HR BLENDER v3.0")
st.subheader("LIVE SLATE DASHBOARD (STABLE ENGINE)")

# ----------------------------
# LOAD DATA BUTTON
# ----------------------------
if st.button("Run Slate Engine"):

    # You plug your real slate fetch here
    # Example placeholder:
    games = st.session_state.get("games", [])

    if not games:
        st.warning("No games loaded")
        st.stop()

    # ----------------------------
    # RUN ENGINE
    # ----------------------------
    results = run_slate(games)

    core3 = build_core3(results)

    # ----------------------------
    # MAIN LAYOUT
    # ----------------------------
    col1, col2 = st.columns([2, 1])

    # ============================
    # LEFT SIDE — GAMES OUTPUT
    # ============================
    with col1:

        st.header("📊 Game Results")

        for r in results:

            with st.container():

                st.markdown(f"""
                ### {r['game']}

                **SURVIVOR:** {r['survivor']}

                **WHY:** {r['why']}
                """)

                st.divider()

    # ============================
    # RIGHT SIDE — CORE 3 LOCK
    # ============================
    with col2:

        st.header("🔥 CORE 3 LOCKED")

        for i, p in enumerate(core3, 1):

            st.markdown(f"""
            ### {i}. {p['player']}

            **Game:** {p['game']}

            **Reason:** {p['reason']}
            """)

        st.divider()

    # ----------------------------
    # RAW DEBUG (OPTIONAL)
    # ----------------------------
    with st.expander("Raw Engine Output"):

        st.json(results)
