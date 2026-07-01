import requests
from services.player_map import get_player_name


def get_confirmed_lineup(gamePk):

    """
    STRICT MODE:
    - only uses liveData linescore batting order
    - enforces 9 hitters max per team
    - removes incomplete/empty feeds
    """

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        live = data.get("liveData", {})
        box = live.get("boxscore", {})
        teams = box.get("teams", {})

        hitters = []

        for side in ["away", "home"]:

            team_data = teams.get(side, {})
            batters = team_data.get("batters", [])

            # 🔒 HARD RULE: must be 9 max
            batters = batters[:9]

            if len(batters) < 7:
                # 🚨 invalid lineup feed → reject game integrity
                return []

            for i, pid in enumerate(batters):

                hitters.append({
                    "id": pid,
                    "name": get_player_name(pid),
                    "team_side": side,
                    "slot": i + 1
                })

        return hitters

    except:
        return []
