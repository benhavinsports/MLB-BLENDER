import requests
from datetime import datetime


def get_mlb_pregame_slate(date=None):

    # FORCE TODAY (fixes frozen slate issue)
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
    params = {"date": date}

    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
    except Exception as e:
        print("SLATE ERROR:", e)
        return []

    games = []

    for d in data.get("dates", []):

        for g in d.get("games", []):

            games.append({
                "gamePk": g.get("gamePk"),
                "away": g.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                "home": g.get("teams", {}).get("home", {}).get("team", {}).get("name"),

                # PROBABLE PITCHERS (important for your model)
                "away_pitcher": g.get("teams", {}).get("away", {}).get("probablePitcher", {}).get("fullName"),
                "home_pitcher": g.get("teams", {}).get("home", {}).get("probablePitcher", {}).get("fullName"),

                "status": g.get("status", {}).get("detailedState")
            })

    return games
