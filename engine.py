
def score_player(p, sc):

    return (
        0.22 * sc["pull"] +
        0.18 * sc["hh"] +
        0.18 * sc["barrel"] +
        0.12 * sc["ev"] +
        0.10 * sc["iso"] +
        0.20
    )
