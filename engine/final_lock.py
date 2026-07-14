# engine/final_lock.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 18 — FINAL SURVIVOR LOCK
#
# Final output enforcement.
#
# One game = one HR recipient
#
# No:
# - rankings
# - alternates
# - backups
# - top plays
#
# ==========================================================



def final_lock(game, players):


    """
    Receives only final survivors.

    Selects the single owner
    of the HR event.
    """


    if not players:


        return {


            "game":

                f"{game.get('away')} vs {game.get('home')}",


            "survivor":

                "NONE",


            "why":

                "NO SURVIVOR PASSED FINAL AUDIT",


            "status":

                "FAILED"

        }



    survivor = max(


        players,


        key=lambda x:

            x.get(

                "ownership_score",

                0

            )


    )



    return {


        "game":

            f"{game.get('away')} vs {game.get('home')}",



        "survivor":

            survivor.get(

                "name",

                "UNKNOWN"

            ),



        "team":

            survivor.get(

                "team",

                "UNKNOWN"

            ),



        "why":

            "HR EVENT RECIPIENT AFTER OWNERSHIP AUDIT",



        "status":

            "LOCKED"


    }




# ==========================================================
# CORE 3 BUILDER
# ==========================================================


def build_core3(results):


    """
    Final 3 games only.

    No reranking.

    Uses Blender output order.
    """


    core = []


    for result in results[:3]:


        core.append(

            result

        )


    return core
