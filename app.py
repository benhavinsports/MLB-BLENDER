
import streamlit as st
import requests

BASE = "https://statsapi.mlb.com/api/v1"

def get_schedule(date):
    url = f"{BASE}/schedule?sportId=1&date={date}"
    data = requests.get(url, timeout=20).json()
    games = []
    for d in data.get("dates", []):
        for g in d.get("games", []):
            games.append(g)
    return games

def deterministic_score(team_name, gamePk):
    s = sum(ord(c) for c in (team_name or "")) + int(gamePk)
    return (s % 1000) / 1000.0

st.set_page_config(page_title="MLB Blender Machine v15", layout="wide")
st.title("MLB Blender Machine v15 — SCHEDULE ENGINE (NO BOXSCORE)")

date = st.date_input("Slate Date")

games = get_schedule(date.isoformat())

if not games:
    st.warning("No games found")
    st.stop()

options = {g["gamePk"]: f"{g['teams']['away']['team']['name']} @ {g['teams']['home']['team']['name']} ({g['gamePk']})" for g in games}

gamePk = st.selectbox("Select Game", list(options.keys()), format_func=lambda x: options[x])

game = next(g for g in games if g["gamePk"] == gamePk)

away = game["teams"]["away"]["team"]["name"]
home = game["teams"]["home"]["team"]["name"]

away_score = deterministic_score(away, gamePk)
home_score = deterministic_score(home, gamePk)

winner = "HOME" if home_score > away_score else "AWAY"

st.subheader("Matchup Result")
st.write({"home": home, "away": away})
st.write({"home_score": home_score, "away_score": away_score, "winner": winner})
