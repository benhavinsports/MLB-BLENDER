def build_core3(results):

    if not results:
        return []

    # -------------------------
    # FILTER VALID RESULTS
    # -------------------------
    valid = [r for r in results if r.get("survivor")]

    # -------------------------
    # RANK BY GAME SIGNAL STRENGTH
    # (fallback if no score exists)
    # -------------------------
    def score(r):
        why = str(r.get("why", "")).lower()

        s = 0
        if "pass gate 1" in why:
            s += 1
        if "pass gate 2" in why:
            s += 1
        if "exploit" in why:
            s += 2

        return s

    valid.sort(key=score, reverse=True)

    # -------------------------
    # CORE 3 LIMIT (TRUE 3 ONLY)
    # -------------------------
    top3 = valid[:3]

    return [
        {
            "rank": i + 1,
            "player": r["survivor"],
            "game": r["game"],
            "reason": "CORE 3 EVENT LOCK"
        }
        for i, r in enumerate(top3)
    ]
