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
from services.lineup_normalizer import normalize_lineup

raw_lineup = get_confirmed_lineup(gamePk)
lineup = normalize_lineup(raw_lineup)

        if not lineup:
            results.append({
                "game": label,
                "survivor": "NO LINEUP DATA YET",
                "why": "MLB FEED NOT POPULATED"
            })
            continue

        # -------------------------
        # STARTER (SAFE FIX)
        # -------------------------
        starters = get_probable_starter(gamePk)

        pitcher_name = (
            starters.get("away")
            or starters.get("home")
            or None
        )

        if not pitcher_name:
            results.append({
                "game": label,
                "survivor": "NO PITCHER DATA",
                "why": "STARTER NOT RESOLVED"
            })
            continue

        # -------------------------
        # PITCHER PROFILE (SAFE FIX)
        # -------------------------
        pitcher_profile = get_pitcher_profile(pitcher_name)

        if not pitcher_profile:
            results.append({
                "game": label,
                "survivor": "NO PITCHER DATA",
                "why": "PITCHER PROFILE MISSING"
            })
            continue

        # -------------------------
        # ELIMINATION GATES
        # -------------------------
        survivors = apply_elimination_gates(lineup, pitcher_profile)

        if not survivors:
            results.append({
                "game": label,
                "survivor": "NO SURVIVOR",
                "why": "ALL PLAYERS ELIMINATED"
            })
            continue

        # -------------------------
        # SAFE WINNER SELECTION (FIX)
        # -------------------------
        winner = max(
            survivors,
            key=lambda x: x.get("score", 0)
        )

        # -------------------------
        # OUTPUT
        # -------------------------
        results.append({
            "game": label,
            "survivor": get_player_name(winner["id"]),
            "why": "PURE ELIMINATION ENGINE PASS"
        })

    return results
