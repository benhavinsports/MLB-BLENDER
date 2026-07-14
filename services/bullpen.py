# services/bullpen.py

# ==========================================================
# MLB HR BLENDER vFINAL
# BULLPEN CONTINUATION ENGINE
#
# Determines if HR environment survives
# past the starting pitcher.
#
# No picks.
# Data only.
# ==========================================================



def calculate_bullpen_risk(bullpen):

    """
    Bullpen HR Risk Score

    Inputs:

    HR/9 allowed
    Fatigue
    Relief ERA
    Recent usage

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


    recent_usage = bullpen.get(
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

        recent_usage * .10

    )


    return round(
        score,
        3
    )




# ==========================================================
# BUILD BULLPEN CARD
# ==========================================================


def build_bullpen_card(team_data):


    return {


        "team":

            team_data.get(
                "team"
            ),


        "hr9":

            team_data.get(
                "bullpen_hr9",
                0
            ),


        "era":

            team_data.get(
                "bullpen_era",
                0
            ),


        "fatigue":

            team_data.get(
                "fatigue",
                0
            ),


        "recent_usage":

            team_data.get(
                "recent_usage",
                0
            ),


        "risk_score":

            calculate_bullpen_risk(
                team_data
            )

    }




# ==========================================================
# GATE 11 CHECK
# ==========================================================


def bullpen_hr_path(bullpen):


    """

    PASS:

    HR/9 > 1.2

    OR

    fatigue present


    """

    hr9 = bullpen.get(
        "hr9",
        0
    )


    fatigue = bullpen.get(
        "fatigue",
        0
    )


    if hr9 > 1.2:

        return True


    if fatigue >= 1:

        return True


    # Missing data does not kill

    if hr9 == 0 and fatigue == 0:

        return True


    return False




# ==========================================================
# GATE 13 CONTINUATION
# ==========================================================


def bullpen_continuation(bullpen):


    risk = bullpen.get(
        "risk_score",
        0
    )


    if risk >= 1:

        return True


    return True
