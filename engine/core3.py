from services.player_map import get_player_name


def build_core3(results):

    """
    Takes full slate results and returns GLOBAL CORE 3
    (cross-game aggregation layer)
    """

    pool = []

    for r in results:

        survivor = r.get("survivor")

        # skip empty or invalid outputs
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
    # DETERMINISTIC CORE 3 RULE
    # ----------------------------
    # (NO randomness, NO scoring drift)

    core3 = pool[:3]

    # format output cleanly
    formatted = []

    for i, p in enumerate(core3, 1):

        formatted.append({
            "rank": i,
            "player": p["name"],
            "game": p["game"],
            "reason": p["why"]
        })

    return formatted
