from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, Optional
import requests


BASE_URL = "https://statsapi.mlb.com/api/v1"


class MLBAPIError(Exception):
    pass


class MLBRequestError(MLBAPIError):
    pass


class MLBDataError(MLBAPIError):
    pass


class MLBAPI:

    def __init__(self, timeout=20, retries=3, backoff=1.5):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.session = requests.Session()

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

    def today(self):
        return date.today().isoformat()

    def get_schedule(self, target_date=None):

        if not target_date:
            target_date = self.today()

        data = self._get("/schedule", {
            "sportId": 1,
            "date": target_date
        })

        games = []

        for d in data.get("dates", []):
            for g in d.get("games", []):

                games.append({
                    "game_id": g.get("gamePk"),
                    "away": g["teams"]["away"]["team"]["name"],
                    "home": g["teams"]["home"]["team"]["name"],
                })

        return games

    def get_boxscore(self, game_id):

        return self._get(f"/game/{game_id}/boxscore")

    def get_player_game_logs(self, player_id):

        data = self._get(
            f"/people/{player_id}/stats",
            {
                "stats": "gameLog",
                "group": "hitting",
                "season": "2026"
            }
        )

        return data

    def get_team_roster(self, team_id):

        return self._get(f"/teams/{team_id}/roster")

    def get_starting_lineup(self, game_id):

        box = self.get_boxscore(game_id)

        return {
            "home": box.get("teams", {}).get("home", {}),
            "away": box.get("teams", {}).get("away", {}),
        }

    def get_today_games_bundle(self):

        schedule = self.get_schedule()

        return {
            "date": self.today(),
            "games": schedule
        }
