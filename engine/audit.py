from __future__ import annotations

REQUIRED_SEQUENCE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10.5, 11, 12, 13, 14, 15, 16]


def _as_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def run_audit(survivors: list[dict], logs: list[dict]) -> dict:
    """Audit a True Blender run without forcing a fake survivor.

    A structurally valid run may finish with zero players when every hitter was
    legitimately eliminated or when Gate 16 has an unresolved true tie. That is
    a WHO outcome, not an audit failure. Data gaps, inactive required gates,
    broken continuity, fake Universe scoring, or more than one last man fail the
    audit and block Gate 18.
    """
    issues: list[dict] = []
    warnings: list[dict] = []

    gates = [item.get("gate") for item in logs]
    if gates != REQUIRED_SEQUENCE:
        issues.append(
            {
                "code": "GATE_SEQUENCE_INVALID",
                "expected": REQUIRED_SEQUENCE,
                "actual": gates,
            }
        )

    by_gate = {item.get("gate"): item for item in logs}
    previous_after = None
    first_empty_gate = None
    effective_gates: list[float] = []

    for index, item in enumerate(logs):
        gate = item.get("gate")
        before = _as_int(item.get("before"))
        after = _as_int(item.get("after"))
        removed = item.get("removed") or []
        note = _dict(item.get("note"))

        if before < 0 or after < 0 or after > before:
            issues.append(
                {"code": "INVALID_GATE_COUNTS", "gate": gate, "before": before, "after": after}
            )

        if index > 0 and previous_after is not None and before != previous_after:
            issues.append(
                {
                    "code": "GATE_CONTINUITY_BROKEN",
                    "gate": gate,
                    "expected_before": previous_after,
                    "actual_before": before,
                }
            )

        if before - after != len(removed):
            issues.append(
                {
                    "code": "REMOVAL_COUNT_MISMATCH",
                    "gate": gate,
                    "before": before,
                    "after": after,
                    "removed_count": len(removed),
                }
            )

        if before != after:
            effective_gates.append(gate)
        if before > 0 and after == 0 and first_empty_gate is None:
            first_empty_gate = gate

        for removal in removed:
            reason = str(removal.get("reason") or "").lower()
            if any(token in reason for token in ("missing", "unavailable", "invalid source")):
                warnings.append(
                    {
                        "code": "CANDIDATE_DATA_MISSING",
                        "gate": gate,
                        "player": removal.get("player"),
                        "reason": removal.get("reason"),
                    }
                )

        previous_after = after

    # Required shared context cannot silently pass without data.
    for gate in (0, 1, 2):
        item = by_gate.get(gate) or {}
        note = _dict(item.get("note"))
        if item.get("before", 0) > 0 and note.get("data_status") != "ACTIVE":
            issues.append(
                {
                    "code": "REQUIRED_CONTEXT_UNAVAILABLE",
                    "gate": gate,
                    "name": item.get("name"),
                }
            )

    # Gate 3 must be the one-side lock.
    side_lock = by_gate.get(3) or {}
    if side_lock.get("name") != "Side Lock":
        issues.append({"code": "SIDE_LOCK_GATE_INVALID", "gate": 3})

    # Pull AIR must be direct Savant evidence, not a synthetic weighted index.
    pull_gate = by_gate.get(5) or {}
    pull_note = _dict(pull_gate.get("note"))
    if pull_gate.get("name") != "Pull-Air Profile":
        issues.append({"code": "PULL_AIR_GATE_INVALID", "gate": 5})
    if pull_gate.get("before", 0) > 0:
        if pull_note.get("required_source") != "SAVANT_PULL_AIR_PERCENTILE":
            issues.append({"code": "PULL_AIR_SOURCE_INVALID", "gate": 5})
        if "DIRECT_PULL_AIR" not in str(pull_note.get("raw_source") or ""):
            issues.append({"code": "PULL_AIR_RAW_SOURCE_INVALID", "gate": 5})
        if _as_int(pull_note.get("complete_profiles")) == 0:
            issues.append({"code": "PULL_AIR_DATA_UNAVAILABLE", "gate": 5})

    # Every data-backed gate must disclose whether usable profiles existed.
    for gate in (6, 7, 8, 9):
        item = by_gate.get(gate) or {}
        note = _dict(item.get("note"))
        if item.get("before", 0) > 0 and note.get("data_status") != "ACTIVE":
            issues.append(
                {
                    "code": "GATE_DATA_UNAVAILABLE",
                    "gate": gate,
                    "name": item.get("name"),
                }
            )

    # Pitch type and zone are separate gates with the real detail source.
    pitch_gate = by_gate.get(7) or {}
    zone_gate = by_gate.get(8) or {}
    if pitch_gate.get("name") != "Pitch-Type Matchup":
        issues.append({"code": "PITCH_TYPE_GATE_INVALID", "gate": 7})
    if zone_gate.get("name") != "Zone Match":
        issues.append({"code": "ZONE_GATE_INVALID", "gate": 8})
    for gate in (7, 8):
        note = _dict((by_gate.get(gate) or {}).get("note"))
        if note.get("required_source") != "STATCAST_DETAIL_PITCH_ZONE":
            issues.append({"code": "MATCHUP_SOURCE_INVALID", "gate": gate})

    # Gate 10 must expose categorical lanes and no blended score.
    finisher_identity = by_gate.get(10) or {}
    finisher_note = _dict(finisher_identity.get("note"))
    if finisher_identity.get("before", 0) > 0 and not finisher_note.get("profiles"):
        issues.append({"code": "FINISHER_IDENTITY_NOT_AUDITED", "gate": 10})
    if any(key in finisher_note for key in ("score", "scores", "ranking")):
        issues.append({"code": "BLENDED_FINISHER_SCORE_PRESENT", "gate": 10})

    # Gate 10.5 must make and expose the actual transfer decision while the pool is live.
    transfer = by_gate.get(10.5) or {}
    transfer_note = _dict(transfer.get("note"))
    if "executed" not in transfer_note:
        issues.append({"code": "TRANSFER_DECISION_NOT_AUDITED", "gate": 10.5})
    if transfer_note.get("executed") and transfer.get("before", 0) < 2:
        issues.append({"code": "TRANSFER_EXECUTED_WITHOUT_LIVE_POOL", "gate": 10.5})

    # Recent and protection signals must be loaded; NO_SEPARATION is allowed only
    # when the feed loaded but no hitter owned the signal.
    for gate in (11, 12):
        item = by_gate.get(gate) or {}
        note = _dict(item.get("note"))
        if item.get("before", 0) > 0 and note.get("data_status") != "ACTIVE":
            issues.append(
                {
                    "code": "GATE_DATA_UNAVAILABLE",
                    "gate": gate,
                    "name": item.get("name"),
                }
            )

    # Universe is isolated: no elimination, hash, score, rank, or numerology.
    universe = by_gate.get(13) or {}
    universe_note = _dict(universe.get("note"))
    if universe.get("before") != universe.get("after") or universe.get("removed"):
        issues.append({"code": "UNIVERSE_MUST_BE_TIE_BREAK_ONLY", "gate": 13})
    if universe_note.get("mode") != "TIE_BREAK_ONLY":
        issues.append({"code": "UNIVERSE_MODE_INVALID", "gate": 13})
    serialized_universe = str(universe_note).lower()
    if any(token in serialized_universe for token in ("hash", "numerology", "universe_score", "ranking")):
        # The rule text may say "no hash"; only actual score/hash data is invalid.
        if universe_note.get("scores") or universe_note.get("hash") or universe_note.get("ranking"):
            issues.append({"code": "FABRICATED_UNIVERSE_SCORE", "gate": 13})

    # Chaos cannot promote a lower finisher tier over a stronger live tier.
    chaos = by_gate.get(14) or {}
    chaos_note = _dict(chaos.get("note"))
    if chaos_note.get("trigger") == "UNIQUE_WHO_CHAOS":
        profiles = chaos_note.get("profiles") or []
        qualifying = [profile for profile in profiles if profile.get("qualifies")]
        if len(qualifying) != 1:
            issues.append({"code": "CHAOS_TRIGGER_NOT_UNIQUE", "gate": 14})

    # Gate 15 is categorical and Gate 16 may finish with one owner or zero WHO.
    last_man = by_gate.get(16) or {}
    if last_man.get("after") not in (0, 1):
        issues.append({"code": "GATE16_CARDINALITY_INVALID", "after": last_man.get("after")})
    if len(survivors) not in (0, 1):
        issues.append({"code": "SURVIVOR_COUNT_INVALID", "count": len(survivors)})
    if len(survivors) != _as_int(last_man.get("after")):
        issues.append(
            {
                "code": "SURVIVOR_LOG_MISMATCH",
                "survivors": len(survivors),
                "gate16_after": last_man.get("after"),
            }
        )

    gate16_note = _dict(last_man.get("note"))
    if any(key in gate16_note for key in ("score", "scores", "ranking", "universe_score")):
        issues.append({"code": "GATE16_RANKING_PRESENT", "gate": 16})

    # A sharp Gate-5 collapse is not automatically wrong, but must be surfaced.
    if pull_gate.get("before", 0) >= 7 and pull_gate.get("after", 0) <= 1:
        warnings.append(
            {
                "code": "PULL_AIR_POOL_COLLAPSE",
                "gate": 5,
                "before": pull_gate.get("before"),
                "after": pull_gate.get("after"),
            }
        )

    outcome = "LOCKED" if len(survivors) == 1 else "WHO"
    return {
        "passed": not issues,
        "lockable": not issues and len(survivors) == 1,
        "outcome": outcome,
        "issues": issues,
        "warnings": warnings,
        "executed_gates": gates,
        "effective_gates": effective_gates,
        "first_empty_gate": first_empty_gate,
        "survivor_count": len(survivors),
    }
