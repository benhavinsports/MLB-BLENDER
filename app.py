
import streamlit as st
import pandas as pd
from core.engine import run_blender
from core.file_loader import load_uploaded_file

st.set_page_config(page_title="BenHavin Blender V2", layout="wide")

st.title("🧠 Master BenHavin Blender V2")

uploaded_file = st.file_uploader("Upload CSV or PDF Slate", type=["csv", "pdf"])

slate = None

if uploaded_file:
    slate = load_uploaded_file(uploaded_file)
    st.success("File loaded successfully")
    st.write("### Parsed Slate")
    st.json(slate)

run_button = st.sidebar.button("Run Blender")

if slate and run_button:
    results = run_blender(slate)
    st.success("Blender Complete")

    st.write("### Final Survivors (Gate 23)")
    st.json(results["final"])

    st.write("### Trace")
    st.json(results["trace"])
