
from fastapi import FastAPI
import random

app = FastAPI(title="Blender V7 CORE3 Slate Engine")

def get_games():
    return [
        {"gamePk": 1, "game": "Yankees vs Red Sox"},
        {"gamePk": 2, "game": "Dodgers vs Giants"},
        {"gamePk": 3, "game": "Braves vs Mets"},
        {"gamePk": 4, "game": "Cubs vs Cardinals"},
    ]

def run_game(gamePk):
    names = ["A","B","C","D","E","F","G"]
    return {
        "name": f"Player_{random.choice(names)}_{gamePk}",
        "score": round(random.uniform(70, 95), 2),
        "gamePk": gamePk
    }

@app.get("/slate")
def slate():
    return get_games()

@app.get("/run_slate")
def run_slate():
    games = get_games()
    survivors = []

    for g in games:
        survivors.append(run_game(g["gamePk"]))

    survivors = sorted(survivors, key=lambda x: x["score"], reverse=True)

    core3 = []
    used = set()

    for s in survivors:
        if s["gamePk"] not in used:
            core3.append(s)
            used.add(s["gamePk"])
        if len(core3) == 3:
            break

    primary = core3[0]
    adjacent = core3[1]
    who = core3[2]

    return {
        "PRIMARY": primary,
        "ADJACENT": adjacent,
        "WHO": who,
        "CORE3": core3
    }
