
import streamlit as st
import requests

st.title("BLENDER V7 LIVE MLB SYSTEM")

game_pk = st.text_input("Game PK")

if game_pk:
    res = requests.get(f"http://localhost:8000/run/{game_pk}").json()
    st.json(res)
