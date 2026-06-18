from __future__ import annotations

from typing import Any, Dict, List

from mlb_api import MLBAPI


# ============================================================
# MLB BLENDER ENGINE v2 (CLEAN FIXED BUILD)
# ============================================================

class BlenderEngine:

    def __init__(self):
        self.api = MLBAPI()

    # =========================================================
    # ENTRYPOINT
    # =========================================================

    def run_today(self) -> List[Dict[str, Any]]:

        bundle = self.api.get_today_games_bundle()

        games = bundle.get("games", []) if isinstance(bundle, dict) else []

        results = []

        for game in games:

            if not isinstance(game, dict):
                continue

            results.append(self.run_game(game))

        return results

    # =========================================================
    # GAME PROCESSOR
    # =========================================================

    def run_game(self, game: Dict[str, Any]) -> Dict[str, Any]:

        game_id = game.get("game_id")

        box = self.api.get_boxscore(game_id)

        home = (
            box.get("teams", {})
               .get("home", {})
               .get("team", {})
               .get("name", "HOME")
        )

        away = (
            box.get("teams", {})
               .get("away", {})
               .get("team", {})
               .get("name", "AWAY")
        )

        hitters = self._build_hitter_pool(box)

        if not hitters:
            return {
                "game_id": game_id,
                "matchup": f"{away} @ {home}",
                "survivor": None,
                "error": "No valid hitters found",
                "home": home,
                "away": away,
            }

        scored = [self._score_hitter(h) for h in hitters]

        survivor = self._select_survivor(scored)

        return {
            "game_id": game_id,
            "matchup": f"{away} @ {home}",
            "survivor": survivor,
            "home": home,
            "away": away,
            "candidates": len(hitters),
        }

    # =========================================================
    # HITTER POOL BUILDER (FIXED MLB STRUCTURE)
    # =========================================================

    def _build_hitter_pool(self, box: Dict[str, Any]) -> List[Dict[str, Any]]:

        hitters = []
        teams = box.get("teams", {})

        for side in ["home", "away"]:

            team_block = teams.get(side, {})
            players = team_block.get("players", {})

            if not isinstance(players, dict):
                continue

            for _, p in players.items():

                if not isinstance(p, dict):
                    continue

                person = p.get("person", {})
                stats = p.get("stats", {}).get("batting")

                if not stats:
                    continue

                hitters.append(
                    {
                        "player_id": person.get("id"),
                        "name": person.get("fullName"),
                        "team_side": side,

                        "ab": stats.get("atBats", 0),
                        "hits": stats.get("hits", 0),
                        "hr": stats.get("homeRuns", 0),
                        "bb": stats.get("baseOnBalls", 0),
                        "so": stats.get("strikeOuts", 0),
                    }
                )

        return hitters

    # =========================================================
    # SCORING ENGINE (DETERMINISTIC)
    # =========================================================

    def _score_hitter(self, h: Dict[str, Any]) -> Dict[str, Any]:

        ab = h["ab"] or 1
        hits = h["hits"]

        pull_pct = hits / ab
        hard_hit_pct = h["hr"] / ab

        hr_heat = h["hr"]

        pitch_edge = 0.0
        condition = 0.05

        event_score = (
            pull_pct * 0.40 +
            hard_hit_pct * 0.35 +
            pitch_edge * 1.25 +
            condition +
            hr_heat * 0.10
        )

        return {
            **h,
            "pull_pct": round(pull_pct, 4),
            "hard_hit_pct": round(hard_hit_pct, 4),
            "hr_heat": hr_heat,
            "event_score": round(event_score, 4),
        }

    # =========================================================
    # SURVIVOR SELECTION
    # =========================================================

    def _select_survivor(self, scored: List[Dict[str, Any]]) -> Dict[str, Any]:

        scored = sorted(
            scored,
            key=lambda x: x["event_score"],
            reverse=True
        )

        return scored[0] if scored else None


# ============================================================
# ENTRYPOINT
# ============================================================

def run_blender():

    engine = BlenderEngine()

    return engine.run_today()


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":

    results = run_blender()

    for r in results:

        print(r["matchup"])

        if r.get("survivor"):
            print("SURVIVOR:", r["survivor"]["name"])
        else:
            print("ERROR:", r.get("error"))
