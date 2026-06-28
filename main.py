
from fastapi import FastAPI
from services.mlb import get_slate
from engine.scorer import score_player
from engine.who import pick_who

app = FastAPI(title="Blender V7 Option A")

@app.get("/live")
def live():
    return {"status":"ok","mode":"AUTO_SLATE"}

@app.get("/slate")
def slate():
    return get_slate()

@app.get("/run/{game_id}")
def run(game_id:int):
    # demo hitters
    hitters = [
        {"name":"Demo Player A","pull":80,"hh":55,"barrel":12,"ev":92,"iso":0.250,"matchup":70,"venue":65},
        {"name":"Demo Player B","pull":72,"hh":50,"barrel":10,"ev":90,"iso":0.220,"matchup":66,"venue":60},
        {"name":"Demo Player C","pull":68,"hh":48,"barrel":9,"ev":88,"iso":0.210,"matchup":64,"venue":58}
    ]

    scored = []
    for h in hitters:
        h["score"] = score_player(h)
        scored.append(h)

    scored = sorted(scored, key=lambda x: x["score"], reverse=True)

    return {
        "PRIMARY": scored[0],
        "ADJACENT": scored[1],
        "WHO": pick_who(scored)
    }
