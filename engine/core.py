# engine/core.py

# ==========================================================
# MLB HR BLENDER vFINAL
# TRUE EVENT ENGINE CONTROLLER
#
# ONE PIPELINE ONLY
#
# app.py
#   ↓
# services/slate.py
#   ↓
# engine/core.py
#   ↓
# Gate 0-18
#   ↓
# final survivors
#
# ==========================================================


from engine.target_layer import (
    rank_offense_targets,
    lock_side
)

from engine.decoy import (
    transfer_event,
    remove_false_chalk
)

from engine.ownership import (
    assign_event_ownership,
    get_owner
)

from engine.final_lock import (
    final_lock
)

from engine.gates import (
    run_all_gates
)

from services.lineups import (
    build_game_pool
)

from services.stats import (
    attach_stats
)

from services.pitchers import (
    build_pitcher_card
)

from services.environment import (
    build_environment_card
)

from services.bullpen import (
    build_bullpen_card
)


# ==========================================================
# GAME PREPARATION
# ==========================================================

def prepare_game(game):

    """
    Builds supporting data layers.

    No picks happen here.
    Data only.
    """

    game["environment"] = (
        build_environment_card(
            game
        )
    )


    # --------------------------
    # Pitcher cards
    # --------------------------

    pitchers = []


    if game.get("away_pitcher"):

        pitchers.append(

            build_pitcher_card(
                game["away_pitcher"]
            )

        )


    if game.get("home_pitcher"):

        pitchers.append(

            build_pitcher_card(
                game["home_pitcher"]
            )

        )


    game["pitchers"] = pitchers



    # --------------------------
    # Bullpens
    # --------------------------

    game["away_bullpen"] = (

        build_bullpen_card(

            game.get(
                "away_bullpen",
                {}
            )

        )

    )


    game["home_bullpen"] = (

        build_bullpen_card(

            game.get(
                "home_bullpen",
                {}
            )

        )

    )


    return game



# ==========================================================
# MAIN BLENDER ENGINE
# ==========================================================

def run_blender(games):


    results = []



    for raw_game in games:



        game = prepare_game(
            raw_game
        )



        # ==================================================
        # GATE 0
        # TARGET LAYER
        # ==================================================

        targets = rank_offense_targets(
            [game]
        )


        if not targets:

            continue



        locked_side = lock_side(
            targets[0]
        )



        # ==================================================
        # GATE 2
        # CONFIRMED HITTER POOL
        # ==================================================

        hitters = build_game_pool(
            game
        )


        hitters = attach_stats(
            hitters
        )



        if not hitters:


            results.append({

                "game":
                    f"{game['away']} vs {game['home']}",

                "survivor":
                    "NO SURVIVOR",

                "why":
                    "NO CONFIRMED HITTER POOL",

                "status":
                    "FAILED"

            })


            continue



        # ==================================================
        # GATE 1-18
        # ==================================================

        survivors, audit = run_all_gates(

            hitters,

            game,

            locked_side

        )



        if not survivors:


            results.append({

                "game":
                    f"{game['away']} vs {game['home']}",

                "survivor":
                    "NO SURVIVOR",

                "why":
                    "ALL PLAYERS ELIMINATED",

                "status":
                    "FAILED",

                "audit":
                    audit

            })


            continue



        # ==================================================
        # GATE 10.5
        # DECOY TRANSFER
        # ==================================================

        survivors = transfer_event(
            survivors
        )


        survivors = remove_false_chalk(
            survivors
        )



        # ==================================================
        # GATE 12
        # EVENT OWNERSHIP
        # ==================================================

        survivors = assign_event_ownership(
            survivors
        )


        owner = get_owner(
            survivors
        )



        # ==================================================
        # GATE 18
        # FINAL LOCK
        # ==================================================

        if owner:


            final = final_lock(

                game,

                [owner]

            )


        else:


            final = {

                "game":
                    f"{game['away']} vs {game['home']}",

                "survivor":
                    "NO SURVIVOR",

                "why":
                    "NO EVENT OWNER",

                "status":
                    "FAILED"

            }



        final["audit"] = audit

        final["target_side"] = locked_side



        results.append(
            final
        )



    return results
