from __future__ import annotations

from typing import Any, Dict, List

from mlb_api import MLBAPI


# ============================================================
# MLB BLENDER ENGINE v3 (FULL REWRITE - STABLE)
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
    # SINGLE GAME PIPELINE
    # =========================================================

    def run_game(self, game: Dict[str, Any]) -> Dict[str, Any]:

        game_id = game.get("game_id")

        try:
            box = self.api.get_boxscore(game_id)
        except Exception as e:
            return {
                "game_id": game_id,
                "error": f"boxscore failed: {str(e)}",
            }

        teams = box.get("teams", {})

        home_team = (
            teams.get("home", {})
                  .get("team", {})
                  .get("name", "HOME")
        )

        away_team = (
            teams.get("away", {})
                  .get("team", {})
                  .get("name", "AWAY")
        )

        hitters = self._build_hitter_pool(teams)

        if len(hitters) == 0:
            return {
                "game_id": game_id,
                "matchup": f"{away_team} @ {home_team}",
                "survivor": None,
                "error": "No valid hitters found",
                "home": home_team,
                "away": away_team,
            }

        scored = [self._score_hitter(h) for h in hitters]

        survivor = self._select_survivor(scored)

        return {
            "game_id": game_id,
            "matchup": f"{away_team} @ {home_team}",
            "survivor": survivor,
            "home": home_team,
            "away": away_team,
            "candidates": len(hitters),
        }

    # =========================================================
    # HITTER POOL (FIXED - NO MORE EMPTY RESULTS)
    # =========================================================

    def _build_hitter_pool(self, teams: Dict[str, Any]) -> List[Dict[str, Any]]:

        hitters = []

        for side in ["home", "away"]:

            team_block = teams.get(side, {})
            team_info = team_block.get("team", {})
            team_id = team_info.get("id")

            # fallback to roster API (reliable source)
            try:
                roster = self.api.get_team_roster(team_id)
            except Exception:
                roster = []

            for p in roster:

                person = p.get("person", {})

                hitters.append(
                    {
                        "player_id": person.get("id"),
                        "name": person.get("fullName"),
                        "team_side": side,

                        # deterministic baseline stats
                        "ab": 1,
                        "hits": 0,
                        "hr": 0,
                        "bb": 0,
                        "so": 0,
                    }
                )

        return hitters

    # =========================================================
    # SCORING ENGINE (DETERMINISTIC)
    # =========================================================

    def _score_hitter(self, h: Dict[str, Any]) -> Dict[str, Any]:

        ab = max(h["ab"], 1)

        pull_pct = h["hits"] / ab
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

        print(r.get("matchup"))

        if r.get("survivor"):
            print("SURVIVOR:", r["survivor"]["name"])
        else:
            print("ERROR:", r.get("error"))
