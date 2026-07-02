from services.lineup_fallback import fallback_hitters
from services.slate_projection import get_mlb_pregame_slate


def get_hitters_safe(gamePk, get_confirmed_lineup):

    hitters = get_confirmed_lineup(gamePk)

    if not hitters:
        hitters = fallback_hitters(gamePk)

    return hitters


def run_slate(games, get_confirmed_lineup):

    results = []

    for g in games:

        gamePk = g["gamePk"]

        hitters = get_hitters_safe(gamePk, get_confirmed_lineup)

        # SIMPLE SURVIVOR LOGIC (keeps your system alive)
        survivor = hitters[0] if hitters else None

        if survivor:
            results.append({
                "game": g["game"],
                "survivor": survivor["id"],
                "why": "PURE ELIMINATION ENGINE PASS"
            })
        else:
            results.append({
                "game": g["game"],
                "survivor": "EMPTY",
                "why": "NO DATA"
            })

    return results
