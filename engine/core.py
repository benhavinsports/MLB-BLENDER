from __future__ import annotations

from engine.audit import run_audit
from engine.decoy import remove_false_chalk, transfer_event
from engine.final_lock import final_lock
from engine.gates import run_all_gates
from engine.ownership import assign_event_ownership, get_owner
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
    game["away_bullpen"]=build_bullpen_card(game.get("away_bullpen"))
    game["home_bullpen"]=build_bullpen_card(game.get("home_bullpen"))
    return game


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
        hitters=attach_stats(raw_hitters,season)
        gate1_profiles=[{
            "name":p.get("name"),"team":p.get("team"),"side":p.get("side"),"slot":p.get("slot"),
            "pull":p.get("pull"),"hard_hit":p.get("hard_hit"),"barrel":p.get("barrel"),
            "ev":p.get("ev"),"blast":p.get("blast"),"squared_up":p.get("squared_up"),
            "sweet_spot":p.get("sweet_spot"),"bat_speed":p.get("bat_speed"),
            "iso":p.get("iso"),"hr_pa":p.get("hr_pa"),"damage_score":p.get("damage_score"),
            "advanced_metrics_loaded":p.get("advanced_metrics_loaded",False),
        } for p in hitters]
        pipeline_health={
            "away_lineup": side_counts["away"],
            "home_lineup": side_counts["home"],
            "pitcher_cards": bool(game.get("away_pitcher_card")) and bool(game.get("home_pitcher_card")),
            "advanced_profiles": sum(1 for p in hitters if p.get("advanced_metrics_loaded")),
            "environment": bool(game.get("environment")),
            "bullpens": bool(game.get("away_bullpen")) and bool(game.get("home_bullpen")),
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
        survivors=remove_false_chalk(survivors)
        survivors=assign_event_ownership(survivors,game,target)
        survivors=transfer_event(survivors)
        owner=get_owner(survivors)
        audit=run_audit(survivors,logs)
        result=final_lock(game,owner,audit)
        result["audit"]=logs
        result["target_side"]=target
        # Make Gate 17/18 audit counts reflect the actual final reduction.
        for entry in logs:
            if entry.get("gate") == 17:
                entry["note"] = audit
            if entry.get("gate") == 18:
                entry["before"] = len(survivors)
                entry["after"] = 1 if owner else 0
        result["pipeline_health"]=pipeline_health
        result["gate1_profiles"]=gate1_profiles
        results.append(result)
    return results


def build_core3(results: list[dict]) -> list[dict]:
    locked=[r for r in results if r.get("status")=="LOCKED" and r.get("survivor") not in {None,"NO SURVIVOR","NONE"}]
    return sorted(locked,key=lambda r:r.get("event_score",0),reverse=True)[:3]
