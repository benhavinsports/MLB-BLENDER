from __future__ import annotations

from engine.audit import run_audit
from engine.final_lock import final_lock
from engine.gates import gate_log, run_all_gates
from engine.target_layer import lock_target
from services.bullpen import build_bullpen_card
from services.environment import build_environment_card
from services.lineups import build_game_pool
from services.pitchers import build_pitcher_card
from services.statcast import get_game_matchup_profiles
from services.stats import attach_stats


def prepare_game(raw_game: dict, season: int) -> dict:
    game = dict(raw_game)
    away_raw = dict(game.get("away_pitcher") or {})
    away_raw.update({"side": "away", "team": game.get("away")})
    home_raw = dict(game.get("home_pitcher") or {})
    home_raw.update({"side": "home", "team": game.get("home")})
    game["away_pitcher_card"] = build_pitcher_card(away_raw, season)
    game["home_pitcher_card"] = build_pitcher_card(home_raw, season)
    game["environment"] = build_environment_card(game)
    game["away_bullpen"] = build_bullpen_card(
        game.get("away_bullpen"),
        team_id=game.get("away_id"),
        season=season,
        team_name=game.get("away"),
    )
    game["home_bullpen"] = build_bullpen_card(
        game.get("home_bullpen"),
        team_id=game.get("home_id"),
        season=season,
        team_name=game.get("home"),
    )
    return game


def _wire_matchup_context(hitters: list[dict], game: dict, target: dict, season: int) -> None:
    """Attach real pitch-type, zone, and mistake-location matchup evidence."""
    target_hitters = [player for player in hitters if player.get("side") == target.get("side")]
    hitter_ids = tuple(
        int(player["id"])
        for player in target_hitters
        if player.get("id") is not None
    )
    opposing_pitcher = target.get("pitcher") or {}
    pitcher_id = opposing_pitcher.get("id")
    profiles = get_game_matchup_profiles(
        hitter_ids,
        int(pitcher_id) if pitcher_id else None,
        int(season),
        game.get("date"),
    )

    bullpen = game.get("away_bullpen") if target.get("side") == "home" else game.get("home_bullpen")
    bullpen = bullpen or {}

    for player in target_hitters:
        matchup = profiles.get(int(player["id"])) if player.get("id") is not None else None
        if matchup:
            player.update(matchup)
        else:
            player.update(
                {
                    "pitch_type_edge": None,
                    "zone_edge": None,
                    "pitch_edge": None,
                    "pitch_edge_source": "MATCHUP_DATA_INCOMPLETE",
                    "matchup_data_complete": False,
                    "mistake_edge": None,
                    "pitcher_mistake_rate": None,
                    "pitch_matchup_evidence": [],
                    "zone_matchup_evidence": [],
                    "mistake_matchup_evidence": [],
                    "pitcher_top_pitches": [],
                    "pitcher_top_zones": [],
                }
            )
        player["bullpen_risk"] = bullpen.get("risk_score")
        player["bullpen_source"] = bullpen.get("source")


def _debug_profiles(hitters: list[dict]) -> list[dict]:
    fields = (
        "name",
        "team",
        "side",
        "slot",
        "lineup_status",
        "pull",
        "pull_percent",
        "pua",
        "pull_barrel",
        "pull_air_source",
        "pull_identity_source",
        "fb",
        "air_source",
        "hard_hit",
        "barrel",
        "ev",
        "blast",
        "squared_up",
        "sweet_spot",
        "bat_speed",
        "iso",
        "hr_pa",
        "damage_score",
        "hr_model_score",
        "pitch_type_edge",
        "zone_edge",
        "pitch_edge",
        "pitch_edge_source",
        "mistake_edge",
        "pitcher_mistake_rate",
        "hr_heat",
        "recent_hr",
        "recent_pa",
        "protection",
        "protection_score",
        "bullpen_risk",
        "bullpen_source",
        "advanced_metrics_loaded",
    )
    return [{field: player.get(field) for field in fields} for player in hitters]


def _who_result(game: dict, reason: str, *, status: str = "WHO") -> dict:
    return {
        "game": f"{game.get('away', 'UNKNOWN')} vs {game.get('home', 'UNKNOWN')}",
        "survivor": "WHO",
        "team": None,
        "why": reason,
        "event_score": 0,
        "status": status,
        "core_lane": "CHAOS" if status == "WHO" else None,
    }


def run_blender(games: list[dict], season: int) -> list[dict]:
    results: list[dict] = []
    for raw_game in games:
        game = prepare_game(raw_game, season)
        target = lock_target(game)
        raw_hitters = build_game_pool(game)
        side_counts = {
            "away": sum(1 for player in raw_hitters if player.get("side") == "away"),
            "home": sum(1 for player in raw_hitters if player.get("side") == "home"),
        }
        hitters = attach_stats(raw_hitters, season, game.get("date"))
        _wire_matchup_context(hitters, game, target, season)

        target_side = target.get("side")
        target_pool = [player for player in hitters if player.get("side") == target_side]
        complete_matchups = sum(1 for player in target_pool if player.get("matchup_data_complete"))
        direct_pull_air = sum(
            1
            for player in target_pool
            if player.get("pull_identity_source") == "SAVANT_PULL_AIR_PERCENTILE"
            and "DIRECT_PULL_AIR" in str(player.get("pull_air_source") or "")
        )
        pipeline_health = {
            "away_lineup": side_counts["away"],
            "home_lineup": side_counts["home"],
            "lineup_source": game.get("lineup_source"),
            "pitcher_cards": bool(game.get("away_pitcher_card")) and bool(game.get("home_pitcher_card")),
            "advanced_profiles": sum(1 for player in hitters if player.get("advanced_metrics_loaded")),
            "target_profiles": len(target_pool),
            "direct_pull_air_profiles": direct_pull_air,
            "real_pitch_zone_matchups": complete_matchups,
            "environment": bool(game.get("environment")),
            "away_bullpen_source": (game.get("away_bullpen") or {}).get("source"),
            "home_bullpen_source": (game.get("home_bullpen") or {}).get("source"),
        }
        profiles = _debug_profiles(hitters)

        if not target_pool:
            result = _who_result(
                game,
                f"TARGET LINEUP NOT LOADED: {target.get('team')} ({target_side})",
                status="DATA ERROR",
            )
            result.update(
                {
                    "target_side": target,
                    "lineup_counts": side_counts,
                    "pipeline_health": pipeline_health,
                    "gate1_profiles": profiles,
                    "audit": [
                        gate_log(
                            0,
                            "Hydrated Game Pool",
                            len(hitters),
                            len(hitters),
                            note={
                                "data_status": "UNAVAILABLE",
                                "target": target,
                                "lineup_counts": side_counts,
                            },
                        )
                    ],
                }
            )
            results.append(result)
            continue

        survivors, logs = run_all_gates(hitters, game, target)
        audit = run_audit(survivors, logs)
        audit_before = len(survivors)
        audit_after = audit_before if audit.get("passed") else 0
        logs.append(
            gate_log(
                17,
                "Audit",
                audit_before,
                audit_after,
                []
                if audit.get("passed")
                else [
                    {
                        "player": survivors[0].get("name") if survivors else "WHO",
                        "reason": "audit failed",
                    }
                ],
                note=audit,
            )
        )

        owner = survivors[0] if audit.get("lockable") else None
        if owner:
            result = final_lock(game, owner, audit)
            result.update(
                {
                    "core_lane": owner.get("core_lane"),
                    "finisher_tier": owner.get("finisher_tier"),
                    "finisher_label": owner.get("finisher_label"),
                    "transfer_flag": bool(owner.get("transfer_flag")),
                    "chaos_flag": bool(owner.get("chaos_flag")),
                    "core_evidence": {
                        "matchup_trifecta": (
                            float(owner.get("pitch_type_edge") or 0) > 0
                            and float(owner.get("zone_edge") or 0) > 0
                            and float(owner.get("mistake_edge") or 0) > 0
                        ),
                        "recent_heat": owner.get("hr_heat") is True,
                        "positive_protection": float(owner.get("protection") or 0) >= 0,
                        "top_four_slot": int(owner.get("slot") or 99) <= 4,
                    },
                }
            )
        else:
            issue_codes = [issue.get("code") for issue in audit.get("issues") or []]
            if issue_codes:
                result = _who_result(
                    game,
                    f"DATA ERROR: audit blocked lock ({', '.join(str(code) for code in issue_codes)})",
                    status="DATA ERROR",
                )
            else:
                gate16_note = next(
                    (
                        entry.get("note") or {}
                        for entry in logs
                        if entry.get("gate") == 16
                    ),
                    {},
                )
                decision = gate16_note.get("decision")
                if decision == "WHO_UNRESOLVED_TRUE_TIE":
                    reason = "WHO: true tie remained after every elimination lane; no arbitrary name was forced"
                else:
                    first_empty = audit.get("first_empty_gate")
                    reason = f"WHO: no hitter cleared the full Blender; first empty gate {first_empty}"
                result = _who_result(game, reason)

        lock_before = 1 if owner else 0
        lock_after = 1 if result.get("status") == "LOCKED" else 0
        logs.append(
            gate_log(
                18,
                "Final Lock",
                lock_before,
                lock_after,
                note={
                    "status": result.get("status"),
                    "survivor": result.get("survivor"),
                    "why": result.get("why"),
                },
            )
        )
        result["audit"] = logs
        result["target_side"] = target
        result["pipeline_health"] = pipeline_health
        result["gate1_profiles"] = profiles
        results.append(result)
    return results


def _pick_lane_candidate(candidates: list[dict]) -> dict | None:
    """Choose inside a categorical lane without an event-score ranking."""
    if not candidates:
        return None

    # Finisher class is categorical. Within the class, evidence filters only
    # when they separate; otherwise slate order remains intact and name bias is
    # impossible.
    live = list(candidates)
    max_tier = max(int(result.get("finisher_tier") or 0) for result in live)
    live = [result for result in live if int(result.get("finisher_tier") or 0) == max_tier]
    for evidence in ("matchup_trifecta", "recent_heat", "positive_protection", "top_four_slot"):
        supported = [result for result in live if (result.get("core_evidence") or {}).get(evidence)]
        if supported and len(supported) < len(live):
            live = supported
    return live[0]


def build_core3(results: list[dict]) -> list[dict]:
    """Build Core 3 by Primary / Transfer / Chaos lanes from distinct games.

    No event_score, name reputation, or global hitter ranking is used.
    """
    locked = [
        result
        for result in results
        if result.get("status") == "LOCKED"
        and result.get("survivor") not in {None, "NO SURVIVOR", "NONE", "WHO"}
    ]
    selected: list[dict] = []
    used_games: set[str] = set()

    for lane in ("PRIMARY", "TRANSFER", "CHAOS"):
        candidates = [
            result
            for result in locked
            if result.get("core_lane") == lane and str(result.get("game")) not in used_games
        ]
        pick = _pick_lane_candidate(candidates)
        if pick is not None:
            selected.append(pick)
            used_games.add(str(pick.get("game")))

    # Fill a missing lane only from remaining validated game owners, still by
    # categorical finisher class and evidence rather than event score.
    while len(selected) < 3:
        remaining = [
            result
            for result in locked
            if result not in selected and str(result.get("game")) not in used_games
        ]
        pick = _pick_lane_candidate(remaining)
        if pick is None:
            break
        selected.append(pick)
        used_games.add(str(pick.get("game")))

    return selected[:3]
