from __future__ import annotations

from typing import Any, Dict, List

from mlb_api import MLBAPI


# ============================================================
# MLB BLENDER ENGINE
# ============================================================

class BlenderEngine:

    def __init__(self):

        self.api = MLBAPI()

    # --------------------------------------------------------
    # MAIN RUN
    # --------------------------------------------------------

    def run_today(self) -> List[Dict[str, Any]]:

        bundles = self.api.get_today_games_bundle()

        results = []

        # Normalize safely
        if isinstance(bundles, dict):
            games = bundles.get("games", [])
        else:
            games = bundles if isinstance(bundles, list) else []

        for game in games:

            if not isinstance(game, dict):
                continue

            try:
                outcome = self.run_game(game)

                results.append(
                    {
                        "game_id": game.get("game_id"),
                        "matchup": f"{game.get('away')} @ {game.get('home')}",
                        **outcome,
                    }
                )

            except Exception as exc:

                results.append(
                    {
                        "game_id": game.get("game_id"),
                        "matchup": f"{game.get('away')} @ {game.get('home')}",
                        "error": str(exc),
                    }
                )

        return results

    # --------------------------------------------------------
    # SINGLE GAME RUN
    # --------------------------------------------------------

    def run_game(self, game: Dict[str, Any]) -> Dict[str, Any]:
        """
        Minimal safe game processor.
        Full G0–G18 logic will plug in here later.
        """

        game_id = game.get("game_id")

        box = self.api.get_boxscore(game_id)

        # Extract basic team info safely
        home = box.get("teams", {}).get("home", {}).get("team", {}).get("name", "HOME")
        away = box.get("teams", {}).get("away", {}).get("team", {}).get("name", "AWAY")

        # Placeholder deterministic survivor logic (safe baseline)
        survivor = {
            "name": f"{away} hitter (placeholder)",
            "reason": "baseline engine active"
        }

        return {
            "game_id": game_id,
            "survivor": survivor,
            "home": home,
            "away": away,
        }


# ============================================================
# ENTRYPOINT
# ============================================================

def run_blender() -> List[Dict[str, Any]]:

    engine = BlenderEngine()

    return engine.run_today()


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":

    results = run_blender()

    for game in results:

        print(game.get("matchup"))

        if "survivor" in game:
            print("SURVIVOR:", game["survivor"]["name"])
        else:
            print("ERROR:", game.get("error"))
