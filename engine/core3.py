from collections import defaultdict


def build_core3(results):
    """
    CORE 3 v2 — EVENT OWNERSHIP ENGINE

    PURPOSE:
    Assign HR event recipients per game using:
    - gate survivors
    - pitcher leak environment
    - decoy transfer logic
    - adjacency inheritance rules

    NO SCORE RANKING
    NO TOP PLAYERS
    ONLY EVENT ASSIGNMENT
    """

    if not results:
        return []

    # -------------------------
    # GROUP BY GAME
    # -------------------------
    game_map = defaultdict(list)

    for r in results:
        if r.get("survivor") in [
            "NO LINEUP DATA YET",
            "NO SURVIVOR",
            "NO PITCHER DATA",
            None
        ]:
            continue

        game_map[r["game"]].append(r)

    core3 = []

    # -------------------------
    # PROCESS EACH GAME INDEPENDENTLY
    # -------------------------
    for game, players in game_map.items():

        if not players:
            continue

        # -------------------------
        # STEP 1 — IDENTIFY EVENT LANE CANDIDATES
        # -------------------------
        # These are all valid gate survivors for this game
        candidates = players

        # -------------------------
        # STEP 2 — CHECK DECOY RISK
        # -------------------------
        # If multiple strong candidates exist, avoid obvious chalk pick

        def decoy_score(p):
            why = str(p.get("why", "")).lower()

            score = 0

            # simple proxies for "chalk / obvious"
            if "top order" in why:
                score += 1
            if "exploit" in why:
                score += 1
            if "pass" in why:
                score += 1

            return score

        # sort by decoy risk (LOW risk preferred)
        candidates.sort(key=lambda x: decoy_score(x))

        # -------------------------
        # STEP 3 — EVENT OWNERSHIP SELECTION
        # -------------------------
        # NOT highest score — lowest "visibility bias"

        chosen = candidates[0]

        # -------------------------
        # STEP 4 — ADJACENCY TRANSFER CHECK
        # -------------------------
        # If multiple similar candidates exist, allow transfer

        if len(candidates) > 1:

            gap = abs(
                decoy_score(candidates[0]) - decoy_score(candidates[1])
            )

            # transfer condition (your rule)
            if gap <= 1:
                # shift ownership to "less obvious" hitter
                chosen = candidates[1]

        # -------------------------
        # STEP 5 — FINAL LOCK
        # -------------------------
        core3.append({
            "rank": len(core3) + 1,
            "player": chosen.get("survivor"),
            "game": game,
            "reason": chosen.get("why", "EVENT OWNERSHIP LOCK")
        })

        # enforce 1 per game (your rule)
        if len(core3) >= len(game_map):
            break

    # -------------------------
    # FINAL SAFETY SORT (NOT SCORING — JUST STABILITY)
    # -------------------------
    core3.sort(key=lambda x: x["game"])

    return core3
