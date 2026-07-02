import requests
from datetime import datetime


def get_mlb_pregame_slate(date=None):

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
    r = requests.get(url, params={"date": date}, timeout=10)
    data = r.json()

    games = []

    for d in data.get("dates", []):
        for g in d.get("games", []):

            games.append({
                "gamePk": g["gamePk"],
                "game": f"{g['teams']['away']['team']['name']} vs {g['teams']['home']['team']['name']}",

                "away": g['teams']['away']['team']['name'],
                "home": g['teams']['home']['team']['name'],

                "away_pitcher": g.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("fullName"),
                "home_pitcher": g.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("fullName"),
            })

    return games
