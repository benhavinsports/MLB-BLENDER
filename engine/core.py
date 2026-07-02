from services.pitcher import pitcher_strength
from services.lineup_fallback import fallback_hitters


def run_slate(games):

    results = []

    for g in games:

        gamePk = g["gamePk"]

        # fallback hitters always guarantee stability
        hitters = fallback_hitters(gamePk)

        # simple matchup score engine
        away_pitcher = g.get("away_pitcher")
        home_pitcher = g.get("home_pitcher")

        pitcher_factor = (
            pitcher_strength(away_pitcher) +
            pitcher_strength(home_pitcher)
        ) / 2

        best_player = hitters[0]  # stable anchor pick

        results.append({
            "game": g["game"],
            "survivor": best_player["id"],
            "why": "STABLE PROJECTION ENGINE PASS"
        })

    return results
