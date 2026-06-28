
from fastapi import FastAPI
from engine.pipeline import run_pipeline

app = FastAPI(title="Blender V7 MLB Live System")

@app.get("/live")
def live():
    return {"status": "ok", "system": "V7 MLB LIVE"}

@app.get("/run/{game_pk}")
def run(game_pk: str):
    return run_pipeline(game_pk)
