# engine/ownership.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 12 — EVENT OWNERSHIP ENGINE
#
# Determines the most likely HR event recipient.
#
# NOT:
# - best hitter
# - biggest name
# - highest HR total
#
# ONLY:
# Who owns the mistake pitch?
# ==========================================================



def calculate_ownership_score(player):

    """
    Ownership combines:

    Pitch matchup
    Weak slot match
    Hitter archetype
    HR model
    Gate survival

    Alignment =
    Pitcher Weakness
    + Weak Slot Match
    + Hitter Archetype
    + HR Model
    + Gate Score

    """

    pitcher_weakness = player.get(
        "pitcher_weakness_match",
        0
    )


    weak_slot = player.get(
        "slot_match",
        0
    )


    archetype = player.get(
        "archetype_score",
        0
    )


    hr_model = player.get(
        "hr_model_score",
        0
    )


    gate_score = player.get(
        "gate_score",
        0
    )


    ownership = (

        pitcher_weakness * .30

        +

        weak_slot * .25

        +

        archetype * .20

        +

        hr_model * .15

        +

        gate_score * .10

    )


    return round(
        ownership,
        3
    )




# ==========================================================
# OWNERSHIP BUILD
# ==========================================================


def assign_event_ownership(players):


    """

    Every survivor receives
    an event ownership score.

    No ranking changes after
    Final Isolation.

    """


    output = []


    for player in players:


        player["ownership_score"] = (
            calculate_ownership_score(
                player
            )
        )


        output.append(
            player
        )


    return output




# ==========================================================
# FINAL OWNERSHIP CHECK
# ==========================================================


def get_owner(players):


    """

    Returns the player with
    strongest HR event ownership.

    No name bias.

    """


    if not players:

        return None



    owner = max(

        players,

        key=lambda x:
            x.get(
                "ownership_score",
                0
            )

    )


    return owner
