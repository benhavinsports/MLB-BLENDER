import requests


def get_confirmed_lineup(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        box = data.get("liveData", {}).get("boxscore", {})
        teams = box.get("teams", {})

        hitters = []

        for side in ["away", "home"]:

            batters = teams.get(side, {}).get("batters", [])

            for i, player_id in enumerate(batters):

                hitters.append({
                    "id": player_id,
                    "slot": i + 1,
                    "side": side
                })

        return hitters

    except:
        return []
