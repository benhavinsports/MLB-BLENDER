def build_core3(results):

    """
    CORE 3 — Gate-aligned survivor selection (NO scoring, NO ML)
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
        # GATE SIGNAL ALIGNMENT
        # ----------------------------

        signal = 0

        # strongest system confirmation
        if "PURE ELIMINATION ENGINE PASS" in why:
            signal += 3

        # normal pass signal
        elif "PASS" in why:
            signal += 2

        # weak/unclear signal fallback
        else:
            signal += 1

        pool.append({
            "name": survivor,
            "game": r.get("game"),
            "why": r.get("why"),
            "signal": signal
        })

    # ----------------------------
    # CORE 3 SELECTION
    # (pattern-aligned, NOT random slice)
    # ----------------------------

    core3 = sorted(
        pool,
        key=lambda x: x["signal"],
        reverse=True
    )[:3]

    # ----------------------------
    # FORMAT OUTPUT
    # ----------------------------

    formatted = []

    for i, p in enumerate(core3, 1):

        formatted.append({
            "rank": i,
            "player": p["name"],
            "game": p["game"],
            "reason": p["why"]
        })

    return formatted
