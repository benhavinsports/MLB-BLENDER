def assign_event_ownership(players: list[dict], game: dict, target: dict) -> list[dict]:
    env = (game.get("environment") or {}).get("environment_score") or 0
    leak = target.get("leak_score") or 0

    for player in players:
        slot_score = max(0, 10 - (player.get("slot") or 9)) * 2
        rhythm = 2.5 if player.get("hr_heat") is True else 0
        protection = max(0, player.get("protection") or 0) * 2
        pitch_edge = max(0, player.get("pitch_edge") or 0) * 1.25
        bullpen = max(0, player.get("bullpen_risk") or 0) * .75

        player["ownership_score"] = round(
            leak * 8
            + env * 2
            + player.get("damage_score", 0) * .30
            + player.get("hr_model_score", 0) * .35
            + slot_score
            + rhythm
            + protection
            + pitch_edge
            + bullpen,
            3,
        )
        player["event_reason"] = (
            "HR event recipient: pitcher leak + pitch edge + damage + "
            "lineup access + recent rhythm + protection + bullpen continuation"
        )
    return players


def get_owner(players: list[dict]):
    return max(players, key=lambda p: p.get("ownership_score", 0)) if players else None
