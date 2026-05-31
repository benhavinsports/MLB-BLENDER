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
    key="start_tile_upload",
)

results = st.session_state.get("blender_results", {})

if uploaded is not None:
    upload_key = f"{uploaded.name}:{uploaded.size}"
    if st.session_state.get("last_upload_key") != upload_key:
        st.session_state["last_upload_key"] = upload_key
        st.session_state["uploaded_file_name"] = uploaded.name
        try:
            parsed_df = read_feed(uploaded.name, uploaded.getvalue())
            results = run_true_blender(parsed_df)
            st.session_state["blender_results"] = results
            st.session_state["blender_error"] = ""
        except Exception as e:
            st.session_state["blender_error"] = str(e)
            results = {"games": [], "meta": {"message": str(e)}}
    else:
        results = st.session_state.get("blender_results", results)

render_board(results)
