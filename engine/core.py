from services.lineup import get_confirmed_lineup
from services.starter import get_probable_starter
from engine.gates import apply_gates
from engine.scoring import score_player


def run_slate(games):

    results = []

    processed_games = set()

    for g in games:

        gamePk = g["gamePk"]

        # 🔒 ISOLATION LOCK
        if gamePk in processed_games:
            continue

        processed_games.add(gamePk)

        # 🔥 STRICT LINEUP ONLY
        hitters = get_confirmed_lineup(gamePk)
        starters = get_probable_starter(gamePk)

        if not hitters:
            results.append({
                "game": f"{g['away']} vs {g['home']}",
                "survivor": "NO VALID LINEUP",
                "why": "LINEUP INTEGRITY FAIL"
            })
            continue

        pitcher = starters.get("away", "unknown")

        candidates = apply_gates(hitters, pitcher)

        if not candidates:
            candidates = hitters[:1]

        best = max(candidates, key=lambda x: score_player(x))

        results.append({
            "game": f"{g['away']} vs {g['home']}",
            "survivor": best["name"],
            "why": "LINEUP INTEGRITY LOCK + ISOLATED CORE ENGINE"
        })

    return results
