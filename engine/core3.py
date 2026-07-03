def build_core3(results):
    """
    CORE 3 v1 — PURE EVENT SELECTION ENGINE

    RULE:
    - NO scoring parsing
    - NO string analysis
    - ONLY structured winners per game
    """

    final = []

    for r in results:

        if r.get("survivor") in [
            "NO LINEUP DATA",
            "NO PITCHER",
            "NO SURVIVOR"
        ]:
            continue

        final.append({
            "game": r["game"],
            "player": r["survivor"],
            "gate_info": r.get("why", [])
        })

    # -------------------------
    # FINAL REDUCTION (ONLY HERE)
    # -------------------------
    return final[:3]
