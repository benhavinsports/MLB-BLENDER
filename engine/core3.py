def build_core3(results):

    """
    Takes full slate results and returns GLOBAL CORE 3 (cross-game pool)
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

        pool.append({
            "name": survivor,
            "game": r.get("game"),
            "why": r.get("why")
        })

    # ----------------------------
    # CORE 3 SELECTION (FIRST 3 VALID)
    # ----------------------------
    core3 = pool[:3]

    formatted = []

    for i, p in enumerate(core3, 1):

        formatted.append({
            "rank": i,
            "player": p["name"],
            "game": p["game"],
            "reason": p["why"]
        })

    return formatted
