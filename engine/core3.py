from collections import defaultdict


def build_core3(results):
    """
    CORE 3 v3 — EVENT OWNERSHIP ENGINE (STABLE FIX)

    PURPOSE:
    - keep your per-game logic intact
    - BUT ALSO enforce true global Core 3 selection
    """

    if not results:
        return []

    # -------------------------
    # GROUP BY GAME (KEEP YOUR STRUCTURE)
    # -------------------------
    games = defaultdict(list)

    for r in results:
        if not r.get("survivor"):
            continue

        games[r["game"]].append(r)

    final_pool = []

    # =========================
    # STEP 1 — PROCESS EACH GAME (UNCHANGED LOGIC STYLE)
    # =========================
    for game, players in games.items():

        if len(players) == 0:
            continue

        # -------------------------
        # EVENT OWNERSHIP SCORE (YOUR LOGIC PRESERVED)
        # -------------------------
        def ownership_score(p):
            gates = p.get("gates", [])
            score = 0

            for g in gates:
                if not isinstance(g, dict):
                    continue

                if g.get("pass") is True:
                    score += 1

                if g.get("gate") in [4, 6, 12, 15, 18]:
                    score += float(g.get("score", 0) or 0)

            return score

        # attach score
        for p in players:
            p["ownership_score"] = ownership_score(p)

        # sort inside game (KEEP THIS)
        players.sort(key=lambda x: x["ownership_score"], reverse=True)

        if not players:
            continue

        chosen = players[0]

        # decoy logic (KEEP YOUR 10.5 IDEA)
        if len(players) > 1:
            second = players[1]

            gap = abs(
                chosen["ownership_score"] - second["ownership_score"]
            )

            if gap <= 1.0:
                chosen = second

        # -------------------------
        # ADD TO GLOBAL POOL (THIS IS THE FIX YOU WERE MISSING)
        # -------------------------
        final_pool.append({
            "survivor": chosen["survivor"],
            "game": game,
            "score": chosen["ownership_score"]
        })

    # =========================
    # STEP 2 — GLOBAL CORE 3 SELECTION (CRITICAL FIX)
    # =========================
    if not final_pool:
        return []

    final_pool.sort(key=lambda x: x["score"], reverse=True)

    top3 = final_pool[:3]

    # =========================
    # STEP 3 — OUTPUT (STRICT 3 ONLY)
    # =========================
    return [
        {
            "rank": i + 1,
            "player": p["survivor"],
            "game": p["game"],
            "score": p["score"],
            "reason": "CORE 3 EVENT OWNERSHIP LOCK"
        }
        for i, p in enumerate(top3)
    ]
