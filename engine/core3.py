def build_core3(results):

    """
    CORE 3 — Stable Deterministic Tier Selector
    Fixes order-based selection bug when all survivors share same tier
    (NO scoring, NO ML, 18-gate aligned)
    """

    pool = []

    for r in results:

        survivor = r.get("survivor")

        # skip invalid outputs
        if survivor in [
            "NO LINEUP DATA YET",
            "NO SURVIVOR",
            "NONE",
            None
        ]:
            continue

        why = str(r.get("why", "")).upper()

        # ----------------------------
        # TIER SYSTEM (your gate language only)
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
    # SAFETY CHECK
    # ----------------------------
    if not pool:
        return []

    # ----------------------------
    # FIND STRONGEST TIER
    # ----------------------------
    max_tier = max(p["tier"] for p in pool)

    top_cluster = [p for p in pool if p["tier"] == max_tier]

    # ----------------------------
    # FIX: STABLE ORDERING (IMPORTANT)
    # prevents random 2/3 mismatch like Kevin issue
    # ----------------------------
    top_cluster = sorted(
        top_cluster,
        key=lambda x: x["game"]  # deterministic ordering
    )

    # ----------------------------
    # CORE 3 SELECTION
    # ----------------------------
    core3 = top_cluster[:3]

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
        for i, p in enumerate(core3)
    ]
