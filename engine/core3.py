from collections import defaultdict


def build_core3(results):
    """
    CORE 3 v3 — EVENT OWNERSHIP ENGINE

    PURPOSE:
    Assign EXACT HR event recipient per game using:
    - gate survivors
    - matchup context
    - decoy suppression
    - adjacency transfer logic
    """

    if not results:
        return []

    # -------------------------
    # GROUP BY GAME
    # -------------------------
    games = defaultdict(list)

    for r in results:
        if r.get("survivor") in [
            "NO LINEUP DATA YET",
            "NO SURVIVOR",
            "NO PITCHER DATA",
            None
        ]:
            continue

        games[r["game"]].append(r)

    final = []

    # -------------------------
    # PROCESS EACH GAME
    # -------------------------
    for game, players in games.items():

        if not players:
            continue

        # -------------------------
        # STEP 1 — EVENT LANE SCORING (NOT RANKING PLAYERS)
        # -------------------------
        def event_lane_score(p):
            score = 0

            why = str(p.get("why", "")).lower()

            # gate strength signals (soft interpretation)
            if "top order" in why:
                score += 1
            if "exploit" in why:
                score += 2
            if "pass" in why:
                score += 1

            return score

        for p in players:
            p["event_score"] = event_lane_score(p)

        # -------------------------
        # STEP 2 — DECOY RISK DETECTION
        # -------------------------
        players.sort(key=lambda x: x["event_score"])

        # lowest visibility bias = best event recipient candidate
        base = players[0]

        # -------------------------
        # STEP 3 — TRANSFER ENGINE (YOUR GATE 10.5 LOGIC)
        # -------------------------
        if len(players) > 1:

            next_p = players[1]

            gap = abs(base["event_score"] - next_p["event_score"])

            # if too similar → transfer event away from obvious chalk
            if gap <= 1:
                chosen = next_p
            else:
                chosen = base
        else:
            chosen = base

        # -------------------------
        # STEP 4 — FINAL EVENT LOCK
        # -------------------------
        final.append({
            "rank": len(final) + 1,
            "player": chosen.get("survivor"),
            "game": game,
            "reason": "HR EVENT RECIPIENT ASSIGNED"
        })

        # enforce 1 per game
        if len(final) >= len(games):
            break

    # stable ordering
    final.sort(key=lambda x: x["game"])

    return final
