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


def _metric(value, default: float) -> float:
    number = _number(value)
    return default if number is None else number


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
    """Use a support signal only when it separates the live pool.

    This never creates a survivor. If nobody owns the signal, the incoming
    pool remains intact and the audit records NO_SEPARATION.
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


def _finisher_tier(player: Player) -> tuple[int, str]:
    """Discrete finisher lanes. No blended ranking score is created here."""
    missing = _missing(player, "hr_pa", "iso", "damage_score", "fb")
    if missing:
        return 0, f"missing finisher data: {', '.join(missing)}"

    hr_pa = float(player["hr_pa"])
    iso = float(player["iso"])
    damage = float(player["damage_score"])
    air = float(player["fb"])
    pull = _metric(player.get("pull"), 0.0)
    hard_hit = _metric(player.get("hard_hit"), 0.0)
    barrel = _metric(player.get("barrel"), 0.0)

    # Locked Core finisher lane.
    if hr_pa >= 0.050 and iso >= 0.200 and damage >= 70.0 and air >= 30.0:
        return 3, "CORE_FINISHER"

    # Primary event-capable lane.
    if (
        hr_pa >= 0.035
        and iso >= 0.180
        and damage >= 55.0
        and hard_hit >= 40.0
        and air >= 30.0
    ):
        return 2, "PRIMARY_FINISHER"

    # WHO/chaos floor. It is weaker than Core and cannot replace a higher tier.
    if (
        hr_pa >= 0.025
        and iso >= 0.150
        and damage >= 45.0
        and air >= 30.0
        and ((pull >= 60.0 and hard_hit >= 40.0) or barrel >= 10.0)
    ):
        return 1, "WHO_CHAOS_FINISHER"

    return 0, "FINISHER_FLOOR_FAILED"


def _pressure_flags(player: Player, target: dict, environment: dict) -> dict:
    """Context flags only. They are never added into a weighted score."""
    return {
        "top_four_slot": int(player.get("slot") or 99) <= 4,
        "recent_heat": player.get("hr_heat") is True,
        "positive_protection": _metric(player.get("protection"), -1.0) > 0.0,
        "high_bullpen_risk": _metric(player.get("bullpen_risk"), 0.0) >= 5.0,
        "high_pitcher_leak": _metric(target.get("leak_score"), 0.0) >= 0.75,
        "positive_environment": _metric(environment.get("environment_score"), 0.0) > 0.0,
    }


def _matchup_total(player: Player) -> float:
    return (
        _metric(player.get("pitch_type_edge"), -99.0)
        + _metric(player.get("zone_edge"), -99.0)
        + _metric(player.get("mistake_edge"), -99.0)
    )


def _transfer_candidate(players: list[Player]) -> dict | None:
    """Flag only a legitimate adjacent transfer; never select a winner here."""
    if len(players) < 2:
        return None

    # Primary is the highest finisher tier, then the better lineup-access lane.
    ordered = sorted(
        players,
        key=lambda player: (
            int(player.get("finisher_tier") or 0),
            -int(player.get("slot") or 99),
        ),
        reverse=True,
    )
    primary = ordered[0]
    primary_tier = int(primary.get("finisher_tier") or 0)
    primary_matchup = _matchup_total(primary)

    for adjacent in ordered[1:]:
        if abs(int(primary.get("slot") or 99) - int(adjacent.get("slot") or 99)) > 1:
            continue
        if int(adjacent.get("finisher_tier") or 0) != primary_tier:
            continue
        matchup_advantage = _matchup_total(adjacent) - primary_matchup
        if matchup_advantage >= 0.35:
            adjacent["transfer_candidate"] = True
            return {
                "primary": _name(primary),
                "adjacent": _name(adjacent),
                "primary_slot": primary.get("slot"),
                "adjacent_slot": adjacent.get("slot"),
                "finisher_tier": primary_tier,
                "matchup_advantage": round(matchup_advantage, 3),
            }
    return None


def _keep_if_any(
    candidates: list[Player],
    predicate: Callable[[Player], bool],
    stage: str,
    stages: list[dict],
) -> list[Player]:
    """Gate-16 elimination stage: keep a subgroup only when it exists."""
    if len(candidates) <= 1:
        return candidates
    kept = [player for player in candidates if predicate(player)]
    if not kept or len(kept) == len(candidates):
        stages.append(
            {
                "stage": stage,
                "before": len(candidates),
                "after": len(candidates),
                "mode": "NO_SEPARATION",
            }
        )
        return candidates
    stages.append(
        {
            "stage": stage,
            "before": len(candidates),
            "after": len(kept),
            "kept": [_name(player) for player in kept],
        }
    )
    return kept


def _keep_best_band(
    candidates: list[Player],
    field: str,
    bands: tuple[float, ...],
    stage: str,
    stages: list[dict],
) -> list[Player]:
    if len(candidates) <= 1:
        return candidates
    for floor in bands:
        kept = [
            player
            for player in candidates
            if _metric(player.get(field), -999.0) >= floor
        ]
        if kept:
            if len(kept) < len(candidates):
                stages.append(
                    {
                        "stage": stage,
                        "floor": floor,
                        "before": len(candidates),
                        "after": len(kept),
                        "kept": [_name(player) for player in kept],
                    }
                )
                return kept
            break
    stages.append(
        {
            "stage": stage,
            "before": len(candidates),
            "after": len(candidates),
            "mode": "NO_SEPARATION",
        }
    )
    return candidates


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

    # Gate 1: pitcher vulnerability must be identified.
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

    # Gate 2: shared game context. It is audited, not falsely used as a hitter kill.
    environment = game.get("environment") or {}
    env_score = environment.get("environment_score")
    logs.append(
        gate_log(
            2,
            "Game Environment",
            len(current),
            len(current),
            note={
                **environment,
                "data_status": "ACTIVE" if env_score is not None else "UNAVAILABLE",
            },
        )
    )

    # Gate 3: Pull-Air identity. PUA/air support is required only in the support
    # lane; an elite or pass profile is not killed merely because one support
    # column is missing.
    def pull_air(player: Player) -> tuple[bool, str]:
        valid_starter = (
            player.get("lineup_status") in {"OFFICIAL", "CONFIRMED", "PROJECTED"}
            and 1 <= int(player.get("slot") or 99) <= 9
            and str(player.get("position") or "").upper() not in {"P", "SP", "RP"}
        )
        if not valid_starter:
            return False, "not a valid starting position player"

        missing = _missing(player, "pull", "hard_hit")
        if missing:
            return False, f"missing Pull-Air identity data: {', '.join(missing)}"

        pull = float(player["pull"])
        hard_hit = float(player["hard_hit"])
        pitch_edge = _number(player.get("pitch_edge"))

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

        # 50-54 support lane.
        pull_percent = _number(player.get("pull_percent"))
        air = _number(player.get("fb"))
        pua = _number(player.get("pua"))
        pull_barrel = _number(player.get("pull_barrel"))
        missing_support = [
            name
            for name, value in (
                ("pull_percent", pull_percent),
                ("air", air),
                ("pua", pua),
            )
            if value is None
        ]
        if missing_support:
            return False, f"50-54 support lane missing: {', '.join(missing_support)}"

        support = pull_percent >= 45.0 and air >= 40.0 and pua >= 28.0
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
                "support": "50-54 requires raw Pull >= 45, AIR >= 40, PUA >= 28 and matchup edge",
                "auto_kill": "Pull < 50",
            },
            "fb_field": "AIR_PERCENT",
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

    # Gate 5: actual Statcast pitch-type + strike-zone compatibility.
    def matchup(player: Player) -> tuple[bool, str]:
        missing = _missing(player, "pitch_type_edge", "zone_edge", "pitch_edge")
        if missing:
            return False, f"missing Statcast matchup data: {', '.join(missing)}"
        if player.get("pitch_edge_source") != "STATCAST_DETAIL_PITCH_ZONE":
            return False, f"invalid matchup source: {player.get('pitch_edge_source')}"
        pitch_type_edge = float(player["pitch_type_edge"])
        zone_edge = float(player["zone_edge"])
        combined = float(player["pitch_edge"])
        elite_identity = (
            float(player.get("pull") or 0.0) >= 70.0
            and float(player.get("hard_hit") or 0.0) >= 45.0
        )
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

    # Gate 6: lineup access.
    current = _apply(
        current,
        6,
        "Lineup Access",
        lambda player: (
            int(player.get("slot") or 99) <= 7,
            "slot 8-9 lacks primary event access",
        ),
        logs,
    )

    # Gate 7: recent signal separates only when a live signal exists.
    recent_loaded = sum(1 for player in current if player.get("hr_heat") is not None)
    current = _separator(
        current,
        7,
        "Recent HR Signal",
        lambda player: (
            player.get("hr_heat") is True,
            "no live 14-day HR/slugging signal"
            if player.get("hr_heat") is not None
            else "recent feed unavailable",
        ),
        logs,
        note={
            "loaded": recent_loaded,
            "data_status": "ACTIVE" if recent_loaded else "UNAVAILABLE",
        },
    )

    # Gate 8: season conversion.
    def conversion(player: Player) -> tuple[bool, str]:
        missing = _missing(player, "hr_pa", "iso")
        if missing:
            return False, f"missing conversion data: {', '.join(missing)}"
        hr_pa = float(player["hr_pa"])
        iso = float(player["iso"])
        barrel = _metric(player.get("barrel"), 0.0)
        passed = hr_pa >= 0.025 or (iso >= 0.180 and barrel >= 10.0)
        return passed, "HR conversion below floor"

    current = _apply(current, 8, "HR Conversion", conversion, logs)

    # Gate 9: actual mistake-location compatibility.
    mistake_loaded = sum(1 for player in current if player.get("mistake_edge") is not None)
    current = _separator(
        current,
        9,
        "Count / Mistake Access",
        lambda player: (
            player.get("mistake_edge") is not None and float(player["mistake_edge"]) >= 0.0,
            "negative performance against the pitcher's mistake locations"
            if player.get("mistake_edge") is not None
            else "mistake-location data unavailable",
        ),
        logs,
        note={
            "loaded": mistake_loaded,
            "data_status": "ACTIVE" if mistake_loaded else "UNAVAILABLE",
            "pitcher_mistake_rate": next(
                (
                    player.get("pitcher_mistake_rate")
                    for player in current
                    if player.get("pitcher_mistake_rate") is not None
                ),
                None,
            ),
        },
    )

    # Gate 10: projected PA stop.
    current = _apply(
        current,
        10,
        "Opportunity Stop",
        lambda player: (
            int(player.get("slot") or 99) <= 6,
            "slot outside projected PA stop",
        ),
        logs,
    )

    # Finisher tiers are calculated before transfer, but no winner is selected.
    for player in current:
        tier, label = _finisher_tier(player)
        player["finisher_tier"] = tier
        player["finisher_label"] = label

    # Gate 10.5: identify a legitimate adjacent lane only.
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

    # Gate 11: bullpen continuation is shared context, not a fake hitter score.
    bullpen = (
        game.get("away_bullpen")
        if target.get("side") == "home"
        else game.get("home_bullpen")
    )
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
            note={
                **bullpen,
                "data_status": "ACTIVE" if bullpen.get("loaded") else "UNAVAILABLE",
            },
        )
    )

    # Gate 12: pressure/cadence is audited as flags only; no weighted score.
    for player in current:
        player["pressure_flags"] = _pressure_flags(player, target, environment)
    logs.append(
        gate_log(
            12,
            "Pressure / Cadence",
            len(current),
            len(current),
            note={
                "scores": [
                    {
                        "player": _name(player),
                        "flags": player.get("pressure_flags"),
                    }
                    for player in current
                ],
                "rule": "context only; never outweighs finisher",
            },
        )
    )

    # Gate 13: Universe is isolated and tie-break only.
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
                    {
                        "player": _name(player),
                        "universe_score": player.get("universe_score"),
                    }
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
            "isolated lineup cluster"
            if player.get("protection") is not None
            else "protection data unavailable",
        ),
        logs,
        note={
            "loaded": protection_loaded,
            "data_status": "ACTIVE" if protection_loaded else "UNAVAILABLE",
        },
    )

    # Gate 15: discrete HR finisher identity. Keep the strongest available lane,
    # not a weighted score winner.
    before = len(current)
    removed: list[dict] = []
    if current:
        for player in current:
            tier, label = _finisher_tier(player)
            player["finisher_tier"] = tier
            player["finisher_label"] = label
        best_tier = max(int(player.get("finisher_tier") or 0) for player in current)
        if best_tier > 0:
            finishers = [
                player
                for player in current
                if int(player.get("finisher_tier") or 0) == best_tier
            ]
            removed = [
                {
                    "player": _name(player),
                    "reason": (
                        f"lower finisher lane {player.get('finisher_tier')} "
                        f"than live lane {best_tier}"
                    ),
                }
                for player in current
                if int(player.get("finisher_tier") or 0) != best_tier
            ]
            current = finishers
        else:
            removed = [
                {
                    "player": _name(player),
                    "reason": player.get("finisher_label") or "finisher floor failed",
                }
                for player in current
            ]
            current = []
    logs.append(
        gate_log(
            15,
            "HR Finisher Identity",
            before,
            len(current),
            removed,
            note={
                "scores": [
                    {
                        "player": _name(player),
                        "finisher_tier": player.get("finisher_tier"),
                        "finisher_label": player.get("finisher_label"),
                        "hr_pa": player.get("hr_pa"),
                        "iso": player.get("iso"),
                        "damage": player.get("damage_score"),
                        "air": player.get("fb"),
                    }
                    for player in current
                ],
                "rule": "discrete Core / Primary / WHO lanes; no blended finisher score",
            },
        )
    )

    # Gate 16: one last man through explicit sequential elimination stages.
    before = len(current)
    if not current:
        logs.append(gate_log(16, "Last-Man Survivor", 0, 0, note={"decision": "WHO"}))
        return [], logs

    candidates = list(current)
    stages: list[dict] = []

    # A marked adjacent transfer only survives if it still owns the stronger
    # matchup after every later gate. It never jumps a higher finisher tier.
    if candidate and len(candidates) > 1:
        adjacent_name = candidate.get("adjacent")
        primary_name = candidate.get("primary")
        adjacent = next((p for p in candidates if _name(p) == adjacent_name), None)
        primary = next((p for p in candidates if _name(p) == primary_name), None)
        if adjacent is not None and primary is not None:
            advantage = _matchup_total(adjacent) - _matchup_total(primary)
            if (
                int(adjacent.get("finisher_tier") or 0)
                == int(primary.get("finisher_tier") or 0)
                and advantage >= 0.35
            ):
                candidates = [adjacent]
                stages.append(
                    {
                        "stage": "ADJACENT_TRANSFER",
                        "before": before,
                        "after": 1,
                        "winner": _name(adjacent),
                        "matchup_advantage": round(advantage, 3),
                    }
                )

    if len(candidates) > 1:
        max_tier = max(int(player.get("finisher_tier") or 0) for player in candidates)
        candidates = _keep_if_any(
            candidates,
            lambda player: int(player.get("finisher_tier") or 0) == max_tier,
            "FINISHER_TIER",
            stages,
        )

    candidates = _keep_if_any(
        candidates,
        lambda player: _metric(player.get("pitch_type_edge"), -99.0) >= 0.20,
        "PITCH_TYPE_EDGE_0.20",
        stages,
    )
    candidates = _keep_if_any(
        candidates,
        lambda player: _metric(player.get("zone_edge"), -99.0) >= 0.20,
        "ZONE_EDGE_0.20",
        stages,
    )
    candidates = _keep_if_any(
        candidates,
        lambda player: _metric(player.get("mistake_edge"), -99.0) >= 0.10,
        "MISTAKE_EDGE_0.10",
        stages,
    )
    candidates = _keep_if_any(
        candidates,
        lambda player: player.get("hr_heat") is True,
        "RECENT_HR_SIGNAL",
        stages,
    )
    candidates = _keep_if_any(
        candidates,
        lambda player: _metric(player.get("protection"), -1.0) > 0.0,
        "POSITIVE_PROTECTION",
        stages,
    )
    candidates = _keep_if_any(
        candidates,
        lambda player: int(player.get("slot") or 99) <= 4,
        "TOP_FOUR_ACCESS",
        stages,
    )

    # Finisher component bands are used one at a time, never added together.
    candidates = _keep_best_band(
        candidates,
        "hr_pa",
        (0.060, 0.050, 0.045, 0.040, 0.035, 0.030, 0.025),
        "HR_PA_BAND",
        stages,
    )
    candidates = _keep_best_band(
        candidates,
        "iso",
        (0.300, 0.260, 0.230, 0.200, 0.180, 0.150),
        "ISO_BAND",
        stages,
    )
    candidates = _keep_best_band(
        candidates,
        "damage_score",
        (90.0, 80.0, 70.0, 60.0, 55.0, 45.0),
        "DAMAGE_BAND",
        stages,
    )

    # Universe is the final tie-break only.
    if len(candidates) > 1:
        winner = max(candidates, key=lambda player: int(player.get("universe_score") or 0))
        stages.append(
            {
                "stage": "UNIVERSE_FINAL_TIE_BREAK",
                "before": len(candidates),
                "after": 1,
                "winner": _name(winner),
            }
        )
        candidates = [winner]

    winner = candidates[0]
    winner["ownership_score"] = int(winner.get("finisher_tier") or 0)
    winner["event_reason"] = (
        "Gate 16 last man through sequential finisher, matchup, recent, "
        "protection and opportunity eliminations; Universe used only if still tied"
    )

    removed = [
        {"player": _name(player), "reason": "lost Gate 16 sequential elimination"}
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
                "finisher_tier": winner.get("finisher_tier"),
                "finisher_label": winner.get("finisher_label"),
                "stages": stages,
                "rule": "no blended ranking; explicit gate-by-gate last-man elimination",
            },
        )
    )
    return [winner], logs
