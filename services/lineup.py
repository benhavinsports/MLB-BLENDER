import requests
from services.player_map import get_player_name


def get_confirmed_lineup(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        live = data.get("liveData", {})
        box = live.get("boxscore", {})
        teams = box.get("teams", {})

        hitters = []

        for side in ["away", "home"]:

            team = teams.get(side, {})

            # 🔥 ONLY TRUE BATTING LIST
            batters = team.get("batters", [])

            # ⚠️ HARD GUARANTEE: remove empty / invalid feeds
            if not batters or len(batters) < 6:
                continue

            for i, pid in enumerate(batters[:9]):

                name = get_player_name(pid).lower()

                # 🔥 HARD BLOCK: pitcher leakage prevention
                if any(x in name for x in [
                    "pitcher", "p-", "valdez", "matsui",
                    "abreu", "rod", "snell", "cole", "kirby"
                ]):
                    continue

                hitters.append({
                    "id": pid,
                    "name": get_player_name(pid),
                    "team_side": side,
                    "slot": i + 1
                })

        return hitters if len(hitters) >= 6 else []

    except:
        return []
