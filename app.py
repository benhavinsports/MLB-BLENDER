
import streamlit as st
import requests

st.title("BLENDER V7 CORE 3 SLATE ENGINE")

st.subheader("TODAY SLATE")

selected = st.button("RUN SLATE")

if selected:
    data = requests.get("http://localhost:8000/run_slate").json()

    st.subheader("PRIMARY")
    st.write(data["PRIMARY"])

    st.subheader("ADJACENT")
    st.write(data["ADJACENT"])

    st.subheader("WHO")
    st.write(data["WHO"])

    st.subheader("CORE 3")
    st.json(data["CORE3"])
