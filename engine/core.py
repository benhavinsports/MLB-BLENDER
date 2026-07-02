from services.lineup import project_lineup
from services.pitcher import pitcher_strength


def run_slate(games):

    results = []

    # fake player pool placeholder (replace with your player_map later)
    player_pool = [
        "player_a",
        "player_b",
        "player_c",
        "player_d",
        "player_e"
    ]

    for g in games:

        away_pitcher = g.get("away_pitcher")
        home_pitcher = g.get("home_pitcher")

        pitcher_factor = (
            pitcher_strength(away_pitcher) +
            pitcher_strength(home_pitcher)
        ) / 2

        lineup = project_lineup(g, player_pool)

        # APPLY MATCHUP FILTERING (THIS IS YOUR REAL CORE LOGIC)
        scored = []

        for item in lineup:

            score = item["role_score"] * (1 + pitcher_factor)

            scored.append({
                "player": item["player"],
                "score": score
            })

        scored.sort(key=lambda x: x["score"], reverse=True)

        # CORE SURVIVOR (REAL PICK)
        survivor = scored[0]["player"] if scored else None

        results.append({
            "game": g["game"],
            "survivor": survivor,
            "why": "ROLE + PITCHER MATCHUP ENGINE PASS"
        })

    return results
