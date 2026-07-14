# services/pitchers.py

# ==========================================================
# MLB HR BLENDER vFINAL
# PITCHER TARGET LAYER
#
# Finds HR vulnerability.
# Does NOT pick hitters.
# ==========================================================


def calculate_leak_score(pitcher):

    """
    Gate 0 Leak Score

    Formula:

    HR/9 × .25
    Barrel Allowed × .25
    xwOBA Allowed × .20
    Hard Hit Allowed × .15
    Pitch Predictability × .15

    """

    hr9 = pitcher.get(
        "hr9",
        0
    )

    barrel = pitcher.get(
        "barrel_allowed",
        0
    )

    xwoba = pitcher.get(
        "xwoba_allowed",
        0
    )

    hard_hit = pitcher.get(
        "hard_hit_allowed",
        0
    )

    predictability = pitcher.get(
        "pitch_predictability",
        0
    )


    score = (

        hr9 * .25

        +

        barrel * .25

        +

        xwoba * .20

        +

        hard_hit * .15

        +

        predictability * .15

    )


    return round(
        score,
        3
    )



# ==========================================================
# BUILD PITCHER CARD
# ==========================================================


def build_pitcher_card(pitcher):


    return {


        "name":
            pitcher.get(
                "name"
            ),


        "hand":
            pitcher.get(
                "hand"
            ),


        "hr9":
            pitcher.get(
                "hr9",
                0
            ),


        "barrel_allowed":
            pitcher.get(
                "barrel_allowed",
                0
            ),


        "xwoba_allowed":
            pitcher.get(
                "xwoba_allowed",
                0
            ),


        "hard_hit_allowed":
            pitcher.get(
                "hard_hit_allowed",
                0
            ),


        "pitch_predictability":
            pitcher.get(
                "pitch_predictability",
                0
            ),


        "leak_score":
            calculate_leak_score(
                pitcher
            )

    }



# ==========================================================
# TARGET MAP
# ==========================================================


def rank_pitchers(pitchers):


    cards = []


    for pitcher in pitchers:

        cards.append(
            build_pitcher_card(
                pitcher
            )
        )



    return sorted(

        cards,

        key=lambda x:
            x["leak_score"],

        reverse=True

    )
