
import streamlit as st
import requests

st.title("BLENDER V7 AUTO SLATE (OPTION A)")

# get slate
try:
    slate = requests.get("http://localhost:8000/slate").json()
except:
    slate = {"games":[{"id":1,"name":"Demo Game"}]}

st.subheader("TODAY SLATE")

for g in slate["games"]:
    if st.button(g["name"]):
        try:
            data = requests.get(f"http://localhost:8000/run/{g['id']}").json()
        except:
            data = {}

        st.divider()
        st.subheader("PRIMARY")
        st.write(data.get("PRIMARY"))

        st.subheader("ADJACENT")
        st.write(data.get("ADJACENT"))

        st.subheader("WHO")
        st.write(data.get("WHO"))
