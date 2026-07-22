from __future__ import annotations


REQUIRED_PRELOCK_GATES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10.5, 11, 12, 13, 14, 15, 16}
SCORING_ONLY_GATES = {1, 12, 13}


def _gate_map(logs: list[dict]) -> dict:
    return {item.get("gate"): item for item in logs}


def run_audit(survivors: list[dict], logs: list[dict]) -> dict:
    issues: list[dict] = []
    warnings: list[dict] = []
    gates = [item.get("gate") for item in logs]
    executed = set(gates)

    duplicates = sorted({gate for gate in gates if gates.count(gate) > 1}, key=float)
    if duplicates:
        issues.append({"code": "DUPLICATE_GATE_EXECUTION", "gates": duplicates})

    missing = sorted(REQUIRED_PRELOCK_GATES - executed, key=float)
    if missing:
        issues.append({"code": "MISSING_GATE_EXECUTION", "gates": missing})

    malformed = [
        item.get("gate")
        for item in logs
        if item.get("before") is None or item.get("after") is None or item.get("removed") is None
    ]
    if malformed:
        issues.append({"code": "MALFORMED_GATE_LOG", "gates": malformed})

    ordered = sorted(
        [item for item in logs if item.get("gate") in REQUIRED_PRELOCK_GATES],
        key=lambda item: float(item.get("gate")),
    )
    previous_after = None
    for item in ordered:
        gate = item.get("gate")
        before = item.get("before")
        after = item.get("after")
        removed = item.get("removed") or []
        note = item.get("note") or {}

        if after is not None and before is not None and after > before:
            issues.append({"code": "GATE_ADDED_PLAYERS", "gate": gate, "before": before, "after": after})

        if previous_after is not None and before != previous_after:
            issues.append(
                {
                    "code": "BROKEN_GATE_CONTINUITY",
                    "gate": gate,
                    "expected_before": previous_after,
                    "actual_before": before,
                }
            )

        if gate not in SCORING_ONLY_GATES and gate != 0 and before is not None and after is not None:
            expected_removed = before - after
            if len(removed) != expected_removed:
                issues.append(
                    {
                        "code": "REMOVAL_COUNT_MISMATCH",
                        "gate": gate,
                        "expected": expected_removed,
                        "logged": len(removed),
                    }
                )

        mode = note.get("mode") if isinstance(note, dict) else None
        if mode == "WHO_RESCUE":
            issues.append(
                {
                    "code": "PREMATURE_WHO_RESCUE",
                    "gate": gate,
                    "player": note.get("rescued"),
                    "failed_reason": note.get("failed_reason"),
                }
            )
        elif mode == "FINAL_WHO":
            warnings.append(
                {
                    "code": "FINAL_WHO_LANE",
                    "gate": gate,
                    "player": note.get("selected"),
                }
            )
        elif mode == "NO_SEPARATION":
            warnings.append(
                {
                    "code": "NON_DISCRIMINATING_GATE",
                    "gate": gate,
                    "reason": note.get("reason"),
                }
            )
        elif mode == "DATA_WARNING":
            warnings.append({"code": "GATE_DATA_WARNING", "gate": gate, "reason": note.get("reason")})

        previous_after = after

    by_gate = _gate_map(logs)
    universe = by_gate.get(13) or {}
    if universe and (
        universe.get("before") != universe.get("after") or bool(universe.get("removed"))
    ):
        issues.append({"code": "UNIVERSE_MUST_BE_TIE_BREAK_ONLY"})

    ownership = by_gate.get(12) or {}
    ownership_note = ownership.get("note") or {}
    if ownership.get("before", 0) > 0 and not ownership_note.get("ownership"):
        issues.append({"code": "OWNERSHIP_SCORES_NOT_AUDITED"})

    gate3 = by_gate.get(3) or {}
    if gate3.get("before", 0) >= 7 and gate3.get("after", 0) <= 1:
        warnings.append(
            {
                "code": "PREMATURE_POOL_COLLAPSE",
                "gate": 3,
                "before": gate3.get("before"),
                "after": gate3.get("after"),
            }
        )

    effective_gates = [
        item.get("gate")
        for item in ordered
        if item.get("before") != item.get("after")
    ]
    if len(effective_gates) < 4:
        warnings.append({"code": "TOO_FEW_EFFECTIVE_GATES", "effective_gates": effective_gates})

    pitch_note = (by_gate.get(5) or {}).get("note") or {}
    pitch_sources = pitch_note.get("sources") or []
    if any("PROXY" in str(source).upper() for source in pitch_sources):
        warnings.append({"code": "PITCH_MATCHUP_PROXY", "sources": pitch_sources})

    bullpen_note = (by_gate.get(11) or {}).get("note") or {}
    if "PROXY" in str(bullpen_note.get("source") or "").upper():
        warnings.append({"code": "BULLPEN_PROXY", "source": bullpen_note.get("source")})

    if len(survivors) == 0:
        issues.append({"code": "NO_SURVIVOR"})
    elif len(survivors) > 1:
        issues.append({"code": "MULTIPLE_SURVIVORS", "count": len(survivors)})

    return {
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "executed_gates": sorted(executed, key=float),
        "effective_gates": effective_gates,
        "survivor_count": len(survivors),
    }
