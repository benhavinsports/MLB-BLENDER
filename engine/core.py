# engine/core.py

# ==========================================================
# MLB HR BLENDER vFINAL
# MAIN ENGINE CONTROLLER
# ==========================================================

from engine.target_layer import build_target_map
from engine.gates import run_all_gates

from services.lineup import get_game_lineup
from services.stats import attach_stats



# ==========================================================
# RUN FULL SLATE
# ==========================================================

def run_blender(games):

    results = []


    # Gate 0
    targets = build_target_map(
        games
    )


    for game in games:


        result = process_game(
            game,
            targets
        )


        results.append(
            result
        )


    return results




# ==========================================================
# SINGLE GAME PIPELINE
# ==========================================================

def process_game(game, targets):


    game_name = (
        f"{game['away']} vs {game['home']}"
    )


    # ----------------------------------
    # FIND TARGET SIDE
    # ----------------------------------

    target = next(

        (
            t
            for t in targets
            if t["game"] == game_name
        ),

        None

    )



    if not target:

        return {

            "game":
                game_name,

            "survivor":
                "NO TARGET",

            "status":
                "FAILED"

        }



    # ----------------------------------
    # BUILD HITTER POOL
    # ----------------------------------

    hitters = get_game_lineup(
        game
    )


    # ----------------------------------
    # ATTACH PLAYER DATA
    # ----------------------------------

    hitters = attach_stats(
        hitters
    )



    # ----------------------------------
    # LOCK TARGET OFFENSE
    # ----------------------------------

    hitters = [

        h

        for h in hitters

        if h.get("team")
        == target["target_offense"]

    ]



    # ----------------------------------
    # RUN GATES 1-18
    # ----------------------------------

    winner, audit = run_all_gates(
        hitters
    )



    if winner:


        survivor = winner.get(
            "name",
            "UNKNOWN"
        )


    else:

        survivor = "NO SURVIVOR"



    return {


        "game":
            game_name,


        "survivor":
            survivor,


        "status":
            "LOCKED",


        "target":
            target,


        "audit":
            audit

    }
