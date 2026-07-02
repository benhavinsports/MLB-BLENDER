from services.lineup import get_confirmed_lineup
from services.starter import get_probable_starter
from services.pitcher import get_pitcher_profile
from services.player_map import get_player_name
from engine.gates import apply_elimination_gates


def run_slate(games):

    results = []

    for g in games:

        gamePk = g.get("gamePk")
        label = f"{g.get('away')} vs {g.get('home')}"

        # -------------------------
        # LINEUP
        # -------------------------
        lineup = get_confirmed_lineup(gamePk)

        if not lineup:
            results.append({
                "game": label,
                "survivor": "NO LINEUP DATA YET",
                "why": "MLB FEED NOT POPULATED"
            })
            continue

        # -------------------------
        # STARTER
        # -------------------------
        starters = get_probable_starter(gamePk)
        pitcher_name = starters.get("away") or starters.get("home") or "unknown"

        # -------------------------
        # PITCHER PROFILE
        # -------------------------
        pitcher_profile = get_pitcher_profile(pitcher_name)

        # -------------------------
        # ELIMINATION
        # -------------------------
        survivors = apply_elimination_gates(lineup, pitcher_profile)

        # -------------------------
        # OUTPUT FIX (NAME RESOLUTION)
        # -------------------------
        if not survivors:
            results.append({
                "game": label,
                "survivor": "NO SURVIVOR",
                "why": "ALL PLAYERS ELIMINATED"
            })
            continue

        winner = survivors[0]

        results.append({
            "game": label,
            "survivor": get_player_name(winner["id"]),
            "why": "PURE ELIMINATION ENGINE PASS"
        })

    return results
