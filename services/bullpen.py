# services/bullpen.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 11 — BULLPEN CONTINUATION ENGINE
#
# Determines late HR continuation risk.
#
# No picks.
# No hitter ranking.
# Data layer only.
# ==========================================================



def build_bullpen_card(team_data):


    """
    Builds bullpen weakness profile.

    Inputs:

    bullpen HR/9
    relief ERA
    recent usage
    fatigue
    """



    return {


        "team":

            team_data.get(
                "team",
                "UNKNOWN"
            ),


        "hr9":

            team_data.get(
                "hr9",
                0
            ),


        "era":

            team_data.get(
                "era",
                0
            ),


        "recent_usage":

            team_data.get(
                "recent_usage",
                0
            ),


        "fatigue":

            team_data.get(
                "fatigue",
                0
            ),


        "risk_score":

            calculate_bullpen_risk(
                team_data
            )

    }





# ==========================================================
# BULLPEN RISK SCORE
# ==========================================================


def calculate_bullpen_risk(bullpen):


    """

    Higher score =
    weaker late inning HR resistance.


    Formula:

    HR/9      40%
    Fatigue   30%
    ERA       20%
    Usage     10%

    """



    hr9 = bullpen.get(
        "hr9",
        0
    )


    fatigue = bullpen.get(
        "fatigue",
        0
    )


    era = bullpen.get(
        "era",
        0
    )


    usage = bullpen.get(
        "recent_usage",
        0
    )



    score = (

        hr9 * .40

        +

        fatigue * .30

        +

        era * .20

        +

        usage * .10

    )


    return round(
        score,
        3
    )





# ==========================================================
# GATE 11 CHECK
# ==========================================================


def bullpen_continuation_check(bullpen):


    """

    PASS:

    HR/9 > 1.2

    OR

    fatigue present


    Undefined data:
    PASS THROUGH

    """



    if not bullpen:

        return True



    hr9 = bullpen.get(
        "hr9",
        0
    )


    fatigue = bullpen.get(
        "fatigue",
        0
    )



    if hr9 == 0 and fatigue == 0:

        return True



    if hr9 > 1.2:

        return True



    if fatigue >= 1:

        return True



    return False
