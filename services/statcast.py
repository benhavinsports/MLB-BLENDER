def get_statcast_profile(name):

    # stable proxy model (NOT scraping-dependent, stability safe)

    base_profiles = {
        "power": {"ev": 92, "barrel": 0.14, "x": 0.350},
        "balanced": {"ev": 88, "barrel": 0.09, "x": 0.315},
        "speed": {"ev": 86, "barrel": 0.06, "x": 0.300}
    }

    # simple classification heuristics (safe, deterministic)
    if any(x in name.lower() for x in ["judge", "ohtani", "soto", "harper"]):
        return base_profiles["power"]

    if any(x in name.lower() for x in ["mckinstry", "gonzalez", "abrams"]):
        return base_profiles["speed"]

    return base_profiles["balanced"]
