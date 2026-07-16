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
        hitters=attach_stats(raw_hitters,season)
        gate1_profiles=[{
            "name":p.get("name"),"team":p.get("team"),"side":p.get("side"),"slot":p.get("slot"),
            "pull":p.get("pull"),"hard_hit":p.get("hard_hit"),"barrel":p.get("barrel"),
            "ev":p.get("ev"),"blast":p.get("blast"),"squared_up":p.get("squared_up"),
            "sweet_spot":p.get("sweet_spot"),"bat_speed":p.get("bat_speed"),
            "iso":p.get("iso"),"hr_pa":p.get("hr_pa"),"damage_score":p.get("damage_score"),
        } for p in hitters]
        survivors,logs=run_all_gates(hitters,game,target)
        survivors=remove_false_chalk(survivors)
        survivors=assign_event_ownership(survivors,game,target)
        survivors=transfer_event(survivors)
        owner=get_owner(survivors)
        audit=run_audit(survivors,logs)
        result=final_lock(game,owner,audit)
        result["audit"]=logs
        result["target_side"]=target
        result["gate1_profiles"]=gate1_profiles
        results.append(result)
    return results


def build_core3(results: list[dict]) -> list[dict]:
    locked=[r for r in results if r.get("status")=="LOCKED" and r.get("survivor") not in {None,"NO SURVIVOR","NONE"}]
    return sorted(locked,key=lambda r:r.get("event_score",0),reverse=True)[:3]
