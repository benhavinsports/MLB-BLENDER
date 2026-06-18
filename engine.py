from __future__ import annotations

from typing import Any, Dict, List
from mlb_api import MLBAPI


class BlenderEngine:

    def __init__(self):
        self.api = MLBAPI()

    def run_today(self) -> List[Dict[str, Any]]:

        bundle = self.api.get_today_games_bundle()

        games = bundle.get("games", []) if isinstance(bundle, dict) else []

        results = []

        for game in games:
            results.append(self.run_game(game))

        return results

    def run_game(self, game: Dict[str, Any]) -> Dict[str, Any]:

        game_id = game.get("game_id")

        box = self.api.get_boxscore(game_id)

        teams = box.get("teams", {})

        home = teams.get("home", {}).get("team", {}).get("name", "HOME")
        away = teams.get("away", {}).get("team", {}).get("name", "AWAY")

        hitters = self._build_hitter_pool(teams)

        if not hitters:
            return {
                "game_id": game_id,
                "matchup": f"{away} @ {home}",
                "survivor": None,
                "error": "No valid hitters found",
                "home": home,
                "away": away,
            }

        scored = [self._score(h) for h in hitters]

        return {
            "game_id": game_id,
            "matchup": f"{away} @ {home}",
            "survivor": max(scored, key=lambda x: x["event_score"]),
            "home": home,
            "away": away,
            "candidates": len(hitters),
        }

    def _build_hitter_pool(self, teams: Dict[str, Any]) -> List[Dict[str, Any]]:

        hitters = []

        for side in ["home", "away"]:

            team = teams.get(side, {}).get("team", {})
            team_id = team.get("id")

            if not team_id:
                continue

            roster = self.api.get_team_roster(team_id).get("roster", [])

            for p in roster:

                if not isinstance(p, dict):
                    continue

                person = p.get("person", {})
                position = p.get("position", {}).get("abbreviation")

                if position == "P":
                    continue

                hitters.append({
                    "player_id": person.get("id"),
                    "name": person.get("fullName"),
                    "team_side": side,
                    "ab": 1,
                    "hits": 0,
                    "hr": 0
                })

        return hitters

    def _score(self, h: Dict[str, Any]) -> Dict[str, Any]:

        return {
            **h,
            "event_score": 0.05
        }


def run_blender():

    engine = BlenderEngine()

    return engine.run_today()
