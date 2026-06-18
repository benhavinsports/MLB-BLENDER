"""
mlb_api.py

MLB Blender Machine v14
Production MLB Stats API client

- Schedule ingestion
- Boxscore ingestion
- Player game logs
- Team roster extraction
- Starting lineup extraction
- Normalization layer
- Retry + rate limit handling
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, List, Optional

import requests


BASE_URL = "https://statsapi.mlb.com/api/v1"


# ============================================================
# EXCEPTIONS
# ============================================================

class MLBAPIError(Exception):
    pass


class MLBRequestError(MLBAPIError):
    pass


class MLBDataError(MLBAPIError):
    pass


# ============================================================
# MLB API CLIENT
# ============================================================

class MLBAPI:
    def __init__(
        self,
        timeout: int = 20,
        retries: int = 3,
        backoff: float = 1.5,
    ) -> None:

        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "MLBBlenderMachine/14.0"
            }
        )

    # --------------------------------------------------------
    # CORE REQUEST HANDLER
    # --------------------------------------------------------

    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        url = f"{BASE_URL}{endpoint}"
        last_error = None

        for attempt in range(self.retries):

            try:
                resp = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                )

                if resp.status_code == 429:
                    time.sleep(self.backoff * (attempt + 1))
                    continue

                resp.raise_for_status()

                data = resp.json()

                if not isinstance(data, dict):
                    raise MLBDataError("Invalid MLB API response")

                return data

            except requests.RequestException as e:
                last_error = e
                time.sleep(self.backoff * (attempt + 1))

        raise MLBRequestError(
            f"MLB request failed: {url}"
        ) from last_error

    # --------------------------------------------------------
    # UTILS
    # --------------------------------------------------------

    @staticmethod
    def today() -> str:
        return date.today().isoformat()

    def ping(self) -> bool:
        try:
            data = self._get("/sports")
            return bool(data)
        except Exception:
            return False

    # ============================================================
    # SCHEDULE
    # ============================================================

    def get_schedule(
        self,
        target_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        if target_date is None:
            target_date = self.today()

        payload = self._get(
            "/schedule",
            params={
                "sportId": 1,
                "date": target_date,
            },
        )

        games = []

        for d in payload.get("dates", []):
            for g in d.get("games", []):

                away = g.get("teams", {}).get("away", {})
                home = g.get("teams", {}).get("home", {})

                games.append(
                    {
                        "game_id": g.get("gamePk"),
                        "game_date": target_date,
                        "game_datetime": g.get("gameDate"),
                        "status": g.get("status", {}).get("detailedState"),

                        "away_team_id": away.get("team", {}).get("id"),
                        "away_team_name": away.get("team", {}).get("name"),

                        "home_team_id": home.get("team", {}).get("id"),
                        "home_team_name": home.get("team", {}).get("name"),
                    }
                )

        return games

    # ============================================================
    # BOXSCORE
    # ============================================================

    def get_boxscore(
        self,
        game_id: int,
    ) -> Dict[str, Any]:

        payload = self._get(f"/game/{game_id}/boxscore")
        teams = payload.get("teams")

        if not teams:
            raise MLBDataError(f"Missing teams in game {game_id}")

        return {
            "game_id": game_id,
            "home": self._normalize_team(teams["home"]),
            "away": self._normalize_team(teams["away"]),
        }

    # ============================================================
    # TEAM NORMALIZATION
    # ============================================================

    def _normalize_team(
        self,
        team_block: Dict[str, Any],
    ) -> Dict[str, Any]:

        players_out = []

        for p in team_block.get("players", {}).values():

            person = p.get("person", {})
            batting = p.get("stats", {}).get("batting", {})

            if not batting:
                continue

            players_out.append(
                {
                    "player_id": person.get("id"),
                    "name": person.get("fullName"),
                    "position": p.get("position", {}).get("abbreviation"),
                    "batting_order": p.get("battingOrder"),

                    "ab": batting.get("atBats", 0),
                    "hits": batting.get("hits", 0),
                    "hr": batting.get("homeRuns", 0),
                    "rbi": batting.get("rbi", 0),
                    "bb": batting.get("baseOnBalls", 0),
                    "so": batting.get("strikeOuts", 0),
                }
            )

        return {
            "team_id": team_block.get("team", {}).get("id"),
            "team_name": team_block.get("team", {}).get("name"),
            "players": players_out,
        }

    # ============================================================
    # PLAYER GAME LOGS
    # ============================================================

    def get_player_game_logs(
        self,
        player_id: int,
        season: str = "2026",
    ) -> List[Dict[str, Any]]:

        payload = self._get(
            f"/people/{player_id}/stats",
            params={
                "stats": "gameLog",
                "group": "hitting",
                "season": season,
            },
        )

        logs = []

        for block in payload.get("stats", []):
            for split in block.get("splits", []):

                s = split.get("stat", {})

                logs.append(
                    {
                        "date": split.get("date"),
                        "ab": s.get("atBats", 0),
                        "hits": s.get("hits", 0),
                        "hr": s.get("homeRuns", 0),
                        "rbi": s.get("rbi", 0),
                        "bb": s.get("baseOnBalls", 0),
                        "so": s.get("strikeOuts", 0),
                        "avg": s.get("avg"),
                        "slg": s.get("slg"),
                        "ops": s.get("ops"),
                    }
                )

        return logs

    # ============================================================
    # TEAM ROSTER
    # ============================================================

    def get_team_roster(
        self,
        team_id: int,
    ) -> List[Dict[str, Any]]:

        payload = self._get(f"/teams/{team_id}/roster")

        roster = []

        for p in payload.get("roster", []):

            person = p.get("person", {})

            roster.append(
                {
                    "player_id": person.get("id"),
                    "name": person.get("fullName"),
                    "position": p.get("position", {}).get("abbreviation"),
                }
            )

        return roster

    # ============================================================
    # STARTING LINEUP
    # ============================================================

    def get_starting_lineup(
        self,
        game_id: int,
    ) -> Dict[str, List[Dict[str, Any]]]:

        box = self.get_boxscore(game_id)

        return {
            "home": self._extract_lineup(box["home"]),
            "away": self._extract_lineup(box["away"]),
        }

    def _extract_lineup(
        self,
        team: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        players = team.get("players", [])

        lineup = []

        for p in players:

            order = p.get("batting_order")

            if not order:
                continue

            try:
                slot = int(str(order)[0])
            except Exception:
                continue

            lineup.append(
                {
                    "player_id": p.get("player_id"),
                    "name": p.get("name"),
                    "lineup_slot": slot,
                }
            )

        lineup.sort(key=lambda x: x["lineup_slot"])

        return lineup
