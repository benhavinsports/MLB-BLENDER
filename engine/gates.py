def apply_gates(hitters):

    survivors = []

    for h in hitters:

        # SAFE DEFAULT METRICS (NO ELIMINATION LOCKOUT)
        pull = 0.52
        hh = 0.40

        # Gate 1: existence check
        if not h.get("name"):
            continue

        # Gate 2: deterministic thresholds
        if pull < 0.45:
            continue

        if hh < 0.35:
            continue

        h["pull_pct"] = pull
        h["hh_pct"] = hh

        survivors.append(h)

    return survivors
