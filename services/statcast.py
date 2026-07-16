from __future__ import annotations

import csv
import io
from functools import lru_cache

from services.http import get_text

CUSTOM_URL = "https://baseballsavant.mlb.com/leaderboard/custom"
BAT_URL = "https://baseballsavant.mlb.com/leaderboard/bat-tracking"


def _number(value):
    if value in (None, "", "--", "-"):
        return None
    try:
        return float(str(value).replace("%", "").replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _key(row: dict, *names: str):
    lowered = {str(k).strip().lower(): v for k, v in row.items()}
    for name in names:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return None


def _read_csv(text: str) -> list[dict]:
    if not text or "<html" in text.lower():
        return []
    return list(csv.DictReader(io.StringIO(text)))


@lru_cache(maxsize=8)
def load_statcast_hitter_map(season: int) -> dict[int, dict]:
    params = {
        "year": season,
        "type": "batter",
        "min": 1,
        "csv": "true",
        "selections": ",".join([
            "pa", "home_run", "batting_avg", "slg_percent", "woba",
            "isolated_power", "exit_velocity_avg", "barrel_batted_rate",
            "hard_hit_percent", "sweet_spot_percent", "pull_percent",
            "flyballs_percent"
        ]),
    }
    rows = _read_csv(get_text(CUSTOM_URL, params=params))
    result: dict[int, dict] = {}
    for row in rows:
        player_id = _number(_key(row, "player_id", "player id", "id"))
        if player_id is None:
            continue
        pa = _number(_key(row, "pa"))
        hr = _number(_key(row, "home_run", "hr"))
        result[int(player_id)] = {
            "pa": pa,
            "hr": hr,
            "hr_pa": (hr / pa) if hr is not None and pa else None,
            "pull": _number(_key(row, "pull_percent", "pull %", "pull%")),
            "hard_hit": _number(_key(row, "hard_hit_percent", "hard hit %", "hard hit%")),
            "barrel": _number(_key(row, "barrel_batted_rate", "barrel%", "barrels/pa %", "brls/bbe %")),
            "ev": _number(_key(row, "exit_velocity_avg", "avg ev (mph)", "avg exit velocity")),
            "sweet_spot": _number(_key(row, "sweet_spot_percent", "la sweet-spot %", "sweet spot %")),
            "fb": _number(_key(row, "flyballs_percent", "fb%", "fb %")),
            "iso": _number(_key(row, "isolated_power", "iso")),
            "slg": _number(_key(row, "slg_percent", "slg")),
            "woba": _number(_key(row, "woba")),
        }
    return result


@lru_cache(maxsize=8)
def load_bat_tracking_map(season: int) -> dict[int, dict]:
    params = {
        "type": "batter", "seasonStart": season, "seasonEnd": season,
        "minSwings": 1, "csv": "true",
    }
    rows = _read_csv(get_text(BAT_URL, params=params))
    result: dict[int, dict] = {}
    for row in rows:
        player_id = _number(_key(row, "player_id", "player id", "id"))
        if player_id is None:
            continue
        result[int(player_id)] = {
            "bat_speed": _number(_key(row, "avg_bat_speed", "avg. bat speed", "avg bat speed")),
            "fast_swing": _number(_key(row, "fast_swing_rate", "fast swing rate")),
            "squared_up": _number(_key(row, "squared_up_per_swing", "squared-up % swing", "squared-up")),
            "blast": _number(_key(row, "blast_per_swing", "blasts % swing", "blast %")),
        }
    return result
