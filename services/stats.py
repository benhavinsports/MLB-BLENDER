from __future__ import annotations

from functools import lru_cache

from services.http import get_json
from services.statcast import get_hitter_statcast_profile

PEOPLE_URL = "https://statsapi.mlb.com/api/v1/people/{player_id}/stats"


def _float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=1024)
def _mlb_hitting(player_id: int, season: int) -> dict:
    data = get_json(
        PEOPLE_URL.format(player_id=player_id),
        params={"stats": "season", "group": "hitting", "season": season},
    )
    stats_blocks = data.get("stats") or []
    splits = ((stats_blocks[0] or {}).get("splits") or []) if stats_blocks else []
    stat = (splits[0].get("stat") or {}) if splits else {}
    pa = _float(stat.get("plateAppearances"))
    hr = _float(stat.get("homeRuns"))
    avg = _float(stat.get("avg"))
    slg = _float(stat.get("slg"))
    return {
        "pa": pa,
        "hr": hr,
        "hr_pa": (hr / pa) if hr is not None and pa else None,
        "iso": (slg - avg) if slg is not None and avg is not None else None,
        "slg": slg,
        "ops": _float(stat.get("ops")),
    }


def _merge_non_null(base: dict, extra: dict) -> dict:
    for key, value in extra.items():
        if value is not None:
            base[key] = value
    return base


def attach_stats(hitters: list[dict], season: int) -> list[dict]:
    profiles: list[dict] = []
    for hitter in hitters:
        player_id = hitter.get("id")
        player_name = hitter.get("name") or hitter.get("player")
        profile = dict(hitter)
        metrics = {
            "pull": None,
            "hard_hit": None,
            "barrel": None,
            "ev": None,
            "fb": None,
            "pua": None,
            "pull_barrel": None,
            "blast": None,
            "squared_up": None,
            "sweet_spot": None,
            "bat_speed": None,
            "fast_swing": None,
            "iso": None,
            "slg": None,
            "woba": None,
            "hr_pa": None,
            "pa": None,
            "hr": None,
            "pitch_edge": None,
            "hr_heat": None,
            "protection": None,
        }
        if player_id:
            _merge_non_null(metrics, _mlb_hitting(int(player_id), season))
        _merge_non_null(
            metrics,
            get_hitter_statcast_profile(
                int(player_id) if player_id else None,
                str(player_name) if player_name else None,
                season,
            ),
        )
        profile.update(metrics)
        profile["damage_score"] = damage_score(profile)
        profile["hr_model_score"] = hr_model_score(profile)
        profile["archetype"] = archetype(profile)
        profile["advanced_metrics_loaded"] = any(
            profile.get(key) is not None
            for key in (
                "pull",
                "hard_hit",
                "barrel",
                "ev",
                "sweet_spot",
                "bat_speed",
                "squared_up",
                "blast",
            )
        )
        profiles.append(profile)
    return profiles


def damage_score(p: dict) -> float:
    checks = [
        (p.get("hard_hit"), 45, 20),
        (p.get("ev"), 89, 15),
        (p.get("barrel"), 12, 20),
        (p.get("blast"), 14, 15),
        (p.get("squared_up"), 30, 10),
        (p.get("sweet_spot"), 34, 10),
        (p.get("bat_speed"), 72, 10),
    ]
    available = [(v, t, w) for v, t, w in checks if v is not None]
    if not available:
        iso = p.get("iso") or 0
        hr_pa = p.get("hr_pa") or 0
        return round(min(100.0, iso * 180 + hr_pa * 700), 3)
    total_weight = sum(w for _, _, w in available)
    points = sum(min(1.35, max(0.0, v / t)) * w for v, t, w in available)
    return round(points / total_weight * 100, 3)


def hr_model_score(p: dict) -> float:
    score = 0.0
    if p.get("pull") is not None:
        score += min(30, p["pull"] / 70 * 30)
    if p.get("hard_hit") is not None:
        score += min(25, p["hard_hit"] / 45 * 25)
    if p.get("iso") is not None:
        score += min(20, p["iso"] / 0.200 * 20)
    if p.get("hr_pa") is not None:
        score += min(15, p["hr_pa"] / 0.05 * 15)
    score += max(0, 10 - max(0, (p.get("slot") or 9) - 1) * 1.25)
    return round(score, 3)


def archetype(p: dict) -> str:
    pull = p.get("pull")
    hh = p.get("hard_hit")
    if pull is not None and pull >= 65 and hh is not None and hh >= 45:
        return "PULL_DAMAGE_FINISHER"
    if p.get("iso") is not None and p["iso"] >= 0.200:
        return "POWER_FINISHER"
    return "BALANCED"
