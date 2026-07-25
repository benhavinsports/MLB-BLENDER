from __future__ import annotations

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


def _metric(player: Player, field: str, default: float = -999.0) -> float:
    value = _number(player.get(field))
    return default if value is None else value


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
    """Apply a strict elimination gate.

    Missing/failed evidence removes the hitter. The gate never rescues a player
    and never chooses a fallback winner.
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
    """Use a support signal only when it genuinely separates the live pool.

    Recent form and protection are supporting evidence, not permission to erase
    an entire valid game. When nobody owns the signal, the incoming pool remains
    unchanged and the audit records NO_SEPARATION. Missing feed data is still
    exposed to Gate 17 and can block the final lock.
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

    if passed and len(passed) < before:
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


def _finisher_lane(player: Player) -> tuple[int, str, str]:
    """Return a categorical finisher lane; no blended score is created."""
    missing = _missing(player, "hr_pa", "iso", "damage_score", "fb", "hard_hit")
    if missing:
        return 0, "NO_FINISHER", f"missing finisher data: {', '.join(missing)}"

    hr_pa = float(player["hr_pa"])
    iso = float(player["iso"])
    damage = float(player["damage_score"])
    air = float(player["fb"])
    hard_hit = float(player["hard_hit"])
    pull = _metric(player, "pull", 0.0)
    barrel = _metric(player, "barrel", 0.0)

    if hr_pa >= 0.050 and iso >= 0.210 and damage >= 70.0 and air >= 40.0:
        return 3, "CORE_FINISHER", "core finisher lane"
    if (
        hr_pa >= 0.035
        and iso >= 0.180
        and damage >= 55.0
        and hard_hit >= 40.0
        and air >= 35.0
    ):
        return 2, "PRIMARY_FINISHER", "primary finisher lane"
    if (
        hr_pa >= 0.025
        and iso >= 0.150
        and damage >= 45.0
        and hard_hit >= 40.0
        and air >= 35.0
        and ((pull >= 55.0 and hard_hit >= 40.0) or barrel >= 10.0)
    ):
        return 1, "WHO_CHAOS_FINISHER", "WHO/chaos finisher lane"
    return 0, "NO_FINISHER", "finisher floor failed"


def _chaos_signals(player: Player, game: dict) -> dict:
    environment = game.get("environment") or {}
    return {
        "weak_slot": 5 <= int(player.get("slot") or 99) <= 7,
        "positive_pitch_type": _metric(player, "pitch_type_edge") >= 0.0,
        "positive_zone": _metric(player, "zone_edge") >= 0.0,
        "mistake_leak": _metric(player, "mistake_edge") >= 0.10,
        "bullpen_chaos": _metric(player, "bullpen_risk", 0.0) >= 5.5,
        "unstable_environment": abs(
            _number(environment.get("environment_score"), 0.0) or 0.0
        ) >= 1.5,
        "low_pressure_lane": int(player.get("slot") or 99) >= 5,
        "isolated_cluster": _metric(player, "protection", 0.0) <= 0.0,
    }


def _prequalifies_who(player: Player, game: dict) -> bool:
    signals = _chaos_signals(player, game)
    required = (
        signals["weak_slot"]
        and signals["positive_pitch_type"]
        and signals["positive_zone"]
        and signals["mistake_leak"]
        and (signals["bullpen_chaos"] or signals["unstable_environment"])
    )
    return bool(required)


def _adjacent_transfer(players: list[Player]) -> tuple[list[Player], dict]:
    """Execute Gate 10.5 only for one unambiguous adjacent transfer.

    The adjacent hitter must remain in the same finisher lane, sit directly next
    to the primary, own both matchup lanes, and remain within the primary's
    conversion/damage lane. Pressure alone can never transfer the event.
    """
    if len(players) < 2:
        return players, {"executed": False, "reason": "fewer than two live hitters"}

    max_tier = max(int(player.get("finisher_tier") or 0) for player in players)
    obvious = [
        player
        for player in players
        if int(player.get("finisher_tier") or 0) == max_tier
        and int(player.get("slot") or 99) <= 4
        and (
            player.get("finisher_label") == "CORE_FINISHER"
            or _metric(player, "hr_pa", 0.0) >= 0.040
            or _metric(player, "hr", 0.0) >= 20.0
        )
    ]
    if len(obvious) != 1:
        return players, {
            "executed": False,
            "reason": "no unique obvious primary",
            "obvious": [_name(player) for player in obvious],
        }

    primary = obvious[0]
    primary["primary_flag"] = True
    primary_slot = int(primary.get("slot") or 99)
    eligible: list[Player] = []
    evidence_by_name: dict[str, list[str]] = {}

    for adjacent in players:
        if adjacent is primary:
            continue
        if abs(int(adjacent.get("slot") or 99) - primary_slot) != 1:
            continue
        if int(adjacent.get("finisher_tier") or 0) != max_tier:
            continue

        pitch_adv = _metric(adjacent, "pitch_type_edge") - _metric(primary, "pitch_type_edge")
        zone_adv = _metric(adjacent, "zone_edge") - _metric(primary, "zone_edge")
        conversion_close = (
            _metric(adjacent, "hr_pa", -1.0) >= _metric(primary, "hr_pa", -1.0) - 0.003
            and _metric(adjacent, "iso", -1.0) >= _metric(primary, "iso", -1.0) - 0.015
            and _metric(adjacent, "damage_score", -1.0)
            >= _metric(primary, "damage_score", -1.0) - 5.0
        )
        matchup_clear = (
            pitch_adv >= 0.0
            and zone_adv >= 0.0
            and max(pitch_adv, zone_adv) >= 0.15
        )
        if not (conversion_close and matchup_clear):
            continue

        evidence = ["adjacent_slot", "same_finisher_lane", "conversion_lane_held"]
        if pitch_adv >= 0.15:
            evidence.append("stronger_pitch_type")
        if zone_adv >= 0.15:
            evidence.append("stronger_zone")
        if adjacent.get("hr_heat") is True and primary.get("hr_heat") is not True:
            evidence.append("live_recent_signal")
        if _metric(adjacent, "protection", -1.0) > _metric(primary, "protection", -1.0):
            evidence.append("better_protection")

        adjacent["transfer_pitch_advantage"] = round(pitch_adv, 3)
        adjacent["transfer_zone_advantage"] = round(zone_adv, 3)
        evidence_by_name[_name(adjacent)] = evidence
        eligible.append(adjacent)

    if len(eligible) != 1:
        return players, {
            "executed": False,
            "reason": "transfer lane not unique",
            "primary": _name(primary),
            "eligible": [_name(player) for player in eligible],
            "evidence": evidence_by_name,
        }

    adjacent = eligible[0]
    adjacent["transfer_flag"] = True
    adjacent["primary_source"] = _name(primary)
    adjacent["transfer_evidence"] = evidence_by_name[_name(adjacent)]
    kept = [player for player in players if player is not primary]
    return kept, {
        "executed": True,
        "primary": _name(primary),
        "adjacent": _name(adjacent),
        "primary_slot": primary.get("slot"),
        "adjacent_slot": adjacent.get("slot"),
        "finisher_tier": max_tier,
        "pitch_advantage": adjacent.get("transfer_pitch_advantage"),
        "zone_advantage": adjacent.get("transfer_zone_advantage"),
        "evidence": adjacent.get("transfer_evidence"),
    }


def _categorical_separate(
    players: list[Player],
    predicate: Callable[[Player], bool],
    stage: str,
    stages: list[dict],
) -> list[Player]:
    if len(players) <= 1:
        return players
    kept = [player for player in players if predicate(player)]
    if not kept or len(kept) == len(players):
        stages.append(
            {
                "stage": stage,
                "before": len(players),
                "after": len(players),
                "mode": "NO_SEPARATION",
            }
        )
        return players
    stages.append(
        {
            "stage": stage,
            "before": len(players),
            "after": len(kept),
            "kept": [_name(player) for player in kept],
        }
    )
    return kept


def _dominates(left: Player, right: Player) -> bool:
    """Tolerance-aware, non-weighted last-man dominance test."""
    metrics = (
        ("hr_pa", 0.002),
        ("iso", 0.010),
        ("damage_score", 3.0),
        ("pitch_type_edge", 0.05),
        ("zone_edge", 0.05),
        ("mistake_edge", 0.05),
        ("pull", 3.0),
        ("hard_hit", 2.0),
    )
    no_worse = 0
    clearly_better = 0
    for field, tolerance in metrics:
        l_value = _metric(left, field)
        r_value = _metric(right, field)
        if l_value >= r_value - tolerance:
            no_worse += 1
        if l_value > r_value + tolerance:
            clearly_better += 1
    return no_worse == len(metrics) and clearly_better >= 3


def _unique_dominant(players: list[Player]) -> Player | None:
    dominant = [
        candidate
        for candidate in players
        if all(candidate is other or _dominates(candidate, other) for other in players)
    ]
    return dominant[0] if len(dominant) == 1 else None


def run_all_gates(hitters: list[dict], game: dict, target: dict):
    logs: list[dict] = []

    # Gate 0 — hydrated game pool. No side is selected here.
    current = list(hitters)
    logs.append(
        gate_log(
            0,
            "Hydrated Game Pool",
            len(hitters),
            len(current),
            note={
                "data_status": "ACTIVE" if current else "UNAVAILABLE",
                "away_count": sum(1 for player in current if player.get("side") == "away"),
                "home_count": sum(1 for player in current if player.get("side") == "home"),
            },
        )
    )

    # Gate 1 — opposing pitcher vulnerability must be hydrated.
    pitcher = target.get("pitcher") or {}
    pitcher_missing = [
        field
        for field, value in (
            ("pitcher_id", pitcher.get("id")),
            ("throws", pitcher.get("throws")),
            ("hr9", pitcher.get("hr9")),
            ("leak_score", target.get("leak_score")),
        )
        if value is None
    ]
    pitcher_ready = not pitcher_missing
    current = _apply(
        current,
        1,
        "Pitcher Vulnerability",
        lambda _player: (
            pitcher_ready,
            f"pitcher vulnerability data missing: {', '.join(pitcher_missing)}",
        ),
        logs,
        note={
            "data_status": "ACTIVE" if pitcher_ready else "UNAVAILABLE",
            "pitcher": pitcher.get("name"),
            "pitcher_id": pitcher.get("id"),
            "throws": pitcher.get("throws"),
            "hr9": pitcher.get("hr9"),
            "k_rate": pitcher.get("k_rate"),
            "leak_score": target.get("leak_score"),
            "missing": pitcher_missing,
        },
    )

    # Gate 2 — game environment must exist, but is common to every hitter.
    environment = game.get("environment") or {}
    environment_missing = [
        field
        for field in ("venue", "park_factor", "environment_score")
        if environment.get(field) is None
    ]
    environment_ready = not environment_missing
    current = _apply(
        current,
        2,
        "Game Environment",
        lambda _player: (
            environment_ready,
            f"environment data missing: {', '.join(environment_missing)}",
        ),
        logs,
        note={
            **environment,
            "data_status": "ACTIVE" if environment_ready else "UNAVAILABLE",
            "missing": environment_missing,
        },
    )

    # Gate 3 — one pitcher-side only; no cross contamination.
    side_before = len(current)
    target_side = target.get("side")
    side_kept = [player for player in current if player.get("side") == target_side]
    side_removed = [
        {"player": _name(player), "reason": "opposite offense side eliminated"}
        for player in current
        if player.get("side") != target_side
    ]
    current = side_kept
    logs.append(
        gate_log(
            3,
            "Side Lock",
            side_before,
            len(current),
            side_removed,
            note={
                "target_team": target.get("team"),
                "target_side": target_side,
                "opposing_pitcher": pitcher.get("name"),
            },
        )
    )

    # Gate 4 — valid starting hitter pool.
    def valid_hitter(player: Player) -> tuple[bool, str]:
        if player.get("id") is None or not _name(player) or _name(player) == "UNKNOWN":
            return False, "missing player identity"
        if player.get("lineup_status") not in {"OFFICIAL", "CONFIRMED", "PROJECTED"}:
            return False, "not a valid starting lineup status"
        if not 1 <= int(player.get("slot") or 99) <= 9:
            return False, "invalid lineup slot"
        if str(player.get("position") or "").upper() in {"P", "SP", "RP"}:
            return False, "pitcher excluded from hitter pool"
        return True, "valid hitter"

    current = _apply(current, 4, "Valid Hitter Pool", valid_hitter, logs)

    # Gate 5 — direct Savant Pull AIR percentile identity.
    pull_complete = sum(
        1
        for player in current
        if player.get("pull") is not None
        and player.get("pua") is not None
        and player.get("hard_hit") is not None
        and player.get("pull_identity_source") == "SAVANT_PULL_AIR_PERCENTILE"
    )

    def pull_air_gate(player: Player) -> tuple[bool, str]:
        missing = _missing(player, "pull", "pua", "hard_hit")
        if missing:
            return False, f"missing direct Pull-Air data: {', '.join(missing)}"
        if player.get("pull_identity_source") != "SAVANT_PULL_AIR_PERCENTILE":
            return False, f"invalid Pull-Air identity source: {player.get('pull_identity_source')}"
        if "DIRECT_PULL_AIR" not in str(player.get("pull_air_source") or ""):
            return False, f"invalid Pull AIR source: {player.get('pull_air_source')}"

        pull = float(player["pull"])
        hard_hit = float(player["hard_hit"])
        pitch_edge = _number(player.get("pitch_edge"))

        if pull < 50.0:
            if pull >= 45.0 and _prequalifies_who(player, game):
                player["who_prequalified"] = True
                return True, "WHO exception: direct Pull AIR 45-49 with full chaos/matchup lane"
            return False, "Pull AIR percentile < 50 auto-kill"
        if pull >= 70.0:
            return True, "elite direct Pull AIR lane"
        if pull >= 65.0:
            return True, "direct Pull AIR pass lane"
        if 55.0 <= pull < 65.0:
            passed = hard_hit >= 45.0 and pitch_edge is not None and pitch_edge >= 0.0
            return passed, "borderline Pull AIR requires HH >= 45 and positive pitch edge"

        raw_pull = _number(player.get("pull_percent"))
        air = _number(player.get("fb"))
        pua = _number(player.get("pua"))
        support_missing = [
            name
            for name, value in (("raw_pull", raw_pull), ("air", air), ("pull_air", pua))
            if value is None
        ]
        if support_missing:
            return False, f"50-54 Pull AIR support missing: {', '.join(support_missing)}"
        passed = (
            hard_hit >= 50.0
            and raw_pull >= 45.0
            and air >= 40.0
            and pua >= 28.0
            and pitch_edge is not None
            and pitch_edge >= 0.0
        )
        return passed, "50-54 Pull AIR lane lacks full support"

    current = _apply(
        current,
        5,
        "Pull-Air Profile",
        pull_air_gate,
        logs,
        note={
            "data_status": "ACTIVE" if pull_complete else "UNAVAILABLE",
            "complete_profiles": pull_complete,
            "required_source": "SAVANT_PULL_AIR_PERCENTILE",
            "raw_source": "SAVANT_BATTED_BALL_DIRECT_PULL_AIR",
            "thresholds": {
                "elite": ">=70",
                "pass": "65-69",
                "borderline": "55-64 plus HH and pitch edge",
                "auto_kill": "<50 unless full WHO prequalification",
            },
        },
    )

    # Gate 6 — damage quality.
    damage_complete = sum(
        1 for player in current if player.get("hard_hit") is not None and player.get("damage_score") is not None
    )

    def damage_gate(player: Player) -> tuple[bool, str]:
        missing = _missing(player, "hard_hit", "damage_score")
        if missing:
            return False, f"missing damage data: {', '.join(missing)}"
        hard_hit = float(player["hard_hit"])
        damage = float(player["damage_score"])
        barrel = _number(player.get("barrel"))
        pull = _metric(player, "pull", 0.0)

        if hard_hit < 40.0:
            return False, "Hard Hit < 40 auto-kill"
        if pull >= 70.0 and hard_hit >= 45.0:
            return True, "Pull >=70 / HH >=45 combo pass"
        if pull >= 65.0 and hard_hit >= 50.0:
            return True, "Pull >=65 / HH >=50 combo pass"
        if hard_hit >= 45.0 and damage >= 45.0:
            return True, "strong damage lane"
        if 40.0 <= hard_hit < 45.0:
            passed = barrel is not None and barrel >= 10.0 and damage >= 55.0
            return passed, "borderline HH requires Barrel >=10 and damage >=55"
        return False, "damage quality below floor"

    current = _apply(
        current,
        6,
        "Damage Quality",
        damage_gate,
        logs,
        note={
            "data_status": "ACTIVE" if damage_complete else "UNAVAILABLE",
            "complete_profiles": damage_complete,
        },
    )

    # Gate 7 — pitch-type matchup is separate from zone.
    pitch_complete = sum(
        1
        for player in current
        if player.get("pitch_type_edge") is not None
        and player.get("pitch_edge_source") == "STATCAST_DETAIL_PITCH_ZONE"
    )

    def pitch_type_gate(player: Player) -> tuple[bool, str]:
        if player.get("pitch_type_edge") is None:
            return False, "pitch-type matchup data missing"
        if player.get("pitch_edge_source") != "STATCAST_DETAIL_PITCH_ZONE":
            return False, f"invalid pitch-type source: {player.get('pitch_edge_source')}"
        return float(player["pitch_type_edge"]) >= 0.0, "negative pitch-type matchup"

    current = _apply(
        current,
        7,
        "Pitch-Type Matchup",
        pitch_type_gate,
        logs,
        note={
            "data_status": "ACTIVE" if pitch_complete else "UNAVAILABLE",
            "complete_profiles": pitch_complete,
            "required_source": "STATCAST_DETAIL_PITCH_ZONE",
            "pitcher": pitcher.get("name"),
        },
    )

    # Gate 8 — zone match remains its own gate.
    zone_complete = sum(
        1
        for player in current
        if player.get("zone_edge") is not None
        and player.get("pitch_edge_source") == "STATCAST_DETAIL_PITCH_ZONE"
    )

    def zone_gate(player: Player) -> tuple[bool, str]:
        if player.get("zone_edge") is None:
            return False, "zone matchup data missing"
        if player.get("pitch_edge_source") != "STATCAST_DETAIL_PITCH_ZONE":
            return False, f"invalid zone source: {player.get('pitch_edge_source')}"
        return float(player["zone_edge"]) >= 0.0, "negative zone matchup"

    current = _apply(
        current,
        8,
        "Zone Match",
        zone_gate,
        logs,
        note={
            "data_status": "ACTIVE" if zone_complete else "UNAVAILABLE",
            "complete_profiles": zone_complete,
            "required_source": "STATCAST_DETAIL_PITCH_ZONE",
        },
    )

    # Gate 9 — count/mistake conversion access.
    mistake_complete = sum(1 for player in current if player.get("mistake_edge") is not None)
    current = _apply(
        current,
        9,
        "Count / Mistake Conversion",
        lambda player: (
            player.get("mistake_edge") is not None and float(player["mistake_edge"]) >= 0.0,
            "mistake-location data missing"
            if player.get("mistake_edge") is None
            else "negative mistake-location conversion",
        ),
        logs,
        note={
            "data_status": "ACTIVE" if mistake_complete else "UNAVAILABLE",
            "complete_profiles": mistake_complete,
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

    # Gate 10 — categorical HR finisher identity / conversion floor.
    finisher_profiles: list[dict] = []
    finisher_before = len(current)
    finisher_kept: list[Player] = []
    finisher_removed: list[dict] = []
    for player in current:
        tier, label, reason = _finisher_lane(player)
        player["finisher_tier"] = tier
        player["finisher_label"] = label
        finisher_profiles.append(
            {
                "player": _name(player),
                "tier": tier,
                "label": label,
                "hr_pa": player.get("hr_pa"),
                "iso": player.get("iso"),
                "damage": player.get("damage_score"),
                "air": player.get("fb"),
            }
        )
        if tier > 0:
            finisher_kept.append(player)
        else:
            finisher_removed.append({"player": _name(player), "reason": reason})
    current = finisher_kept
    logs.append(
        gate_log(
            10,
            "HR Finisher Identity",
            finisher_before,
            len(current),
            finisher_removed,
            note={
                "profiles": finisher_profiles,
                "rule": "categorical Core / Primary / WHO lanes; no blended score",
            },
        )
    )

    # Gate 10.5 — mandatory dynamic adjacent/decoy transfer.
    transfer_before = len(current)
    current, transfer_note = _adjacent_transfer(current)
    transfer_removed = []
    if transfer_note.get("executed"):
        transfer_removed = [
            {
                "player": transfer_note.get("primary"),
                "reason": f"event transferred to adjacent {transfer_note.get('adjacent')}",
            }
        ]
    logs.append(
        gate_log(
            10.5,
            "Adjacent / Decoy Transfer",
            transfer_before,
            len(current),
            transfer_removed,
            note=transfer_note,
        )
    )

    # Gate 11 — recent HR signal. Missing feed is not silently ignored.
    recent_loaded = sum(
        1
        for player in current
        if player.get("recent_pa") is not None and player.get("recent_hr") is not None
    )
    current = _separator(
        current,
        11,
        "Recent HR Signal",
        lambda player: (
            player.get("recent_pa") is not None
            and player.get("recent_hr") is not None
            and float(player["recent_pa"]) >= 8.0
            and (float(player["recent_hr"]) >= 1.0 or player.get("hr_heat") is True),
            "recent feed unavailable"
            if player.get("recent_pa") is None or player.get("recent_hr") is None
            else "no live 14-day HR signal",
        ),
        logs,
        note={
            "data_status": "ACTIVE" if recent_loaded else "UNAVAILABLE",
            "loaded_profiles": recent_loaded,
            "window": "14 days",
            "minimum_pa": 8,
        },
    )

    # Gate 12 — lineup protection. It separates only when support exists.
    protection_loaded = sum(1 for player in current if player.get("protection") is not None)
    current = _separator(
        current,
        12,
        "Lineup Protection",
        lambda player: (
            player.get("protection") is not None and float(player["protection"]) >= 0.0,
            "protection data unavailable"
            if player.get("protection") is None
            else "negative lineup protection",
        ),
        logs,
        note={
            "data_status": "ACTIVE" if protection_loaded else "UNAVAILABLE",
            "loaded_profiles": protection_loaded,
            "profiles": [
                {
                    "player": _name(player),
                    "protection": player.get("protection"),
                    "protection_score": player.get("protection_score"),
                }
                for player in current
            ],
        },
    )

    # Gate 13 — Universe is a completely separate explicit signal layer.
    logs.append(
        gate_log(
            13,
            "Universe",
            len(current),
            len(current),
            note={
                "mode": "TIE_BREAK_ONLY",
                "signals": [
                    {"player": _name(player), "signal": player.get("universe_signal")}
                    for player in current
                ],
                "rule": "no hash, numerology, hidden score, or automatic elimination",
            },
        )
    )

    # Gate 14 — explicit WHO/chaos engine. It cannot beat a higher finisher tier.
    chaos_before = len(current)
    chaos_pool = list(current)
    chaos_candidates: list[Player] = []
    max_tier = max((int(player.get("finisher_tier") or 0) for player in current), default=0)
    chaos_profiles: list[dict] = []
    for player in current:
        signals = _chaos_signals(player, game)
        player["chaos_signals"] = signals
        qualifies = (
            int(player.get("finisher_tier") or 0) == max_tier == 1
            and bool(player.get("who_prequalified") or signals["weak_slot"])
            and signals["positive_pitch_type"]
            and signals["positive_zone"]
            and signals["mistake_leak"]
            and (signals["bullpen_chaos"] or signals["unstable_environment"])
        )
        chaos_profiles.append(
            {"player": _name(player), "qualifies": qualifies, "signals": signals}
        )
        if qualifies:
            chaos_candidates.append(player)

    chaos_note: dict = {
        "profiles": chaos_profiles,
        "rule": "WHO never overrides validation, matchup, conversion, or a stronger finisher tier",
    }
    if len(chaos_candidates) == 1:
        current = [chaos_candidates[0]]
        current[0]["chaos_flag"] = True
        chaos_note.update({"trigger": "UNIQUE_WHO_CHAOS", "winner": _name(current[0])})
    else:
        chaos_note.update(
            {
                "trigger": "NO_SEPARATION",
                "candidates": [_name(player) for player in chaos_candidates],
            }
        )
    logs.append(
        gate_log(
            14,
            "Chaos / WHO Engine",
            chaos_before,
            len(current),
            [
                {"player": _name(player), "reason": "lost unique WHO/chaos lane"}
                for player in chaos_pool
                if player not in current
            ],
            note=chaos_note,
        )
    )

    # Gate 15 — finisher gate: the strongest categorical lane survives.
    finisher_gate_before = len(current)
    finisher_gate_pool = list(current)
    if current:
        max_tier = max(int(player.get("finisher_tier") or 0) for player in current)
        current = [
            player for player in current if int(player.get("finisher_tier") or 0) == max_tier
        ]
    logs.append(
        gate_log(
            15,
            "Finisher Gate",
            finisher_gate_before,
            len(current),
            [
                {
                    "player": _name(player),
                    "reason": f"lower finisher tier {player.get('finisher_tier')}",
                }
                for player in finisher_gate_pool
                if player not in current
            ],
            note={
                "live_tier": int(current[0].get("finisher_tier") or 0) if current else None,
                "rule": "pressure can never outweigh finisher identity",
            },
        )
    )

    # Gate 16 — last-man elimination without a global ranking or fake tie-break.
    last_before = len(current)
    if not current:
        logs.append(
            gate_log(
                16,
                "Last-Man Elimination",
                0,
                0,
                note={"decision": "NO_LIVE_HITTER"},
            )
        )
        return [], logs

    candidates = list(current)
    stages: list[dict] = []

    # Valid transfer/chaos lanes are explicit outcomes, not score bonuses.
    candidates = _categorical_separate(
        candidates,
        lambda player: player.get("transfer_flag") is True,
        "UNIQUE_TRANSFER_LANE",
        stages,
    )
    candidates = _categorical_separate(
        candidates,
        lambda player: player.get("chaos_flag") is True,
        "UNIQUE_CHAOS_LANE",
        stages,
    )
    candidates = _categorical_separate(
        candidates,
        lambda player: (
            _metric(player, "pitch_type_edge") > 0.0
            and _metric(player, "zone_edge") > 0.0
            and _metric(player, "mistake_edge") > 0.0
        ),
        "MATCHUP_TRIFECTA",
        stages,
    )
    candidates = _categorical_separate(
        candidates,
        lambda player: player.get("hr_heat") is True and _metric(player, "protection", -1.0) >= 0.0,
        "RECENT_PLUS_PROTECTION",
        stages,
    )
    candidates = _categorical_separate(
        candidates,
        lambda player: int(player.get("slot") or 99) <= 4,
        "TOP_FOUR_ACCESS",
        stages,
    )
    candidates = _categorical_separate(
        candidates,
        lambda player: _metric(player, "hr_pa", 0.0) >= 0.040 and _metric(player, "iso", 0.0) >= 0.200,
        "CONVERSION_PLUS",
        stages,
    )
    candidates = _categorical_separate(
        candidates,
        lambda player: _metric(player, "damage_score", 0.0) >= 65.0,
        "ELITE_DAMAGE",
        stages,
    )

    decision: dict
    winner: Player | None = candidates[0] if len(candidates) == 1 else None

    if winner is None and len(candidates) > 1:
        dominant = _unique_dominant(candidates)
        if dominant is not None:
            winner = dominant
            stages.append(
                {
                    "stage": "PARETO_LAST_MAN",
                    "before": len(candidates),
                    "after": 1,
                    "winner": _name(winner),
                    "rule": "no weighted score; one hitter is not worse across every core lane and clearly better in at least three",
                }
            )
            candidates = [winner]

    if winner is None and len(candidates) > 1:
        universe_live = [player for player in candidates if player.get("universe_signal") is True]
        if len(universe_live) == 1:
            winner = universe_live[0]
            candidates = [winner]
            stages.append(
                {
                    "stage": "EXPLICIT_UNIVERSE_TIE_BREAK",
                    "before": len(current),
                    "after": 1,
                    "winner": _name(winner),
                }
            )

    if winner is None:
        logs.append(
            gate_log(
                16,
                "Last-Man Elimination",
                last_before,
                0,
                [
                    {"player": _name(player), "reason": "unresolved true tie; no arbitrary winner"}
                    for player in current
                ],
                note={
                    "decision": "WHO_UNRESOLVED_TRUE_TIE",
                    "live_hitters": [_name(player) for player in candidates],
                    "stages": stages,
                    "rule": "no score, hash, reputation, or name tie-break",
                },
            )
        )
        return [], logs

    winner["core_lane"] = (
        "TRANSFER"
        if winner.get("transfer_flag")
        else "CHAOS"
        if winner.get("chaos_flag") or winner.get("finisher_label") == "WHO_CHAOS_FINISHER"
        else "PRIMARY"
    )
    # Kept only for existing UI compatibility; it is categorical, not a ranking.
    winner["ownership_score"] = int(winner.get("finisher_tier") or 0)
    winner["event_reason"] = (
        f"True Blender last man: {winner.get('finisher_label')} / {winner.get('core_lane')}"
    )

    logs.append(
        gate_log(
            16,
            "Last-Man Elimination",
            last_before,
            1,
            [
                {"player": _name(player), "reason": "lost explicit last-man elimination"}
                for player in current
                if player is not winner
            ],
            note={
                "decision": "ONE_TRUE_OWNER",
                "winner": _name(winner),
                "finisher_label": winner.get("finisher_label"),
                "core_lane": winner.get("core_lane"),
                "stages": stages,
                "rule": "pure elimination; no blended ranking and no fabricated Universe score",
            },
        )
    )
    return [winner], logs
