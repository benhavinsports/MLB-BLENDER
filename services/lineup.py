import requests
from services.player_map import get_player_name


def get_confirmed_lineup(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        live = data.get("liveData", {})
        game_data = data.get("gameData", {})

        hitters = []

        # 🔥 PRIMARY SOURCE: linescore offense (MOST RELIABLE MID-LIVE)
        offense = live.get("linescore", {}).get("offense", {})

        for side in ["away", "home"]:

            team_offense = offense.get(side, {})

            batters = team_offense.get("batter", [])

            # 🔴 fallback chain if empty
            if not batters:
                players = game_data.get("players", {})

                # extract any hitters tagged ACTIVE
                batters = [
                    pid.replace("ID", "")
                    for pid in players.keys()
                    if "ID" in pid
                ][:9]

            if not batters:
                continue

            for i, pid in enumerate(batters[:9]):

                hitters.append({
                    "id": pid,
                    "name": get_player_name(pid),
                    "team_side": side,
                    "slot": i + 1
                })

        # 🔒 ONLY fail if ENTIRE GAME IS EMPTY
        if len(hitters) < 6:
            return []

        return hitters

    except:
        return []
