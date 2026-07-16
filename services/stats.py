# services/stats.py

# ==========================================================
# MLB HR BLENDER vFINAL
# HITTER STAT PROFILE ENGINE
#
# Data attachment layer only.
#
# No selections.
# No rankings.
#
# Feeds Gates 1-18
# ==========================================================



def build_hitter_profile(player, stat_data):


    """
    Combines player identity
    with HR finisher metrics.
    """

    return {


        "id":

            player.get(
                "id"
            ),


        "name":

            player.get(
                "name"
            ),


        "player":

            player.get(
                "name"
            ),


        "team":

            player.get(
                "team"
            ),


        "slot":

            player.get(
                "slot"
            ),



        # ======================
        # HR MECHANICS
        # ======================


        "pull":

            stat_data.get(
                "pull"
            ),


        "hard_hit":

            stat_data.get(
                "hard_hit"
            ),


        "barrel":

            stat_data.get(
                "barrel"
            ),


        "ev":

            stat_data.get(
                "ev"
            ),


        "fb":

            stat_data.get(
                "fb"
            ),


        "pua":

            stat_data.get(
                "pua"
            ),


        "pull_barrel":

            stat_data.get(
                "pull_barrel"
            ),



        # ======================
        # CONTACT QUALITY
        # ======================


        "blast":

            stat_data.get(
                "blast"
            ),


        "squared_up":

            stat_data.get(
                "squared_up"
            ),


        "sweet_spot":

            stat_data.get(
                "sweet_spot"
            ),



        # ======================
        # SWING PROFILE
        # ======================


        "bat_speed":

            stat_data.get(
                "bat_speed"
            ),


        "fast_swing":

            stat_data.get(
                "fast_swing"
            ),



        # ======================
        # HR CONVERSION
        # ======================


        "iso":

            stat_data.get(
                "iso"
            ),


        "slg":

            stat_data.get(
                "slg"
            ),


        "woba":

            stat_data.get(
                "woba"
            ),


        "hr_pa":

            stat_data.get(
                "hr_pa"
            )

    }




# ==========================================================
# HR FINISHER CHECK
# ==========================================================


def finisher_profile(player):


    """
    Gate 15 / HR Finisher Identity

    Must meet:

    HR/PA >= .05
    ISO >= .200
    FB >= 30

    """

    hr_pa = player.get(
        "hr_pa"
    )


    iso = player.get(
        "iso"
    )


    fb = player.get(
        "fb"
    )



    if (

        hr_pa is not None

        and iso is not None

        and fb is not None

    ):


        if (

            hr_pa >= .05

            and iso >= .200

            and fb >= 30

        ):

            return True



    # Undefined data does not kill

    return True




# ==========================================================
# DAMAGE SCORE
# ==========================================================


def damage_score(player):


    """
    Gate 6 support

    Uses:

    HH
    EV
    Barrel
    Blast
    Squared Up

    """

    hh = player.get(
        "hard_hit",
        0
    ) or 0


    ev = player.get(
        "ev",
        0
    ) or 0


    barrel = player.get(
        "barrel",
        0
    ) or 0


    blast = player.get(
        "blast",
        0
    ) or 0


    squared = player.get(
        "squared_up",
        0
    ) or 0



    return round(

        (hh * .35)

        +

        (ev * .20)

        +

        (barrel * .20)

        +

        (blast * .15)

        +

        (squared * .10),


        3

    )





# ==========================================================
# CORE PIPELINE CONNECTION
# ==========================================================


def attach_stats(hitters):


    """
    Converts raw lineup hitters
    into Blender hitter profiles.

    Core.py calls this.

    No filtering.
    No picks.
    No rankings.
    """



    updated = []



    for hitter in hitters:


        stat_data = hitter.get(

            "stats",

            {}

        )



        profile = build_hitter_profile(

            hitter,

            stat_data

        )



        updated.append(

            profile

        )



    return updated
