# engine/final_lock.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 18 — FINAL HR SURVIVOR LOCK
#
# Final output layer.
#
# Rule:
# Exactly ONE hitter per game.
#
# No:
# - Top 3
# - Rankings
# - Alternates
# - Hedge picks
#
# ==========================================================



def final_lock(
    survivors,
    game
):


    """
    Final event ownership lock.

    Input:
        survivors after all gates

    Output:
        single locked HR recipient
    """



    if not survivors:


        return {

            "game":

                game_name(game),


            "survivor":

                "NONE",


            "why":

                "NO VALID SURVIVOR",


            "status":

                "FAILED"

        }



    # ======================================================
    # FINAL EVENT OWNERSHIP FILTER
    #
    # No star bias.
    # No name value.
    #
    # Uses accumulated gate score.
    # ======================================================


    locked = sorted(

        survivors,

        key=lambda x:

            x.get(
                "gate_score",
                0
            ),

        reverse=True

    )[0]



    return {


        "game":

            game_name(
                game
            ),


        "survivor":

            locked.get(
                "player",
                "UNKNOWN"
            ),


        "team":

            locked.get(
                "team",
                "UNKNOWN"
            ),


        "why":

            locked.get(
                "event_reason",
                "HR EVENT RECIPIENT"
            ),


        "gate_score":

            locked.get(
                "gate_score",
                0
            ),


        "status":

            "LOCKED"

    }





# ==========================================================
# GAME FORMATTER
# ==========================================================


def game_name(game):


    if not game:

        return "UNKNOWN GAME"



    away = game.get(
        "away",
        "UNKNOWN"
    )


    home = game.get(
        "home",
        "UNKNOWN"
    )


    return f"{away} vs {home}"
