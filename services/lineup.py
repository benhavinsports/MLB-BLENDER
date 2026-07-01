import requests


def get_confirmed_lineup(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        box = data.get("liveData", {}).get("boxscore", {})
        teams = box.get("teams", {})

        hitters = []

        # -------------------------
        # extract batters safely
        # -------------------------
        for side in ["away", "home"]:

            team_data = teams.get(side, {})
            batters = team_data.get("batters", [])

            # if batters exist → assign proper slot order
            for i, p in enumerate(batters):

                hitters.append({
                    "id": p,
                    "side": side,
                    "slot": i + 1
                })

        # IMPORTANT:
        # never crash engine if empty
        return hitters

    except:
        return []
