import requests
from services.player_map import get_player_name


def get_confirmed_lineup(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        teams = data.get("gameData", {}).get("teams", {})

        hitters = []

        for side in ["away", "home"]:

            team = teams.get(side, {})

            lineup = team.get("lineup", [])

            if not lineup:
                continue

            for i, pid in enumerate(lineup[:9]):

                hitters.append({
                    "id": pid,
                    "name": get_player_name(pid),
                    "team_side": side,
                    "slot": i + 1
                })

        return hitters

    except:
        return None
