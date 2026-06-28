
import streamlit as st
import requests
import random

st.title("BLENDER V9 STABLE - CORE 3 + MATCHUP ENGINE")

# -------------------------
# MLB SCHEDULE (SAFE)
# -------------------------
def get_games():
    try:
        url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
        data = requests.get(url, timeout=5).json()

        games = []
        dates = data.get("dates", [])
        if not dates:
            raise Exception("no dates")

        for g in dates[0].get("games", [])[:6]:
            games.append({
                "gamePk": g["gamePk"],
                "game": g["teams"]["away"]["team"]["name"] + " vs " + g["teams"]["home"]["team"]["name"],
                "away": g["teams"]["away"]["team"]["name"],
                "home": g["teams"]["home"]["team"]["name"]
            })
        return games

    except:
        return [
            {"gamePk":1,"game":"Yankees vs Red Sox","away":"Yankees","home":"Red Sox"},
            {"gamePk":2,"game":"Dodgers vs Giants","away":"Dodgers","home":"Giants"},
            {"gamePk":3,"game":"Braves vs Mets","away":"Braves","home":"Mets"},
        ]

# -------------------------
# PITCHER PROXY MODEL (STABLE V9)
# -------------------------
def get_pitcher(team):
    return {
        "hr_per9": random.uniform(0.8, 1.6),
        "hard_hit_allowed": random.uniform(0.35, 0.48),
        "xFIP": random.uniform(3.5, 4.8),
        "k_rate": random.uniform(0.18, 0.32)
    }

# -------------------------
# HITTER STATCAST PROXY (STABLE)
# -------------------------
def get_hitter(name):
    return {
        "barrel": random.uniform(0.06, 0.18),
        "hard_hit": random.uniform(0.35, 0.62),
        "ev": random.uniform(86, 94),
        "iso": random.uniform(0.120, 0.260),
        "launch_angle": random.uniform(10, 28)
    }

# -------------------------
# MATCHUP SCORE
# -------------------------
def matchup_score(hitter, pitcher):
    h = (
        hitter["barrel"] * 30 +
        hitter["hard_hit"] * 25 +
        hitter["ev"] * 0.8 +
        hitter["iso"] * 40
    )

    p = (
        pitcher["hr_per9"] * 20 +
        pitcher["hard_hit_allowed"] * 25 +
        pitcher["xFIP"] * 2
    )

    return h - p

# -------------------------
# GAME ENGINE (18 GATE SIMPLIFIED SAFE)
# -------------------------
def run_game(game):
    pitcher = get_pitcher(game["home"])

    players = ["A","B","C","D","E","F","G"]

    best = None

    for p in players:
        hitter = get_hitter(p)
        score = matchup_score(hitter, pitcher)

        if best is None or score > best["score"]:
            best = {
                "name": f"{game['away']}_{p}",
                "score": round(score,2),
                "game": game["game"]
            }

    return best

# -------------------------
# CORE 3
# -------------------------
def core3(survivors):
    survivors = sorted(survivors, key=lambda x: x["score"], reverse=True)

    out = []
    used = set()

    for s in survivors:
        if s["game"] not in used:
            out.append(s)
            used.add(s["game"])
        if len(out) == 3:
            break

    return out

# -------------------------
# UI
# -------------------------
games = get_games()

if st.button("RUN V9 SLATE"):
    survivors = [run_game(g) for g in games]

    c3 = core3(survivors)

    st.subheader("PRIMARY")
    st.write(c3[0])

    st.subheader("ADJACENT")
    st.write(c3[1])

    st.subheader("WHO")
    st.write(c3[2])

    st.subheader("CORE 3")
    st.json(c3)
