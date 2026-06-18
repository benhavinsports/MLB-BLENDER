"""
gates.py

G0–G18 deterministic elimination pipeline
for MLB Blender Machine v14

RULES:
- No randomness
- No ranking-only systems (only elimination)
- Must always output exactly 1 survivor
- Every gate explicitly PASS/ELIMINATE logic
"""

from __future__ import annotations

from typing import List, Dict, Any
from dataclasses import dataclass

from features import build_feature_set


# ============================================================
# DATA STRUCTURES
# ============================================================


@dataclass
class HitterState:
    player_id: int
    name: str
    lineup_slot: int
    raw: dict
    features: Any
    alive: bool = True
    eliminated_by: str = ""


# ============================================================
# UTILS
# ============================================================


def eliminate(player: HitterState, gate: str):
    player.alive = False
    player.eliminated_by = gate


def alive(pool: List[HitterState]) -> List[HitterState]:
    return [p for p in pool if p.alive]


# ============================================================
# G0 — TARGET ISOLATION
# ============================================================


def G0(pool: List[HitterState]) -> List[HitterState]:
    # Ensure valid hitters only
    for p in pool:
        if not p.player_id or not p.name:
            eliminate(p, "G0")
    return alive(pool)


# ============================================================
# G1 — ENVIRONMENT CHECK
# ============================================================


def G1(pool: List[HitterState], game: Dict) -> List[HitterState]:
    # Always pass but enforce deterministic structure
    return pool


# ============================================================
# G2 — POOL BUILD
# ============================================================


def G2(pool: List[HitterState]) -> List[HitterState]:
    # Keep only starting lineup slots 1–9
    for p in pool:
        if not (1 <= p.lineup_slot <= 9):
            eliminate(p, "G2")
    return alive(pool)


# ============================================================
# G3 — PULL %
# ============================================================


def G3(pool: List[HitterState]) -> List[HitterState]:
    threshold = 35.0
    for p in pool:
        if p.features.pull_pct < threshold:
            eliminate(p, "G3")
    return alive(pool)


# ============================================================
# G4 — HARD HIT %
# ============================================================


def G4(pool: List[HitterState]) -> List[HitterState]:
    threshold = 30.0
    for p in pool:
        if p.features.hard_hit_pct < threshold:
            eliminate(p, "G4")
    return alive(pool)


# ============================================================
# G5 — PITCH EDGE KILL
# ============================================================


def G5(pool: List[HitterState]) -> List[HitterState]:
    for p in pool:
        if p.features.pitch_edge < 0:
            eliminate(p, "G5")
    return alive(pool)


# ============================================================
# G6 — ZONE WEAKNESS
# ============================================================


def G6(pool: List[HitterState]) -> List[HitterState]:
    threshold = 60.0
    for p in pool:
        if p.features.zone_weakness > threshold:
            eliminate(p, "G6")
    return alive(pool)


# ============================================================
# G7 — RECENT FORM
# ============================================================


def G7(pool: List[HitterState]) -> List[HitterState]:
    threshold = 20.0
    for p in pool:
        if p.features.condition_pct < threshold:
            eliminate(p, "G7")
    return alive(pool)


# ============================================================
# G8 — CONVERSION HISTORY
# ============================================================


def G8(pool: List[HitterState]) -> List[HitterState]:
    threshold = 15.0
    for p in pool:
        if p.features.conversion_history < threshold:
            eliminate(p, "G8")
    return alive(pool)


# ============================================================
# G9 — PARK / CONTEXT (neutral deterministic pass)
# ============================================================


def G9(pool: List[HitterState]) -> List[HitterState]:
    return pool


# ============================================================
# G10 — OPPORTUNITY (LINEUP ORDER FILTER)
# ============================================================


def G10(pool: List[HitterState]) -> List[HitterState]:
    # Favor top 5 lineup slots first pass
    survivors = []
    for p in pool:
        if p.lineup_slot <= 5:
            survivors.append(p)

    # fallback if empty
    return survivors if survivors else pool


# ============================================================
# G10.5 — ADJACENT TRANSFER LOGIC
# ============================================================


def G10_5(pool: List[HitterState]) -> List[HitterState]:
    if len(pool) <= 1:
        return pool

    # sort by event score
    pool.sort(key=lambda x: x.features.event_score, reverse=True)

    top = pool[0]
    second = pool[1]

    diff = abs(top.features.event_score - second.features.event_score)

    epsilon = 0.75

    if diff <= epsilon:
        # adjacency rule: choose closer lineup slot neighbor
        if abs(top.lineup_slot - second.lineup_slot) == 1:
            # deterministic tie-break: lower lineup slot wins
            chosen = min([top, second], key=lambda x: x.lineup_slot)
            return [chosen]

    return pool


# ============================================================
# G11 — BULLPEN CONTINUATION (neutral pass)
# ============================================================


def G11(pool: List[HitterState]) -> List[HitterState]:
    return pool


# ============================================================
# G12 — EVENT OWNERSHIP FILTER
# ============================================================


def G12(pool: List[HitterState]) -> List[HitterState]:
    threshold = 20.0
    for p in pool:
        if p.features.event_ownership < threshold:
            eliminate(p, "G12")
    return alive(pool)


# ============================================================
# G13 — NUMEROLOGY FALLBACK (ONLY IF DEADLOCK)
# ============================================================


def G13(pool: List[HitterState]) -> List[HitterState]:
    if len(pool) <= 2:
        return pool

    # deterministic digit sum of player_id
    def digit_sum(n: int) -> int:
        return sum(int(x) for x in str(n))

    pool.sort(key=lambda x: digit_sum(x.player_id), reverse=True)

    return pool[: max(2, len(pool) // 2)]


# ============================================================
# G14 — LINEUP PROTECTION
# ============================================================


def G14(pool: List[HitterState]) -> List[HitterState]:
    # protect cleanup hitters (3–5)
    protected = [p for p in pool if 3 <= p.lineup_slot <= 5]

    if protected:
        return protected

    return pool


# ============================================================
# G15 — FINISHER CHECK
# ============================================================


def G15(pool: List[HitterState]) -> List[HitterState]:
    if len(pool) == 1:
        return pool

    pool.sort(key=lambda x: x.features.hr_heat, reverse=True)
    return pool[: max(1, len(pool) // 2)]


# ============================================================
# G16 — LAST MAN ENFORCEMENT
# ============================================================


def G16(pool: List[HitterState]) -> List[HitterState]:
    if len(pool) == 1:
        return pool

    pool.sort(key=lambda x: x.features.event_score, reverse=True)
    return [pool[0]]


# ============================================================
# G17 — AUDIT VALIDATION
# ============================================================


def G17(pool: List[HitterState]) -> List[HitterState]:
    # ensure no empty names
    pool = [p for p in pool if p.name]
    return pool


# ============================================================
# G18 — FINAL LOCK
# ============================================================


def G18(pool: List[HitterState]) -> HitterState:
    if not pool:
        raise ValueError("No survivors reached G18")

    pool.sort(key=lambda x: x.features.event_score, reverse=True)
    return pool[0]


# ============================================================
# ENGINE RUNNER
# ============================================================


def run_gates(
    lineup: List[Dict],
    game_bundle: Dict,
    pitcher_stats: Dict,
) -> Dict[str, Any]:

    pool: List[HitterState] = []

    # BUILD INITIAL STATE
    for p in lineup:

        # dummy game logs fallback structure
        game_logs = p.get("game_logs", [])

        feats = build_feature_set(
            player_id=p["player_id"],
            player_name=p["name"],
            game_logs=game_logs,
            pitcher_stats=pitcher_stats,
            gate_wins=0,
        )

        pool.append(
            HitterState(
                player_id=p["player_id"],
                name=p["name"],
                lineup_slot=p["lineup_slot"],
                raw=p,
                features=feats,
            )
        )

    trace = {}

    # PIPELINE EXECUTION
    pool = G0(pool)
    trace["G0"] = len(pool)

    pool = G1(pool, game_bundle)
    trace["G1"] = len(pool)

    pool = G2(pool)
    trace["G2"] = len(pool)

    pool = G3(pool)
    trace["G3"] = len(pool)

    pool = G4(pool)
    trace["G4"] = len(pool)

    pool = G5(pool)
    trace["G5"] = len(pool)

    pool = G6(pool)
    trace["G6"] = len(pool)

    pool = G7(pool)
    trace["G7"] = len(pool)

    pool = G8(pool)
    trace["G8"] = len(pool)

    pool = G9(pool)
    trace["G9"] = len(pool)

    pool = G10(pool)
    trace["G10"] = len(pool)

    pool = G10_5(pool)
    trace["G10.5"] = len(pool)

    pool = G11(pool)
    trace["G11"] = len(pool)

    pool = G12(pool)
    trace["G12"] = len(pool)

    pool = G13(pool)
    trace["G13"] = len(pool)

    pool = G14(pool)
    trace["G14"] = len(pool)

    pool = G15(pool)
    trace["G15"] = len(pool)

    pool = G16(pool)
    trace["G16"] = len(pool)

    pool = G17(pool)
    trace["G17"] = len(pool)

    winner = G18(pool)

    return {
        "survivor": {
            "player_id": winner.player_id,
            "name": winner.name,
            "lineup_slot": winner.lineup_slot,
            "event_score": winner.features.event_score,
            "pull_pct": winner.features.pull_pct,
            "hard_hit_pct": winner.features.hard_hit_pct,
            "pitch_edge": winner.features.pitch_edge,
        },
        "trace": trace,
    }
