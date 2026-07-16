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
    return person.get("fullName") or person.get("name")


def _extract_team(team_data: dict, team_name: str, side: str) -> list[dict]:
    players_map = team_data.get("players") or {}
    batter_ids = team_data.get("batters") or []
    ordered: list[tuple[int, dict]] = []

    if batter_ids:
        for idx, player_id in enumerate(batter_ids, 1):
            record = players_map.get(f"ID{player_id}") or players_map.get(str(player_id)) or {}
            if record:
                ordered.append((idx, record))
    else:
        for record in players_map.values():
            if record.get("battingOrder"):
                ordered.append((_slot(record.get("battingOrder"), 99), record))
        ordered.sort(key=lambda item: item[0])

    hitters: list[dict] = []
    seen: set[str] = set()
    for fallback, record in ordered:
        person = record.get("person") or {}
        player_id = person.get("id")
        name = _person_name(record)
        position = ((record.get("position") or {}).get("abbreviation") or "").upper()
        if not player_id or not name or position in {"P", "SP", "RP"}:
            continue
        key = str(player_id)
        if key in seen:
            continue
        seen.add(key)
        hitters.append({
            "id": player_id,
            "name": name,
            "player": name,
            "team": team_name,
            "side": side,
            "slot": _slot(record.get("battingOrder"), fallback),
            "position": position or "UNKNOWN",
            "handedness": None,
        })
    return hitters


def build_game_pool(game: dict) -> list[dict]:
    game_id = game.get("game_id") or game.get("gamePk")
    if not game_id:
        return []

    feed = get_json(FEED_URL.format(game_id=game_id))
    boxscore = ((feed.get("liveData") or {}).get("boxscore") or {})
    if not boxscore:
        boxscore = get_json(BOXSCORE_URL.format(game_id=game_id))

    teams = boxscore.get("teams") or {}
    away = _extract_team(teams.get("away") or {}, game.get("away", "AWAY"), "away")
    home = _extract_team(teams.get("home") or {}, game.get("home", "HOME"), "home")
    return away + home
