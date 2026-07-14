# engine/ownership.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 12 — EVENT OWNERSHIP ENGINE
#
# Determines HR event recipient.
#
# No star bias.
# No reputation weighting.
#
# ==========================================================



def assign_event_ownership(
    survivors
):


    """
    Adds ownership score.

    Survivors already passed gates.

    This does NOT create survivors.
    It only measures event ownership.
    """



    for hitter in survivors:


        score = 0



        # ==================================================
        # DAMAGE PRESSURE
        # ==================================================


        score += (

            hitter.get(
                "damage_score",
                0
            )

            *

            0.35

        )



        # ==================================================
        # PULL PATH
        # ==================================================


        pull = hitter.get(
            "pull"
        )


        if pull is not None:


            score += (

                pull

                *

                0.25

            )



        # ==================================================
        # HARD HIT QUALITY
        # ==================================================


        hh = hitter.get(
            "hard_hit"
        )


        if hh is not None:


            score += (

                hh

                *

                0.20

            )



        # ==================================================
        # LINEUP ACCESS
        # ==================================================


        slot = hitter.get(
            "slot",
            9
        )


        if slot <= 5:


            score += 10



        hitter["ownership_score"] = round(

            score,

            3

        )



        hitter["event_reason"] = (

            "HR event ownership: "

            "damage + pull path + opportunity"

        )



    return survivors





# ==========================================================
# GET FINAL EVENT OWNER
# ==========================================================


def get_owner(
    survivors
):


    if not survivors:

        return None



    owner = sorted(

        survivors,

        key=lambda x:

            x.get(
                "ownership_score",
                0
            ),

        reverse=True

    )[0]



    return owner
