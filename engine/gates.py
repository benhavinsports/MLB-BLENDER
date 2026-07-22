from __future__ import annotations

import hashlib
from typing import Callable

from engine.ownership import assign_event_ownership


Player = dict
Predicate = Callable[[Player], tuple[bool, str]]
Ranker = Callable[[Player], tuple]


def gate_log(gate, name, before, after, removed=None, note=None):
    return {
        "gate": gate,
        "name": name,
        "before": before,
        "after": after,
        "removed": removed or [],
        "note": note,
    }


def _number(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _merge_note(note, extra: dict):
    if isinstance(note, dict):
        merged = dict(note)
        merged.update(extra)
        return merged
    if note is None:
        return extra
    return {"context": note, **extra}


def _default_rank(player: Player) -> tuple:
    return (
        _number(player.get("hr_model_score")),
        _number(player.get("damage_score")),
        _number(player.get("pitch_edge"), -999.0),
        _number(player.get("hr_pa")) * 1000.0,
        _number(player.get("iso")) * 100.0,
        -_number(player.get("slot"), 99.0),
    )


def _apply(
    players: list[Player],
    gate,
    name: str,
    predicate: Predicate,
    logs: list[dict],
    *,
    note=None,
    empty_mode: str = "no_separation",
    ranker: Ranker | None = None,
):
    """Apply one elimination gate without inventing an early winner.

    A gate may eliminate hitters only when at least one hitter genuinely passes.
    When every remaining hitter fails, the gate is non-discriminating and the
    incoming pool continues unchanged. The complete failure detail is audited.

    ``empty_mode="strict"`` is reserved for validity gates such as the starting
    lineup check. WHO is created only at Gate 16 after every baseball gate has
    had its chance to separate the pool.
    """
    before = len(players)
    if before == 0:
        logs.append(gate_log(gate, name, 0, 0, [], note=note))
        return []

    kept: list[Player] = []
    failures: list[tuple[Player, str]] = []
    for player in players:
        passed, reason = predicate(player)
        if passed:
            kept.append(player)
        else:
            failures.append((player, reason))

    if kept:
        removed = [
            {"player": player.get("name"), "reason": reason}
            for player, reason in failures
        ]
        logs.append(gate_log(gate, name, before, len(kept), removed, note=note))
        return kept

    failure_details = [
        {"player": player.get("name"), "reason": reason}
        for player, reason in failures
    ]

    if empty_mode == "strict":
        logs.append(gate_log(gate, name, before, 0, failure_details, note=note))
        return []

    logs.append(
        gate_log(
            gate,
            name,
            before,
            before,
            [],
            note=_merge_note(
                note,
                {
                    "mode": "NO_SEPARATION",
                    "reason": "no hitter cleared this gate; pool preserved so the gate cannot manufacture a winner",
                    "failed_checks": failure_details,
                },
            ),
        )
    )
    return list(players)


def _missing(player: dict, *fields: str) -> list[str]:
    return [field for field in fields if player.get(field) is None]


def _universe_score(player: dict, game: dict) -> int:
    """Isolated deterministic tie-break only; never a baseball score or kill."""
    seed = "|".join(
        [
            str(game.get("date") or ""),
            str(game.get("game_id") or game.get("gamePk") or ""),
            str(player.get("id") or ""),
            str(player.get("slot") or ""),
        ]
    )
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 1000


def _ownership_snapshot(players: list[dict]) -> list[dict]:
    return [
        {
            "player": player.get("name"),
            "score": player.get("ownership_score"),
            "components": player.get("ownership_components"),
        }
        for player in sorted(
            players,
            key=lambda p: (p.get("ownership_score") or 0),
            reverse=True,
        )
    ]


def _transfer_evidence(top: Player, second: Player) -> list[str]:
    evidence: list[str] = []
    if _number(second.get("pitch_edge"), -999.0) > _number(top.get("pitch_edge"), -999.0) + 0.25:
        evidence.append("stronger_pitch_edge")
    if bool(second.get("hr_heat")) and not bool(top.get("hr_heat")):
        evidence.append("live_recent_rhythm")
    if _number(second.get("damage_score")) > _number(top.get("damage_score")) + 2.0:
        evidence.append("stronger_damage")
    if _number(second.get("hr_pa")) > _number(top.get("hr_pa")) + 0.004:
        evidence.append("stronger_hr_conversion")
    if _number(second.get("protection"), -1.0) > _number(top.get("protection"), -1.0):
        evidence.append("better_lineup_protection")
    return evidence


def run_all_gates(hitters: list[dict], game: dict, target: dict):
    logs: list[dict] = []

    # Gate 0: target layer has already locked exactly one offense side.
    current = [p for p in hitters if p.get("side") == target.get("side")]
    logs.append(gate_log(0, "Target Side Isolation", len(hitters), len(current), note=target))

    # Gate 1: environment is a game context, not permission to erase the game.
    env = game.get("environment") or {}
    env_score = env.get("environment_score")
    before = len(current)
    env_note = dict(env)
    if env_score is None:
        env_note.update({"mode": "DATA_WARNING", "reason": "environment score missing"})
    elif float(env_score) <= -3:
        env_note.update({"mode": "SUPPRESSED", "reason": "heavy suppression carried into later gates"})
    else:
        env_note.update({"mode": "ACTIVE"})
    logs.append(gate_log(1, "Environment", before, before, note=env_note))

    # Gate 2: official/confirmed/projected starting nine only.
    current = _apply(
        current,
        2,
        "Confirmed Starter Pool",
        lambda p: (
            p.get("lineup_status") in {"OFFICIAL", "CONFIRMED", "PROJECTED"}
            and 1 <= (p.get("slot") or 99) <= 9,
            "not a valid starting hitter",
        ),
        logs,
        empty_mode="strict",
    )

    # Gate 3: Pull-Air identity. <50 is still a kill unless the entire pool
    # misses, in which case exactly one explicit WHO survives.
    def pull_gate(player):
        missing = _missing(player, "pull", "hard_hit")
        if missing:
            return False, f"missing pull data: {', '.join(missing)}"
        pull = float(player["pull"])
        hard_hit = float(player["hard_hit"])
        pitch_edge = player.get("pitch_edge")

        if pull < 50:
            return False, "Pull < 50 auto-kill"
        if pull >= 70 and hard_hit >= 45:
            return True, "elite pull combo"
        if pull >= 65 and hard_hit >= 50:
            return True, "strong pull combo"
        if 55 <= pull < 65:
            passed = hard_hit >= 45 and pitch_edge is not None and float(pitch_edge) >= 0
            return passed, "borderline pull lacks damage/pitch support"
        passed = hard_hit >= 40 and pitch_edge is not None and float(pitch_edge) >= 0
        return passed, "50-54 pull lane lacks hard-hit/pitch support"

    current = _apply(
        current,
        3,
        "Pull-Air Identity",
        pull_gate,
        logs,
        empty_mode="no_separation",
        ranker=lambda p: (
            _number(p.get("pull"), -1.0),
            _number(p.get("hard_hit"), -1.0),
            _number(p.get("pitch_edge"), -999.0),
            _default_rank(p),
        ),
    )

    # Gate 4: Damage support. A total miss enters WHO instead of returning zero.
    def damage_gate(player):
        missing = _missing(player, "hard_hit", "damage_score")
        if missing:
            return False, f"missing damage data: {', '.join(missing)}"
        if float(player["hard_hit"]) < 40:
            return False, "Hard Hit < 40 auto-kill"
        if float(player["damage_score"]) < 35:
            return False, "damage score below floor"
        return True, "damage supported"

    current = _apply(
        current,
        4,
        "Damage Quality",
        damage_gate,
        logs,
        empty_mode="no_separation",
        ranker=lambda p: (
            _number(p.get("damage_score")),
            _number(p.get("hard_hit")),
            _default_rank(p),
        ),
    )

    # Gate 5: matchup edge. If every candidate is negative, the least-negative
    # candidate becomes the explicit WHO rather than erasing the game.
    def pitch_gate(player):
        if player.get("pitch_edge") is None:
            return False, "pitch matchup data missing"
        return float(player["pitch_edge"]) >= 0, "negative pitch edge"

    current = _apply(
        current,
        5,
        "Pitch Matchup",
        pitch_gate,
        logs,
        note={
            "sources": sorted({str(p.get("pitch_edge_source")) for p in current}),
            "pitcher": (target.get("pitcher") or {}).get("name"),
        },
        empty_mode="no_separation",
        ranker=lambda p: (
            _number(p.get("pitch_edge"), -999.0),
            _number(p.get("damage_score")),
            _default_rank(p),
        ),
    )

    # Gate 6: lineup access.
    current = _apply(
        current,
        6,
        "Lineup Access",
        lambda p: ((p.get("slot") or 99) <= 7, "slot outside access lane"),
        logs,
        empty_mode="no_separation",
    )

    # Gate 7: recent rhythm only separates the pool when somebody is actually
    # hot. It cannot kill the only remaining hitter because everybody is cold.
    def rhythm_gate(player):
        if player.get("recent_pa") is None or player.get("hr_heat") is None:
            return False, "recent rhythm data missing"
        return bool(player.get("hr_heat")), "dead recent rhythm"

    current = _apply(
        current,
        7,
        "Recent Rhythm",
        rhythm_gate,
        logs,
        empty_mode="no_separation",
    )

    # Gate 8: conversion separates only when at least one remaining candidate
    # clears the floor.
    current = _apply(
        current,
        8,
        "HR Conversion",
        lambda p: (
            p.get("hr_pa") is not None and float(p["hr_pa"]) >= 0.025,
            "HR/PA data missing" if p.get("hr_pa") is None else "HR/PA below WHO floor",
        ),
        logs,
        empty_mode="no_separation",
    )

    # Gate 9: environment alignment separates when the context can distinguish.
    def environment_alignment(player):
        if env_score is None:
            return False, "environment data missing"
        damage = player.get("damage_score")
        if damage is None:
            return False, "damage data missing"
        required_damage = 45 if float(env_score) < 0 else 35
        return float(damage) >= required_damage, f"damage below environment floor {required_damage}"

    current = _apply(
        current,
        9,
        "Hitter Environment Alignment",
        environment_alignment,
        logs,
        note=env,
        empty_mode="no_separation",
    )

    # Gate 10: true PA opportunity lane.
    current = _apply(
        current,
        10,
        "Opportunity",
        lambda p: ((p.get("slot") or 99) <= 6, "insufficient projected PA"),
        logs,
        empty_mode="no_separation",
    )

    # Gate 10.5: identify false chalk and a real adjacent transfer lane.
    before = len(current)
    assign_event_ownership(current, game, target)
    failed = []
    kept = []
    for player in current:
        pull = _number(player.get("pull"))
        hard_hit = _number(player.get("hard_hit"))
        if pull < 55 and hard_hit < 45:
            failed.append((player, "false chalk: pull <55 and HH <45"))
        else:
            kept.append(player)

    decoy_note: dict = {}
    if not kept and current:
        kept = list(current)
        decoy_note.update(
            {
                "mode": "NO_SEPARATION",
                "reason": "false-chalk test rejected the entire live pool; no adjacent winner was manufactured",
                "failed_checks": [
                    {"player": player.get("name"), "reason": reason}
                    for player, reason in failed
                ],
            }
        )

    current = kept
    removed = [
        {"player": player.get("name"), "reason": reason}
        for player, reason in failed
        if player not in current
    ]

    ordered = sorted(current, key=lambda p: p.get("ownership_score", 0), reverse=True)
    transfer_lane = None
    if len(ordered) >= 2:
        top, second = ordered[0], ordered[1]
        gap = _number(top.get("ownership_score")) - _number(second.get("ownership_score"))
        evidence = _transfer_evidence(top, second)
        finisher_gap = _number(top.get("damage_score")) - _number(second.get("damage_score"))
        if gap <= 10 and len(evidence) >= 2 and finisher_gap <= 8:
            second["transfer_candidate"] = True
            second["transfer_evidence"] = evidence
            transfer_lane = {
                "from": top.get("name"),
                "to": second.get("name"),
                "ownership_gap": round(gap, 3),
                "evidence": evidence,
            }

    decoy_note.update({"transfer_lane": transfer_lane, "ownership": _ownership_snapshot(current)})
    logs.append(
        gate_log(
            10.5,
            "Adjacent / Decoy Transfer",
            before,
            len(current),
            removed,
            note=decoy_note,
        )
    )

    # Gate 11: bullpen continuation is a separator, not a zero-survivor switch.
    bullpen = game.get("away_bullpen") if target.get("side") == "home" else game.get("home_bullpen")
    bullpen = bullpen or {}
    bullpen_risk = bullpen.get("risk_score")

    def bullpen_gate(player):
        if bullpen_risk is None:
            return False, "bullpen data missing"
        if float(bullpen_risk) >= 5:
            return True, "bullpen continuation available"
        strong_finisher = (
            _number(player.get("hr_pa")) >= 0.04
            and _number(player.get("iso")) >= 0.200
            and _number(player.get("damage_score")) >= 50
        )
        return strong_finisher, "low-risk bullpen blocks non-elite finisher"

    current = _apply(
        current,
        11,
        "Bullpen Continuation",
        bullpen_gate,
        logs,
        note=bullpen,
        empty_mode="no_separation",
    )

    # Gate 12: official event ownership scoring while the pool is still alive.
    before = len(current)
    assign_event_ownership(current, game, target)
    logs.append(
        gate_log(
            12,
            "Event Ownership",
            before,
            len(current),
            note={"ownership": _ownership_snapshot(current)},
        )
    )

    # Gate 13: Universe is isolated and tie-break only. It may never eliminate.
    before = len(current)
    for player in current:
        player["universe_score"] = _universe_score(player, game)
    logs.append(
        gate_log(
            13,
            "Universe",
            before,
            len(current),
            note={
                "mode": "TIE_BREAK_ONLY",
                "scores": [
                    {"player": p.get("name"), "universe_score": p.get("universe_score")}
                    for p in current
                ],
            },
        )
    )

    # Gate 14: protection only separates if at least one candidate has support.
    def protection_gate(player):
        if player.get("protection") is None:
            return False, "lineup protection data missing"
        if float(player["protection"]) >= 0:
            return True, "protected cluster"
        elite = _number(player.get("damage_score")) >= 65 and _number(player.get("hr_pa")) >= 0.04
        return elite, "isolated lineup cluster"

    current = _apply(
        current,
        14,
        "Lineup Protection",
        protection_gate,
        logs,
        empty_mode="no_separation",
    )

    # Gate 15: pressure cannot outweigh the finisher, but No Empty Bat means the
    # best available finisher enters WHO if nobody clears every absolute floor.
    def finisher_gate(player):
        missing = _missing(player, "hr_pa", "iso", "damage_score")
        if missing:
            player["finisher_pass"] = False
            return False, f"missing finisher data: {', '.join(missing)}"
        passed = (
            float(player["hr_pa"]) >= 0.025
            and float(player["iso"]) >= 0.150
            and float(player["damage_score"]) >= 35
        )
        player["finisher_pass"] = passed
        return passed, "finisher floor failed"

    current = _apply(
        current,
        15,
        "HR Finisher Identity",
        finisher_gate,
        logs,
        empty_mode="no_separation",
        ranker=lambda p: (
            _number(p.get("hr_pa")) * 1000.0,
            _number(p.get("iso")) * 100.0,
            _number(p.get("damage_score")),
            _default_rank(p),
        ),
    )

    # Gate 16: one last man. Baseball finisher identity owns the event.
    # Ownership is pressure context only and can never outrank the finisher.
    before = len(current)
    assign_event_ownership(current, game, target)

    def finisher_key(player: Player) -> tuple:
        return (
            1 if player.get("finisher_pass") else 0,
            _number(player.get("hr_pa"), -1.0),
            _number(player.get("iso"), -1.0),
            _number(player.get("damage_score"), -1.0),
            _number(player.get("pitch_edge"), -999.0),
            1 if player.get("hr_heat") else 0,
            _number(player.get("pull"), -1.0),
            _number(player.get("hard_hit"), -1.0),
            _number(player.get("protection"), -2.0),
            -_number(player.get("slot"), 99.0),
            _number(player.get("ownership_score"), -1.0),
            _number(player.get("universe_score"), -1.0),
        )

    ordered = sorted(current, key=finisher_key, reverse=True)
    selected = ordered[0] if ordered else None
    transfer = None

    # A Gate 10.5 transfer must have real adjacent evidence and remain inside
    # the primary finisher's absolute performance lane. Pressure alone cannot
    # transfer the event to a visibly weaker bat.
    if selected:
        candidates = [
            player
            for player in ordered[1:]
            if player.get("transfer_candidate")
            and len(player.get("transfer_evidence") or []) >= 3
        ]
        if candidates:
            adjacent = max(candidates, key=finisher_key)
            ownership_gap = abs(
                _number(selected.get("ownership_score"))
                - _number(adjacent.get("ownership_score"))
            )
            inside_finisher_lane = (
                _number(adjacent.get("hr_pa"), -1.0)
                >= _number(selected.get("hr_pa"), -1.0) - 0.003
                and _number(adjacent.get("iso"), -1.0)
                >= _number(selected.get("iso"), -1.0) - 0.015
                and _number(adjacent.get("damage_score"), -1.0)
                >= _number(selected.get("damage_score"), -1.0) - 5.0
                and _number(adjacent.get("pitch_edge"), -999.0)
                >= _number(selected.get("pitch_edge"), -999.0) + 0.25
            )
            if ownership_gap <= 10.0 and inside_finisher_lane:
                primary = selected
                selected = adjacent
                selected["transfer_flag"] = True
                selected["event_reason"] = (
                    "Gate 10.5 adjacent transfer with equal finisher strength and stronger matchup"
                )
                transfer = {
                    "from": primary.get("name"),
                    "to": selected.get("name"),
                    "ownership_gap": round(ownership_gap, 3),
                    "evidence": selected.get("transfer_evidence") or [],
                }

    final_who = bool(selected and not selected.get("finisher_pass"))
    if selected:
        if final_who:
            selected["who_lane"] = True
            selected["event_reason"] = (
                "WHO last-man: no remaining hitter cleared the absolute Gate 15 finisher floor"
            )
        elif not selected.get("transfer_flag"):
            selected["event_reason"] = (
                "HR event owner after finisher-first Gate 16 elimination"
            )

    current = [selected] if selected else []
    removed = [
        {"player": player.get("name"), "reason": "lost finisher-first Gate 16 comparison"}
        for player in ordered
        if selected is not player
    ]
    logs.append(
        gate_log(
            16,
            "Last-Man Elimination",
            before,
            len(current),
            removed,
            note={
                "mode": "FINAL_WHO" if final_who else "FINISHER_OWNER",
                "transfer": transfer,
                "selected": selected.get("name") if selected else None,
                "ownership": _ownership_snapshot(ordered),
            },
        )
    )

    return current, logs
