
import requests

def get_slate():
    try:
        url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
        data = requests.get(url, timeout=3).json()

        games = []
        for d in data.get("dates", []):
            for g in d.get("games", []):
                games.append({
                    "id": g["gamePk"],
                    "name": f"{g['teams']['away']['team']['name']} vs {g['teams']['home']['team']['name']}"
                })

        return {"games": games}

    except:
        return {
            "games": [
                {"id":1,"name":"Demo Game A vs B"},
                {"id":2,"name":"Demo Game C vs D"}
            ]
        }
