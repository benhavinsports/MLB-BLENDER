"""
utils.py

Shared utility functions for
MLB Blender Machine v14.
"""

from __future__ import annotations

from typing import Any, Dict, List


def clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    return max(
        minimum,
        min(maximum, value),
    )


def safe_div(
    numerator: float,
    denominator: float,
) -> float:
    if denominator == 0:
        return 0.0

    return numerator / denominator


def normalize_name(
    name: str,
) -> str:

    if not name:
        return ""

    return (
        name.strip()
        .replace("  ", " ")
    )


def sort_desc(
    rows: List[Dict],
    field: str,
) -> List[Dict]:

    return sorted(
        rows,
        key=lambda x: x.get(
            field,
            0,
        ),
        reverse=True,
    )


def sort_asc(
    rows: List[Dict],
    field: str,
) -> List[Dict]:

    return sorted(
        rows,
        key=lambda x: x.get(
            field,
            0,
        ),
    )


def lineup_distance(
    slot_a: int,
    slot_b: int,
) -> int:

    return abs(
        slot_a - slot_b
    )


def digit_sum(
    value: int,
) -> int:

    return sum(
        int(x)
        for x in str(value)
    )


def ensure_one_survivor(
    players: List[Any],
):

    if not players:
        raise ValueError(
            "No survivors available."
        )

    return players[0]


def gate_trace_entry(
    gate: str,
    survivors: int,
) -> Dict:

    return {
        "gate": gate,
        "survivors": survivors,
    }


def build_matchup_string(
    away_team: str,
    home_team: str,
) -> str:

    return (
        f"{away_team} @ "
        f"{home_team}"
    )
