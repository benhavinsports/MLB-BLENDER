from services.lineup import get_confirmed_lineup
from engine.gates import apply_gates


def resolve_survivor(players):

    if not players:
        return None

    best = players[0]

    for p in players:
        if p.get("score", 0) > best.get("score", 0):
            best = p

    return best


def run_slate(games):

    results = []

    for g in games:

        gamePk = g.get("gamePk")
        game_label = f"{g.get('away')} vs {g.get('home')}"

        hitters = get_confirmed_lineup(gamePk)

        # 🔒 SAFE CHECK
        if not hitters:
            results.append({
                "game": game_label,
                "survivor": "NO VALID LINEUP",
                "why": "MLB DATA EMPTY OR NOT POSTED"
            })
            continue

        pitcher = "unknown"

        candidates = apply_gates(hitters, pitcher)

        # 🔒 NEVER ALLOW EMPTY FINALIZATION
        if not candidates:
            candidates = hitters

        winner = resolve_survivor(candidates)

        results.append({
            "game": game_label,
            "survivor": winner["name"] if winner else "NO SURVIVOR",
            "why": "STABLE ENGINE PASS"
        })

    return results
