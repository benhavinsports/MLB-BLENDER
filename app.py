
import streamlit as st
from ui import inject_css, render_board

st.set_page_config(layout="wide")

inject_css()

results = {}
render_board(results)
