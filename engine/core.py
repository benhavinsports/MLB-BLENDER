from services.lineup import get_confirmed_lineup
from engine.gates import apply_elimination_gates


def run_slate(games):

    results = []

    for g in games:

        gamePk = g.get("gamePk")
        label = f"{g.get('away')} vs {g.get('home')}"

        # -----------------------------
        # STEP 1 — GET LINEUP
        # -----------------------------
        lineup = get_confirmed_lineup(gamePk)

        # HARD STOP ONLY IF API FAILS
        if lineup is None:
            results.append({
                "game": label,
                "survivor": "NO VALID LINEUP",
                "why": "MLB DATA MISSING"
            })
            continue

        if len(lineup) == 0:
            results.append({
                "game": label,
                "survivor": "NO VALID LINEUP",
                "why": "MLB DATA EMPTY OR NOT POSTED"
            })
            continue

        # -----------------------------
        # STEP 2 — PURE ELIMINATION GATES
        # -----------------------------
        survivors = apply_elimination_gates(lineup)

        # -----------------------------
        # STEP 3 — FINAL SURVIVOR RULE
        # -----------------------------
        if len(survivors) == 1:
            winner = survivors[0]

        elif len(survivors) > 1:
            # PURE ELIMINATION RULE:
            # no scoring, just deterministic pick = first in order
            winner = survivors[0]

        else:
            winner = None

        results.append({
            "game": label,
            "survivor": winner["name"] if winner else "NO SURVIVOR",
            "why": "PURE ELIMINATION ENGINE PASS"
        })

    return results
