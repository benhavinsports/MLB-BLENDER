def build_core3(results):

    pool = []

    for r in results:

        if not r.get("survivor"):
            continue

        pool.append({
            "player": r["survivor"],
            "game": r["game"],
            "why": r["why"]
        })

    # FINAL INTELLIGENCE RANKING
    return [
        {
            "rank": i + 1,
            "player": p["player"],
            "game": p["game"],
            "reason": p["why"]
        }
        for i, p in enumerate(pool[:3])
    ]
