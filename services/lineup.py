import requests
from services.player_map import get_player_name


def get_confirmed_lineup(gamePk):

    try:
        url = f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live"
        data = requests.get(url, timeout=10).json()

        hitters = []

        game_data = data.get("gameData", {})
        live_data = data.get("liveData", {})

        teams = game_data.get("teams", {})

        # -----------------------------
        # 🔥 TIER 1 — OFFICIAL LINEUP (WHEN AVAILABLE)
        # -----------------------------
        for side in ["away", "home"]:

            team = teams.get(side, {})

            lineup = team.get("lineup")

            if lineup and isinstance(lineup, list):

                for i, pid in enumerate(lineup[:9]):

                    hitters.append({
                        "id": pid,
                        "name": get_player_name(pid),
                        "team_side": side,
                        "slot": i + 1
                    })

        # -----------------------------
        # 🔥 TIER 2 — BOX SCORE FALLBACK
        # -----------------------------
        if len(hitters) == 0:

            box = live_data.get("boxscore", {}).get("teams", {})

            for side in ["away", "home"]:

                batters = box.get(side, {}).get("batters", [])

                for i, pid in enumerate(batters[:9]):

                    hitters.append({
                        "id": pid,
                        "name": get_player_name(pid),
                        "team_side": side,
                        "slot": i + 1
                    })

        # -----------------------------
        # FINAL SAFE RETURN
        # -----------------------------
        return hitters

    except:
        return []
