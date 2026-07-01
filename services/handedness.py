def get_handedness_profile(name):

    # deterministic placeholder model (no external dependency)

    lefty_power = ["soto", "harper", "betts", "seager"]
    righty_power = ["judge", "ohtani", "trout", "acuna"]

    if any(x in name.lower() for x in lefty_power):
        return "LHH"

    if any(x in name.lower() for x in righty_power):
        return "RHH"

    return "RHH"  # default safe assumption
