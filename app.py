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
)

results = {}

if uploaded is not None:
    st.session_state["uploaded_file_name"] = uploaded.name

    try:
        parsed_df = read_feed(uploaded)
        results = run_true_blender(parsed_df)
    except Exception as e:
        st.error(f"Blender pipeline error: {e}")

render_board(results)
