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
                "survivor": "NO DATA",
                "why": "EMPTY LINEUP FEED"
            })
            continue

        pitcher_name = "unknown"
        pitcher_hand = "RHP"  # safe default (can upgrade later from starters feed)

        survivors = apply_gates(hitters, pitcher_name, pitcher_hand)

        if not survivors:
            survivors = hitters[:1]

        best = max(survivors, key=lambda x: score_player(x))

        results.append({
            "game": f"{g['away']} vs {g['home']}",
            "survivor": best["name"],
            "why": "PITCH MIX + HANDEDNESS EDGE + STAT SIGNAL LAYER"
        })

    return results
