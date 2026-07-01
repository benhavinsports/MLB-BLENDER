def get_pitch_profile(pitcher_name):

    # deterministic archetype model (stable, no API dependency)

    if any(x in pitcher_name.lower() for x in ["cole", "burnes", "strider"]):
        return {
            "sequence": "fastball_heavy",
            "zone_weakness": "high_fastball"
        }

    if any(x in pitcher_name.lower() for x in ["snell", "kirby", "gallen"]):
        return {
            "sequence": "breaking_ball_heavy",
            "zone_weakness": "low_outside"
        }

    return {
        "sequence": "balanced",
        "zone_weakness": "middle_plate"
    }
