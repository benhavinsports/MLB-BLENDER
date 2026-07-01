from services.lineup import get_lineup
from engine.gates import apply_gates
from engine.scoring import score_player

def run_slate(games):

    results = []

    for g in games:

        hitters = get_lineup(g["gamePk"])

        if not hitters:
            results.append({
                "game": f"{g['away']} vs {g['home']}",
                "survivor": "DATA UNAVAILABLE",
                "why": "NO VERIFIED LINEUP DATA"
            })
            continue

        survivors = apply_gates(hitters)

        if not survivors:
            results.append({
                "game": f"{g['away']} vs {g['home']}",
                "survivor": "NONE",
                "why": "ALL PLAYERS ELIMINATED"
            })
            continue

        best = max(survivors, key=lambda x: score_player(x))

        results.append({
            "game": f"{g['away']} vs {g['home']}",
            "survivor": best["name"],
            "why": "PASS ALL GATES + BEST EVENT SCORE"
        })

    return results
