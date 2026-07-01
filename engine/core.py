from services.lineup import get_confirmed_lineup
from services.starter import get_probable_starter
from services.pitcher import get_pitcher_profile
from engine.gates import apply_elimination_gates


def run_slate(games):

    results = []

    for g in games:

        gamePk = g.get("gamePk")
        label = f"{g.get('away')} vs {g.get('home')}"

        lineup = get_confirmed_lineup(gamePk)

        if not lineup:
            results.append({
                "game": label,
                "survivor": "NO VALID LINEUP",
                "why": "MLB DATA EMPTY OR NOT POSTED"
            })
            continue

        starters = get_probable_starter(gamePk)

        pitcher_name = starters.get("away") or starters.get("home")

        pitcher_profile = get_pitcher_profile(pitcher_name)

        survivors = apply_elimination_gates(lineup, pitcher_profile)

        if len(survivors) == 0:
            winner = None
        else:
            winner = survivors[0]

        results.append({
            "game": label,
            "survivor": winner["id"] if winner else "NO SURVIVOR",
            "why": "PURE ELIMINATION ENGINE PASS"
        })

    return results
