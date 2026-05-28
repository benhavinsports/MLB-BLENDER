import streamlit as st
from ui import inject_css, hero, blender_visual, tickets_view, game_board_grid_view

st.set_page_config(page_title="Blender Machine", layout="wide")

inject_css()
hero()

results = st.session_state.get("results", {})

tab1, tab2, tab3 = st.tabs(["🔥 Blender Visual", "🎟 Tickets", "🧩 Game Board"])

with tab1:
    blender_visual()

with tab2:
    tickets_view(results)

with tab3:
    game_board_grid_view(results)
