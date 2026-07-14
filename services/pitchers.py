# services/pitchers.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 0 — PITCHER LEAK MAP
#
# Purpose:
# Find where HR resistance breaks.
#
# Does NOT select hitters.
# Does NOT select teams.
#
# Outputs pitcher vulnerability profile.
# ==========================================================



def build_pitcher_card(pitcher):

    """
    Creates standardized pitcher weakness profile.

    Input:
    {
        name,
        hr9,
        barrel_allowed,
        xwoba_allowed,
        hard_hit_allowed,
        k_rate,
        pitch_mix,
        platoon_splits
    }

    """

    if pitcher is None:

        return {

            "name": "UNKNOWN",

            "leak_score": 0,

            "status": "NO DATA"

        }



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


    k_rate = pitcher.get(
        "k_rate",
        0
    )



    predictability = (
        pitch_predictability(
            pitcher.get(
                "pitch_mix",
                {}
            )
        )
    )


    platoon = (
        platoon_weakness(
            pitcher.get(
                "platoon_splits",
                {}
            )
        )
    )



    leak_score = calculate_leak_score(

        hr9,

        barrel,

        xwoba,

        hard_hit,

        k_rate,

        predictability

    )



    return {


        "name":

            pitcher.get(
                "name",
                "UNKNOWN"
            ),



        "hr9":

            hr9,



        "barrel_allowed":

            barrel,



        "xwoba_allowed":

            xwoba,



        "hard_hit_allowed":

            hard_hit,



        "k_rate":

            k_rate,



        "pitch_predictability":

            predictability,



        "platoon_weakness":

            platoon,



        "leak_score":

            leak_score

    }





# ==========================================================
# LEAK SCORE
# ==========================================================


def calculate_leak_score(

    hr9,

    barrel,

    xwoba,

    hard_hit,

    k_rate,

    predictability

):


    """
    HR resistance failure score.

    Higher = easier HR environment.

    """



    score = (

        (hr9 * 2.0)

        +

        (barrel * 1.5)

        +

        (xwoba * 1.2)

        +

        (hard_hit * 1.0)

        -

        (k_rate * 0.8)

        +

        (predictability)

    )



    return round(

        score,

        3

    )





# ==========================================================
# PITCH PREDICTABILITY
# ==========================================================


def pitch_predictability(pitch_mix):


    """
    More predictable arsenals create
    better HR hunting lanes.

    """



    if not pitch_mix:

        return 0



    pitch_count = len(
        pitch_mix
    )



    # Fewer reliable weapons =
    # easier pattern recognition


    if pitch_count <= 2:

        return 2.0


    if pitch_count == 3:

        return 1.0



    return 0.5





# ==========================================================
# PLATOON WEAKNESS
# ==========================================================


def platoon_weakness(splits):


    """
    Determines whether pitcher has
    exploitable LHB/RHB weakness.

    """



    if not splits:

        return "UNKNOWN"



    lhb = splits.get(
        "vs_lhb",
        0
    )


    rhb = splits.get(
        "vs_rhb",
        0
    )



    if lhb > rhb:

        return "LHB_TARGET"


    if rhb > lhb:

        return "RHB_TARGET"



    return "NEUTRAL"





# ==========================================================
# PITCHER MAP BUILDER
# ==========================================================


def rank_pitchers(pitchers):


    """
    Creates Gate 0 resistance map.

    Only ranks pitchers.
    No hitter selection.
    """



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

            x.get(
                "leak_score",
                0
            ),

        reverse=True

    )
