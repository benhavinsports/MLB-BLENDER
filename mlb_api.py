from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, List, Optional
import requests

BASE_URL = "https://statsapi.mlb.com/api/v1"


# =========================================================
# ERRORS
# =========================================================

class MLBAPIError(Exception):
    pass


class MLBRequestError(MLBAPIError):
    pass


# =========================================================
# CORE CLIENT
# =========================================================

class MLBAPI:

    def __init__(self, timeout=20, retries=3, backoff=1.5):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.session = requests.Session()

    # -----------------------------------------------------
    # HTTP LAYER
    # -----------------------------------------------------

    def _get(self, endpoint: str, params=None):

        url = f"{BASE_URL}{endpoint}"

        for i in range(self.retries):
            try:
                r = self.session.get(url, params=params, timeout=self.timeout)

                if r.status_code == 429:
                    time.sleep(self.backoff * (i + 1))
                    continue

                r.raise_for_status()
                return r.json()

            except Exception as e:
                if i == self.retries - 1:
                    raise MLBRequestError(str(e))
                time.sleep(self.backoff * (i + 1))

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    def today(self):
        return date.today().isoformat()

    # -----------------------------------------------------
    # SCHEDULE (FIXED SAFE STRUCTURE)
    # -----------------------------------------------------

    def get_schedule(self, target_date=None):

        if not target_date:
            target_date = self.today()

        data = self._get(
            "/schedule",
            {"sportId": 1, "date": target_date},
        )

        games = []

        for d in data.get("dates", []):
            for g in d.get("games", []):

                games.append({
                    "game_id": g.get("gamePk"),
                    "home_team_name": g["teams"]["home"]["team"]["name"],
                    "away_team_name": g["teams"]["away"]["team"]["name"],
                })

        return games

    # -----------------------------------------------------
    # BOXSCORE
    # -----------------------------------------------------

    def get_boxscore(self, game_id):
        return self._get(f"/game/{game_id}/boxscore")

    # -----------------------------------------------------
    # FIXED LINEUP EXTRACTION (CRITICAL FIX)
    # -----------------------------------------------------

    def get_starting_lineup(self, game_id):

        box = self.get_boxscore(game_id)
        teams = box.get("teams", {})

        lineup = {"home": [], "away": []}

        for side in ["home", "away"]:

            team = teams.get(side, {})
            players = team.get("players", {})

            if not isinstance(players, dict):
                continue

            for _, pdata in players.items():

                person = pdata.get("person", {})
                stats = pdata.get("stats", {})

                batting = stats.get("batting", {})

                # ONLY hitters
                if not batting:
                    continue

                name = person.get("fullName")
                pid = person.get("id")

                if not name or not pid:
                    continue

                lineup[side].append({
                    "player_id": pid,
                    "name": name,
                    "lineup_slot": 99  # MLB API does NOT reliably expose slot here
                })

        return lineup

    # -----------------------------------------------------
    # FIXED GAME LOGS (CRITICAL FIX)
    # -----------------------------------------------------

    def get_player_game_logs(self, player_id: int) -> List[Dict]:

        data = self._get(
            f"/people/{player_id}/stats",
            {
                "stats": "gameLog",
                "group": "hitting",
                "season": 2026
            },
        )

        logs = []

        try:
            splits = data["stats"][0]["splits"]
        except Exception:
            return []

        for s in splits:

            stat = s.get("stat", {})

            logs.append({
                "date": s.get("date"),
                "ab": stat.get("atBats", 0),
                "hits": stat.get("hits", 0),
                "hr": stat.get("homeRuns", 0),
                "bb": stat.get("baseOnBalls", 0),
                "so": stat.get("strikeOuts", 0),
                "avg": stat.get("avg", 0),
                "ops": stat.get("ops", 0),
                "slg": stat.get("slg", 0),
                "rbi": stat.get("rbi", 0),
            })

        return logs
