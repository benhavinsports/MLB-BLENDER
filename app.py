import streamlit as st
from ui import inject_css, render_board
st.set_page_config(layout='wide', page_title='Blender')
inject_css()
render_board({})
