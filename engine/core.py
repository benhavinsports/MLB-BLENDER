from __future__ import annotations

from engine.audit import run_audit
from engine.final_lock import final_lock
from engine.gates import gate_log, run_all_gates
from engine.target_layer import lock_target
from services.bullpen import build_bullpen_card
from services.environment import build_environment_card
from services.lineups import build_game_pool
from services.pitchers import build_pitcher_card
from services.stats import attach_stats


def prepare_game(raw_game: dict, season: int) -> dict:
    game=dict(raw_game)
    away_raw=dict(game.get("away_pitcher") or {})
    away_raw.update({"side":"away","team":game.get("away")})
    home_raw=dict(game.get("home_pitcher") or {})
    home_raw.update({"side":"home","team":game.get("home")})
    game["away_pitcher_card"]=build_pitcher_card(away_raw,season)
    game["home_pitcher_card"]=build_pitcher_card(home_raw,season)
    game["environment"]=build_environment_card(game)
    game["away_bullpen"]=build_bullpen_card(
        game.get("away_bullpen"), team_id=game.get("away_id"), season=season, team_name=game.get("away")
    )
    game["home_bullpen"]=build_bullpen_card(
        game.get("home_bullpen"), team_id=game.get("home_id"), season=season, team_name=game.get("home")
    )
    return game


def _wire_matchup_context(hitters: list[dict], game: dict, target: dict) -> None:
    """Attach matchup context without selecting a hitter.

    Until true pitch-type and zone feeds are added, this is explicitly labeled
    as a proxy and centered around zero so Gate 5 can actually reject negative
    matchups instead of passing every remaining hitter.
    """
    opposing_pitcher = target.get("pitcher") or {}
    pitcher_throws = opposing_pitcher.get("throws")
    leak = float(target.get("leak_score") or 0)
    k_rate = opposing_pitcher.get("k_rate")

    bullpen = game.get("away_bullpen") if target.get("side") == "home" else game.get("home_bullpen")
    bullpen = bullpen or {}

    for player in hitters:
        if player.get("side") != target.get("side"):
            continue

        damage = float(player.get("damage_score") or 0)
        model = float(player.get("hr_model_score") or 0)
        components = {
            "pitcher_leak": (leak - 0.75) * 2.5,
            "damage": (damage - 50.0) * 0.04,
            "hr_model": (model - 50.0) * 0.025,
            "strikeout": 0.0,
            "platoon": 0.0,
        }
        if k_rate is not None:
            components["strikeout"] = -max(0.0, float(k_rate) - 23.0) * 0.12

        bat_side = str(player.get("handedness") or "").upper()
        if pitcher_throws in {"R", "L"} and bat_side in {"R", "L"}:
            components["platoon"] = 0.75 if bat_side != pitcher_throws else -0.25

        edge = sum(components.values())
        player["pitch_edge"] = round(edge, 3)
        player["pitch_edge_components"] = {key: round(value, 3) for key, value in components.items()}
        player["pitch_edge_source"] = "PITCHER_LEAK_DAMAGE_PLATOON_PROXY"
        player["bullpen_risk"] = bullpen.get("risk_score")
        player["bullpen_source"] = bullpen.get("source")


def run_blender(games: list[dict], season: int) -> list[dict]:
    results=[]
    for raw_game in games:
        game=prepare_game(raw_game,season)
        target=lock_target(game)
        raw_hitters=build_game_pool(game)
        side_counts={
            "away": sum(1 for p in raw_hitters if p.get("side") == "away"),
            "home": sum(1 for p in raw_hitters if p.get("side") == "home"),
        }
        hitters=attach_stats(raw_hitters,season,game.get("date"))
        _wire_matchup_context(hitters,game,target)
        gate1_profiles=[{
            "name":p.get("name"),"team":p.get("team"),"side":p.get("side"),"slot":p.get("slot"),
            "pull":p.get("pull"),"pull_percent":p.get("pull_percent"),"pua":p.get("pua"),
            "pull_air_source":p.get("pull_air_source"),"hard_hit":p.get("hard_hit"),"barrel":p.get("barrel"),
            "ev":p.get("ev"),"blast":p.get("blast"),"squared_up":p.get("squared_up"),
            "sweet_spot":p.get("sweet_spot"),"bat_speed":p.get("bat_speed"),
            "iso":p.get("iso"),"hr_pa":p.get("hr_pa"),"damage_score":p.get("damage_score"),
            "pitch_edge":p.get("pitch_edge"),"pitch_edge_source":p.get("pitch_edge_source"),
            "pitch_edge_components":p.get("pitch_edge_components"),"hr_heat":p.get("hr_heat"),
            "recent_hr":p.get("recent_hr"),"recent_pa":p.get("recent_pa"),
            "protection":p.get("protection"),"protection_score":p.get("protection_score"),
            "bullpen_risk":p.get("bullpen_risk"),
            "advanced_metrics_loaded":p.get("advanced_metrics_loaded",False),
        } for p in hitters]
        pipeline_health={
            "away_lineup": side_counts["away"],
            "home_lineup": side_counts["home"],
            "pitcher_cards": bool(game.get("away_pitcher_card")) and bool(game.get("home_pitcher_card")),
            "advanced_profiles": sum(1 for p in hitters if p.get("advanced_metrics_loaded")),
            "environment": bool(game.get("environment")),
            "bullpens": bool((game.get("away_bullpen") or {}).get("loaded")) and bool((game.get("home_bullpen") or {}).get("loaded")),
        }
        target_side=target.get("side")
        target_pool_count=sum(1 for p in hitters if p.get("side") == target_side)

        # Data-integrity guard: Gate 0 must never eliminate a valid side merely
        # because that lineup failed to load. This does not alter gate logic;
        # it reports the upstream lineup failure directly.
        if target_pool_count == 0:
            game_name=f"{game.get('away','UNKNOWN')} vs {game.get('home','UNKNOWN')}"
            results.append({
                "game": game_name,
                "survivor": "NO SURVIVOR",
                "why": f"TARGET LINEUP NOT LOADED: {target.get('team')} ({target_side})",
                "status": "DATA ERROR",
                "target_side": target,
                "lineup_counts": side_counts,
                "pipeline_health": pipeline_health,
                "gate1_profiles": gate1_profiles,
                "audit": [{
                    "gate": 0,
                    "name": "Target Side Isolation",
                    "before": len(hitters),
                    "after": 0,
                    "removed": [],
                    "note": {"target": target, "lineup_counts": side_counts},
                }],
            })
            continue

        survivors,logs=run_all_gates(hitters,game,target)
        audit=run_audit(survivors,logs)
        logs.append(
            gate_log(
                17,
                "Audit",
                len(survivors),
                len(survivors) if audit.get("passed") else 0,
                [] if audit.get("passed") else [{"player": (survivors[0].get("name") if survivors else None), "reason": "audit failed"}],
                note=audit,
            )
        )
        owner=survivors[0] if audit.get("passed") and survivors else None
        result=final_lock(game,owner,audit)
        logs.append(
            gate_log(
                18,
                "Final Lock",
                1 if owner else 0,
                1 if result.get("status") == "LOCKED" else 0,
                note={
                    "status": result.get("status"),
                    "survivor": result.get("survivor"),
                    "why": result.get("why"),
                },
            )
        )
        result["audit"]=logs
        result["target_side"]=target
        result["pipeline_health"]=pipeline_health
        result["gate1_profiles"]=gate1_profiles
        results.append(result)
    return results


def build_core3(results: list[dict]) -> list[dict]:
    locked=[r for r in results if r.get("status")=="LOCKED" and r.get("survivor") not in {None,"NO SURVIVOR","NONE"}]
    return sorted(locked,key=lambda r:r.get("event_score",0),reverse=True)[:3]
