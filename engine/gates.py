from __future__ import annotations

import hashlib
from typing import Callable

Player = dict
Predicate = Callable[[Player], tuple[bool, str]]


def gate_log(gate, name, before, after, removed=None, note=None):
    return {
        "gate": gate,
        "name": name,
        "before": before,
        "after": after,
        "removed": removed or [],
        "note": note,
    }


def _number(value, default: float | None = None) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _name(player: Player) -> str:
    return str(player.get("name") or player.get("player") or "UNKNOWN")


def _missing(player: Player, *fields: str) -> list[str]:
    return [field for field in fields if player.get(field) is None]


def _apply(
    players: list[Player],
    gate,
    name: str,
    predicate: Predicate,
    logs: list[dict],
    *,
    note=None,
) -> list[Player]:
    """Apply a real elimination gate.

    Missing information is never treated as a pass.  A gate is allowed to
    empty the pool; core.py then returns the explicit WHO result instead of
    inventing a hitter or silently restoring somebody who failed.
    """
    before = len(players)
    kept: list[Player] = []
    removed: list[dict] = []
    for player in players:
        passed, reason = predicate(player)
        if passed:
            kept.append(player)
        else:
            removed.append({"player": _name(player), "reason": reason})
    logs.append(gate_log(gate, name, before, len(kept), removed, note=note))
    return kept


def _separator(
    players: list[Player],
    gate,
    name: str,
    predicate: Predicate,
    logs: list[dict],
    *,
    note=None,
) -> list[Player]:
    """Use a signal only when it genuinely separates the remaining pool.

    This is for support gates such as recent rhythm and protection.  When the
    signal is loaded but nobody owns it, the gate records NO_SEPARATION and
    preserves the incoming pool.  That is not a missing-data pass and it never
    creates a winner.
    """
    before = len(players)
    if not players:
        logs.append(gate_log(gate, name, 0, 0, note=note))
        return []

    passed: list[Player] = []
    failed: list[tuple[Player, str]] = []
    for player in players:
        ok, reason = predicate(player)
        if ok:
            passed.append(player)
        else:
            failed.append((player, reason))

    if passed:
        logs.append(
            gate_log(
                gate,
                name,
                before,
                len(passed),
                [{"player": _name(player), "reason": reason} for player, reason in failed],
                note=note,
            )
        )
        return passed

    detail = {
        "mode": "NO_SEPARATION",
        "failed_checks": [
            {"player": _name(player), "reason": reason} for player, reason in failed
        ],
    }
    if isinstance(note, dict):
        detail = {**note, **detail}
    elif note is not None:
        detail["context"] = note
    logs.append(gate_log(gate, name, before, before, note=detail))
    return list(players)


def _universe_score(player: Player, game: dict) -> int:
    """Deterministic final tie-break only; never a baseball score or kill."""
    seed = "|".join(
        [
            str(game.get("date") or ""),
            str(game.get("game_id") or game.get("gamePk") or ""),
            str(player.get("id") or ""),
            str(player.get("slot") or ""),
        ]
    )
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 1000


def _finisher_score(player: Player) -> float | None:
    required = ("hr_pa", "iso", "damage_score", "pull", "pitch_edge")
    if _missing(player, *required):
        return None

    hr_pa = max(0.0, float(player["hr_pa"]))
    iso = max(0.0, float(player["iso"]))
    damage = max(0.0, min(100.0, float(player["damage_score"])))
    pull = max(0.0, min(100.0, float(player["pull"])))
    pitch_edge = max(-1.5, min(1.5, float(player["pitch_edge"])))

    score = (
        min(1.35, hr_pa / 0.050) * 28.0
        + min(1.35, iso / 0.220) * 24.0
        + (damage / 100.0) * 24.0
        + min(1.25, pull / 70.0) * 14.0
        + ((pitch_edge + 1.5) / 3.0) * 10.0
    )
    return round(min(100.0, score), 3)


def _pressure_score(player: Player, target: dict, environment: dict) -> float:
    """Secondary context only. Gate 16 never places this above finisher."""
    slot = int(player.get("slot") or 9)
    access = max(0.0, 8.0 - slot) * 0.7
    rhythm = 2.0 if player.get("hr_heat") is True else 0.0
    protection = max(0.0, float(player.get("protection") or 0.0)) * 1.5
    bullpen = max(0.0, float(player.get("bullpen_risk") or 0.0)) * 0.35
    pitcher = max(0.0, float(target.get("leak_score") or 0.0)) * 0.5
    env = max(-2.0, min(3.0, float(environment.get("environment_score") or 0.0))) * 0.4
    return round(access + rhythm + protection + bullpen + pitcher + env, 3)


def _transfer_candidate(players: list[Player]) -> dict | None:
    if len(players) < 2:
        return None
    ordered = sorted(
        players,
        key=lambda p: (
            _number(p.get("pre_finisher_score"), -999.0),
            _number(p.get("damage_score"), -999.0),
            _number(p.get("pitch_edge"), -999.0),
        ),
        reverse=True,
    )
    primary, adjacent = ordered[0], ordered[1]
    top_score = float(primary.get("pre_finisher_score") or 0.0)
    second_score = float(adjacent.get("pre_finisher_score") or 0.0)
    gap = top_score - second_score
    same_lane = abs(int(primary.get("slot") or 99) - int(adjacent.get("slot") or 99)) <= 1
    stronger_matchup = float(adjacent.get("pitch_edge") or -999.0) > float(primary.get("pitch_edge") or -999.0) + 0.15
    stronger_rhythm = adjacent.get("hr_heat") is True and primary.get("hr_heat") is not True
    obvious_primary = float(primary.get("hr_model_score") or 0.0) >= 80.0 or float(primary.get("hr") or 0.0) >= 20.0

    if same_lane and obvious_primary and gap <= 5.0 and (stronger_matchup or stronger_rhythm):
        adjacent["transfer_candidate"] = True
        return {
            "primary": _name(primary),
            "adjacent": _name(adjacent),
            "finisher_gap": round(gap, 3),
            "stronger_matchup": stronger_matchup,
            "stronger_rhythm": stronger_rhythm,
        }
    return None


def run_all_gates(hitters: list[dict], game: dict, target: dict):
    logs: list[dict] = []

    # Gate 0: one pitcher-side only.
    current = [player for player in hitters if player.get("side") == target.get("side")]
    logs.append(
        gate_log(
            0,
            "Target Side Isolation",
            len(hitters),
            len(current),
            note={
                "target_team": target.get("team"),
                "target_side": target.get("side"),
                "opposing_pitcher": (target.get("pitcher") or {}).get("name"),
                "pitcher_leak_score": target.get("leak_score"),
            },
        )
    )

    # Gate 1: the selected pitcher vulnerability must be real and identified.
    pitcher = target.get("pitcher") or {}
    pitcher_ready = pitcher.get("id") is not None and target.get("leak_score") is not None
    current = _apply(
        current,
        1,
        "Pitcher Vulnerability",
        lambda player: (
            pitcher_ready,
            "opposing probable pitcher or vulnerability data unavailable",
        ),
        logs,
        note={
            "pitcher": pitcher.get("name"),
            "pitcher_id": pitcher.get("id"),
            "throws": pitcher.get("throws"),
            "hr9": pitcher.get("hr9"),
            "k_rate": pitcher.get("k_rate"),
            "leak_score": target.get("leak_score"),
        },
    )

    # Gate 2: environment is game-level context. It cannot favor one hitter on
    # the same side, so it is audited and carried forward instead of pretending
    # to eliminate individuals.
    environment = game.get("environment") or {}
    env_score = environment.get("environment_score")
    env_status = "ACTIVE" if env_score is not None else "UNAVAILABLE"
    logs.append(
        gate_log(
            2,
            "Game Environment",
            len(current),
            len(current),
            note={**environment, "data_status": env_status},
        )
    )

    # Gate 3: locked Pull-Air identity rules. The lineup service already
    # returns the starting nine, but validity is rechecked here so an invalid
    # player can never enter the baseball gates.
    def pull_air(player: Player) -> tuple[bool, str]:
        valid_starter = (
            player.get("lineup_status") in {"OFFICIAL", "CONFIRMED", "PROJECTED"}
            and 1 <= int(player.get("slot") or 99) <= 9
            and str(player.get("position") or "").upper() not in {"P", "SP", "RP"}
        )
        if not valid_starter:
            return False, "not a valid starting position player"

        missing = _missing(player, "pull", "hard_hit", "pua", "fb")
        if missing:
            return False, f"missing Pull-Air data: {', '.join(missing)}"
        pull = float(player["pull"])
        hard_hit = float(player["hard_hit"])
        pitch_edge = _number(player.get("pitch_edge"))
        pull_percent = _number(player.get("pull_percent"), 0.0) or 0.0
        flyball = float(player["fb"])
        pua = float(player["pua"])
        pull_barrel = _number(player.get("pull_barrel"))

        if pull < 50.0:
            return False, "Pull-Air identity < 50 auto-kill"
        if pull >= 70.0 and hard_hit >= 45.0:
            return True, "Pull >= 70 and HH >= 45 combo auto-pass"
        if pull >= 65.0 and hard_hit >= 50.0:
            return True, "Pull >= 65 and HH >= 50 combo auto-pass"
        if pull >= 65.0:
            return True, "Pull-Air pass lane"
        if 55.0 <= pull < 65.0:
            passed = hard_hit >= 45.0 and pitch_edge is not None and pitch_edge >= 0.0
            return passed, "borderline Pull-Air requires HH >= 45 and positive pitch edge"

        support = pull_percent >= 45.0 and flyball >= 40.0 and pua >= 28.0
        if pull_barrel is not None:
            support = support and pull_barrel >= 10.0
        passed = support and hard_hit >= 45.0 and pitch_edge is not None and pitch_edge >= 0.15
        return passed, "50-54 Pull-Air lane lacks full support and matchup edge"

    current = _apply(
        current,
        3,
        "Pull-Air Identity",
        pull_air,
        logs,
        note={
            "thresholds": {
                "elite": "Pull >= 70 and HH >= 45",
                "pass": "Pull >= 65",
                "borderline": "55-64 requires HH >= 45 plus positive pitch edge",
                "auto_kill": "Pull < 50",
            }
        },
    )

    # Gate 4: damage quality is independent of ownership and pressure.
    def damage_quality(player: Player) -> tuple[bool, str]:
        missing = _missing(player, "hard_hit", "damage_score")
        if missing:
            return False, f"missing damage data: {', '.join(missing)}"
        hard_hit = float(player["hard_hit"])
        damage = float(player["damage_score"])
        barrel = _number(player.get("barrel"))
        pull = float(player.get("pull") or 0.0)

        if hard_hit < 40.0:
            return False, "Hard Hit < 40 auto-kill"
        if pull >= 70.0 and hard_hit >= 45.0:
            return True, "elite Pull/HH damage combo"
        if pull >= 65.0 and hard_hit >= 50.0:
            return True, "strong Pull/HH damage combo"
        if hard_hit >= 45.0 and damage >= 45.0:
            return True, "damage pass lane"
        if 40.0 <= hard_hit < 45.0:
            passed = barrel is not None and barrel >= 10.0 and damage >= 65.0
            return passed, "borderline HH requires Barrel >= 10 and damage >= 65"
        return False, "damage quality below floor"

    current = _apply(current, 4, "Damage Quality", damage_quality, logs)

    # Gate 5: real pitch-type + strike-zone compatibility from Statcast.
    def matchup(player: Player) -> tuple[bool, str]:
        missing = _missing(player, "pitch_type_edge", "zone_edge", "pitch_edge")
        if missing:
            return False, f"missing Statcast matchup data: {', '.join(missing)}"
        if player.get("pitch_edge_source") != "STATCAST_DETAIL_PITCH_ZONE":
            return False, f"invalid matchup source: {player.get('pitch_edge_source')}"
        pitch_type_edge = float(player["pitch_type_edge"])
        zone_edge = float(player["zone_edge"])
        combined = float(player["pitch_edge"])
        elite_identity = float(player.get("pull") or 0.0) >= 70.0 and float(player.get("hard_hit") or 0.0) >= 45.0
        passed = combined >= 0.0 and pitch_type_edge >= -0.20 and zone_edge >= -0.20
        if not passed and elite_identity:
            passed = combined >= -0.08 and pitch_type_edge >= -0.15 and zone_edge >= -0.15
        return passed, "negative pitch-type/zone compatibility"

    matchup_sources = sorted({str(player.get("pitch_edge_source")) for player in current})
    current = _apply(
        current,
        5,
        "Pitch-Type + Zone Matchup",
        matchup,
        logs,
        note={
            "sources": matchup_sources,
            "pitcher": pitcher.get("name"),
            "required_source": "STATCAST_DETAIL_PITCH_ZONE",
        },
    )

    # Gate 6: lineup access. Bottom two slots cannot own the primary event.
    current = _apply(
        current,
        6,
        "Lineup Access",
        lambda player: (int(player.get("slot") or 99) <= 7, "slot 8-9 lacks primary event access"),
        logs,
    )

    # Gate 7: recent signal separates only when at least one live signal exists.
    recent_loaded = sum(1 for player in current if player.get("hr_heat") is not None)
    current = _separator(
        current,
        7,
        "Recent HR Signal",
        lambda player: (
            player.get("hr_heat") is True,
            "no live 14-day HR/slugging signal" if player.get("hr_heat") is not None else "recent feed unavailable",
        ),
        logs,
        note={
            "loaded": recent_loaded,
            "data_status": "ACTIVE" if recent_loaded else "UNAVAILABLE",
        },
    )

    # Gate 8: season conversion cannot be missing and must show a real HR lane.
    def conversion(player: Player) -> tuple[bool, str]:
        missing = _missing(player, "hr_pa", "iso")
        if missing:
            return False, f"missing conversion data: {', '.join(missing)}"
        hr_pa = float(player["hr_pa"])
        iso = float(player["iso"])
        barrel = _number(player.get("barrel"), 0.0) or 0.0
        passed = hr_pa >= 0.025 or (iso >= 0.180 and barrel >= 10.0)
        return passed, "HR conversion below floor"

    current = _apply(current, 8, "HR Conversion", conversion, logs)

    # Gate 9: actual middle-third mistake locations and hitter damage there.
    mistake_loaded = sum(1 for player in current if player.get("mistake_edge") is not None)
    current = _separator(
        current,
        9,
        "Count / Mistake Access",
        lambda player: (
            player.get("mistake_edge") is not None and float(player["mistake_edge"]) >= 0.0,
            "negative performance against the pitcher's middle-third locations"
            if player.get("mistake_edge") is not None
            else "mistake-location data unavailable",
        ),
        logs,
        note={
            "loaded": mistake_loaded,
            "data_status": "ACTIVE" if mistake_loaded else "UNAVAILABLE",
            "pitcher_mistake_rate": next(
                (player.get("pitcher_mistake_rate") for player in current if player.get("pitcher_mistake_rate") is not None),
                None,
            ),
        },
    )

    # Gate 10: stop at hitters projected for enough plate appearances.
    current = _apply(
        current,
        10,
        "Opportunity Stop",
        lambda player: (int(player.get("slot") or 99) <= 6, "slot outside projected PA stop"),
        logs,
    )
    for player in current:
        player["pre_finisher_score"] = _finisher_score(player)

    # Gate 10.5: adjacent transfer is only flagged here; it cannot override a
    # clearly stronger finisher and cannot eliminate anybody by itself.
    candidate = _transfer_candidate(current)
    logs.append(
        gate_log(
            10.5,
            "Adjacent / Decoy Transfer",
            len(current),
            len(current),
            note={"candidate": candidate, "executed": False},
        )
    )

    # Gate 11: continuation through the opposing relief corps. Same bullpen for
    # every hitter, so this is a verified context gate rather than a fake player
    # elimination.
    bullpen = game.get("away_bullpen") if target.get("side") == "home" else game.get("home_bullpen")
    bullpen = bullpen or {}
    for player in current:
        player["bullpen_risk"] = bullpen.get("risk_score")
        player["bullpen_source"] = bullpen.get("source")
    logs.append(
        gate_log(
            11,
            "Bullpen Continuation",
            len(current),
            len(current),
            note={**bullpen, "data_status": "ACTIVE" if bullpen.get("loaded") else "UNAVAILABLE"},
        )
    )

    # Gate 12: pressure/cadence is calculated for every survivor but remains a
    # secondary component. It never ranks above the finisher at Gate 16.
    for player in current:
        player["pressure_score"] = _pressure_score(player, target, environment)
    logs.append(
        gate_log(
            12,
            "Pressure / Cadence",
            len(current),
            len(current),
            note={
                "scores": [
                    {"player": _name(player), "pressure_score": player.get("pressure_score")}
                    for player in current
                ],
                "rule": "pressure cannot outweigh finisher",
            },
        )
    )

    # Gate 13: Universe remains completely isolated and tie-break only.
    for player in current:
        player["universe_score"] = _universe_score(player, game)
    logs.append(
        gate_log(
            13,
            "Universe",
            len(current),
            len(current),
            note={
                "mode": "TIE_BREAK_ONLY",
                "scores": [
                    {"player": _name(player), "universe_score": player.get("universe_score")}
                    for player in current
                ],
            },
        )
    )

    # Gate 14: lineup protection separates only if a positive cluster exists.
    protection_loaded = sum(1 for player in current if player.get("protection") is not None)
    current = _separator(
        current,
        14,
        "Lineup Protection",
        lambda player: (
            player.get("protection") is not None and float(player["protection"]) >= 0.0,
            "isolated lineup cluster" if player.get("protection") is not None else "protection data unavailable",
        ),
        logs,
        note={
            "loaded": protection_loaded,
            "data_status": "ACTIVE" if protection_loaded else "UNAVAILABLE",
        },
    )

    # Gate 15: HR finisher identity. No pressure or Universe input is included.
    removed = []
    finishers = []
    before = len(current)
    for player in current:
        score = _finisher_score(player)
        player["finisher_score"] = score
        if score is None:
            removed.append({"player": _name(player), "reason": "missing finisher data"})
            continue
        hr_pa = float(player.get("hr_pa") or 0.0)
        iso = float(player.get("iso") or 0.0)
        damage = float(player.get("damage_score") or 0.0)
        if score >= 50.0 and hr_pa >= 0.020 and iso >= 0.140 and damage >= 45.0:
            finishers.append(player)
        else:
            removed.append(
                {
                    "player": _name(player),
                    "reason": f"finisher floor failed (score={score}, HR/PA={hr_pa:.3f}, ISO={iso:.3f}, damage={damage:.1f})",
                }
            )
    current = finishers
    logs.append(
        gate_log(
            15,
            "HR Finisher Identity",
            before,
            len(current),
            removed,
            note={
                "scores": [
                    {"player": _name(player), "finisher_score": player.get("finisher_score")}
                    for player in current
                ]
            },
        )
    )

    # Gate 16: exactly one last man from the hitters who survived every hard
    # baseball gate. Finisher leads; transfer is allowed only inside a narrow
    # finisher band with stronger matchup/recent evidence.
    before = len(current)
    if not current:
        logs.append(gate_log(16, "Last-Man Survivor", 0, 0, note={"decision": "WHO"}))
        return [], logs

    ordered = sorted(
        current,
        key=lambda player: (
            _number(player.get("finisher_score"), -999.0),
            _number(player.get("damage_score"), -999.0),
            _number(player.get("pitch_edge"), -999.0),
            _number(player.get("hr_pa"), -999.0),
            _number(player.get("iso"), -999.0),
            bool(player.get("hr_heat")),
            _number(player.get("pressure_score"), -999.0),
            _number(player.get("universe_score"), -999.0),
        ),
        reverse=True,
    )
    winner = ordered[0]
    transfer_executed = False
    transfer_reason = None

    for challenger in ordered[1:]:
        if not challenger.get("transfer_candidate"):
            continue
        finisher_gap = float(winner.get("finisher_score") or 0.0) - float(challenger.get("finisher_score") or 0.0)
        stronger_matchup = float(challenger.get("pitch_edge") or -999.0) >= float(winner.get("pitch_edge") or -999.0) + 0.20
        stronger_rhythm = challenger.get("hr_heat") is True and winner.get("hr_heat") is not True
        if finisher_gap <= 3.0 and (stronger_matchup or stronger_rhythm):
            winner = challenger
            transfer_executed = True
            transfer_reason = {
                "finisher_gap": round(finisher_gap, 3),
                "stronger_matchup": stronger_matchup,
                "stronger_rhythm": stronger_rhythm,
            }
        break

    winner["ownership_score"] = winner.get("finisher_score") or 0.0
    winner["event_reason"] = (
        "Gate 16 last man: survived Pull-Air, damage, real pitch-type/zone, "
        "conversion, mistake, opportunity, bullpen, protection and finisher gates"
    )
    if transfer_executed:
        winner["event_reason"] += "; adjacent transfer executed inside the 3-point finisher band"

    removed = [
        {"player": _name(player), "reason": "lost Gate 16 last-man comparison"}
        for player in current
        if player is not winner
    ]
    logs.append(
        gate_log(
            16,
            "Last-Man Survivor",
            before,
            1,
            removed,
            note={
                "winner": _name(winner),
                "finisher_score": winner.get("finisher_score"),
                "pressure_score": winner.get("pressure_score"),
                "transfer_executed": transfer_executed,
                "transfer_reason": transfer_reason,
                "rule": "finisher first; pressure and Universe are tie-breakers only",
            },
        )
    )
    return [winner], logs
