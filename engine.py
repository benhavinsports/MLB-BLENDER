"""
engine.py

MLB Blender Machine v14
Official Detector Engine

Responsibilities:
- Pull today's MLB schedule
- Build game bundles
- Determine target hitting side
- Generate feature sets
- Execute G0–G18 pipeline
- Return exactly 1 survivor per game
"""

from __future__ import annotations

from typing import Dict, List, Any

from mlb_api import MLBAPI
from gates import run_gates


class BlenderEngine:
    """
    Main orchestration engine.
    """

    def __init__(self):
        self.api =MLBAPI ()

    # ============================================================
    # PITCHER EXTRACTION
    # ============================================================

    def _extract_pitcher_stats(
        self,
        team_players: List[dict],
    ) -> Dict[str, float]:
        """
        Deterministic pitcher profile.

        MLB boxscore endpoint does not expose
        season-level K% / BB%.

        We derive proxy values from available
        pitching stat lines.

        Returns:
            {
                k_rate,
                bb_rate
            }
        """

        strikeouts = 0
        walks = 0
        batters_faced_proxy = 0

        for p in team_players:

            so = p.get("so", 0)
            bb = p.get("bb", 0)

            strikeouts += so
            walks += bb

            batters_faced_proxy += (
                so +
                bb +
                20
            )

        if batters_faced_proxy <= 0:
            return {
                "k_rate": 0.22,
                "bb_rate": 0.08,
            }

        return {
            "k_rate": round(
                strikeouts / batters_faced_proxy,
                4,
            ),
            "bb_rate": round(
                walks / batters_faced_proxy,
                4,
            ),
        }

    # ============================================================
    # TARGET SIDE
    # ============================================================

    def _choose_target_side(
        self,
        game_bundle: Dict[str, Any],
    ) -> str:
        """
        Required:

        ONE pitcher-side per game.

        Deterministic selection.

        Side facing stronger pitcher
        becomes the target side.
        """

        home_pitch = self._extract_pitcher_stats(
            game_bundle["boxscore"]["home"]["players"]
        )

        away_pitch = self._extract_pitcher_stats(
            game_bundle["boxscore"]["away"]["players"]
        )

        home_strength = (
            home_pitch["k_rate"]
            - home_pitch["bb_rate"]
        )

        away_strength = (
            away_pitch["k_rate"]
            - away_pitch["bb_rate"]
        )

        if home_strength >= away_strength:
            return "away"

        return "home"

    # ============================================================
    # LINEUP ENRICHMENT
    # ============================================================

    def _attach_game_logs(
        self,
        lineup: List[dict],
    ) -> List[dict]:

        enriched = []

        for hitter in lineup:

            try:

                logs = self.api.get_player_game_logs(
                    hitter["player_id"],
                    days_back=30,
                )

            except Exception:
                logs = []

            enriched.append(
                {
                    **hitter,
                    "game_logs": logs,
                }
            )

        return enriched

    # ============================================================
    # SINGLE GAME
    # ============================================================

    def run_game(
        self,
        game_bundle: Dict[str, Any],
    ) -> Dict[str, Any]:

        side = self._choose_target_side(
            game_bundle
        )

        lineup = game_bundle["lineups"][side]

        lineup = self._attach_game_logs(
            lineup
        )

        opposing_side = (
            "home"
            if side == "away"
            else "away"
        )

        pitcher_stats = (
            self._extract_pitcher_stats(
                game_bundle["boxscore"][
                    opposing_side
                ]["players"]
            )
        )

        result = run_gates(
            lineup=lineup,
            game_bundle=game_bundle,
            pitcher_stats=pitcher_stats,
        )

        result["target_side"] = side

        return result

    # ============================================================
    # ALL GAMES
    # ============================================================

    def run_today(
        self,
    ) -> List[Dict[str, Any]]:

        bundles = (
            self.api.get_today_games_bundle()
        )

        results = []

        for game in bundles:

            try:

                outcome = self.run_game(
                    game
                )

                results.append(
                    {
                        "game_id": game["game_id"],
                        "matchup":
                            f"{game['away_team_name']} @ "
                            f"{game['home_team_name']}",
                        **outcome,
                    }
                )

            except Exception as exc:

                results.append(
                    {
                        "game_id": game[
                            "game_id"
                        ],
                        "matchup":
                            f"{game['away_team_name']} @ "
                            f"{game['home_team_name']}",
                        "error": str(exc),
                    }
                )

        return results


# ============================================================
# PUBLIC ENTRYPOINT
# ============================================================

def run_blender() -> List[Dict[str, Any]]:
    """
    External application entrypoint.
    """

    engine = BlenderEngine()

    return engine.run_today()


# ============================================================
# CLI TEST
# ============================================================

if __name__ == "__main__":

    results = run_blender()

    for game in results:

        print(
            game["matchup"]
        )

        if "survivor" in game:

            print(
                "LOCK:",
                game["survivor"]["name"],
            )

        else:

            print(
                "ERROR:",
                game["error"]
            )
