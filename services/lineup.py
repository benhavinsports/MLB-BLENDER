import requests
from services.player_map import get_player_name
from services.role_filter import is_valid_hitter


def get_confirmed_lineup(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        game_data = data.get("gameData", {})
        live_data = data.get("liveData", {})

        hitters = []

        teams = game_data.get("teams", {})

        for side in ["away", "home"]:

            team = teams.get(side, {})

            # 🔥 PRIMARY SOURCE
            lineup = team.get("lineup", [])

            # 🔥 FALLBACK 1
            if not lineup:
                lineup = live_data.get("boxscore", {}).get("teams", {}).get(side, {}).get("batters", [])

            # ❗ DO NOT HARD FAIL
            if not lineup:
                continue

            for i, pid in enumerate(lineup[:9]):

                name = get_player_name(pid)

                player_obj = {
                    "id": pid,
                    "name": name,
                    "team_side": side,
                    "slot": i + 1
                }

                # 🔥 ROLE FILTER (SOFT)
                if is_valid_hitter(player_obj):
                    hitters.append(player_obj)

        # 🔒 IMPORTANT: ONLY FAIL IF COMPLETELY EMPTY
        if len(hitters) == 0:
            return []

        return hitters

    except:
        return []
