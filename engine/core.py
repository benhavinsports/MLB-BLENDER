from services.lineup import get_confirmed_lineup
from services.starter import get_probable_starter
from services.pitcher import get_pitcher_profile
from engine.gates import apply_elimination_gates


def run_slate(games):

    results = []

    for g in games:

        gamePk = g.get("gamePk")
        label = f"{g.get('away')} vs {g.get('home')}"

        # -------------------------
        # STEP 1: LINEUP
        # -------------------------
        lineup = get_confirmed_lineup(gamePk)

        if lineup is None:
            lineup = []

        # -------------------------
        # SAFE HANDLING (NO GAME DROP)
        # -------------------------
        if len(lineup) == 0:
            results.append({
                "game": label,
                "survivor": "NO LINEUP DATA YET",
                "why": "MLB FEED NOT POPULATED (STABLE MODE)"
            })
            continue

        # -------------------------
        # STEP 2: STARTER
        # -------------------------
        starters = get_probable_starter(gamePk)

        pitcher_name = starters.get("away") or starters.get("home") or "unknown"

        # -------------------------
        # STEP 3: PITCHER PROFILE
        # -------------------------
        pitcher_profile = get_pitcher_profile(pitcher_name)

        # -------------------------
        # STEP 4: ELIMINATION ENGINE
        # -------------------------
        survivors = apply_elimination_gates(lineup, pitcher_profile)

        # -------------------------
        # STEP 5: FINAL OUTPUT
        # -------------------------
        if len(survivors) == 0:
            results.append({
                "game": label,
                "survivor": "NO SURVIVOR",
                "why": "ALL PLAYERS ELIMINATED"
            })
        else:
            results.append({
                "game": label,
                "survivor": survivors[0]["id"],
                "why": "PURE ELIMINATION ENGINE PASS"
            })

    return results
