from services.lineup import get_confirmed_lineup
from services.starter import get_probable_starter
from services.pitcher import get_pitcher_profile
from services.player_map import get_player_name
from engine.gates import apply_elimination_gates
from services.lineup_normalizer import normalize_lineup


def run_slate(games):

    results = []

    for g in games:

        gamePk = g.get("gamePk")
        label = f"{g.get('away')} vs {g.get('home')}"

        # -------------------------
        # LINEUP
        # -------------------------
        raw_lineup = get_confirmed_lineup(gamePk)
        lineup = normalize_lineup(raw_lineup)

        if not lineup:
            results.append({
                "game": label,
                "survivor": "NO LINEUP DATA",
                "why": "EMPTY LINEUP"
            })
            continue

        # -------------------------
        # PITCHER
        # -------------------------
        starters = get_probable_starter(gamePk)

        pitcher_name = starters.get("away") or starters.get("home")

        if not pitcher_name:
            results.append({
                "game": label,
                "survivor": "NO PITCHER",
                "why": "NO STARTER FOUND"
            })
            continue

        pitcher_profile = get_pitcher_profile(pitcher_name)

        # -------------------------
        # TRUE GATE ENGINE
        # -------------------------
        survivors = apply_elimination_gates(lineup, pitcher_profile)

        if not survivors:
            results.append({
                "game": label,
                "survivor": "NO SURVIVOR",
                "why": "ALL ELIMINATED"
            })
            continue

        # -------------------------
        # GAME WINNER = FIRST SURVIVOR (NO SCORING)
        # -------------------------
        winner = survivors[0]

        results.append({
            "game": label,
            "survivor": get_player_name(winner["id"]),
            "why": winner["gate_history"]
        })

    return results
