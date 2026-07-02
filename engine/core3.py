def build_core3(results):

    """
    CORE 3 — Environment-Aware Stable Selector
    (NO ML, NO scoring, 18-gate aligned, context-preserving)
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
        # GATE TIER (ONLY YOUR SYSTEM LANGUAGE)
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

    if not pool:
        return []

    # ----------------------------
    # STEP 1: GET STRONGEST TIER
    # ----------------------------
    max_tier = max(p["tier"] for p in pool)

    top_cluster = [p for p in pool if p["tier"] == max_tier]

    # ----------------------------
    # STEP 2: ENVIRONMENT PRESERVATION SORT
    # (DO NOT FLATTEN GAME CONTEXT)
    # ----------------------------
    top_cluster = sorted(
        top_cluster,
        key=lambda x: (
            x["game"],   # preserves different game environments
            x["tier"]    # keeps gate strength inside environment
        )
    )

    # ----------------------------
    # STEP 3: CORE 3 SELECTION
    # ----------------------------
    core3 = top_cluster[:3]

    # ----------------------------
    # OUTPUT FORMAT
    # ----------------------------
    return [
        {
            "rank": i + 1,
            "player": p["name"],
            "game": p["game"],
            "reason": p["why"]
        }
        for i, p in enumerate(core3)
    ]
