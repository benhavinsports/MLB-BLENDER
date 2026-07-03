from datetime import datetime
import requests


def get_mlb_slate_stable(date=None):

    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    url = "https://statsapi.mlb.com/api/v1/schedule"

    params = {
        "sportId": 1,
        "date": date
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

    except Exception as e:
        print("SLATE FETCH ERROR:", e)
        return []

    games = []

    for d in data.get("dates", []):
        for g in d.get("games", []):

            games.append({
                "gamePk": g.get("gamePk"),
                "away": g.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                "home": g.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                "status": g.get("status", {}).get("detailedState")
            })

    return games
