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

run_clicked = st.button(
    "RUN BLENDER",
    key="finish_tile_run",
)

results = st.session_state.get("blender_results", {})

if uploaded is not None:
    upload_key = f"{uploaded.name}:{uploaded.size}"
    if st.session_state.get("last_upload_key") != upload_key:
        st.session_state["last_upload_key"] = upload_key
        st.session_state["uploaded_file_name"] = uploaded.name
        st.session_state["blender_results"] = {}
        st.session_state["blender_error"] = ""
        try:
            parsed_df = read_feed(uploaded.name, uploaded.getvalue())
            st.session_state["parsed_feed"] = parsed_df
            st.session_state["parsed_feed_rows"] = int(len(parsed_df)) if hasattr(parsed_df, "__len__") else 0
            st.session_state["ready_to_run"] = True
        except Exception as e:
            st.session_state["parsed_feed"] = None
            st.session_state["ready_to_run"] = False
            st.session_state["blender_error"] = f"Feed parse error: {e}"

if run_clicked:
    parsed_df = st.session_state.get("parsed_feed")
    if parsed_df is None:
        st.session_state["blender_error"] = "Upload a slate PDF with START before pressing FINISH."
    else:
        try:
            results = run_true_blender(parsed_df)
            st.session_state["blender_results"] = results
            st.session_state["blender_error"] = ""
            st.session_state["ready_to_run"] = False
        except Exception as e:
            st.session_state["blender_error"] = f"Blender run error: {e}"

render_board(st.session_state.get("blender_results", results))
