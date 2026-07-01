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

            # 🔥 FIX: use battingOrder FIRST (more reliable than batters list)
            batting_order = team.get("battingOrder")

            # fallback chain (VERY IMPORTANT)
            if not batting_order:
                batting_order = team.get("batters", [])

            if not batting_order:
                continue

            # do NOT hard fail game anymore
            # just skip weak entries instead

            for i, pid in enumerate(batting_order[:9]):

                hitters.append({
                    "id": pid,
                    "name": get_player_name(pid),
                    "team_side": side,
                    "slot": i + 1
                })

        # 🔒 relaxed integrity rule (key fix)
        if len(hitters) < 10:
            return []  # only fail truly broken games

        return hitters

    except:
        return []
