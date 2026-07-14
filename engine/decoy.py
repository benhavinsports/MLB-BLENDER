# engine/decoy.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 10.5 / GATE 16
# DECOY TRANSFER ENGINE
#
# Purpose:
# Detect false chalk and transfer HR ownership.
#
# ==========================================================



def transfer_event(
    survivors
):


    """
    Checks if event should transfer.

    Conditions:

    - Multiple survivors
    - Similar event profile
    - Chalk risk present

    """



    if not survivors:

        return []



    if len(survivors) < 2:

        return survivors



    # Sort only for comparison
    # NOT final ranking


    ordered = sorted(

        survivors,

        key=lambda x:

            x.get(
                "ownership_score",
                0
            ),

        reverse=True

    )


    top = ordered[0]

    second = ordered[1]



    gap = abs(

        top.get(
            "ownership_score",
            0
        )

        -

        second.get(
            "ownership_score",
            0
        )

    )



    # ======================================================
    # TRANSFER CONDITION
    # ======================================================


    if gap <= 10:


        second["transfer_flag"] = True


        second["event_reason"] = (

            "Transferred event ownership "

            "through decoy layer"

        )


        return [second]



    return [top]





# ==========================================================
# FALSE CHALK REMOVAL
# ==========================================================


def remove_false_chalk(
    survivors
):


    """
    Removes obvious profiles if:

    - weak ownership
    - only reputation support
    - no event mechanics

    """



    clean = []



    for hitter in survivors:



        damage = hitter.get(

            "damage_score",

            0

        )


        pull = hitter.get(

            "pull"

        )



        hh = hitter.get(

            "hard_hit"

        )



        # Undefined data passes


        if (

            damage == 0

            or

            pull is None

            or

            hh is None

        ):


            clean.append(
                hitter
            )

            continue



        if (

            pull < 55

            and

            hh < 45

        ):


            continue



        clean.append(
            hitter
        )



    return clean
