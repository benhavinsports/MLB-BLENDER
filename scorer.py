
def score_player(p):
    return (
        0.22*p["pull"] +
        0.18*p["hh"] +
        0.18*p["barrel"] +
        0.12*p["ev"] +
        0.10*p["iso"] +
        0.10*p["matchup"] +
        0.10*p["venue"]
    )
