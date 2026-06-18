"""
mlb_api.py

Part 1
- Imports
- Exceptions
- MLBAPI class
- Session management
- Production HTTP request handling

MLB Blender Machine v14
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any, Dict, Optional

import requests


BASE_URL = "https://statsapi.mlb.com/api/v1"


# ============================================================
# EXCEPTIONS
# ============================================================

class MLBAPIError(Exception):
    """Base MLB API exception."""


class MLBRequestError(MLBAPIError):
    """Request failure."""


class MLBDataError(MLBAPIError):
    """Unexpected API payload."""


# ============================================================
# API CLIENT
# ============================================================

class MLBAPI:
    """
    Production MLB Stats API client.

    Features:
    - retries
    - timeout protection
    - rate-limit handling
    - normalized JSON responses
    """

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
                "User-Agent":
                "MLBBlenderMachine/14.0"
            }
        )

    # ========================================================
    # INTERNAL REQUEST HANDLER
    # ========================================================

    def _get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        url = f"{BASE_URL}{endpoint}"

        last_exception = None

        for attempt in range(self.retries):

            try:

                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                )

                # Rate limit handling
                if response.status_code == 429:

                    sleep_time = (
                        self.backoff
                        * (attempt + 1)
                    )

                    time.sleep(sleep_time)
                    continue

                response.raise_for_status()

                payload = response.json()

                if not isinstance(payload, dict):

                    raise MLBDataError(
                        f"Unexpected payload type "
                        f"from {url}"
                    )

                return payload

            except requests.RequestException as exc:

                last_exception = exc

                if attempt < self.retries - 1:

                    sleep_time = (
                        self.backoff
                        * (attempt + 1)
                    )

                    time.sleep(sleep_time)

                else:
                    break

        raise MLBRequestError(
            f"Request failed: {url}"
        ) from last_exception

    # ========================================================
    # HEALTH CHECK
    # ========================================================

    def ping(self) -> bool:
        """
        Verifies MLB API availability.
        """

        try:

            payload = self._get(
                "/sports"
            )

            return bool(payload)

        except Exception:
            return False

    # ========================================================
    # DATE HELPERS
    # ========================================================

    @staticmethod
    def today() -> str:
        """
        Returns today's date
        in MLB API format.
        """

        return date.today().isoformat()

# ============================================================
# SCHEDULE
# ============================================================

    def get_schedule(
        self,
        target_date: Optional[str] = None,
    ) -> list[dict]:
        """
        Returns normalized MLB schedule.

        Output:
        [
            {
                "game_id": 123,
                "game_date": "2026-06-18",
                "game_datetime": "...",
                "status": "...",
                "away_team_id": 111,
                "away_team_name": "...",
                "home_team_id": 222,
                "home_team_name": "..."
            }
        ]
        """

        if target_date is None:
            target_date = self.today()

        payload = self._get(
            "/schedule",
            params={
                "sportId": 1,
                "date": target_date,
            },
        )

        schedule = []

        for date_block in payload.get(
            "dates",
            [],
        ):

            for game in date_block.get(
                "games",
                [],
            ):

                away = (
                    game.get("teams", {})
                    .get("away", {})
                )

                home = (
                    game.get("teams", {})
                    .get("home", {})
                )

                schedule.append(
                    {
                        "game_id":
                            game.get("gamePk"),
                        "game_date":
                            target_date,
                        "game_datetime":
                            game.get(
                                "gameDate"
                            ),
                        "status":
                            game.get(
                                "status",
                                {},
                            ).get(
                                "detailedState"
                            ),
                        "away_team_id":
                            away.get(
                                "team",
                                {},
                            ).get("id"),
                        "away_team_name":
                            away.get(
                                "team",
                                {},
                            ).get("name"),
                        "home_team_id":
                            home.get(
                                "team",
                                {},
                            ).get("id"),
                        "home_team_name":
                            home.get(
                                "team",
                                {},
                            ).get("name"),
                    }
                )

        return schedule


# ============================================================
# PLAYER NORMALIZATION
# ============================================================

    def _normalize_player(
        self,
        player_data: Dict[str, Any],
    ) -> Dict[str, Any]:

        person = player_data.get(
            "person",
            {}
        )

        batting = (
            player_data.get(
                "stats",
                {},
            )
            .get(
                "batting",
                {},
            )
        )

        return {
            "player_id":
                person.get("id"),

            "name":
                person.get(
                    "fullName"
                ),

            "position":
                player_data.get(
                    "position",
                    {},
                ).get(
                    "abbreviation"
                ),

            "batting_order":
                player_data.get(
                    "battingOrder"
                ),

            "ab":
                batting.get(
                    "atBats",
                    0,
                ),

            "hits":
                batting.get(
                    "hits",
                    0,
                ),

            "hr":
                batting.get(
                    "homeRuns",
                    0,
                ),

            "rbi":
                batting.get(
                    "rbi",
                    0,
                ),

            "bb":
                batting.get(
                    "baseOnBalls",
                    0,
                ),

            "so":
                batting.get(
                    "strikeOuts",
                    0,
                ),
        }


# ============================================================
# TEAM NORMALIZATION
# ============================================================

    def _normalize_team(
        self,
        team_payload: Dict[str, Any],
    ) -> Dict[str, Any]:

        players = []

        for player in (
            team_payload.get(
                "players",
                {}
            ).values()
        ):

            players.append(
                self._normalize_player(
                    player
                )
            )

        return {
            "team_id":
                team_payload.get(
                    "team",
                    {},
                ).get("id"),

            "team_name":
                team_payload.get(
                    "team",
                    {},
                ).get("name"),

            "players":
                players,
        }


# ============================================================
# BOXSCORE
# ============================================================

    def get_boxscore(
        self,
        game_id: int,
    ) -> Dict[str, Any]:
        """
        Returns normalized boxscore.

        Output:
        {
            "game_id": ...,
            "home": {...},
            "away": {...}
        }
        """

        payload = self._get(
            f"/game/{game_id}/boxscore"
        )

        teams = payload.get(
            "teams"
        )

        if not teams:

            raise MLBDataError(
                f"No teams found for "
                f"game {game_id}"
            )

        return {
            "game_id":
                game_id,

            "home":
                self._normalize_team(
                    teams["home"]
                ),

            "away":
                self._normalize_team(
                    teams["away"]
                ),
        }

# ============================================================
# PLAYER GAME LOGS
# ============================================================

    def get_player_game_logs(
        self,
        player_id: int,
        days_back: int = 30,
    ) -> list[dict]:
        """
        Returns normalized hitter game logs.
        """

        payload = self._get(
            f"/people/{player_id}/stats",
            params={
                "stats": "gameLog",
                "group": "hitting",
                "season": "2026",
            },
        )

        logs = []

        for stat_block in payload.get(
            "stats",
            [],
        ):

            for split in stat_block.get(
                "splits",
                [],
            ):

                stat = split.get(
                    "stat",
                    {},
                )

                logs.append(
                    {
                        "date":
                            split.get(
                                "date"
                            ),

                        "ab":
                            stat.get(
                                "atBats",
                                0,
                            ),

                        "hits":
                            stat.get(
                                "hits",
                                0,
                            ),

                        "hr":
                            stat.get(
                                "homeRuns",
                                0,
                            ),

                        "rbi":
                            stat.get(
                                "rbi",
                                0,
                            ),

                        "bb":
                            stat.get(
                                "baseOnBalls",
                                0,
                            ),

                        "so":
                            stat.get(
                                "strikeOuts",
                                0,
                            ),

                        "avg":
                            stat.get(
                                "avg",
                            ),

                        "slg":
                            stat.get(
                                "slg",
                            ),

                        "ops":
                            stat.get(
                                "ops",
                            ),
                    }
                )

        return logs


# ============================================================
# TEAM ROSTER
# ============================================================

    def get_team_roster(
        self,
        team_id: int,
    ) -> list[dict]:
        """
        Returns full team roster.
        """

        payload = self._get(
            f"/teams/{team_id}/roster",
        )

        roster = []

        for player in payload.get(
            "roster",
            [],
        ):

            person = player.get(
                "person",
                {},
            )

            roster.append(
                {
                    "player_id":
                        person.get("id"),

                    "name":
                        person.get(
                            "fullName"
                        ),

                    "position":
                        player.get(
                            "position",
                            {},
                        ).get(
                            "abbreviation"
                        ),
                }
            )

        return roster


# ============================================================
# STARTING LINEUP
# ============================================================

    def get_starting_lineup(
        self,
        game_id: int,
    ) -> dict:
        """
        Extracts starting lineup from boxscore.
        """

        box = self.get_boxscore(
            game_id
        )

        def extract(team: dict) -> list[dict]:

            players = team.get(
                "players",
                [],
            )

            lineup = []

            for p in players:

                order = p.get(
                    "batting_order"
                )

                if not order:
                    continue

                try:
                    slot = int(
                        str(order)[0]
                    )
                except Exception:
                    continue

                lineup.append(
                    {
                        "player_id":
                            p.get(
                                "player_id"
                            ),

                        "name":
                            p.get(
                                "name"
                            ),

                        "lineup_slot":
                            slot,
                    }
                )

            lineup.sort(
                key=lambda x: x[
                    "lineup_slot"
                ]
            )

            return lineup

        return {
            "home":
                extract(
                    box["home"]
                ),

            "away":
                extract(
                    box["away"]
                ),
        }

# ============================================================
# CONTINUATION — LINEUP NORMALIZATION + FINAL HELPERS
# ============================================================

    def _normalize_lineup(
        self,
        team_block: dict,
    ) -> list[dict]:
        """
        Converts raw team boxscore players into
        clean lineup-ready hitters.
        """

        players = team_block.get(
            "players",
            {}
        )

        normalized = []

        for p in players.values():

            person = p.get(
                "person",
                {}
            )

            stats = p.get(
                "stats",
                {}
            ).get(
                "batting",
                {}
            )

            if not stats:
                continue

            normalized.append(
                {
                    "player_id":
                        person.get("id"),

                    "name":
                        person.get(
                            "fullName"
                        ),

                    "position":
                        p.get(
                            "position",
                            {},
                        ).get(
                            "abbreviation"
                        ),

                    "batting_order":
                        p.get(
                            "battingOrder"
                        ),

                    "ab":
                        stats.get(
                            "atBats",
                            0,
                        ),

                    "hits":
                        stats.get(
                            "hits",
                            0,
                        ),

                    "hr":
                        stats.get(
                            "homeRuns",
                            0,
                        ),

                    "rbi":
                        stats.get(
                            "rbi",
                            0,
                        ),

                    "bb":
                        stats.get(
                            "baseOnBalls",
                            0,
                        ),

                    "so":
                        stats.get(
                            "strikeOuts",
                            0,
                        ),
                }
            )

        return normalized


# ============================================================
# STARTING LINEUP (IMPROVED SAFE VERSION)
# ============================================================

    def get_starting_lineup(
        self,
        game_id: int,
    ) -> dict:
        """
        Returns cleaned starting lineups
        for both teams.
        """

        box = self.get_boxscore(
            game_id
        )

        return {
            "home":
                self._extract_lineup(
                    box["home"]
                ),

            "away":
                self._extract_lineup(
                    box["away"]
                ),
        }


    def _extract_lineup(
        self,
        team: dict,
    ) -> list[dict]:
        """
        Safe lineup extraction fallback.
        """

        players = team.get(
            "players",
            [],
        )

        lineup = []

        for p in players:

            order = p.get(
                "batting_order"
            )

            if not order:
                continue

            try:
                slot = int(
                    str(order)[0]
                )
            except Exception:
                continue

            lineup.append(
                {
                    "player_id":
                        p.get(
                            "player_id"
                        ),

                    "name":
                        p.get("name"),

                    "lineup_slot":
                        slot,
                }
            )

        lineup.sort(
            key=lambda x: x[
                "lineup_slot"
            ]
        )

        return lineup


# ============================================================
# FINAL HELPER (OPTIONAL SAFETY)
# ============================================================

    def safe_get(
        self,
        endpoint: str,
        params: dict | None = None,
    ) -> dict:
        """
        Wrapper around _get with fallback safety.
        """

        try:
            return self._get(
                endpoint,
                params=params,
            )
        except Exception:
            return {}

def get_today_games_bundle(self):
    """
    Returns full today's game dataset:
    schedule + boxscores (basic bundle for engine)
    """

    today = self.today()

    schedule = self.get_schedule(today)

    games = []

    for g in schedule:

        game_id = g.get("game_id")

        try:
            box = self.get_boxscore(game_id)
        except Exception:
            box = None

        games.append(
            {
                "game_id": game_id,
                "matchup": f"{g.get('away_team_name')} @ {g.get('home_team_name')}",
                "status": g.get("status"),
                "boxscore": box,
            }
        )

    return {
        "date": today,
        "games": games,
    }
