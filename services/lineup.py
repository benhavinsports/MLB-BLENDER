import requests
from services.player_map import get_player_name


def get_confirmed_lineup(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        game_data = data.get("gameData", {})
        live_data = data.get("liveData", {})

        teams = game_data.get("teams", {})

        hitters = []

        # ⚠️ REAL FIX: use roster + lineup order fallback
        for side in ["away", "home"]:

            team = teams.get(side, {})
            roster = team.get("roster", {})

            # fallback: sometimes lineup is stored here
            lineup = live_data.get("linescore", {}).get("offense", {})

            # we now fallback to boxscore ONLY if needed
            box = live_data.get("boxscore", {}).get("teams", {}).get(side, {})

            batters = box.get("batters", [])

            # 🔥 FINAL FALLBACK CHAIN
            candidate_pool = batters or lineup.get(side, []) or []

            # 🚨 last resort: skip instead of kill entire game
            if not candidate_pool:
                continue

            for i, pid in enumerate(candidate_pool[:9]):

                hitters.append({
                    "id": pid,
                    "name": get_player_name(pid),
                    "team_side": side,
                    "slot": i + 1
                })

        # 🔒 IMPORTANT: DO NOT hard-fail entire slate anymore
        if len(hitters) < 6:
            return []

        return hitters

    except:
        return []
