import streamlit as st
from ui import inject_css, render_gameboard

st.set_page_config(
    page_title="Blender Machine",
    layout="wide",
    initial_sidebar_state="collapsed"
)

inject_css()

demo_results = {
    "core3":[
        {
            "game":"Los Angeles Angels vs Detroit Tigers",
            "player":"Dillon Dingler",
            "archetype":"Primary / Clean Lane",
            "weakness":"Fastball inner-third damage"
        }
    ],
    "alt3":[
        {
            "game":"Minnesota Twins vs Chicago White Sox",
            "player":"Trevor Larnach",
            "archetype":"Adjacent / Transfer",
            "weakness":"Pull-side flyball lane"
        }
    ],
    "chaos3":[
        {
            "game":"Houston Astros vs Texas Rangers",
            "player":"Ezequiel Duran",
            "archetype":"WHO / Chaos",
            "weakness":"Bullpen continuation lane"
        }
    ]
}

render_gameboard(demo_results)
