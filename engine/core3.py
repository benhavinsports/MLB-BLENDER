def build_core3(results):

    cleaned = []

    for r in results:
        if r.get("survivor"):
            cleaned.append(r)

    # ONLY TOP 3 GAMES → CORE 3
    cleaned = cleaned[:3]

    return [
        {
            "rank": i + 1,
            "player": r["survivor"],
            "game": r["game"],
            "reason": "CORE 3 EVENT LOCK"
        }
        for i, r in enumerate(cleaned)
    ]
