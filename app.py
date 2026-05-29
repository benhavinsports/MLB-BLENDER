
import streamlit as st
from ui import inject_css, hero, start_tile, render_gameboard

st.set_page_config(layout="wide")

inject_css()
hero()

uploaded = start_tile()

demo_results = {
    "games":[
        {
            "label":"Los Angeles Angels vs Detroit Tigers",
            "type":"core",
            "owner":"Dillon Dingler",
            "archetype":"Primary / Clean Lane Owner",
            "weakness":"Fastball inner-third damage",
            "gates":"18/23",
            "lane":"Clean Lane"
        },
        {
            "label":"Minnesota Twins vs Chicago White Sox",
            "type":"alt",
            "owner":"Trevor Larnach",
            "archetype":"Adjacent / Transfer",
            "weakness":"Fly-ball pull lane",
            "gates":"17/23",
            "lane":"Adjacent"
        },
        {
            "label":"Houston Astros vs Texas Rangers",
            "type":"chaos",
            "owner":"Ezequiel Duran",
            "archetype":"WHO / Chaos",
            "weakness":"Bullpen continuation lane",
            "gates":"16/23",
            "lane":"Chaos"
        }
    ]
}

render_gameboard(demo_results)
