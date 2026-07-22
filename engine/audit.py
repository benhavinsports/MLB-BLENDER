REQUIRED_GATES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10.5, 11, 12, 13, 14, 15, 16, 17, 18}


def run_audit(survivors: list[dict], logs: list[dict]) -> dict:
    executed = {item.get("gate") for item in logs}
    issues = []

    missing_gates = sorted(REQUIRED_GATES - executed, key=float)
    if missing_gates:
        issues.append({"code": "MISSING_GATE_EXECUTION", "gates": missing_gates})

    malformed = [
        item.get("gate")
        for item in logs
        if item.get("before") is None or item.get("after") is None or item.get("removed") is None
    ]
    if malformed:
        issues.append({"code": "MALFORMED_GATE_LOG", "gates": malformed})

    if len(survivors) == 0:
        issues.append({"code": "NO_SURVIVOR"})
    elif len(survivors) > 1:
        issues.append({"code": "MULTIPLE_SURVIVORS", "count": len(survivors)})

    return {
        "passed": not issues,
        "issues": issues,
        "executed_gates": sorted(executed, key=float),
        "survivor_count": len(survivors),
    }
