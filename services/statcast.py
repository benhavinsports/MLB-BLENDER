from __future__ import annotations

import csv
import datetime as dt
import io
import re
import unicodedata
from collections import defaultdict
from functools import lru_cache
from typing import Iterable

from services.http import get_text

CUSTOM_CSV_URL = "https://baseballsavant.mlb.com/leaderboard/custom.csv"
CUSTOM_PAGE_URL = "https://baseballsavant.mlb.com/leaderboard/custom"
STATCAST_URL = "https://baseballsavant.mlb.com/leaderboard/statcast"
BAT_TRACKING_URL = "https://baseballsavant.mlb.com/leaderboard/bat-tracking"
BATTED_BALL_URL = "https://baseballsavant.mlb.com/leaderboard/batted-ball"
PITCH_ARSENAL_URL = "https://baseballsavant.mlb.com/leaderboard/pitch-arsenal-stats"
STATCAST_SEARCH_CSV_URL = "https://baseballsavant.mlb.com/statcast_search/csv"

PITCH_NAME_TO_CODE = {
    "4-seam": "FF",
    "4-seam fastball": "FF",
    "four-seam": "FF",
    "four-seam fastball": "FF",
    "fastball": "FF",
    "sinker": "SI",
    "two-seam": "SI",
    "two-seam fastball": "SI",
    "cutter": "FC",
    "slider": "SL",
    "sweeper": "ST",
    "slurve": "SV",
    "curve": "CU",
    "curveball": "CU",
    "knuckle curve": "KC",
    "change": "CH",
    "changeup": "CH",
    "splitter": "FS",
    "split-finger": "FS",
    "forkball": "FO",
    "knuckleball": "KN",
}


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


def _rate(value):
    """Return a percentage on a 0-100 scale.

    Savant leaderboards are inconsistent: some downloads return 0.347 while
    others return 34.7 for the same rate. The old engine treated 0.347 as
    0.347%, which caused Gate 3 to erase almost every lineup.
    """
    number = _number(value)
    if number is None:
        return None
    if -1.5 <= number <= 1.5:
        number *= 100.0
    return number


def _normalize_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").strip().lower()).strip("_")


def _normalize_name(value: object) -> str:
    raw = str(value or "")
    if "," in raw:
        last, first = raw.split(",", 1)
        raw = f"{first.strip()} {last.strip()}"
    text = unicodedata.normalize("NFKD", raw)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-zA-Z0-9 ]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


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


def _first_csv(url_param_pairs: list[tuple[str, dict | list[tuple[str, object]]]]) -> list[dict]:
    for url, params in url_param_pairs:
        rows = _read_csv(get_text(url, params=params, timeout=60))
        if rows:
            return rows
    return []


def _blender_pull_profile(
    pull_percent: float | None,
    flyball_percent: float | None,
    pull_air_percent: float | None = None,
    pull_barrel_percent: float | None = None,
) -> dict:
    """Build the 0-100 Blender Pull-Air identity index from real rate fields.

    The user's locked 50/55/65/70 thresholds apply to this identity index, not
    raw league-scale Pull%. Hitting every available support mark equals 65.
    """
    lanes = [
        (pull_percent, 45.0, 0.45),
        (flyball_percent, 40.0, 0.20),
        (pull_air_percent, 28.0, 0.30),
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
            "pitcher",
            "pitcher_id",
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
        pull_percent = _rate(_key(row, "pull_percent", "pull %", "pull%"))
        hard_hit = _rate(_key(row, "hard_hit_percent", "hard hit %", "hardhit%"))
        barrel = _rate(_key(row, "barrel_batted_rate", "barrel %", "barrel%", "brls/bbe %"))
        flyball = _rate(_key(row, "flyballs_percent", "fb%", "fb %"))
        _put(
            by_id,
            by_name,
            row,
            {
                "pa": pa,
                "hr": hr,
                "hr_pa": (hr / pa) if hr is not None and pa else None,
                **_blender_pull_profile(pull_percent, flyball),
                "hard_hit": hard_hit,
                "barrel": barrel,
                "ev": _number(_key(row, "exit_velocity_avg", "avg ev (mph)", "avg exit velocity", "avg ev")),
                "sweet_spot": _rate(_key(row, "sweet_spot_percent", "la sweet-spot %", "sweet spot %", "la swsp%")),
                "fb": flyball,
                "iso": _number(_key(row, "isolated_power", "iso")),
                "slg": _number(_key(row, "slg_percent", "slg")),
                "woba": _number(_key(row, "woba")),
            },
        )
    return by_id, by_name


@lru_cache(maxsize=8)
def load_batted_ball_maps(season: int) -> tuple[dict[int, dict], dict[str, dict]]:
    """Load direct Pull AIR% rather than manufacturing it from Pull% x FB%."""
    rows = _first_csv(
        [
            (
                BATTED_BALL_URL,
                {
                    "csv": "true",
                    "type": "batter",
                    "season[]": season,
                    "gameType": "Regular",
                    "sortColumn": "pull_air_rate",
                    "sortDirection": "desc",
                },
            ),
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
        pull_percent = _rate(_key(row, "pull_rate", "pull_percent", "pull %", "pull%"))
        flyball_percent = _rate(_key(row, "fly_ball_rate", "fb_rate", "flyballs_percent", "fb %", "fb%"))
        pull_air_percent = _rate(
            _key(row, "pull_air_rate", "pull air %", "pull air%", "pull_air_percent")
        )
        pull_barrel_percent = _rate(
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
            (BAT_TRACKING_URL, {"type": "batter", "year": season, "minSwings": 1, "csv": "true"}),
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
                "bat_speed": _number(_key(row, "avg_bat_speed", "avg. bat speed", "avg bat speed", "average bat speed")),
                "fast_swing": _rate(_key(row, "fast_swing_rate", "fast swing rate", "fast swing %")),
                "squared_up": _rate(
                    _key(
                        row,
                        "squared_up_per_swing",
                        "squared-up % swing",
                        "squared-up",
                        "squared_up_with_speed",
                        "squared up rate",
                    )
                ),
                "blast": _rate(_key(row, "blast_per_swing", "blasts % swing", "blast %", "blast rate")),
            },
        )
    return by_id, by_name


def _pitch_code(value: object) -> str | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in {"FF", "SI", "FC", "SL", "ST", "SV", "CU", "KC", "CH", "FS", "FO", "KN"}:
        return upper
    return PITCH_NAME_TO_CODE.get(raw.lower())


def _arsenal_row_metrics(row: dict) -> dict:
    return {
        "pitches": _number(_key(row, "pitches", "pitch count", "pitch_count")),
        "usage": _rate(_key(row, "percent", "pitch percent", "pitch_percent", "%")),
        "pa": _number(_key(row, "pa", "plate appearances")),
        "slg": _number(_key(row, "slg")),
        "xslg": _number(_key(row, "xslg", "xslg_percent", "expected slg")),
        "xwoba": _number(_key(row, "xwoba", "expected woba")),
        "hard_hit": _rate(_key(row, "hard_hit_percent", "hard hit %", "hard_hit")),
        "rv100": _number(_key(row, "run_value_per_100", "rv_100", "rv/100", "run value / 100 pitches")),
    }


@lru_cache(maxsize=16)
def load_pitch_arsenal_maps(season: int, player_type: str) -> tuple[dict[int, dict], dict[str, dict]]:
    """Load Savant pitch-type outcomes for every batter or pitcher in one CSV."""
    player_type = "pitcher" if player_type == "pitcher" else "batter"
    common = {
        "csv": "true",
        "type": player_type,
        "year": season,
        "pitchType": "",
        "team": "",
        "min": 1,
        "minPitches": 1,
        "sort": 4,
        "sortDir": "desc",
    }
    rows = _first_csv([(PITCH_ARSENAL_URL, common)])
    by_id: dict[int, dict] = {}
    by_name: dict[str, dict] = {}
    for row in rows:
        player_id, player_name = _identity(row)
        code = _pitch_code(_key(row, "pitch_type", "pitch type", "pitch", "pitch_name"))
        if not code:
            continue
        metrics = {k: v for k, v in _arsenal_row_metrics(row).items() if v is not None}
        if player_id is not None:
            by_id.setdefault(player_id, {})[code] = metrics
        if player_name:
            by_name.setdefault(player_name, {})[code] = metrics
    return by_id, by_name


def _season_window(season: int, as_of: str | None) -> tuple[str, str]:
    try:
        end = dt.date.fromisoformat(str(as_of)[:10]) if as_of else dt.date(season, 10, 1)
    except (TypeError, ValueError):
        end = dt.date(season, 10, 1)
    if end.year != season:
        end = dt.date(season, 10, 1)
    return dt.date(season, 3, 1).isoformat(), end.isoformat()


def _lookup_pairs(key: str, ids: Iterable[int]) -> list[tuple[str, object]]:
    return [(key, str(int(player_id))) for player_id in ids if player_id]


@lru_cache(maxsize=128)
def _detail_rows(
    player_type: str,
    ids: tuple[int, ...],
    season: int,
    as_of: str,
) -> tuple[dict, ...]:
    if not ids:
        return tuple()
    start_date, end_date = _season_window(season, as_of)
    # Keep the full set of blank Statcast Search filters used by the official
    # CSV form/pybaseball. Savant has historically ignored or rejected partial
    # detail queries even when the core lookup fields were valid.
    base: list[tuple[str, object]] = [
        ("all", "true"),
        ("hfPT", ""),
        ("hfAB", ""),
        ("hfBBT", ""),
        ("hfPR", ""),
        ("hfZ", ""),
        ("stadium", ""),
        ("hfBBL", ""),
        ("hfNewZones", ""),
        ("hfGT", "R|"),
        ("hfSea", f"{season}|"),
        ("hfSit", ""),
        ("player_type", player_type),
        ("hfOuts", ""),
        ("opponent", ""),
        ("pitcher_throws", ""),
        ("batter_stands", ""),
        ("hfSA", ""),
        ("game_date_gt", start_date),
        ("game_date_lt", end_date),
        ("team", ""),
        ("position", ""),
        ("hfRO", ""),
        ("home_road", ""),
        ("hfFlag", ""),
        ("metric_1", ""),
        ("hfInn", ""),
        ("min_pitches", 0),
        ("min_results", 0),
        ("group_by", "name"),
        ("sort_col", "pitches"),
        ("player_event_sort", "h_launch_speed"),
        ("sort_order", "desc"),
        ("min_abs", 0),
        ("type", "details"),
    ]
    lookup_keys = ["player_lookup[]"]
    if player_type == "batter":
        lookup_keys.insert(0, "batters_lookup[]")
    else:
        lookup_keys.insert(0, "pitchers_lookup[]")

    attempts = [
        (STATCAST_SEARCH_CSV_URL, base + _lookup_pairs(key, ids))
        for key in lookup_keys
    ]
    rows = _first_csv(attempts)
    return tuple(rows)


def _aggregate_detail_rows(rows: Iterable[dict], id_field: str) -> dict[int, dict]:
    result: dict[int, dict] = {}
    for row in rows:
        player_id = _number(_key(row, id_field, f"{id_field}_id"))
        if player_id is None:
            continue
        player_id = int(player_id)
        profile = result.setdefault(
            player_id,
            {
                "pitch_types": defaultdict(lambda: {"pitches": 0, "bbe": 0, "hr": 0, "xwoba_sum": 0.0, "xwoba_n": 0, "hard_hit": 0}),
                "zones": defaultdict(lambda: {"pitches": 0, "bbe": 0, "hr": 0, "xwoba_sum": 0.0, "xwoba_n": 0, "hard_hit": 0}),
                "total_pitches": 0,
            },
        )
        pitch = _pitch_code(_key(row, "pitch_type", "pitch name", "pitch_name"))
        zone_number = _number(_key(row, "zone"))
        zone = int(zone_number) if zone_number is not None else None
        launch_speed = _number(_key(row, "launch_speed", "exit_velocity"))
        xwoba = _number(_key(row, "estimated_woba_using_speedangle", "estimated_woba"))
        event = str(_key(row, "events", "event") or "").lower()
        is_bbe = launch_speed is not None or str(_key(row, "type") or "").upper() == "X"
        is_hr = event == "home_run"

        profile["total_pitches"] += 1
        buckets = []
        if pitch:
            buckets.append(profile["pitch_types"][pitch])
        if zone is not None:
            buckets.append(profile["zones"][zone])
        for bucket in buckets:
            bucket["pitches"] += 1
            if is_bbe:
                bucket["bbe"] += 1
                if is_hr:
                    bucket["hr"] += 1
                if xwoba is not None:
                    bucket["xwoba_sum"] += xwoba
                    bucket["xwoba_n"] += 1
                if launch_speed is not None and launch_speed >= 95:
                    bucket["hard_hit"] += 1

    for profile in result.values():
        for group_name in ("pitch_types", "zones"):
            cleaned = {}
            for key, raw in profile[group_name].items():
                bbe = raw["bbe"]
                cleaned[key] = {
                    "pitches": raw["pitches"],
                    "bbe": bbe,
                    "hr": raw["hr"],
                    "xwoba": (raw["xwoba_sum"] / raw["xwoba_n"]) if raw["xwoba_n"] else None,
                    "hard_hit": (raw["hard_hit"] / bbe * 100.0) if bbe else None,
                    "hr_bbe": (raw["hr"] / bbe) if bbe else None,
                }
            profile[group_name] = cleaned
    return result


def _performance_score(stats: dict | None) -> float | None:
    if not stats:
        return None
    components: list[tuple[float, float]] = []
    xwoba = stats.get("xwoba")
    if xwoba is not None:
        components.append(((float(xwoba) - 0.320) / 0.090, 0.45))
    xslg = stats.get("xslg")
    slg = xslg if xslg is not None else stats.get("slg")
    if slg is not None:
        components.append(((float(slg) - 0.420) / 0.180, 0.25))
    hard_hit = stats.get("hard_hit")
    if hard_hit is not None:
        components.append(((float(hard_hit) - 40.0) / 18.0, 0.20))
    hr_bbe = stats.get("hr_bbe")
    if hr_bbe is not None:
        components.append(((float(hr_bbe) - 0.045) / 0.050, 0.10))
    rv100 = stats.get("rv100")
    if rv100 is not None and not components:
        components.append((float(rv100) / 2.5, 1.0))
    if not components:
        return None
    weight = sum(w for _, w in components)
    score = sum(value * w for value, w in components) / weight
    return round(max(-3.0, min(3.0, score)), 3)


def _pitch_usage(profile: dict | None, fallback_arsenal: dict | None = None) -> dict[str, float]:
    usage: dict[str, float] = {}
    if profile and profile.get("pitch_types"):
        total = float(profile.get("total_pitches") or 0)
        if total:
            usage = {
                code: float(stats.get("pitches") or 0) / total
                for code, stats in profile["pitch_types"].items()
                if stats.get("pitches")
            }
    if not usage and fallback_arsenal:
        raw = {
            code: float(stats.get("usage") or 0)
            for code, stats in fallback_arsenal.items()
            if stats.get("usage") is not None
        }
        total = sum(raw.values())
        if total:
            usage = {code: value / total for code, value in raw.items()}
    return usage


def _top_weighted_items(usage: dict, *, coverage: float, maximum: int) -> list[tuple[object, float]]:
    ordered = sorted(usage.items(), key=lambda item: item[1], reverse=True)
    selected: list[tuple[object, float]] = []
    covered = 0.0
    for key, weight in ordered:
        selected.append((key, weight))
        covered += weight
        if len(selected) >= maximum or covered >= coverage:
            break
    total = sum(weight for _, weight in selected)
    return [(key, weight / total) for key, weight in selected] if total else []


def _weighted_edge(
    selected: list[tuple[object, float]],
    detailed: dict,
    arsenal: dict | None = None,
    *,
    minimum_bbe: int = 3,
) -> tuple[float | None, list[dict]]:
    values: list[tuple[float, float]] = []
    evidence: list[dict] = []
    for key, weight in selected:
        stats = detailed.get(key) or {}
        sample = int(stats.get("bbe") or 0)
        score = _performance_score(stats) if sample >= minimum_bbe else None
        source = "STATCAST_DETAIL"
        if score is None and arsenal and key in arsenal:
            score = _performance_score(arsenal[key])
            sample = int(arsenal[key].get("pa") or arsenal[key].get("pitches") or 0)
            source = "SAVANT_PITCH_ARSENAL"
        if score is None:
            continue
        values.append((score, weight))
        evidence.append({"key": key, "weight": round(weight, 3), "score": score, "sample": sample, "source": source})
    total_weight = sum(weight for _, weight in values)
    if not total_weight:
        return None, evidence
    return round(sum(score * weight for score, weight in values) / total_weight, 3), evidence


@lru_cache(maxsize=64)
def get_game_matchup_profiles(
    hitter_ids: tuple[int, ...],
    pitcher_id: int | None,
    season: int,
    as_of: str | None,
) -> dict[int, dict]:
    """Return real pitch-type and zone edges for one target lineup.

    The detailed Savant feed is queried once for the target lineup and once for
    the opposing pitcher, then matched by the pitcher's actual usage and zone
    distribution. No pitcher-leak/damage proxy is used here.
    """
    hitter_ids = tuple(sorted({int(player_id) for player_id in hitter_ids if player_id}))
    if not hitter_ids or not pitcher_id:
        return {}
    date_key = str(as_of or f"{season}-10-01")[:10]
    hitter_rows = _detail_rows("batter", hitter_ids, season, date_key)
    pitcher_rows = _detail_rows("pitcher", (int(pitcher_id),), season, date_key)
    hitter_detail = _aggregate_detail_rows(hitter_rows, "batter")
    pitcher_detail = _aggregate_detail_rows(pitcher_rows, "pitcher").get(int(pitcher_id), {})

    hitter_arsenal_by_id, _ = load_pitch_arsenal_maps(season, "batter")
    pitcher_arsenal_by_id, _ = load_pitch_arsenal_maps(season, "pitcher")
    pitcher_arsenal = pitcher_arsenal_by_id.get(int(pitcher_id), {})

    pitch_usage = _pitch_usage(pitcher_detail, pitcher_arsenal)
    top_pitches = _top_weighted_items(pitch_usage, coverage=0.65, maximum=3)

    zone_usage: dict[int, float] = {}
    if pitcher_detail.get("zones"):
        in_zone = {
            zone: float(stats.get("pitches") or 0)
            for zone, stats in pitcher_detail["zones"].items()
            if zone in range(1, 10) and stats.get("pitches")
        }
        total_zone = sum(in_zone.values())
        if total_zone:
            zone_usage = {zone: value / total_zone for zone, value in in_zone.items()}
    top_zones = _top_weighted_items(zone_usage, coverage=0.55, maximum=4)

    # Middle-third strike-zone locations are the clearest repeatable mistake
    # lane available in the pitch-level feed.  This is not guessed from a
    # pitcher's ERA; it is calculated from his actual Statcast locations.
    heart_zones = {2, 5, 8}
    heart_usage_raw = {zone: weight for zone, weight in zone_usage.items() if zone in heart_zones}
    pitcher_mistake_rate = round(sum(heart_usage_raw.values()) * 100.0, 3) if zone_usage else None
    heart_total = sum(heart_usage_raw.values())
    heart_usage = {zone: weight / heart_total for zone, weight in heart_usage_raw.items()} if heart_total else {}
    heart_locations = _top_weighted_items(heart_usage, coverage=1.0, maximum=3)

    result: dict[int, dict] = {}
    for hitter_id in hitter_ids:
        detail = hitter_detail.get(hitter_id, {})
        arsenal = hitter_arsenal_by_id.get(hitter_id, {})
        pitch_edge, pitch_evidence = _weighted_edge(
            top_pitches,
            detail.get("pitch_types") or {},
            arsenal,
            minimum_bbe=3,
        )
        zone_edge, zone_evidence = _weighted_edge(
            top_zones,
            detail.get("zones") or {},
            None,
            minimum_bbe=3,
        )
        mistake_edge, mistake_evidence = _weighted_edge(
            heart_locations,
            detail.get("zones") or {},
            None,
            minimum_bbe=2,
        )
        combined = None
        if pitch_edge is not None and zone_edge is not None:
            combined = round(pitch_edge * 0.65 + zone_edge * 0.35, 3)
        source = "STATCAST_DETAIL_PITCH_ZONE" if combined is not None else "MATCHUP_DATA_INCOMPLETE"
        result[hitter_id] = {
            "pitch_type_edge": pitch_edge,
            "zone_edge": zone_edge,
            "pitch_edge": combined,
            "pitch_edge_source": source,
            "matchup_data_complete": combined is not None,
            "mistake_edge": mistake_edge,
            "pitcher_mistake_rate": pitcher_mistake_rate,
            "pitch_matchup_evidence": pitch_evidence,
            "zone_matchup_evidence": zone_evidence,
            "mistake_matchup_evidence": mistake_evidence,
            "pitcher_top_pitches": [code for code, _ in top_pitches],
            "pitcher_top_zones": [zone for zone, _ in top_zones],
        }
    return result


# Backward-compatible wrappers used by older V5 code.
def load_statcast_hitter_map(season: int) -> dict[int, dict]:
    return load_statcast_hitter_maps(season)[0]


def load_bat_tracking_map(season: int) -> dict[int, dict]:
    return load_bat_tracking_maps(season)[0]


def get_hitter_statcast_profile(player_id: int | None, player_name: str | None, season: int) -> dict:
    stat_by_id, stat_by_name = load_statcast_hitter_maps(season)
    batted_by_id, batted_by_name = load_batted_ball_maps(season)
    bat_by_id, bat_by_name = load_bat_tracking_maps(season)
    arsenal_by_id, arsenal_by_name = load_pitch_arsenal_maps(season, "batter")

    profile: dict = {}
    normalized_name = _normalize_name(player_name)
    if player_id is not None:
        profile.update(stat_by_id.get(int(player_id), {}))
        profile.update(batted_by_id.get(int(player_id), {}))
        profile.update(bat_by_id.get(int(player_id), {}))
        if int(player_id) in arsenal_by_id:
            profile["pitch_arsenal"] = arsenal_by_id[int(player_id)]
    if normalized_name:
        for source in (
            stat_by_name.get(normalized_name, {}),
            batted_by_name.get(normalized_name, {}),
            bat_by_name.get(normalized_name, {}),
        ):
            for key, value in source.items():
                profile.setdefault(key, value)
        if "pitch_arsenal" not in profile and normalized_name in arsenal_by_name:
            profile["pitch_arsenal"] = arsenal_by_name[normalized_name]
    return profile
