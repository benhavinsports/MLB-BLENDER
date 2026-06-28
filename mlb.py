
import requests

def get_lineup(game_pk:int):

    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/feed/live"

    try:
        data = requests.get(url, timeout=5).json()

        box = data["liveData"]["boxscore"]["teams"]

        players = []

        for side in ["away","home"]:
            team = box[side]["batters"]

            for pid in team:
                players.append({
                    "id": pid,
                    "name": f"Player {pid}"
                })

        return players

    except:
        return []
