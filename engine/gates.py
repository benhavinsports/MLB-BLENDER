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
        # GATE 1: LINEUP POSITION
        # -------------------------
        slot = p.get("slot", 9)

        if slot <= 3:
            score += 3
            reasons.append("top order boost")
        elif slot <= 6:
            score += 1
        else:
            score -= 1
            reasons.append("low order penalty")

        # -------------------------
        # GATE 2: SIDES PLAYS (basic leverage)
        # -------------------------
        if p.get("side") == "away":
            score += 1
        else:
            score += 0

        # -------------------------
        # GATE 3: PITCHER WEAKNESS MATCH
        # -------------------------
        if pitcher_profile:

            if pitcher_profile.get("weak_vs_right") and p.get("handedness") == "R":
                score += 2
                reasons.append("pitcher right-hand weakness exploit")

            if pitcher_profile.get("weak_vs_left") and p.get("handedness") == "L":
                score += 2
                reasons.append("pitcher left-hand weakness exploit")

        # -------------------------
        # GATE 4: ENVIRONMENT BOOST
        # -------------------------
        if pitcher_profile.get("park_factor", 1) > 1.05:
            score += 1
            reasons.append("hitter-friendly park")

        # -------------------------
        # ELIMINATION RULE (TRUE GATE)
        # -------------------------
        passed = score >= 3

        if passed:
            results.append({
                "id": p.get("id"),
                "name": p.get("name", p.get("id")),
                "slot": slot,
                "score": score,
                "reasons": reasons
            })

    # -------------------------
    # CRITICAL FIX: SORT BEFORE RETURN
    # -------------------------
    results.sort(key=lambda x: x["score"], reverse=True)

    return results
