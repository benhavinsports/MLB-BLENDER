
import streamlit as st
import requests

st.title("BLENDER V8 REAL MLB")

game_pk = st.text_input("Enter Game PK")

if game_pk:
    try:
        data = requests.get(f"http://localhost:8000/run/{game_pk}").json()
    except:
        data = None

    st.subheader("PRIMARY")
    st.write(data["PRIMARY"])

    st.subheader("ADJACENT")
    st.write(data["ADJACENT"])

    st.subheader("WHO")
    st.write(data["WHO"])
else:
    st.info("Enter Game PK")
