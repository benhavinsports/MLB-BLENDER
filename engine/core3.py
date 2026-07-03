from collections import defaultdict


def build_core3(results):
    """
    CORE 3 v2 — EVENT OWNERSHIP ENGINE (FIXED)

    PURPOSE:
    - NOT ranking hitters
    - NOT slicing lists
    - NOT guessing

    IT RESOLVES:
    WHO RECEIVES THE HR EVENT PER GAME
    """

    if not results:
        return []

    # -------------------------
    # GROUP BY GAME
    # -------------------------
    games = defaultdict(list)

    for r in results:
        if not r.get("survivor"):
            continue

        games[r["game"]].append(r)

    final = []

    # -------------------------
    # PROCESS EACH GAME
    # -------------------------
    for game, players in games.items():

        if len(players) == 0:
            continue

        # =========================
        # STEP 1 — EXTRACT TRUE EVENT SIGNAL
        # =========================
        def ownership_score(p):
            gates = p.get("gates", [])

            score = 0

            for g in gates:

                # HARD PASS SIGNALS ONLY
                if isinstance(g, dict):

                    if g.get("pass") is True:
                        score += 1

                    # reward high-impact gates
                    if g.get("gate") in [4, 6, 12, 15, 18]:
                        score += (g.get("score", 0) or 0)

            return score

        # compute ownership
        for p in players:
            p["ownership_score"] = ownership_score(p)

        # =========================
        # STEP 2 — SORT BY EVENT OWNERSHIP
        # =========================
        players.sort(key=lambda x: x["ownership_score"], reverse=True)

        # strongest event receiver
        primary = players[0]

        # =========================
        # STEP 3 — DECOY COLLISION RESOLUTION
        # =========================
        if len(players) > 1:

            second = players[1]

            gap = abs(primary["ownership_score"] - second["ownership_score"])

            # if too close → event shifts (your 10.5 logic)
            if gap <= 1.0:
                chosen = second
            else:
                chosen = primary
        else:
            chosen = primary

        # =========================
        # STEP 4 — FINAL LOCK (STRICT 1 PER GAME)
        # =========================
        final.append({
            "rank": len(final) + 1,
            "player": chosen["survivor"],
            "game": game,
            "reason": "EVENT OWNERSHIP RESOLVED",
            "ownership_score": chosen["ownership_score"]
        })

    # -------------------------
    # FINAL SAFETY: 1 PER GAME ONLY
    # -------------------------
    final.sort(key=lambda x: x["game"])

    return final
