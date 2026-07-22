from __future__ import annotations

import hashlib


def _log(gate, name, before, after, removed=None, note=None):
    return {
        "gate": gate,
        "name": name,
        "before": before,
        "after": after,
        "removed": removed or [],
        "note": note,
    }


def _apply(players, gate, name, predicate, logs, note=None):
    before = len(players)
    kept = []
    removed = []
    for player in players:
        passed, reason = predicate(player)
        if passed:
            kept.append(player)
        else:
            removed.append({"player": player.get("name"), "reason": reason})
    logs.append(_log(gate, name, before, len(kept), removed, note=note))
    return kept


def _missing(player: dict, *fields: str) -> list[str]:
    return [field for field in fields if player.get(field) is None]


def _universe_score(player: dict, game: dict) -> int:
    """Stable, isolated Gate 13 value; never blended into baseball metrics."""
    seed = "|".join(
        [
            str(game.get("date") or ""),
            str(game.get("game_id") or game.get("gamePk") or ""),
            str(player.get("id") or ""),
            str(player.get("name") or ""),
            str(player.get("slot") or ""),
        ]
    )
    return int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16) % 1000


def run_all_gates(hitters: list[dict], game: dict, target: dict):
    logs = []

    # Gate 0: one pitcher-side only.
    current = [p for p in hitters if p.get("side") == target.get("side")]
    logs.append(_log(0, "Target Side Isolation", len(hitters), len(current), note=target))

    # Gate 1: environment can kill the entire game, but missing environment is a data failure.
    env = game.get("environment") or {}
    env_score = env.get("environment_score")
    current = _apply(
        current,
        1,
        "Environment",
        lambda p: (
            env_score is not None and float(env_score) > -3,
            "environment data missing" if env_score is None else "heavy environment suppression",
        ),
        logs,
        note=env,
    )

    # Gate 2: valid starting hitter only.
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
    )

    # Gate 3: locked pull-air lanes. No unknown-data pass.
    def pull_gate(player):
        missing = _missing(player, "pull", "hard_hit")
        if missing:
            return False, f"missing pull data: {', '.join(missing)}"
        pull = float(player["pull"])
        hard_hit = float(player["hard_hit"])
        if pull < 50:
            return False, "Pull < 50 auto-kill"
        if pull >= 70 and hard_hit >= 45:
            return True, "elite pull combo"
        if pull >= 65 and hard_hit >= 50:
            return True, "strong pull combo"
        if 55 <= pull < 65:
            pitch_edge = player.get("pitch_edge")
            if hard_hit >= 45 and pitch_edge is not None and float(pitch_edge) >= 0:
                return True, "borderline pull supported by damage and pitch edge"
            return False, "borderline pull lacks damage/pitch support"
        return hard_hit >= 40, "pull lane lacks hard-hit support"

    current = _apply(current, 3, "Pull-Air Identity", pull_gate, logs)

    # Gate 4: damage quality.
    def damage_gate(player):
        missing = _missing(player, "hard_hit", "damage_score")
        if missing:
            return False, f"missing damage data: {', '.join(missing)}"
        hard_hit = float(player["hard_hit"])
        if hard_hit < 40:
            return False, "Hard Hit < 40 auto-kill"
        if float(player["damage_score"]) < 35:
            return False, "damage score below floor"
        return True, "damage supported"

    current = _apply(current, 4, "Damage Quality", damage_gate, logs)

    # Gate 5: hitter-specific opposing-pitcher compatibility prepared in core.py.
    def pitch_gate(player):
        if player.get("pitch_edge") is None:
            return False, "pitch matchup data missing"
        return float(player["pitch_edge"]) >= 0, "negative pitch edge"

    current = _apply(current, 5, "Pitch Matchup", pitch_gate, logs)

    # Gate 6: lineup access.
    current = _apply(
        current,
        6,
        "Lineup Access",
        lambda p: ((p.get("slot") or 99) <= 6, "bottom-order protected slot"),
        logs,
    )

    # Gate 7: recent rhythm must be loaded. A cold result is an elimination.
    def rhythm_gate(player):
        if player.get("recent_pa") is None or player.get("hr_heat") is None:
            return False, "recent rhythm data missing"
        return bool(player.get("hr_heat")), "dead recent rhythm"

    current = _apply(current, 7, "Recent Rhythm", rhythm_gate, logs)

    # Gate 8: season conversion floor.
    def conversion_gate(player):
        if player.get("hr_pa") is None:
            return False, "HR/PA data missing"
        return float(player["hr_pa"]) >= 0.025, "HR/PA below WHO floor"

    current = _apply(current, 8, "HR Conversion", conversion_gate, logs)

    # Gate 9: hitter/environment alignment, not a logging-only placeholder.
    def environment_alignment(player):
        if env_score is None:
            return False, "environment data missing"
        damage = player.get("damage_score")
        if damage is None:
            return False, "damage data missing"
        # Mildly negative parks require a stronger damage identity; neutral/positive parks do not.
        required_damage = 45 if float(env_score) < 0 else 35
        return float(damage) >= required_damage, f"damage below environment floor {required_damage}"

    current = _apply(
        current,
        9,
        "Hitter Environment Alignment",
        environment_alignment,
        logs,
        note=env,
    )

    # Gate 10: projected plate-appearance access.
    current = _apply(
        current,
        10,
        "Opportunity",
        lambda p: ((p.get("slot") or 99) <= 6, "insufficient projected PA"),
        logs,
    )

    # Gate 10.5 is executed after ownership assignment in core.py.
    logs.append(_log(10.5, "Adjacent / Decoy Transfer", len(current), len(current), note="executed in core"))

    # Gate 11: bullpen continuation. Bullpen data must exist; a low-risk pen only
    # removes hitters without a strong finishing identity.
    bullpen = game.get("away_bullpen") if target.get("side") == "home" else game.get("home_bullpen")
    bullpen = bullpen or {}
    bullpen_risk = bullpen.get("risk_score")

    def bullpen_gate(player):
        if bullpen_risk is None:
            return False, "bullpen data missing"
        if float(bullpen_risk) >= 5:
            return True, "bullpen continuation available"
        strong_finisher = (
            float(player.get("hr_pa") or 0) >= 0.04
            and float(player.get("iso") or 0) >= 0.200
            and float(player.get("damage_score") or 0) >= 50
        )
        return strong_finisher, "low-risk bullpen blocks non-elite finisher"

    current = _apply(current, 11, "Bullpen Continuation", bullpen_gate, logs, note=bullpen)

    # Gate 12 ownership is assigned in core.py after baseball eliminations.
    logs.append(_log(12, "Event Ownership", len(current), len(current), note="scored in core"))

    # Gate 13: Universe. Kept completely separate from baseball scores.
    before = len(current)
    for player in current:
        player["universe_score"] = _universe_score(player, game)
    if len(current) > 1:
        high = max(player["universe_score"] for player in current)
        floor = max(0, high - 250)
        removed = [
            {"player": p.get("name"), "reason": f"Universe {p['universe_score']} below lane {floor}"}
            for p in current
            if p["universe_score"] < floor
        ]
        current = [p for p in current if p["universe_score"] >= floor]
    else:
        removed = []
    logs.append(
        _log(
            13,
            "Universe",
            before,
            len(current),
            removed,
            note="isolated deterministic layer; not blended into baseball metrics",
        )
    )

    # Gate 14: adjacent lineup protection.
    def protection_gate(player):
        if player.get("protection") is None:
            return False, "lineup protection data missing"
        return float(player["protection"]) >= 0, "isolated lineup cluster"

    current = _apply(current, 14, "Lineup Protection", protection_gate, logs)

    # Gate 15: HR finisher identity. No empty-bat pass.
    def finisher(player):
        missing = _missing(player, "hr_pa", "iso", "damage_score")
        if missing:
            return False, f"missing finisher data: {', '.join(missing)}"
        passed = (
            float(player["hr_pa"]) >= 0.025
            and float(player["iso"]) >= 0.150
            and float(player["damage_score"]) >= 35
        )
        return passed, "finisher floor failed"

    current = _apply(current, 15, "HR Finisher Identity", finisher, logs)

    # Gate 16: true last-man elimination. Exactly one survivor or none.
    before = len(current)
    ordered = sorted(
        current,
        key=lambda p: (
            float(p.get("hr_model_score") or 0),
            float(p.get("damage_score") or 0),
            float(p.get("pitch_edge") or 0),
            float(p.get("universe_score") or 0),
            -(p.get("slot") or 99),
        ),
        reverse=True,
    )
    current = ordered[:1]
    removed = [
        {"player": p.get("name"), "reason": "lost Gate 16 last-man comparison"}
        for p in ordered[1:]
    ]
    logs.append(_log(16, "Last-Man Elimination", before, len(current), removed))

    # Gate 17 and 18 are finalized in core.py.
    logs.append(_log(17, "Audit", len(current), len(current), note="completed in core"))
    logs.append(_log(18, "Final Lock", len(current), len(current), note="completed in core"))
    return current, logs
