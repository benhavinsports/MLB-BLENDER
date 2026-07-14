# engine/decoy.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 10.5 — DECOY TRANSFER ENGINE
#
# Prevents star/chalk bias.
#
# Does not create picks.
# Only modifies ownership priority.
# ==========================================================



def detect_decoy(player):

    """
    Flags obvious public profiles.
    """

    flags = []


    if player.get(
        "hr_total",
        0
    ) >= 30:

        flags.append(
            "HIGH_HR_PROFILE"
        )


    if player.get(
        "public_rating",
        0
    ) >= 90:

        flags.append(
            "PUBLIC_CHALK"
        )


    if player.get(
        "star_flag",
        False
    ):

        flags.append(
            "STAR_PROFILE"
        )


    return flags




# ==========================================================
# EVENT GAP CHECK
# ==========================================================


def close_event_gap(players):

    """
    Checks if survivors are close.

    Transfer only activates when
    multiple real survivors exist.
    """


    if len(players) < 2:

        return False



    scores = []


    for p in players:

        scores.append(

            p.get(
                "gate_score",
                0
            )

        )



    scores.sort(
        reverse=True
    )


    difference = (
        scores[0]
        -
        scores[1]
    )


    if difference <= 10:

        return True


    return False




# ==========================================================
# TRANSFER ENGINE
# ==========================================================


def transfer_event(players):

    """

    If decoy risk exists:

    Move event ownership toward:

    - adjacent hitter
    - protection hitter
    - pressure release hitter


    """


    if not close_event_gap(
        players
    ):

        return players



    for player in players:


        risk = detect_decoy(
            player
        )


        if risk:


            player["decoy_risk"] = True


        else:


            player["decoy_risk"] = False



    return players




# ==========================================================
# FINAL DECOY FILTER
# ==========================================================


def remove_false_chalk(players):


    survivors = []


    for player in players:


        if player.get(
            "decoy_risk",
            False
        ):

            # keep alive but reduce priority

            player["gate_score"] -= 5



        survivors.append(
            player
        )



    return survivors
