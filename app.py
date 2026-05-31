import streamlit as st
from ui import inject_css, render_board
from feeder import read_feed
from engine import run_true_blender

st.set_page_config(
    page_title="Blender Gameboard",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_css()

uploaded = st.file_uploader(
    "START",
    type=["pdf", "csv", "xlsx", "xls"],
    label_visibility="collapsed",
    key="start_upload"
)

results = st.session_state.get("blender_results", {})

if uploaded is not None:
    st.session_state["uploaded_file_name"] = uploaded.name

    try:
        parsed_feed = read_feed(uploaded.name, uploaded.getvalue())
        st.session_state["parsed_feed_rows"] = int(len(parsed_feed)) if hasattr(parsed_feed, "__len__") else 0
        results = run_true_blender(parsed_feed)
        st.session_state["blender_results"] = results
        st.session_state["blender_error"] = ""
    except Exception as e:
        st.session_state["blender_error"] = str(e)
        results = {
            "games": [],
            "meta": {
                "message": f"Blender pipeline error: {e}",
                "owners_locked": 0,
                "core_count": 0,
                "games": 0,
            }
        }

render_board(results)
