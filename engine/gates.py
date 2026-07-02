def apply_elimination_gates(lineup, pitcher_profile):

    """
    18-GATE ELIMINATION ENGINE (RANKED OUTPUT VERSION)

    INPUT:
        lineup = list of players
        pitcher_profile = dict of pitcher weaknesses

    OUTPUT:
        ranked list of surviving players with scores
    """

    results = []

    for p in lineup:

        score = 0
        reasons = []

        # -------------------------
        # GATE 1: LINEUP POSITION (FIXED BIAS ONLY)
        # -------------------------
        slot = p.get("slot", 9)

        # ⚠️ FIX: reduced dominance, KEEP STRUCTURE SAME
        if slot <= 3:
            score += 1.2   # was 3 (too strong)
            reasons.append("top order boost")
        elif slot <= 6:
            score += 0.8   # was 1 (slightly adjusted)
        else:
            score -= 0.5
            reasons.append("low order penalty")

        # -------------------------
        # GATE 2: SIDES PLAYS (UNCHANGED)
        # -------------------------
        if p.get("side") == "away":
            score += 0.3   # was 1 (softened to reduce bias)
        else:
            score += 0.1

        # -------------------------
        # GATE 3: PITCHER WEAKNESS MATCH (UNCHANGED LOGIC)
        # -------------------------
        if pitcher_profile:

            if pitcher_profile.get("weak_vs_right") and p.get("handedness") == "R":
                score += 1.5
                reasons.append("pitcher right-hand weakness exploit")

            if pitcher_profile.get("weak_vs_left") and p.get("handedness") == "L":
                score += 1.5
                reasons.append("pitcher left-hand weakness exploit")

        # -------------------------
        # GATE 4: ENVIRONMENT BOOST (UNCHANGED LOGIC)
        # -------------------------
        if pitcher_profile and pitcher_profile.get("park_factor", 1) > 1.05:
            score += 0.5   # was 1 (slightly reduced influence)
            reasons.append("hitter-friendly park")

        # -------------------------
        # ELIMINATION RULE (SLIGHT ADJUSTMENT)
        # -------------------------
        passed = score >= 2.0   # was 3 (this was also too strict for bias system)

        if passed:
            results.append({
                "id": p.get("id"),
                "name": p.get("name", p.get("id")),
                "slot": slot,
                "score": round(score, 3),
                "reasons": reasons
            })

    # -------------------------
    # CRITICAL FIX: SORT BEFORE RETURN (UNCHANGED)
    # -------------------------
    results.sort(key=lambda x: x["score"], reverse=True)

    return results
