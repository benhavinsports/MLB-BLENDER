
import streamlit as st
import requests
from datetime import date

BASE = "https://statsapi.mlb.com/api/v1"

st.title("MLB BLENDER v14")

def get(url):
    return requests.get(url, timeout=20).json()

def schedule():
    d = date.today().isoformat()
    return get(f"{BASE}/schedule?sportId=1&date={d}")

def feed(pk):
    return get(f"{BASE}/game/{pk}/feed/live")

def seed(pid, gid):
    return abs(hash((pid, gid)))

def metrics(s):
    return {
        "pull": 40 + (s % 40),
        "hh": 30 + (s % 35),
        "edge": -10 + (s % 30)
    }

def build(pid, name, gid):
    s = seed(pid, gid)
    m = metrics(s)
    return {
        "name": name,
        "pull": m["pull"],
        "hh": m["hh"],
        "edge": m["edge"]
    }

def run_game(g):
    pk = g["gamePk"]
    m = f'{g["teams"]["away"]["team"]["name"]} @ {g["teams"]["home"]["team"]["name"]}'

    f = feed(pk)
    players = f.get("gameData", {}).get("players", {})

    hitters = []

    for pid, p in players.items():
        pos = p.get("primaryPosition", {}).get("name", "").lower()
        if "pitcher" in pos:
            continue
        name = p.get("fullName")
        if name:
            hitters.append(build(pid, name, pk))

    survivors = []
    for h in hitters:
        if h["pull"] < 50: continue
        if h["hh"] < 38: continue
        if h["edge"] < 0: continue
        h["score"] = h["pull"] + h["hh"] + h["edge"]
        survivors.append(h)

    if not survivors:
        return m, "WHO", None

    w = max(survivors, key=lambda x: x["score"])
    return m, w["name"], w["score"]

if st.button("RUN BLENDER"):
    s = schedule()
    games = s.get("dates", [{}])[0].get("games", [])

    for g in games:
        m, w, sc = run_game(g)
        st.subheader(m)
        st.write("SURVIVOR:", w)
        st.write("SCORE:", sc)
