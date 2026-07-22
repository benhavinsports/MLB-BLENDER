from __future__ import annotations

import hashlib

from engine.ownership import assign_event_ownership


def gate_log(gate, name, before, after, removed=None, note=None):
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
    logs.append(gate_log(gate, name, before, len(kept), removed, note=note))
    return kept


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


def run_all_gates(hitters: list[dict], game: dict, target: dict):
    logs: list[dict] = []

    # Gate 0: target layer has already locked exactly one offense side.
    current = [p for p in hitters if p.get("side") == target.get("side")]
    logs.append(gate_log(0, "Target Side Isolation", len(hitters), len(current), note=target))

    # Gate 1: game environment.
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
    )

    # Gate 3: Pull-Air identity. ``pull`` must be the Blender index, not raw Pull%.
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

    current = _apply(current, 3, "Pull-Air Identity", pull_gate, logs)

    # Gate 4: Damage support.
    def damage_gate(player):
        missing = _missing(player, "hard_hit", "damage_score")
        if missing:
            return False, f"missing damage data: {', '.join(missing)}"
        if float(player["hard_hit"]) < 40:
            return False, "Hard Hit < 40 auto-kill"
        if float(player["damage_score"]) < 35:
            return False, "damage score below floor"
        return True, "damage supported"

    current = _apply(current, 4, "Damage Quality", damage_gate, logs)

    # Gate 5: matchup edge. The audit records whether this is real or proxy data.
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
    )

    # Gate 6: lineup access. Slot 7 remains alive here but must clear Opportunity.
    current = _apply(
        current,
        6,
        "Lineup Access",
        lambda p: ((p.get("slot") or 99) <= 7, "slot outside access lane"),
        logs,
    )

    # Gate 7: recent HR signal/rhythm.
    def rhythm_gate(player):
        if player.get("recent_pa") is None or player.get("hr_heat") is None:
            return False, "recent rhythm data missing"
        return bool(player.get("hr_heat")), "dead recent rhythm"

    current = _apply(current, 7, "Recent Rhythm", rhythm_gate, logs)

    # Gate 8: season HR conversion floor.
    current = _apply(
        current,
        8,
        "HR Conversion",
        lambda p: (
            p.get("hr_pa") is not None and float(p["hr_pa"]) >= 0.025,
            "HR/PA data missing" if p.get("hr_pa") is None else "HR/PA below WHO floor",
        ),
        logs,
    )

    # Gate 9: environment recheck at hitter level.
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
    )

    # Gate 10: true PA opportunity lane; stricter than Gate 6.
    current = _apply(
        current,
        10,
        "Opportunity",
        lambda p: ((p.get("slot") or 99) <= 6, "insufficient projected PA"),
        logs,
    )

    # Gate 10.5: identify false chalk and a possible adjacent transfer lane.
    before = len(current)
    assign_event_ownership(current, game, target)
    removed = []
    kept = []
    for player in current:
        pull = float(player.get("pull") or 0)
        hard_hit = float(player.get("hard_hit") or 0)
        if pull < 55 and hard_hit < 45:
            removed.append({"player": player.get("name"), "reason": "false chalk: pull <55 and HH <45"})
        else:
            kept.append(player)
    current = kept

    ordered = sorted(current, key=lambda p: p.get("ownership_score", 0), reverse=True)
    transfer_lane = None
    if len(ordered) >= 2:
        top, second = ordered[0], ordered[1]
        gap = float(top.get("ownership_score") or 0) - float(second.get("ownership_score") or 0)
        if gap <= 10:
            second["transfer_candidate"] = True
            transfer_lane = {
                "from": top.get("name"),
                "to": second.get("name"),
                "ownership_gap": round(gap, 3),
            }
    logs.append(
        gate_log(
            10.5,
            "Adjacent / Decoy Transfer",
            before,
            len(current),
            removed,
            note={"transfer_lane": transfer_lane, "ownership": _ownership_snapshot(current)},
        )
    )

    # Gate 11: bullpen continuation.
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

    # Gate 14: lineup protection.
    def protection_gate(player):
        if player.get("protection") is None:
            return False, "lineup protection data missing"
        if float(player["protection"]) >= 0:
            return True, "protected cluster"
        elite = float(player.get("damage_score") or 0) >= 65 and float(player.get("hr_pa") or 0) >= 0.04
        return elite, "isolated lineup cluster"

    current = _apply(current, 14, "Lineup Protection", protection_gate, logs)

    # Gate 15: finisher identity; pressure cannot outweigh finishing ability.
    def finisher_gate(player):
        missing = _missing(player, "hr_pa", "iso", "damage_score")
        if missing:
            return False, f"missing finisher data: {', '.join(missing)}"
        passed = (
            float(player["hr_pa"]) >= 0.025
            and float(player["iso"]) >= 0.150
            and float(player["damage_score"]) >= 35
        )
        return passed, "finisher floor failed"

    current = _apply(current, 15, "HR Finisher Identity", finisher_gate, logs)

    # Gate 16: one last man, with the locked <=10 ownership-gap transfer rule.
    before = len(current)
    assign_event_ownership(current, game, target)
    ordered = sorted(
        current,
        key=lambda p: (
            float(p.get("ownership_score") or 0),
            float(p.get("universe_score") or 0),  # tie-break only
            -(p.get("slot") or 99),
        ),
        reverse=True,
    )

    selected = None
    transfer = None
    if ordered:
        selected = ordered[0]
        if len(ordered) >= 2:
            top, second = ordered[0], ordered[1]
            gap = float(top.get("ownership_score") or 0) - float(second.get("ownership_score") or 0)
            if gap <= 10:
                selected = second
                selected["transfer_flag"] = True
                selected["event_reason"] = "HR event transferred from obvious profile to adjacent pressure-release hitter"
                transfer = {
                    "from": top.get("name"),
                    "to": second.get("name"),
                    "ownership_gap": round(gap, 3),
                }

    current = [selected] if selected else []
    removed = [
        {
            "player": p.get("name"),
            "reason": "lost Gate 16 ownership/transfer comparison",
        }
        for p in ordered
        if selected is not p
    ]
    logs.append(
        gate_log(
            16,
            "Last-Man Elimination",
            before,
            len(current),
            removed,
            note={"transfer": transfer, "ownership": _ownership_snapshot(ordered)},
        )
    )

    return current, logs
