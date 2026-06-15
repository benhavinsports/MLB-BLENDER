
import streamlit as st
from engine import run

st.title("MLB BLENDER MACHINE - FINAL MASTER")

date = st.text_input("Date (YYYY-MM-DD optional)")

if st.button("RUN BLENDER"):
    res = run(date if date else None)

    st.write("## RESULTS")
    for r in res[:20]:
        st.write(r)
