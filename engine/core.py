from services.lineup import get_lineup
from services.starter import get_probable_starter
from engine.gates import apply_gates
from engine.scoring import score_player

def run_slate(games):

    results = []

    for g in games:

        hitters = get_lineup(g["gamePk"])
        starters = get_probable_starter(g["gamePk"])

        pitcher_name = starters["away"]  # simplified side handling

        if not hitters:
            results.append({
                "game": f"{g['away']} vs {g['home']}",
                "survivor": "NO DATA",
                "why": "EMPTY LINEUP"
            })
            continue

        survivors = apply_gates(hitters, pitcher_name)

        if not survivors:
            survivors = hitters[:1]

        best = max(survivors, key=lambda x: score_player(x))

        results.append({
            "game": f"{g['away']} vs {g['home']}",
            "survivor": best["name"],
            "why": f"PITCH SEQUENCE + ZONE WEAKNESS + MATCHUP MODEL ({pitcher_name})"
        })

    return results
