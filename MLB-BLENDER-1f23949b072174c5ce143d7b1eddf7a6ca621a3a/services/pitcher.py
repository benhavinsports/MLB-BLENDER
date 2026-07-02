def get_pitcher_profile(name):

    # deterministic pitch archetypes (stable model)

    profiles = {
        "power_fastball": {
            "fastball": 0.60,
            "slider": 0.20,
            "changeup": 0.10,
            "weakness": "power_hitters"
        },

        "offspeed_heavy": {
            "fastball": 0.35,
            "slider": 0.25,
            "changeup": 0.30,
            "weakness": "timing_hitters"
        },

        "balanced": {
            "fastball": 0.45,
            "slider": 0.25,
            "changeup": 0.20,
            "weakness": "none"
        }
    }

    # simple deterministic assignment (no API dependency)
    if any(x in name.lower() for x in ["cole", "burnes", "strider"]):
        return profiles["power_fastball"]

    if any(x in name.lower() for x in ["snell", "kirby", "nola"]):
        return profiles["offspeed_heavy"]

    return profiles["balanced"]
