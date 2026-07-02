def build_core3(results):

    pool = []

    for r in results:

        survivor = r.get("survivor")

        if not survivor or survivor in ["EMPTY", "NONE"]:
            continue

        pool.append({
            "name": survivor,
            "game": r["game"],
            "why": r["why"]
        })

    # always return up to 3
    return [
        {
            "rank": i + 1,
            "player": p["name"],
            "game": p["game"],
            "reason": p["why"]
        }
        for i, p in enumerate(pool[:3])
    ]
