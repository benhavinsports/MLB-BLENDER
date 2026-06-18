from __future__ import annotations

from typing import Any, Dict, List

from mlb_api import MLBAPI


# ============================================================
# MLB BLENDER ENGINE v1 (REWRITE)
# ============================================================

class BlenderEngine:

    def __init__(self):

        self.api = MLBAPI()

    # =========================================================
    # MAIN ENTRY
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
    # GAME PIPELINE
    # =========================================================

    def run_game(self, game: Dict[str, Any]) -> Dict[str, Any]:

        game_id = game.get("game_id")

        box = self.api.get_boxscore(game_id)

        home_team = (
            box.get("teams", {})
               .get("home", {})
               .get("team", {})
               .get("name", "HOME")
        )

        away_team = (
            box.get("teams", {})
               .get("away", {})
               .get("team", {})
               .get("name", "AWAY")
        )

        # =====================================================
        # STEP 1 — BUILD HITTER POOL (SAFE BASELINE)
        # =====================================================

        hitters = self._build_hitter_pool(box)

        if not hitters:
            return self._empty_result(game_id, home_team, away_team)

        # =====================================================
        # STEP 2 — SCORE ALL HITTERS (DETERMINISTIC)
        # =====================================================

        scored = [self._score_hitter(h) for h in hitters]

        # =====================================================
        # STEP 3 — ELIMINATION (LOWEST SCORE REMOVED ITERATIVELY)
        # =====================================================

        survivor = self._eliminate(scored)

        return {
            "game_id": game_id,
            "matchup": f"{away_team} @ {home_team}",
            "survivor": survivor,
            "home": home_team,
            "away": away_team,
            "candidates": len(hitters),
        }

    # =========================================================
    # HITTER POOL
    # =========================================================

    def _build_hitter_pool(self, box: Dict[str, Any]) -> List[Dict[str, Any]]:

        hitters = []

        for side in ["home", "away"]:

            team_block = (
                box.get("teams", {})
                   .get(side, {})
                   .get("players", {})
            )

            for p in team_block.values():

                person = p.get("person", {})
                stats = p.get("stats", {}).get("batting", {})

                # Only include batters with at least 1 AB
                if not stats or stats.get("atBats", 0) == 0:
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
    # SCORING MODEL (DETERMINISTIC)
    # =========================================================

    def _score_hitter(self, h: Dict[str, Any]) -> Dict[str, Any]:

        ab = h["ab"]
        hits = h["hits"]

        # Pull %
        pull_pct = (hits / ab) if ab > 0 else 0.0

        # Hard hit proxy (HR rate)
        hard_hit = (h["hr"] / ab) if ab > 0 else 0.0

        # HR heat (recent proxy simplified here)
        hr_heat = h["hr"]

        # Pitch edge (neutral baseline in v1)
        pitch_edge = 0.0

        # Condition boost (stable bias)
        condition = 0.05

        event_score = (
            pull_pct * 0.40 +
            hard_hit * 0.35 +
            pitch_edge * 1.25 +
            condition +
            hr_heat * 0.10
        )

        return {
            **h,
            "pull_pct": round(pull_pct, 4),
            "hard_hit_pct": round(hard_hit, 4),
            "hr_heat": hr_heat,
            "pitch_edge": pitch_edge,
            "event_score": round(event_score, 4),
        }

    # =========================================================
    # ELIMINATION ENGINE (LOWEST OUT)
    # =========================================================

    def _eliminate(self, hitters: List[Dict[str, Any]]) -> Dict[str, Any]:

        # deterministic sorting
        hitters = sorted(
            hitters,
            key=lambda x: x["event_score"],
            reverse=True
        )

        survivor = hitters[0] if hitters else None

        return survivor

    # =========================================================
    # EMPTY RESULT HANDLER
    # =========================================================

    def _empty_result(self, game_id, home, away):

        return {
            "game_id": game_id,
            "matchup": f"{away} @ {home}",
            "survivor": None,
            "error": "No valid hitters found",
            "home": home,
            "away": away,
        }


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

    for g in results:

        print(g["matchup"])

        if g.get("survivor"):
            print("SURVIVOR:", g["survivor"]["name"])
        else:
            print("NO SURVIVOR")
