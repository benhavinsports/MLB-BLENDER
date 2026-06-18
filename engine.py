from __future__ import annotations

from typing import Any, Dict, List

from mlb_api import MLBAPI


class BlenderEngine:

    def __init__(self):
        self.api = MLBAPI()

    # =========================================================
    # ENTRYPOINT
    # =========================================================

    def run_today(self):

        schedule = self.api.get_schedule()
        results = []

        for game in schedule:
            results.append(self.run_game(game))

        return results

    # =========================================================
    # GAME CORE
    # =========================================================

    def run_game(self, game: Dict[str, Any]):

        game_id = game.get("game_id")

        try:
            box = self.api.get_boxscore(game_id)
            lineup = self.api.get_starting_lineup(game_id)
        except Exception as e:
            return {"game_id": game_id, "error": str(e)}

        home_team = game.get("home_team_name")
        away_team = game.get("away_team_name")

        hitters = self.build_hitter_pool(lineup)

        if not hitters:
            return {
                "game_id": game_id,
                "matchup": f"{away_team} @ {home_team}",
                "survivor": None,
                "error": "No starting hitters found",
                "home": home_team,
                "away": away_team,
            }

        survivor = max(hitters, key=lambda x: x["score"])

        return {
            "game_id": game_id,
            "matchup": f"{away_team} @ {home_team}",
            "survivor": survivor,
            "home": home_team,
            "away": away_team,
            "candidates": len(hitters),
        }

    # =========================================================
    # HITTER POOL (FIXED + SAFE)
    # =========================================================

    def build_hitter_pool(self, lineup):

        hitters = []

        if not isinstance(lineup, dict):
            return hitters

        for side in ["home", "away"]:

            for p in lineup.get(side, []):

                if not isinstance(p, dict):
                    continue

                player_id = p.get("player_id")
                name = p.get("name")

                if not name:
                    continue

                logs = []

                if player_id:
                    try:
                        logs = self.api.get_player_game_logs(player_id)
                    except:
                        logs = []

                ab = sum(g.get("ab", 0) for g in logs)
                hits = sum(g.get("hits", 0) for g in logs)
                hr = sum(g.get("hr", 0) for g in logs)
                bb = sum(g.get("bb", 0) for g in logs)
                so = sum(g.get("so", 0) for g in logs)

                score = (
                    hits * 1.5 +
                    hr * 3.0 +
                    (hits / max(ab, 1)) * 2.0
                )

                hitters.append({
                    "player_id": player_id,
                    "name": name,
                    "team_side": side,
                    "ab": max(ab, 1),
                    "hits": hits,
                    "hr": hr,
                    "bb": bb,
                    "so": so,
                    "score": score,
                })

        return hitters


def run_blender():
    return BlenderEngine().run_today()
