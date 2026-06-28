from fastapi import FastAPI
import random

app = FastAPI()

def demo_players():
    return [
        {"name": "Player A", "score": random.uniform(70, 95)},
        {"name": "Player B", "score": random.uniform(65, 90)},
        {"name": "Player C", "score": random.uniform(60, 88)},
    ]

@app.get("/run/{game_id}")
def run(game_id: int):

    players = demo_players()

    players = sorted(players, key=lambda x: x["score"], reverse=True)

    primary = players[0]
    adjacent = players[1]
    who = players[2]

    return {
        "PRIMARY": primary,
        "ADJACENT": adjacent,
        "WHO": who
    }
