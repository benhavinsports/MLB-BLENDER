# engine/target_layer.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 0 — TARGET LAYER
#
# Finds HR resistance failure points.
#
# No hitter selection.
# No final picks.
#
# ==========================================================



def rank_offense_targets(games):


    """
    Builds offense vulnerability map.

    Uses pitcher leak scores.

    Higher pitcher leak =
    weaker HR resistance.
    """



    targets = []



    for game in games:



        pitchers = game.get(
            "pitchers",
            []
        )



        if not pitchers:

            continue



        weakest = max(

            pitchers,

            key=lambda x:

                x.get(
                    "leak_score",
                    0
                )

        )



        targets.append({


            "game":

                game,


            "pitcher":

                weakest.get(
                    "name",
                    "UNKNOWN"
                ),


            "leak_score":

                weakest.get(
                    "leak_score",
                    0
                ),


            "side":

                find_attack_side(

                    game,

                    weakest

                )

        })



    return targets





# ==========================================================
# SIDE LOCK
# ==========================================================


def lock_side(target):


    """
    Locks one offense.

    After this point:
    no side flipping.
    """



    return target.get(
        "side"
    )





# ==========================================================
# DETERMINE ATTACK SIDE
# ==========================================================


def find_attack_side(

    game,

    pitcher

):


    """
    Determines which offense receives
    the pitcher weakness lane.

    Uses:

    platoon weakness
    pitcher identity
    matchup side

    """



    weakness = pitcher.get(
        "platoon_weakness"
    )



    if weakness == "LHB_TARGET":


        return {

            "team":

                game.get(
                    "home"
                ),

            "hand":

                "LHB"

        }



    if weakness == "RHB_TARGET":


        return {

            "team":

                game.get(
                    "away"
                ),

            "hand":

                "RHB"

        }



    # Undefined data =
    # pass through


    return {

        "team":

            game.get(
                "home"
            ),

        "hand":

            "NEUTRAL"

    }
