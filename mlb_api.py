
import requests

BASE = "https://statsapi.mlb.com/api/v1"

def get_schedule(date="2026-06-28"):
    return requests.get(f"{BASE}/schedule?sportId=1&date={date}").json()

def get_live_game(game_pk):
    return requests.get(f"{BASE}/game/{game_pk}/feed/live").json()
