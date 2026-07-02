import requests


MLB_SCHEDULE_URL = "https://statsapi.mlb.com/api/v1/schedule?sportId=1"


def get_mlb_slate(date=None):

    try:

        params = {
            "sportId": 1
        }

        if date:
            params["date"] = date

        r = requests.get(MLB_SCHEDULE_URL, params=params, timeout=10)
        data = r.json()

        games = []

        dates = data.get("dates", [])

        for d in dates:

            for g in d.get("games", []):

                status = g.get("status", {}).get("detailedState", "")

                # 🔥 ONLY REAL GAMES
                if status in ["Postponed", "Canceled", "Suspended"]:
                    continue

                games.append({
                    "gamePk": g.get("gamePk"),
                    "away": g.get("teams", {}).get("away", {}).get("team", {}).get("name"),
                    "home": g.get("teams", {}).get("home", {}).get("team", {}).get("name"),
                    "status": status
                })

        # 🚨 HARD VALIDATION
        games = [g for g in games if g.get("gamePk")]

        return games

    except:
        return []
