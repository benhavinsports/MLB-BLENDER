from __future__ import annotations

import csv
import io
import re
import unicodedata
from functools import lru_cache

from services.http import get_text

CUSTOM_CSV_URL = "https://baseballsavant.mlb.com/leaderboard/custom.csv"
CUSTOM_PAGE_URL = "https://baseballsavant.mlb.com/leaderboard/custom"
STATCAST_URL = "https://baseballsavant.mlb.com/leaderboard/statcast"
BAT_TRACKING_URL = "https://baseballsavant.mlb.com/leaderboard/bat-tracking"
BATTED_BALL_URL = "https://baseballsavant.mlb.com/leaderboard/batted-ball"


def _number(value):
    if value in (None, "", "--", "-", "null", "NULL"):
        return None
    try:
        return float(
            str(value)
            .replace("%", "")
            .replace(",", "")
            .replace("\ufeff", "")
            .strip()
        )
    except (TypeError, ValueError):
        return None


def _normalize_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _normalize_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9 ]+", " ", text).lower()
    text = re.sub(r"\s+", " ", text).strip()

    # Savant frequently returns "Last, First".
    raw = str(value or "")
    if "," in raw:
        last, first = raw.split(",", 1)
        reordered = f"{first.strip()} {last.strip()}"
        text = unicodedata.normalize("NFKD", reordered)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"[^a-zA-Z0-9 ]+", " ", text).lower()
        text = re.sub(r"\s+", " ", text).strip()
    return text


def _row_map(row: dict) -> dict:
    return {_normalize_header(k): v for k, v in row.items()}


def _key(row: dict, *names: str):
    mapped = _row_map(row)
    for name in names:
        key = _normalize_header(name)
        if key in mapped:
            return mapped[key]
    return None


def _read_csv(text: str) -> list[dict]:
    if not text:
        return []
    cleaned = text.lstrip("\ufeff").strip()
    if not cleaned or "<html" in cleaned[:500].lower() or "<!doctype" in cleaned[:500].lower():
        return []
    try:
        return [dict(row) for row in csv.DictReader(io.StringIO(cleaned))]
    except Exception:
        return []


def _first_csv(url_param_pairs: list[tuple[str, dict]]) -> list[dict]:
    for url, params in url_param_pairs:
        rows = _read_csv(get_text(url, params=params, timeout=45))
        if rows:
            return rows
    return []


def _blender_pull_profile(
    pull_percent: float | None,
    flyball_percent: float | None,
    pull_air_percent: float | None = None,
    pull_barrel_percent: float | None = None,
) -> dict:
    """Build the Blender pull-air index from real rate fields only.

    ``pull`` is the engine's 0-100 identity index. Raw Savant Pull% is not
    placed directly into that field because the engine's locked thresholds
    (50/55/65/70) are index thresholds, not league-scale raw Pull%.

    Important: do not manufacture Pull AIR% or Pull Barrel% by multiplying
    unrelated season rates. Those products crushed Gate 3 and are not the
    Statcast measures the gate is supposed to use. When the dedicated
    batted-ball feed is unavailable, the index is reweighted across the real
    Pull% and FB% values that are actually present.
    """
    lanes = [
        (pull_percent, 45.0, 0.55),
        (flyball_percent, 40.0, 0.20),
        (pull_air_percent, 28.0, 0.20),
        (pull_barrel_percent, 10.0, 0.05),
    ]
    available = [(value, floor, weight) for value, floor, weight in lanes if value is not None]
    pull_index = None
    if available:
        total_weight = sum(weight for _, _, weight in available)
        support = sum(
            min(1.55, max(0.0, float(value) / floor)) * weight
            for value, floor, weight in available
        ) / total_weight
        # Reaching every available support mark equals the locked 65 PASS lane.
        pull_index = round(min(100.0, support * 65.0), 3)

    return {
        "pull": pull_index,
        "pull_percent": pull_percent,
        "pua": pull_air_percent,
        "pull_barrel": pull_barrel_percent,
    }


def _identity(row: dict) -> tuple[int | None, str]:
    player_id = _number(
        _key(
            row,
            "player_id",
            "player id",
            "id",
            "batter",
            "batter_id",
            "mlbamid",
            "mlb_id",
        )
    )
    name = _key(row, "player_name", "player name", "name", "last_name, first_name", "player")
    return (int(player_id) if player_id is not None else None, _normalize_name(name))


def _put(result_by_id: dict[int, dict], result_by_name: dict[str, dict], row: dict, metrics: dict):
    player_id, player_name = _identity(row)
    clean = {k: v for k, v in metrics.items() if v is not None}
    if not clean:
        return
    if player_id is not None:
        result_by_id.setdefault(player_id, {}).update(clean)
    if player_name:
        result_by_name.setdefault(player_name, {}).update(clean)


@lru_cache(maxsize=8)
def load_statcast_hitter_maps(season: int) -> tuple[dict[int, dict], dict[str, dict]]:
    selections = ",".join(
        [
            "pa",
            "home_run",
            "batting_avg",
            "slg_percent",
            "woba",
            "isolated_power",
            "exit_velocity_avg",
            "barrel_batted_rate",
            "hard_hit_percent",
            "sweet_spot_percent",
            "pull_percent",
            "flyballs_percent",
        ]
    )
    common = {
        "year": season,
        "type": "batter",
        "min": 1,
        "filter": "",
        "selections": selections,
        "chart": "false",
        "x": "pa",
        "y": "pa",
        "r": "no",
        "chartType": "beeswarm",
        "sort": "hard_hit_percent",
        "sortDir": "desc",
    }

    # custom.csv is the actual Savant download route. The page routes are kept
    # as fallbacks because MLB occasionally changes which one honors csv=true.
    rows = _first_csv(
        [
            (CUSTOM_CSV_URL, common),
            (CUSTOM_PAGE_URL, {**common, "csv": "true"}),
            (STATCAST_URL, {"type": "batter", "year": season, "min": 1, "csv": "true"}),
        ]
    )

    by_id: dict[int, dict] = {}
    by_name: dict[str, dict] = {}
    for row in rows:
        pa = _number(_key(row, "pa", "plate appearances"))
        hr = _number(_key(row, "home_run", "home runs", "hr"))
        pull_percent = _number(_key(row, "pull_percent", "pull %", "pull%"))
        hard_hit = _number(_key(row, "hard_hit_percent", "hard hit %", "hardhit%"))
        barrel = _number(
            _key(row, "barrel_batted_rate", "barrel %", "barrel%", "brls/bbe %")
        )
        flyball = _number(_key(row, "flyballs_percent", "fb%", "fb %"))
        pull_profile = _blender_pull_profile(pull_percent, flyball, barrel)
        _put(
            by_id,
            by_name,
            row,
            {
                "pa": pa,
                "hr": hr,
                "hr_pa": (hr / pa) if hr is not None and pa else None,
                **pull_profile,
                "hard_hit": hard_hit,
                "barrel": barrel,
                "ev": _number(
                    _key(row, "exit_velocity_avg", "avg ev (mph)", "avg exit velocity", "avg ev")
                ),
                "sweet_spot": _number(
                    _key(row, "sweet_spot_percent", "la sweet-spot %", "sweet spot %", "la swsp%")
                ),
                "fb": flyball,
                "iso": _number(_key(row, "isolated_power", "iso")),
                "slg": _number(_key(row, "slg_percent", "slg")),
                "woba": _number(_key(row, "woba")),
            },
        )
    return by_id, by_name


@lru_cache(maxsize=8)
def load_batted_ball_maps(season: int) -> tuple[dict[int, dict], dict[str, dict]]:
    """Load real Pull AIR% from Savant's batted-ball profile leaderboard."""
    rows = _first_csv(
        [
            (
                BATTED_BALL_URL,
                {
                    "csv": "true",
                    "type": "batter",
                    "seasonStart": season,
                    "seasonEnd": season,
                    "gameType": "Regular",
                    "minSwings": 1,
                    "minGroupSwings": 1,
                    "sortColumn": "pull_air_rate",
                    "sortDirection": "desc",
                },
            ),
        ]
    )

    by_id: dict[int, dict] = {}
    by_name: dict[str, dict] = {}
    for row in rows:
        pull_percent = _number(
            _key(row, "pull_rate", "pull_percent", "pull %", "pull%")
        )
        flyball_percent = _number(
            _key(row, "fly_ball_rate", "flyballs_percent", "fb %", "fb%")
        )
        pull_air_percent = _number(
            _key(
                row,
                "pull_air_rate",
                "pull air %",
                "pull air%",
                "pull_air_percent",
            )
        )
        pull_barrel_percent = _number(
            _key(row, "pull_barrel_rate", "pull barrel %", "pull_barrel_percent")
        )
        _put(
            by_id,
            by_name,
            row,
            {
                **_blender_pull_profile(
                    pull_percent,
                    flyball_percent,
                    pull_air_percent,
                    pull_barrel_percent,
                ),
                "fb": flyball_percent,
                "pull_air_source": "SAVANT_BATTED_BALL_PROFILE",
            },
        )
    return by_id, by_name


@lru_cache(maxsize=8)
def load_bat_tracking_maps(season: int) -> tuple[dict[int, dict], dict[str, dict]]:
    rows = _first_csv(
        [
            (
                BAT_TRACKING_URL,
                {
                    "type": "batter",
                    "year": season,
                    "minSwings": 1,
                    "csv": "true",
                },
            ),
            (
                BAT_TRACKING_URL,
                {
                    "type": "batter",
                    "seasonStart": season,
                    "seasonEnd": season,
                    "minSwings": 1,
                    "minGroupSwings": 1,
                    "csv": "true",
                },
            ),
        ]
    )

    by_id: dict[int, dict] = {}
    by_name: dict[str, dict] = {}
    for row in rows:
        _put(
            by_id,
            by_name,
            row,
            {
                "bat_speed": _number(
                    _key(row, "avg_bat_speed", "avg. bat speed", "avg bat speed", "average bat speed")
                ),
                "fast_swing": _number(
                    _key(row, "fast_swing_rate", "fast swing rate", "fast swing %")
                ),
                "squared_up": _number(
                    _key(
                        row,
                        "squared_up_per_swing",
                        "squared-up % swing",
                        "squared-up",
                        "squared_up_with_speed",
                        "squared up rate",
                    )
                ),
                "blast": _number(
                    _key(row, "blast_per_swing", "blasts % swing", "blast %", "blast rate")
                ),
            },
        )
    return by_id, by_name


# Backward-compatible wrappers used by older V5 code.
def load_statcast_hitter_map(season: int) -> dict[int, dict]:
    return load_statcast_hitter_maps(season)[0]


def load_bat_tracking_map(season: int) -> dict[int, dict]:
    return load_bat_tracking_maps(season)[0]


def get_hitter_statcast_profile(player_id: int | None, player_name: str | None, season: int) -> dict:
    stat_by_id, stat_by_name = load_statcast_hitter_maps(season)
    batted_by_id, batted_by_name = load_batted_ball_maps(season)
    bat_by_id, bat_by_name = load_bat_tracking_maps(season)

    profile: dict = {}
    normalized_name = _normalize_name(player_name)
    if player_id is not None:
        profile.update(stat_by_id.get(int(player_id), {}))
        # Dedicated batted-ball fields are more authoritative for Pull AIR%.
        profile.update(batted_by_id.get(int(player_id), {}))
        profile.update(bat_by_id.get(int(player_id), {}))
    if normalized_name:
        # Name fallback matters because some Savant CSV variants omit player_id.
        for source in (
            stat_by_name.get(normalized_name, {}),
            batted_by_name.get(normalized_name, {}),
            bat_by_name.get(normalized_name, {}),
        ):
            for key, value in source.items():
                profile.setdefault(key, value)
    return profile
