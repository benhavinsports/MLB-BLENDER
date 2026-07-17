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
    barrel_percent: float | None,
) -> dict:
    """Translate raw Savant batted-ball rates into Blender pull fields.

    Savant's ``pull_percent`` is a raw batted-ball share (normally around
    30-50), while the engine's ``pull`` field is a 0-100 pull-air identity
    index. Feeding the raw rate directly into Gate 3 caused complete pools to
    be removed by the engine's >=50 floor.

    The index preserves the locked Blender support lanes:
      raw pull 45, fly-ball 40, pull-air 28, pull-barrel 10.
    Reaching all four support marks produces a 65 PASS profile. Missing data
    is reweighted rather than treated as zero.
    """
    pua = None
    if pull_percent is not None and flyball_percent is not None:
        pua = pull_percent * flyball_percent / 100.0

    pull_barrel = None
    if pull_percent is not None and barrel_percent is not None:
        pull_barrel = pull_percent * barrel_percent / 100.0

    lanes = [
        (pull_percent, 45.0, 0.50),
        (flyball_percent, 40.0, 0.20),
        (pua, 28.0, 0.20),
        (pull_barrel, 10.0, 0.10),
    ]
    available = [(value, floor, weight) for value, floor, weight in lanes if value is not None]
    pull_index = None
    if available:
        total_weight = sum(weight for _, _, weight in available)
        support = sum(
            min(1.55, max(0.0, value / floor)) * weight
            for value, floor, weight in available
        ) / total_weight
        pull_index = round(min(100.0, support * 65.0), 3)

    return {
        "pull": pull_index,
        "pull_percent": pull_percent,
        "pua": round(pua, 3) if pua is not None else None,
        "pull_barrel": round(pull_barrel, 3) if pull_barrel is not None else None,
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
    bat_by_id, bat_by_name = load_bat_tracking_maps(season)

    profile: dict = {}
    normalized_name = _normalize_name(player_name)
    if player_id is not None:
        profile.update(stat_by_id.get(int(player_id), {}))
        profile.update(bat_by_id.get(int(player_id), {}))
    if normalized_name:
        # Name fallback matters because some Savant CSV variants omit player_id.
        for key, value in stat_by_name.get(normalized_name, {}).items():
            profile.setdefault(key, value)
        for key, value in bat_by_name.get(normalized_name, {}).items():
            profile.setdefault(key, value)
    return profile
