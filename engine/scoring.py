def score_player(p):

    return (
        0.32 * (p.get("pull_pct") or 0)
        + 0.25 * (p.get("hh_pct") or 0)
        + 0.18 * (p.get("pitch_edge") or 0)
        + 0.10 * (p.get("opportunity") or 0)
    )
