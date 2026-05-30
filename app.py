import streamlit as st
from ui import inject_css, render_board

st.set_page_config(page_title='Blender Gameboard', page_icon='🔥', layout='wide', initial_sidebar_state='collapsed')
inject_css()
render_board({})
