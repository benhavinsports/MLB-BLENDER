# services/output.py


# ==========================================================
# MLB HR BLENDER vFINAL
# OUTPUT FORMATTER
# ==========================================================


def build_core3(results):

    """
    Takes final Blender results.

    Returns first 3 locked survivors.

    No ranking.
    No player selection.
    No changes.
    """

    core3 = []


    for result in results:


        survivor = result.get(
            "survivor"
        )


        if not survivor:
            continue


        if survivor == "NO SURVIVOR":
            continue


        core3.append({

            "player":
                survivor,


            "game":
                result.get(
                    "game",
                    "UNKNOWN"
                ),


            "status":
                "CORE 3 EVENT LOCK"

        })



        if len(core3) == 3:

            break



    return core3
