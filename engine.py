from __future__ import annotations

from typing import Any, Dict, List, Tuple

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

        home_team = box.get("home", {}).get("team_name")
        away_team = box.get("away", {}).get("team_name")

        # 🔥 FIX: ONLY STARTING HITTERS
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

        survivor, trace = self.run_gates(hitters)

        return {
            "game_id": game_id,
            "matchup": f"{away_team} @ {home_team}",
            "survivor": survivor,
            "trace": trace,
            "home": home_team,
            "away": away_team,
            "candidates": len(hitters),
        }

    # =========================================================
    # HITTER POOL (CORRECTED ARCHITECTURE)
    # =========================================================

    def build_hitter_pool(self, lineup: Dict[str, Any]):

        hitters = []

        for side in ["home", "away"]:

            for p in lineup.get(side, []):

                player_id = p.get("player_id")
                name = p.get("name")

                if not player_id or not name:
                    continue

                logs = []
                try:
                    logs = self.api.get_player_game_logs(player_id)
                except:
                    logs = []

                ab = sum(g.get("ab", 0) for g in logs)
                hits = sum(g.get("hits", 0) for g in logs)
                hr = sum(g.get("hr", 0) for g in logs)
                bb = sum(g.get("bb", 0) for g in logs)
                so = sum(g.get("so", 0) for g in logs)

                hitters.append({
                    "player_id": player_id,
                    "name": name,
                    "team_side": side,

                    "ab": max(ab, 1),
                    "hits": hits,
                    "hr": hr,
                    "bb": bb,
                    "so": so,

                    "score": 0.0,
                    "risk": 0.0,
                })

        return hitters

    # =========================================================
    # G0–G18 PIPELINE (UNCHANGED LOGIC CORE)
    # =========================================================

    def run_gates(self, pool):

        trace = {}

        pool = self.G0(pool); trace["G0"] = len(pool)
        pool = self.G1(pool)
        pool = self.G2(pool)
        pool = self.G3(pool)
        pool = self.G4(pool)
        pool = self.G5(pool)
        pool = self.G6(pool)
        pool = self.G7(pool)
        pool = self.G8(pool)
        pool = self.G9(pool)
        pool = self.G10(pool)
        pool = self.G10_5(pool)
        pool = self.G11(pool)
        pool = self.G12(pool)
        pool = self.G13(pool)
        pool = self.G14(pool)
        pool = self.G15(pool)
        pool = self.G16(pool)
        pool = self.G17(pool)

        survivor = self.G18(pool)
        trace["G18"] = survivor

        return survivor, trace

    # =========================================================
    # GATES (LIGHTWEIGHT BUT VALID)
    # =========================================================

    def G0(self, pool):
        return [p for p in pool if p.get("name")]

    def G1(self, pool): return pool
    def G2(self, pool): return pool

    def G3(self, pool):
        for p in pool:
            p["score"] += (p["hits"] / max(p["ab"], 1)) * 1.5
        return pool

    def G4(self, pool):
        for p in pool:
            p["score"] += (p["hr"] / max(p["ab"], 1)) * 3.0
        return pool

    def G5(self, pool):
        for p in pool:
            k = p["so"] / max(p["ab"], 1)
            p["risk"] += k * 2.0
        return pool

    def G6(self, pool):
        for p in pool:
            if p["so"] > p["bb"] * 2:
                p["risk"] += 0.2
        return pool

    def G7(self, pool):
        for p in pool:
            p["score"] += p["hr"] * 0.3
        return pool

    def G8(self, pool):
        for p in pool:
            hits = max(p["hits"], 1)
            p["score"] += (p["hr"] / hits) * 2.0
        return pool

    def G9(self, pool):
        return pool

    def G10(self, pool):
        return pool

    def G10_5(self, pool):
        pool = sorted(pool, key=lambda x: x["score"], reverse=True)
        if len(pool) >= 2 and abs(pool[0]["score"] - pool[1]["score"]) < 0.01:
            return pool[:1]
        return pool

    def G11(self, pool): return pool
    def G12(self, pool): return pool
    def G13(self, pool): return pool

    def G14(self, pool):
        for p in pool:
            p["score"] += 0.05
        return pool

    def G15(self, pool): return pool

    def G16(self, pool):
        pool = sorted(pool, key=lambda x: x["score"], reverse=True)
        return pool[:10]

    def G17(self, pool):
        return [p for p in pool if p.get("player_id")]

    def G18(self, pool):
        if not pool:
            return None
        pool = sorted(pool, key=lambda x: x["score"], reverse=True)
        return pool[0]


def run_blender():
    return BlenderEngine().run_today()
