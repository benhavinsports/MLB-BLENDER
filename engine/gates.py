from __future__ import annotations


def _log(gate, name, before, after, removed=None, note=None):
    return {"gate": gate, "name": name, "before": before, "after": after, "removed": removed or [], "note": note}


def _apply(players, gate, name, predicate, logs):
    before = len(players)
    kept = []
    removed = []
    for player in players:
        passed, reason = predicate(player)
        if passed:
            kept.append(player)
        else:
            removed.append({"player": player.get("name"), "reason": reason})
    logs.append(_log(gate, name, before, len(kept), removed))
    return kept


def run_all_gates(hitters: list[dict], game: dict, target: dict):
    logs = []

    # Gate 0: target-side isolation.
    current = [p for p in hitters if p.get("side") == target.get("side")]
    logs.append(_log(0, "Target Side Isolation", len(hitters), len(current), note=target))

    # Gate 1: environment hard suppression only.
    env = game.get("environment") or {}
    suppressed = env.get("environment_score") is not None and env.get("environment_score") <= -3
    current = _apply(current, 1, "Environment", lambda p: (not suppressed, "heavy environment suppression"), logs)

    # Gate 2: confirmed starter pool is enforced upstream by lineups.py.
    current = _apply(
        current,
        2,
        "Confirmed Starter Pool",
        lambda p: (p.get("lineup_status") in {"OFFICIAL", "CONFIRMED", "PROJECTED"} and 1 <= (p.get("slot") or 99) <= 9, "not a valid starting hitter"),
        logs,
    )

    # Gate 3: pull path.
    current = _apply(current, 3, "Pull Angle", lambda p: (p.get("pull") is None or p.get("pull") >= 50, "Pull < 50"), logs)

    # Gate 4: damage support.
    current = _apply(current, 4, "Damage Support", lambda p: (p.get("hard_hit") is None or p.get("hard_hit") >= 40, "Hard Hit < 40"), logs)

    # Gate 5: hitter-specific opposing-pitcher matchup proxy wired in core.py.
    current = _apply(current, 5, "Pitch Matchup", lambda p: (p.get("pitch_edge") is None or p.get("pitch_edge") >= 0, "negative pitch edge"), logs)

    # Gate 6: lineup access.
    current = _apply(current, 6, "Slot Weakness", lambda p: ((p.get("slot") or 9) <= 6, "bottom-order protected slot"), logs)

    # Gate 7: actual 14-day rhythm feed; unknown data passes.
    current = _apply(current, 7, "Recent Rhythm", lambda p: (p.get("hr_heat") is None or bool(p.get("hr_heat")), "dead recent rhythm"), logs)

    # Gate 8: season HR conversion.
    current = _apply(current, 8, "Conversion", lambda p: (p.get("hr_pa") is None or p.get("hr_pa") >= .025, "HR/PA below WHO floor"), logs)

    # Gate 9: hitter/environment alignment. Environment is already a game-level
    # hard kill, so this gate records the surviving context rather than double-killing.
    logs.append(_log(9, "Hitter Environment Recheck", len(current), len(current), note=env))

    # Gate 10: projected plate-appearance access.
    current = _apply(current, 10, "Opportunity", lambda p: ((p.get("slot") or 9) <= 6, "insufficient projected PA"), logs)

    # Gate 10.5 executes after ownership in core.py.
    logs.append(_log(10.5, "Decoy Transfer", len(current), len(current), note="executed after ownership"))

    # Gate 11: continuation through the opposing relief corps. Unknown bullpen
    # data passes; a loaded low-risk card is recorded but does not override a finisher.
    bullpen = game.get("away_bullpen") if target.get("side") == "home" else game.get("home_bullpen")
    bullpen = bullpen or {}
    logs.append(_log(11, "Bullpen Continuation", len(current), len(current), note=bullpen))

    # Gate 12 executes in ownership.py after all eliminations.
    logs.append(_log(12, "Event Ownership", len(current), len(current), note="scored after gates"))

    # Gate 13 remains a tie-break layer by design.
    logs.append(_log(13, "Numerical Resonance", len(current), len(current), note="tie-break only"))

    # Gate 14: adjacent-lineup protection wired after all hitter profiles load.
    current = _apply(current, 14, "Lineup Protection", lambda p: (p.get("protection") is None or p.get("protection") >= 0, "isolated lineup cluster"), logs)

    # Gate 15: final production lane.
    def finisher(player):
        known = [player.get("hr_pa"), player.get("iso"), player.get("fb")]
        if all(value is None for value in known) and not player.get("damage_score"):
            return True, "data unavailable"
        passed = (
            (player.get("hr_pa") or 0) >= .025
            and (player.get("iso") or 0) >= .150
            and (player.get("damage_score") or 0) >= 35
        )
        return passed, "finisher floor failed"

    current = _apply(current, 15, "Finisher", finisher, logs)

    # Gate 16: last two event-capable survivors before ownership/transfer.
    before = len(current)
    current = sorted(
        current,
        key=lambda p: (
            p.get("hr_model_score", 0),
            p.get("damage_score", 0),
            p.get("pitch_edge", 0),
        ),
        reverse=True,
    )[:2]
    logs.append(_log(16, "Survivor Reduction", before, len(current)))

    # Gate 17 and 18 are completed by audit.py and final_lock.py in core.py.
    logs.append(_log(17, "Audit", len(current), len(current), note="completed in core"))
    logs.append(_log(18, "Final Lock", len(current), len(current), note="completed in core"))
    return current, logs
