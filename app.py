import streamlit as st
from engine import run_blender

st.set_page_config(page_title="MLB Blender Machine v14", layout="wide")

st.title("⚾ MLB BLENDER MACHINE v14")

st.write("Safe mode enabled — engine errors will be shown instead of crashing the app.")

if st.button("RUN BLENDER"):
    try:
        with st.spinner("Running MLB engine..."):
            results = run_blender()

        st.success("Engine completed!")

        st.write("Results:")
        st.json(results)

    except Exception as e:
        st.error("Engine crashed (caught safely)")
        st.exception(e)
