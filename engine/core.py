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
    """Attach real pitch-type and zone matchup data to the locked offense."""
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
        "fb",
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
        pipeline_health = {
            "away_lineup": side_counts["away"],
            "home_lineup": side_counts["home"],
            "lineup_source": game.get("lineup_source"),
            "pitcher_cards": bool(game.get("away_pitcher_card")) and bool(game.get("home_pitcher_card")),
            "advanced_profiles": sum(1 for player in hitters if player.get("advanced_metrics_loaded")),
            "target_profiles": len(target_pool),
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
                            "Target Side Isolation",
                            len(hitters),
                            0,
                            note={"target": target, "lineup_counts": side_counts},
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

        owner = survivors[0] if audit.get("passed") and len(survivors) == 1 else None
        if owner:
            result = final_lock(game, owner, audit)
        else:
            first_empty = audit.get("first_empty_gate")
            issue_codes = [issue.get("code") for issue in audit.get("issues") or []]
            reason = (
                f"WHO: no hitter cleared every gate; first empty gate {first_empty}"
                if first_empty is not None
                else f"WHO: audit blocked lock ({', '.join(str(code) for code in issue_codes)})"
            )
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


def build_core3(results: list[dict]) -> list[dict]:
    locked = [
        result
        for result in results
        if result.get("status") == "LOCKED"
        and result.get("survivor") not in {None, "NO SURVIVOR", "NONE", "WHO"}
    ]
    return sorted(locked, key=lambda result: result.get("event_score", 0), reverse=True)[:3]
