
from services.mlb_api import get_live_game
from services.statcast import get_batter_statcast
from engine.scorer import hr_score

def run_pipeline(game_pk):
    game = get_live_game(game_pk)

    # simplified hitter extraction placeholder
    hitters = [{"id":"1","name":"Player A"},{"id":"2","name":"Player B"},{"id":"3","name":"Player C"}]

    results = []

    for h in hitters:
        sc = get_batter_statcast(h["id"])

        features = {
            "pull": 60,
            "hh": sc["hh"],
            "barrel": sc["barrel"],
            "ev": sc["ev"],
            "iso": 0.2,
            "matchup": 50,
            "venue": 50
        }

        score = hr_score(features)

        results.append({"name":h["name"],"score":score})

    results = sorted(results, key=lambda x: x["score"], reverse=True)

    # WHO logic
    primary = results[0]
    adjacent = results[1] if len(results)>1 else None
    who = results[1] if len(results)>1 else None

    return {
        "PRIMARY": primary,
        "ADJACENT": adjacent,
        "WHO": who
    }
