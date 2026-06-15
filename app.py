
import streamlit as st
from datetime import date
from engine import get_schedule, evaluate_game

st.set_page_config(page_title="MLB Blender Machine v14", layout="wide")
st.title("MLB Blender Machine v14 — STRICT OPTIMIZED 18-GATE ENGINE")

selected_date = st.date_input("MLB Slate Date", value=date.today())

games = get_schedule(selected_date.isoformat())

if not games:
    st.warning("No games found.")
    st.stop()

labels = {
    g["gamePk"]: f'{g["away"]["name"]} @ {g["home"]["name"]} ({g["gamePk"]})'
    for g in games
}

game_pk = st.selectbox("Select Game", list(labels.keys()), format_func=lambda x: labels[x])

result = evaluate_game(game_pk)

st.subheader("Survivor Result")
if result["winner"] is None:
    st.error("NO SURVIVOR")
else:
    st.success(f'WINNER: {result["winner"]["player_name"]} | EVENT_SCORE={result["winner"]["EVENT_SCORE"]:.4f}')

st.subheader("Full Player Table")
st.dataframe(result["players"], use_container_width=True)

st.subheader("Audit Panel")
for audit in result["audit"]:
    with st.expander(audit["player_name"]):
        st.json(audit)
