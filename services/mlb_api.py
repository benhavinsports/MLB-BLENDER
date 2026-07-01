import requests
from datetime import date

def get_todays_games():
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date.today()}"

    try:
        data = requests.get(url, timeout=10).json()
        games = data.get("dates", [])[0].get("games", [])

        return [
            {
                "gamePk": g["gamePk"],
                "away": g["teams"]["away"]["team"]["name"],
                "home": g["teams"]["home"]["team"]["name"]
            }
            for g in games
        ]

    except:
        return []
