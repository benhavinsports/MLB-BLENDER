def assign_event_ownership(players: list[dict], game: dict, target: dict) -> list[dict]:
    env = (game.get("environment") or {}).get("environment_score") or 0
    leak = target.get("leak_score") or 0
    for p in players:
        slot_score=max(0,10-(p.get("slot") or 9))*2
        p["ownership_score"]=round(
            leak*8 + env*2 + p.get("damage_score",0)*.30 +
            p.get("hr_model_score",0)*.35 + slot_score,3)
        p["event_reason"]="HR event recipient: pitcher leak + slot access + hitter finisher alignment"
    return players


def get_owner(players: list[dict]):
    return max(players,key=lambda p:p.get("ownership_score",0)) if players else None
