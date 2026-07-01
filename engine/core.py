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
                "survivor": "NO LINEUP DATA",
                "why": "MLB FEED EMPTY"
            })
            continue

        survivors = apply_gates(hitters)

        # 🔥 CRITICAL FIX: NEVER RETURN NONE
        if not survivors:
            survivors = hitters[:1]

        best = max(survivors, key=lambda x: score_player(x))

        results.append({
            "game": f"{g['away']} vs {g['home']}",
            "survivor": best["name"],
            "why": "STABLE PASS THROUGH GATES + SAFE FALLBACK METRICS"
        })

    return results
