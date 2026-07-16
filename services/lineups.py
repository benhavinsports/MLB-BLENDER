from __future__ import annotations

from services.http import get_json

FEED_URL = "https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live"
BOXSCORE_URL = "https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"


def _slot(value, fallback: int) -> int:
    try:
        number = int(str(value))
        if number >= 100:
            number //= 100
        return number if 1 <= number <= 9 else fallback
    except (TypeError, ValueError):
        return fallback


def _person_name(record: dict) -> str | None:
    person = record.get("person") or {}
    return person.get("fullName") or person.get("name") or record.get("fullName")


def _player_record(players_map: dict, player_id) -> dict:
    if not player_id:
        return {}
    direct = (
        players_map.get(f"ID{player_id}")
        or players_map.get(str(player_id))
        or players_map.get(player_id)
    )
    if isinstance(direct, dict):
        return direct
    for record in players_map.values():
        if not isinstance(record, dict):
            continue
        person = record.get("person") or {}
        if str(person.get("id")) == str(player_id):
            return record
    return {}


def _ordered_player_ids(team_data: dict) -> list:
    """
    Use MLB's actual starting batting order first.

    `battingOrder` is the reliable pregame/start-of-game list. `batters`
    can be incomplete or represent players who have appeared, depending on
    game state, so it is only a fallback.
    """
    order = team_data.get("battingOrder") or []
    if order:
        return list(order)[:9]

    batters = team_data.get("batters") or []
    if batters:
        return list(batters)[:9]

    players_map = team_data.get("players") or {}
    ordered: list[tuple[int, int]] = []
    for record in players_map.values():
        if not isinstance(record, dict):
            continue
        batting_order = record.get("battingOrder")
        person = record.get("person") or {}
        player_id = person.get("id")
        if batting_order and player_id:
            ordered.append((_slot(batting_order, 99), player_id))
    ordered.sort(key=lambda item: item[0])
    return [player_id for slot, player_id in ordered if 1 <= slot <= 9][:9]


def _extract_team(team_data: dict, team_name: str, side: str) -> list[dict]:
    players_map = team_data.get("players") or {}
    player_ids = _ordered_player_ids(team_data)
    hitters: list[dict] = []
    seen: set[str] = set()

    for fallback, player_id in enumerate(player_ids, 1):
        record = _player_record(players_map, player_id)
        person = record.get("person") or {}
        resolved_id = person.get("id") or player_id
        name = _person_name(record)
        position = ((record.get("position") or {}).get("abbreviation") or "").upper()

        if not resolved_id or not name:
            continue
        if position in {"P", "SP", "RP"}:
            continue

        key = str(resolved_id)
        if key in seen:
            continue
        seen.add(key)

        hitters.append({
            "id": resolved_id,
            "name": name,
            "player": name,
            "team": team_name,
            "side": side,
            "slot": _slot(record.get("battingOrder"), fallback),
            "position": position or "UNKNOWN",
            "handedness": None,
        })

    return hitters


def _extract_boxscore(feed: dict, game_id) -> dict:
    boxscore = ((feed.get("liveData") or {}).get("boxscore") or {})
    if boxscore:
        return boxscore
    return get_json(BOXSCORE_URL.format(game_id=game_id))


def build_game_pool(game: dict) -> list[dict]:
    """
    Load both official starting lineups for a game.

    The function refuses to silently return a one-team pool. If one side is
    missing, it retries the dedicated boxscore endpoint before returning.
    """
    game_id = game.get("game_id") or game.get("gamePk")
    if not game_id:
        return []

    feed = get_json(FEED_URL.format(game_id=game_id))
    boxscore = _extract_boxscore(feed, game_id)
    teams = boxscore.get("teams") or {}

    away = _extract_team(
        teams.get("away") or {},
        game.get("away", "AWAY"),
        "away",
    )
    home = _extract_team(
        teams.get("home") or {},
        game.get("home", "HOME"),
        "home",
    )

    # Dedicated endpoint retry when one side is missing from the live feed.
    if not away or not home:
        retry = get_json(BOXSCORE_URL.format(game_id=game_id))
        retry_teams = retry.get("teams") or {}
        if not away:
            away = _extract_team(
                retry_teams.get("away") or {},
                game.get("away", "AWAY"),
                "away",
            )
        if not home:
            home = _extract_team(
                retry_teams.get("home") or {},
                game.get("home", "HOME"),
                "home",
            )

    return away + home
