def build_core3(results):

    """
    CORE 3 — Slate Stability Lock Mode
    (NO scoring, NO ML, fully deterministic 18-gate aligned system)
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
        # TIER CLASSIFICATION (gate strength only)
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
    # STEP 1 — FIND STRONGEST TIER
    # ----------------------------
    max_tier = max(p["tier"] for p in pool)

    top_cluster = [p for p in pool if p["tier"] == max_tier]

    # ----------------------------
    # STEP 2 — GROUP BY GAME (ENVIRONMENT LOCK)
    # ----------------------------
    games = {}

    for p in top_cluster:
        games.setdefault(p["game"], []).append(p)

    # ----------------------------
    # STEP 3 — ENVIRONMENT PRIORITY ORDER
    # (most populated strong environments first)
    # ----------------------------
    sorted_games = sorted(
        games.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    # ----------------------------
    # STEP 4 — SLATE LOCK (NO ORDER BIAS)
    # ----------------------------
    core3 = []

    for game, players in sorted_games:
        for p in players:
            core3.append(p)
            if len(core3) == 3:
                break
        if len(core3) == 3:
            break

    # ----------------------------
    # STEP 5 — FINAL OUTPUT FORMAT
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
