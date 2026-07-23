from __future__ import annotations

REQUIRED_SEQUENCE = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10.5, 11, 12, 13, 14, 15, 16]


def _as_int(value, default=0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def run_audit(survivors: list[dict], logs: list[dict]) -> dict:
    """Verify execution, continuity, source integrity and final cardinality."""
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

        # Gate 0 isolates one side and intentionally does not list the opposite
        # side as failed hitters. Every other elimination must reconcile.
        if gate != 0 and before - after != len(removed):
            note = item.get("note") or {}
            no_separation = isinstance(note, dict) and note.get("mode") == "NO_SEPARATION"
            if not no_separation:
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
        previous_after = after

    universe = by_gate.get(13) or {}
    if universe.get("before") != universe.get("after") or universe.get("removed"):
        issues.append({"code": "UNIVERSE_MUST_BE_TIE_BREAK_ONLY", "gate": 13})

    matchup = by_gate.get(5) or {}
    matchup_note = matchup.get("note") or {}
    sources = matchup_note.get("sources") or []
    if matchup.get("before", 0) > 0:
        if not sources:
            issues.append({"code": "MATCHUP_SOURCE_NOT_AUDITED", "gate": 5})
        invalid_sources = [source for source in sources if source != "STATCAST_DETAIL_PITCH_ZONE"]
        if invalid_sources:
            issues.append(
                {"code": "MATCHUP_DATA_NOT_REAL_PITCH_ZONE", "gate": 5, "sources": invalid_sources}
            )

    for gate in (2, 7, 9, 11, 14):
        item = by_gate.get(gate) or {}
        note = item.get("note") or {}
        if item.get("before", 0) > 0 and isinstance(note, dict) and note.get("data_status") == "UNAVAILABLE":
            issues.append({"code": "GATE_DATA_UNAVAILABLE", "gate": gate, "name": item.get("name")})

    bullpen = by_gate.get(11) or {}
    bullpen_note = bullpen.get("note") or {}
    source = str(bullpen_note.get("source") or "")
    if "PROXY" in source.upper():
        warnings.append({"code": "BULLPEN_FALLBACK_PROXY", "gate": 11, "source": source})

    pressure = by_gate.get(12) or {}
    pressure_note = pressure.get("note") or {}
    if pressure.get("before", 0) > 0 and not pressure_note.get("scores"):
        issues.append({"code": "PRESSURE_SCORES_NOT_AUDITED", "gate": 12})

    finisher = by_gate.get(15) or {}
    finisher_note = finisher.get("note") or {}
    if finisher.get("after", 0) > 0 and not finisher_note.get("scores"):
        issues.append({"code": "FINISHER_SCORES_NOT_AUDITED", "gate": 15})

    last_man = by_gate.get(16) or {}
    if len(survivors) != 1:
        issues.append({"code": "SURVIVOR_COUNT_INVALID", "count": len(survivors)})
    if len(survivors) == 1 and last_man.get("after") != 1:
        issues.append({"code": "GATE16_NOT_ONE_SURVIVOR", "after": last_man.get("after")})

    if first_empty_gate is not None:
        issues.append({"code": "POOL_EMPTIED", "gate": first_empty_gate})

    gate3 = by_gate.get(3) or {}
    if gate3.get("before", 0) >= 7 and gate3.get("after", 0) <= 1:
        warnings.append(
            {
                "code": "PULL_AIR_POOL_COLLAPSE",
                "gate": 4,
                "before": gate3.get("before"),
                "after": gate3.get("after"),
            }
        )

    return {
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "executed_gates": gates,
        "effective_gates": effective_gates,
        "first_empty_gate": first_empty_gate,
        "survivor_count": len(survivors),
    }
