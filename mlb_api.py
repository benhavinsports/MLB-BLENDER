from __future__ import annotations

import time
from datetime import date
from typing import Dict, List

import requests


BASE_URL = "https://statsapi.mlb.com/api/v1"


class MLBAPIError(Exception):
    pass


class MLBRequestError(MLBAPIError):
    pass


class MLBDataError(MLBAPIError):
    pass


class MLBAPI:

    def __init__(
        self,
        timeout: int = 20,
        retries: int = 3,
        backoff: float = 1.5,
    ):
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.session = requests.Session()

    # =========================================================
    # HTTP
    # =========================================================

    def _get(
        self,
        endpoint: str,
        params=None,
    ):

        url = f"{BASE_URL}{endpoint}"

        for attempt in range(self.retries):

            try:

                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                )

                if response.status_code == 429:

                    time.sleep(
                        self.backoff * (attempt + 1)
                    )

                    continue

                response.raise_for_status()

                return response.json()

            except Exception as exc:

                if attempt == self.retries - 1:
                    raise MLBRequestError(
                        str(exc)
                    )

                time.sleep(
                    self.backoff * (attempt + 1)
                )

    # =========================================================
    # DATE
    # =========================================================

    def today(self):

        return date.today().isoformat()

    # =========================================================
    # SCHEDULE
    # =========================================================

    def get_schedule(
        self,
        target_date=None,
    ):

        if not target_date:
            target_date = self.today()

        data = self._get(
            "/schedule",
            {
                "sportId": 1,
                "date": target_date,
            },
        )

        games = []

        for d in data.get(
            "dates",
            [],
        ):

            for g in d.get(
                "games",
                [],
            ):

                games.append(
                    {
                        "game_id": g.get(
                            "gamePk"
                        ),
                        "away": g["teams"][
                            "away"
                        ]["team"]["name"],
                        "home": g["teams"][
                            "home"
                        ]["team"]["name"],
                    }
                )

        return games

    # =========================================================
    # BOXSCORE
    # =========================================================

    def get_boxscore(
        self,
        game_id,
    ):

        return self._get(
            f"/game/{game_id}/boxscore"
        )

    # =========================================================
    # PLAYER GAME LOGS
    # =========================================================

    def get_player_game_logs(
        self,
        player_id,
        season="2026",
    ):

        data = self._get(
            f"/people/{player_id}/stats",
            {
                "stats": "gameLog",
                "group": "hitting",
                "season": season,
            },
        )

        try:

            return (
                data["stats"][0]["splits"]
            )

        except Exception:

            return []

    # =========================================================
    # TEAM ROSTER
    # =========================================================

    def get_team_roster(
        self,
        team_id,
    ):

        return self._get(
            f"/teams/{team_id}/roster"
        )

    # =========================================================
    # STARTING LINEUP
    # =========================================================

    def get_starting_lineup(
        self,
        game_id,
    ):

        box = self.get_boxscore(
            game_id
        )

        lineup = []

        teams = box.get(
            "teams",
            {},
        )

        for side in [
            "home",
            "away",
        ]:

            team = teams.get(
                side,
                {},
            )

            batters = team.get(
                "batters",
                [],
            )

            players = team.get(
                "players",
                {},
            )

            slot = 1

            for player_id in batters:

                player_key = (
                    f"ID{player_id}"
                )

                pdata = players.get(
                    player_key
                )

                if not pdata:
                    continue

                person = pdata.get(
                    "person",
                    {},
                )

                name = person.get(
                    "fullName"
                )

                if not name:
                    continue

                logs = self.get_player_game_logs(
                    player_id
                )

                lineup.append(
                    {
                        "player_id": player_id,
                        "name": name,
                        "lineup_slot": slot,
                        "team_side": side,
                        "game_logs": logs,
                    }
                )

                slot += 1

        return lineup

    # =========================================================
    # DAILY BUNDLE
    # =========================================================

    def get_today_games_bundle(
        self,
    ):

        return {
            "date": self.today(),
            "games": self.get_schedule(),
        }
