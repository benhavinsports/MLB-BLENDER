"""
features.py

Deterministic feature-engine layer for MLB Blender Machine v14.

Design goals:

- No randomness
- No ML
- No probabilities
- Reproducible outputs
- MLB Stats API compatible
- Uses only normalized game-log / roster / boxscore data

All unavailable Statcast metrics are replaced with deterministic proxies.

Outputs are scaled to Blender ranges.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List
from statistics import mean


# ============================================================
# HELPERS
# ============================================================


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def safe_div(a: float, b: float) -> float:
    if b == 0:
        return 0.0
    return a / b


# ============================================================
# FEATURE CONTAINER
# ============================================================


@dataclass
class FeatureSet:
    player_id: int
    player_name: str

    pull_pct: float
    hard_hit_pct: float
    pitch_edge: float
    hr_heat: float
    condition_pct: float
    zone_weakness: float
    conversion_history: float
    event_ownership: float

    event_score: float


# ============================================================
# RECENT GAME LOG HELPERS
# ============================================================


def recent_games(
    game_logs: List[dict],
    n: int,
) -> List[dict]:
    return sorted(
        game_logs,
        key=lambda x: x["date"],
        reverse=True,
    )[:n]


def total_hr(
    logs: List[dict],
) -> int:
    return sum(x.get("hr", 0) for x in logs)


def total_hits(
    logs: List[dict],
) -> int:
    return sum(x.get("hits", 0) for x in logs)


def total_ab(
    logs: List[dict],
) -> int:
    return sum(x.get("ab", 0) for x in logs)


def total_so(
    logs: List[dict],
) -> int:
    return sum(x.get("so", 0) for x in logs)


def total_bb(
    logs: List[dict],
) -> int:
    return sum(x.get("bb", 0) for x in logs)


# ============================================================
# PULL %
# ============================================================


def calculate_pull_pct(
    game_logs: List[dict],
) -> float:
    """
    Proxy model.

    Uses:
    SLG
    HR frequency
    RBI production

    Power hitters generally exhibit stronger pull-side
    extra-base tendencies.

    Scale: 0-100
    """

    if not game_logs:
        return 0.0

    values = []

    for g in game_logs:

        slg = float(g.get("slg") or 0)
        hr = g.get("hr", 0)
        rbi = g.get("rbi", 0)

        score = (
            slg * 60
            + hr * 12
            + rbi * 2
        )

        values.append(score)

    return round(
        clamp(mean(values)),
        2,
    )


# ============================================================
# HARD HIT %
# ============================================================


def calculate_hard_hit_pct(
    game_logs: List[dict],
) -> float:
    """
    EV proxy.

    Uses:
    SLG
    OPS
    XBH tendency proxy

    Scale: 0-100
    """

    if not game_logs:
        return 0.0

    values = []

    for g in game_logs:

        slg = float(g.get("slg") or 0)
        ops = float(g.get("ops") or 0)

        score = (
            slg * 55
            + ops * 35
        )

        values.append(score)

    return round(
        clamp(mean(values)),
        2,
    )


# ============================================================
# PITCH EDGE
# ============================================================


def calculate_pitch_edge(
    hitter_logs: List[dict],
    pitcher_stats: Dict,
) -> float:
    """
    Positive:
        hitter advantage

    Negative:
        pitcher advantage

    G5 auto kill:
        pitch_edge < 0
    """

    hitter_ab = total_ab(hitter_logs)

    hitter_so = total_so(hitter_logs)
    hitter_bb = total_bb(hitter_logs)

    hitter_k_rate = safe_div(
        hitter_so,
        hitter_ab,
    )

    hitter_bb_rate = safe_div(
        hitter_bb,
        hitter_ab,
    )

    pitcher_k_rate = pitcher_stats.get(
        "k_rate",
        0,
    )

    pitcher_bb_rate = pitcher_stats.get(
        "bb_rate",
        0,
    )

    score = (
        hitter_bb_rate
        - hitter_k_rate
        - pitcher_k_rate
        + pitcher_bb_rate
    )

    return round(
        score * 100,
        2,
    )


# ============================================================
# HR HEAT
# ============================================================


def calculate_hr_heat(
    game_logs: List[dict],
) -> float:
    """
    HR streak metric.

    Last 7 + Last 14.
    """

    last7 = recent_games(
        game_logs,
        7,
    )

    last14 = recent_games(
        game_logs,
        14,
    )

    hr7 = total_hr(last7)
    hr14 = total_hr(last14)

    score = (
        hr7 * 8
        + hr14 * 4
    )

    return round(
        clamp(score),
        2,
    )


# ============================================================
# CONDITION %
# ============================================================


def calculate_condition_pct(
    game_logs: List[dict],
) -> float:
    """
    Additive boost only.
    Never elimination.
    """

    recent = recent_games(
        game_logs,
        10,
    )

    if not recent:
        return 0.0

    avg_values = []

    for g in recent:
        try:
            avg_values.append(
                float(g.get("avg") or 0)
            )
        except Exception:
            pass

    if not avg_values:
        return 0.0

    season_form = mean(avg_values)

    return round(
        clamp(season_form * 100),
        2,
    )


# ============================================================
# ZONE WEAKNESS
# ============================================================


def calculate_zone_weakness(
    hitter_logs: List[dict],
    pitcher_stats: Dict,
) -> float:
    """
    Strikeout pressure proxy.

    Higher = weaker hitter.
    """

    hitter_ab = total_ab(hitter_logs)

    hitter_so = total_so(hitter_logs)

    hitter_k = safe_div(
        hitter_so,
        hitter_ab,
    )

    pitcher_k = pitcher_stats.get(
        "k_rate",
        0,
    )

    weakness = (
        hitter_k
        * pitcher_k
        * 400
    )

    return round(
        clamp(weakness),
        2,
    )


# ============================================================
# CONVERSION HISTORY
# ============================================================


def calculate_conversion_history(
    game_logs: List[dict],
) -> float:
    """
    HR/XBH proxy.

    HR conversion against opportunities.
    """

    hits = total_hits(game_logs)

    hrs = total_hr(game_logs)

    if hits == 0:
        return 0.0

    score = (
        hrs / hits
    ) * 100

    return round(
        clamp(score),
        2,
    )


# ============================================================
# EVENT OWNERSHIP
# ============================================================


def calculate_event_ownership(
    gate_wins: int,
    total_gates: int = 18,
) -> float:
    """
    Ownership =
    cumulative gate wins.

    Scale 0-100
    """

    score = safe_div(
        gate_wins,
        total_gates,
    ) * 100

    return round(
        clamp(score),
        2,
    )


# ============================================================
# EVENT SCORE
# ============================================================


def calculate_event_score(
    pull_pct: float,
    hard_hit_pct: float,
    pitch_edge: float,
    condition_pct: float,
    hr_heat: float,
) -> float:
    """
    REQUIRED BLENDER FORMULA

    event_score =
        pull * 0.40 +
        hard_hit * 0.35 +
        pitch_edge * 1.25 +
        cond_boost +
        hr_heat * 2
    """

    score = (
        pull_pct * 0.40
        + hard_hit_pct * 0.35
        + pitch_edge * 1.25
        + condition_pct
        + hr_heat * 2
    )

    return round(score, 4)


# ============================================================
# MASTER FEATURE BUILDER
# ============================================================


def build_feature_set(
    player_id: int,
    player_name: str,
    game_logs: List[dict],
    pitcher_stats: Dict,
    gate_wins: int = 0,
) -> FeatureSet:

    pull_pct = calculate_pull_pct(
        game_logs
    )

    hard_hit_pct = calculate_hard_hit_pct(
        game_logs
    )

    pitch_edge = calculate_pitch_edge(
        game_logs,
        pitcher_stats,
    )

    hr_heat = calculate_hr_heat(
        game_logs
    )

    condition_pct = calculate_condition_pct(
        game_logs
    )

    zone_weakness = calculate_zone_weakness(
        game_logs,
        pitcher_stats,
    )

    conversion_history = (
        calculate_conversion_history(
            game_logs
        )
    )

    event_ownership = (
        calculate_event_ownership(
            gate_wins
        )
    )

    event_score = calculate_event_score(
        pull_pct,
        hard_hit_pct,
        pitch_edge,
        condition_pct,
        hr_heat,
    )

    return FeatureSet(
        player_id=player_id,
        player_name=player_name,
        pull_pct=pull_pct,
        hard_hit_pct=hard_hit_pct,
        pitch_edge=pitch_edge,
        hr_heat=hr_heat,
        condition_pct=condition_pct,
        zone_weakness=zone_weakness,
        conversion_history=conversion_history,
        event_ownership=event_ownership,
        event_score=event_score,
    )
