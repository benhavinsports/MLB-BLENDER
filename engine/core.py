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

        lineup = normalize_lineup(get_confirmed_lineup(gamePk))

        if not lineup:
            continue

        starters = get_probable_starter(gamePk)
        pitcher = starters.get("away") or starters.get("home")

        if not pitcher:
            continue

        pitcher_profile = get_pitcher_profile(pitcher)

        enriched = apply_elimination_gates(lineup, pitcher_profile)

        if not enriched:
            continue

        # SORT BY FINAL SCORE (REAL BLENDER LOGIC)
        enriched.sort(key=lambda x: x["final_score"], reverse=True)

        winner = enriched[0]

        results.append({
            "game": label,
            "survivor": winner["name"],
            "id": winner["id"],
            "gates": winner["gates"]
        })

    return results
