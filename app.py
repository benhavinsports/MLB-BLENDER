import streamlit as st

st.set_page_config(page_title="MLB Blender v14", layout="wide")

st.title("⚾ MLB BLENDER MACHINE v14")
st.write("If you see this, the app is working.")

if st.button("RUN TEST"):
    st.success("Button works — Streamlit is fully functional.")
