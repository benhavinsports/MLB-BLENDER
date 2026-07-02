from datetime import datetime
import requests


def get_mlb_slate_stable(date=None):

    # -------------------------
    # FORCE TODAY'S SLATE
    # -------------------------
    if date is None:
        date = datetime.now().strftime("%Y-%m-%d")

    url = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"

    params = {
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

    # -------------------------
    # PARSE MLB RESPONSE
    # -------------------------
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
