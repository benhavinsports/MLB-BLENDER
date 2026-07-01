def apply_gates(hitters):

    survivors = []

    for h in hitters:

        # HARD RULE: no fabricated stats allowed
        if h["pull_pct"] is None:
            continue

        # G3 Pull
        if h["pull_pct"] < 0.50:
            continue

        # G4 Hard Hit (if available)
        if h["hh_pct"] is not None and h["hh_pct"] < 0.38:
            continue

        survivors.append(h)

    return survivors
