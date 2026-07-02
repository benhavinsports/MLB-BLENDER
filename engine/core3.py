def build_core3(results):

    """
    CORE 3 — Tier Cluster Lock (NO scoring, NO ML, 18-gate aligned)
    """

    pool = []

    for r in results:

        survivor = r.get("survivor")

        if survivor in [
            "NO LINEUP DATA YET",
            "NO SURVIVOR",
            "NONE",
            None
        ]:
            continue

        why = str(r.get("why", "")).upper()

        # ----------------------------
        # TIER SYSTEM (ONLY gate language)
        # ----------------------------

        if "PURE ELIMINATION ENGINE PASS" in why:
            tier = 3
        elif "PASS" in why:
            tier = 2
        else:
            tier = 1

        pool.append({
            "name": survivor,
            "game": r.get("game"),
            "why": r.get("why"),
            "tier": tier
        })

    # ----------------------------
    # STEP 1: FIND TOP TIER
    # ----------------------------

    if not pool:
        return []

    max_tier = max(p["tier"] for p in pool)

    top_cluster = [p for p in pool if p["tier"] == max_tier]

    # ----------------------------
    # STEP 2: GAME BALANCE (IMPORTANT FIX)
    # ensures no single game dominates Core 3
    # ----------------------------

    balanced = []
    seen_games = set()

    for p in top_cluster:

        if p["game"] not in seen_games:
            balanced.append(p)
            seen_games.add(p["game"])

        if len(balanced) == 3:
            break

    # ----------------------------
    # STEP 3: FILL IF NEEDED (SECOND TIER)
    # ----------------------------

    if len(balanced) < 3:

        second_tier = [p for p in pool if p["tier"] == max_tier - 1]

        for p in second_tier:

            if p["game"] not in seen_games:
                balanced.append(p)
                seen_games.add(p["game"])

            if len(balanced) == 3:
                break

    # ----------------------------
    # FORMAT OUTPUT
    # ----------------------------

    return [
        {
            "rank": i + 1,
            "player": p["name"],
            "game": p["game"],
            "reason": p["why"]
        }
        for i, p in enumerate(balanced)
    ]
