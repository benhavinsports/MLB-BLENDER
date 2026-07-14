# engine/final_lock.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 18 — FINAL HR SURVIVOR LOCK
#
# Output:
# Exactly ONE HR event recipient per game
#
# No:
# - rankings
# - alternates
# - hedges
# - star bias
#
# ==========================================================



def final_lock(game, survivors):


    if not survivors:


        return {

            "game":
                format_game(game),

            "survivor":
                "NONE",

            "why":
                "NO VALID SURVIVOR",

            "status":
                "FAILED"

        }



    # ======================================================
    # FINAL SINGLE OWNER
    # ======================================================

    player = survivors[0]



    return {


        "game":
            format_game(game),


        "survivor":
            player.get(
                "player",
                "UNKNOWN"
            ),


        "team":
            player.get(
                "team",
                "UNKNOWN"
            ),


        "why":
            player.get(
                "event_reason",
                "HR EVENT RECIPIENT"
            ),


        "gate_score":
            player.get(
                "gate_score",
                0
            ),


        "ownership_score":
            player.get(
                "ownership_score",
                0
            ),


        "status":
            "LOCKED"

    }





# ==========================================================
# GAME FORMAT
# ==========================================================


def format_game(game):


    if not game:

        return "UNKNOWN GAME"



    return (

        str(game.get("away", "UNKNOWN"))

        +

        " vs "

        +

        str(game.get("home", "UNKNOWN"))

    )
