import streamlit as st
import random

st.title("BLENDER V7 CORE 3 (OPTION A FIX)")

# -------------------------
# MOCK SLATE (SAFE FOR CLOUD)
# -------------------------
def get_games():
    return [
        {"gamePk": 1, "game": "Yankees vs Red Sox"},
        {"gamePk": 2, "game": "Dodgers vs Giants"},
        {"gamePk": 3, "game": "Braves vs Mets"},
        {"gamePk": 4, "game": "Cubs vs Cardinals"},
    ]

# -------------------------
# GAME ENGINE (1 SURVIVOR ONLY)
# -------------------------
def run_game(game):
    players = ["A", "B", "C", "D", "E"]

    survivor = {
        "name": f"{game['game'].split('vs')[0].strip()}_STAR_{random.choice(players)}",
        "score": round(random.uniform(70, 95), 2),
        "game": game["game"]
    }

    return survivor

# -------------------------
# CORE 3 ENGINE (STRICT)
# -------------------------
def build_core3(survivors):

    survivors = sorted(survivors, key=lambda x: x["score"], reverse=True)

    core3 = []
    used_games = set()

    for s in survivors:
        if s["game"] not in used_games:
            core3.append(s)
            used_games.add(s["game"])
        if len(core3) == 3:
            break

    return core3

# -------------------------
# UI
# -------------------------
games = get_games()

st.subheader("TODAY SLATE")

if st.button("RUN BLENDER CORE 3"):
    
    survivors = []

    for g in games:
        survivors.append(run_game(g))

    core3 = build_core3(survivors)

    st.subheader("PRIMARY")
    st.write(core3[0])

    st.subheader("ADJACENT")
    st.write(core3[1])

    st.subheader("WHO")
    st.write(core3[2])

    st.subheader("FULL CORE 3")
    st.json(core3)
