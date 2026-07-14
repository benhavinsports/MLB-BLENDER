# engine/target_layer.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 0 — TARGET LAYER
#
# Finds weakest HR resistance point.
#
# Does NOT select hitters.
# Does NOT rank stars.
#
# Output:
# One offense target
# ==========================================================


def rank_offense_targets(games):

    """
    Receives games with pitcher cards attached.

    Finds the offense facing the weaker
    HR resistance profile.
    """

    targets = []


    for game in games:


        away_pitcher = game.get(
            "away_pitcher_card",
            {}
        )


        home_pitcher = game.get(
            "home_pitcher_card",
            {}
        )


        away_leak = away_pitcher.get(
            "leak_score",
            0
        )


        home_leak = home_pitcher.get(
            "leak_score",
            0
        )


        # Higher pitcher leak =
        # weaker HR resistance


        if away_leak > home_leak:


            targets.append({

                "game_id":
                    game.get(
                        "game_id"
                    ),

                "team":
                    game.get(
                        "home"
                    ),

                "pitcher":
                    away_pitcher.get(
                        "name"
                    ),

                "leak_score":
                    away_leak

            })


        else:


            targets.append({

                "game_id":
                    game.get(
                        "game_id"
                    ),

                "team":
                    game.get(
                        "away"
                    ),

                "pitcher":
                    home_pitcher.get(
                        "name"
                    ),

                "leak_score":
                    home_leak

            })


    return targets



# ==========================================================
# SIDE LOCK
# ==========================================================


def lock_side(target):


    """
    Gate 0 rule:

    ONE offense only.

    No side flipping later.
    """


    return {

        "locked_team":
            target.get(
                "team"
            ),

        "target_pitcher":
            target.get(
                "pitcher"
            ),

        "leak_score":
            target.get(
                "leak_score"
            )

    }
