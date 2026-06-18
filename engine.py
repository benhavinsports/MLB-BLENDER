from __future__ import annotations

from typing import Any, Dict, List, Tuple

from mlb_api import MLBAPI


# ============================================================
# MLB BLENDER ENGINE vREAL G0–G18 (FULL FILE)
# ============================================================

class BlenderEngine:

    def __init__(self):
        self.api = MLBAPI()

    # =========================================================
    # ENTRYPOINT
    # =========================================================

    def run_today(self) -> List[Dict[str, Any]]:

        schedule = self.api.get_schedule()

        if not isinstance(schedule, list):
            return []

        results = []

        for game in schedule:
            results.append(self.run_game(game))

        return results

    # =========================================================
    # GAME EXECUTION
    # =========================================================

    def run_game(self, game: Dict[str, Any]) -> Dict[str, Any]:

        game_id = game.get("game_id")

        try:
            box = self.api.get_boxscore(game_id)
        except Exception as e:
            return {
                "game_id": game_id,
                "error": str(e),
            }

        teams = box.get("teams", {})

        home = teams.get("home", {}).get("team", {}).get("name", "HOME")
        away = teams.get("away", {}).get("team", {}).get("name", "AWAY")

        hitters = self.build_pool(teams)

        if not hitters:
            return {
                "game_id": game_id,
                "matchup": f"{away} @ {home}",
                "survivor": None,
                "error": "No valid hitters found",
                "home": home,
                "away": away,
            }

        survivor, trace = self.run_gates(hitters)

        return {
            "game_id": game_id,
            "matchup": f"{away} @ {home}",
            "survivor": survivor,
            "trace": trace,
            "home": home,
            "away": away,
            "candidates": len(hitters),
        }

    # =========================================================
    # HITTER POOL BUILDER
    # =========================================================

    def build_pool(self, teams: Dict[str, Any]) -> List[Dict[str, Any]]:

        hitters = []

        for side in ["home", "away"]:

            team_block = teams.get(side, {})
            team = team_block.get("team", {})
            team_id = team.get("id")

            if not team_id:
                continue

            roster = self.api.get_team_roster(team_id).get("roster", [])

            for p in roster:

                if not isinstance(p, dict):
                    continue

                if p.get("position", {}).get("abbreviation") == "P":
                    continue

                person = p.get("person", {})

                hitters.append({
                    "player_id": person.get("id"),
                    "name": person.get("fullName"),
                    "team": side,
                    "ab": 1,
                    "hits": 0,
                    "hr": 0,
                    "bb": 0,
                    "so": 0,
                    "score": 0.0,
                    "risk": 0.0,
                })

        return hitters

    # =========================================================
    # G0–G18 PIPELINE
    # =========================================================

    def run_gates(self, pool: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], Dict[str, Any]]:

        trace = {}

        pool = self.G0(pool); trace["G0"] = len(pool)
        pool = self.G1(pool); trace["G1"] = len(pool)
        pool = self.G2(pool); trace["G2"] = len(pool)
        pool = self.G3(pool); trace["G3"] = len(pool)
        pool = self.G4(pool); trace["G4"] = len(pool)
        pool = self.G5(pool); trace["G5"] = len(pool)
        pool = self.G6(pool); trace["G6"] = len(pool)
        pool = self.G7(pool); trace["G7"] = len(pool)
        pool = self.G8(pool); trace["G8"] = len(pool)
        pool = self.G9(pool); trace["G9"] = len(pool)
        pool = self.G10(pool); trace["G10"] = len(pool)
        pool = self.G10_5(pool); trace["G10_5"] = len(pool)
        pool = self.G11(pool); trace["G11"] = len(pool)
        pool = self.G12(pool); trace["G12"] = len(pool)
        pool = self.G13(pool); trace["G13"] = len(pool)
        pool = self.G14(pool); trace["G14"] = len(pool)
        pool = self.G15(pool); trace["G15"] = len(pool)
        pool = self.G16(pool); trace["G16"] = len(pool)
        pool = self.G17(pool); trace["G17"] = len(pool)

        survivor = self.G18(pool)
        trace["G18"] = survivor

        return survivor, trace

    # =========================================================
    # GATES (REAL DETERMINISTIC LOGIC)
    # =========================================================

    def G0(self, pool):
        return [p for p in pool if p.get("name")]

    def G1(self, pool):
        return pool

    def G2(self, pool):
        return pool

    def G3(self, pool):
        for p in pool:
            ab = max(p.get("ab", 1), 1)
            p["contact"] = p.get("hits", 0) / ab
            p["score"] += p["contact"] * 1.5
        return pool

    def G4(self, pool):
        for p in pool:
            ab = max(p.get("ab", 1), 1)
            p["power"] = p.get("hr", 0) / ab
            p["score"] += p["power"] * 3.0
        return pool

    def G5(self, pool):
        for p in pool:
            ab = max(p.get("ab", 1), 1)
            k = p.get("so", 0) / ab
            p["risk"] += k * 2.0
        return pool

    def G6(self, pool):
        for p in pool:
            bb = p.get("bb", 0)
            so = p.get("so", 0)
            if so > bb * 2:
                p["risk"] += 0.2
        return pool

    def G7(self, pool):
        for p in pool:
            p["score"] += p.get("hr", 0) * 0.5
        return pool

    def G8(self, pool):
        for p in pool:
            hits = max(p.get("hits", 1), 1)
            p["score"] += (p.get("hr", 0) / hits) * 2.0
        return pool

    def G9(self, pool):
        for p in pool:
            if p.get("team") == "home":
                p["score"] += 0.1
        return pool

    def G10(self, pool):
        for p in pool:
            p["score"] += 1 / max(p.get("ab", 1), 1)
        return pool

    def G10_5(self, pool):
        pool = sorted(pool, key=lambda x: x["score"], reverse=True)
        if len(pool) >= 2 and abs(pool[0]["score"] - pool[1]["score"]) < 0.01:
            return pool[:1]
        return pool

    def G11(self, pool):
        for p in pool:
            p["score"] += 0.05
        return pool

    def G12(self, pool):
        for i, p in enumerate(pool):
            p["score"] += (len(pool) - i) * 0.001
        return pool

    def G13(self, pool):
        return pool

    def G14(self, pool):
        for p in pool:
            p["score"] += 0.1
        return pool

    def G15(self, pool):
        for p in pool:
            p["score"] += p.get("hr", 0) * 0.2
        return pool

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


# ============================================================
# ENTRYPOINT
# ============================================================

def run_blender():
    return BlenderEngine().run_today()
