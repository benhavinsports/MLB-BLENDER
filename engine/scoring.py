def score_player(p):

    return (
        0.35 * p.get("pull_pct", 0)
        + 0.25 * p.get("hh_pct", 0)
        + 0.20
    )
