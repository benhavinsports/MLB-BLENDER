def score_player(p):

    return (
        0.30 * p.get("pull_pct", 0)
        + 0.25 * p.get("hh_pct", 0)
        + 0.25 * p.get("pitch_edge", 0)
        + 0.10
    )
