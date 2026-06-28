
from fastapi import FastAPI
from backend.mlb import get_lineup
from backend.statcast import get_statcast
from backend.engine import score_player

app = FastAPI(title="Blender V8 Real MLB")

@app.get("/live")
def live():
    return {"status":"ok"}

@app.get("/run/{game_pk}")
def run(game_pk:int):

    lineup = get_lineup(game_pk)

    players = []

    for p in lineup:
        sc = get_statcast(p["id"])
        score = score_player(p, sc)

        players.append({
            "name": p["name"],
            "score": score
        })

    if len(players) == 0:
        return {
            "PRIMARY":{"name":"NO DATA","score":0},
            "ADJACENT":{"name":"NO DATA","score":0},
            "WHO":{"name":"NO DATA","score":0}
        }

    players = sorted(players, key=lambda x: x["score"], reverse=True)

    primary = players[0]
    adjacent = players[1] if len(players)>1 else players[0]
    who = players[2] if len(players)>2 else players[-1]

    return {
        "PRIMARY": primary,
        "ADJACENT": adjacent,
        "WHO": who
    }
