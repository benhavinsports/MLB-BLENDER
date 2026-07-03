from collections import defaultdict

def build_core3(results):
    """
    CORE 3 — TRUE EVENT REDUCTION ENGINE

    RULE:
    - Take ALL game winners (no assumption on count)
    - Then reduce to TOP 3 based on gate strength signals
    """

    if not results:
        return []

    # -------------------------
    # STEP 1 — VALIDATE INPUTS
    # -------------------------
    winners = [
        r for r in results
        if r.get("survivor")
        and "NO" not in r["survivor"]
    ]

    if not winners:
        return []

    # -------------------------
    # STEP 2 — SCORE EVENT STRENGTH
    # -------------------------
    def core_score(r):
        score = 0

        why = r.get("why", [])

        # handle list or string safely
        if isinstance(why, list):
            why_text = " ".join(why)
        else:
            why_text = str(why)

        why_text = why_text.lower()

        # signal boosts from your gates
        if "top order" in why_text:
            score += 2
        if "exploit" in why_text:
            score += 2
        if "pass gate 1" in why_text:
            score += 1
        if "pass gate 2" in why_text:
            score += 1

        return score

    # attach scores
    for w in winners:
        w["core_score"] = core_score(w)

    # -------------------------
    # STEP 3 — SORT BY EVENT STRENGTH
    # -------------------------
    winners.sort(key=lambda x: x["core_score"], reverse=True)

    # -------------------------
    # STEP 4 — CORE 3 DYNAMIC REDUCTION
    # -------------------------
    core3 = winners[:3]

    # -------------------------
    # STEP 5 — OUTPUT CLEAN FORMAT
    # -------------------------
    return [
        {
            "rank": i + 1,
            "player": r["survivor"],
            "game": r["game"],
            "reason": "CORE 3 EVENT LOCK"
        }
        for i, r in enumerate(core3)
    ]
