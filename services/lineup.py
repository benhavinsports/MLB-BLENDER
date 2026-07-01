import requests

def get_lineup(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        box = data.get("liveData", {}).get("boxscore", {})
        teams = box.get("teams", {})

        hitters = []

        for side in ["away", "home"]:
            players = teams.get(side, {}).get("players", {})

            for p in players.values():

                # skip pitchers
                if p.get("position", {}).get("type") == "Pitcher":
                    continue

                hitters.append({
                    "name": p.get("person", {}).get("fullName"),

                    # REAL DATA ONLY MODE:
                    # no fake stats → default nulls
                    "pull_pct": None,
                    "hh_pct": None,
                    "pitch_edge": 0.0,
                    "opportunity": 0.5
                })

        return hitters

    except:
        return []
