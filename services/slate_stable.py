import requests


def get_mlb_slate_stable(date=None):

    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"

    params = {}
    if date:
        params["date"] = date

    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    games = []

    for d in data.get("dates", []):

        for g in d.get("games", []):

            gamePk = g.get("gamePk")

            games.append({
                "gamePk": gamePk,
                "away": g.get("teams", {}).get("away", {}).get("team", {}).get("name", "UNKNOWN"),
                "home": g.get("teams", {}).get("home", {}).get("team", {}).get("name", "UNKNOWN"),
                "status": g.get("status", {}).get("detailedState", "Unknown")
            })

    return games
