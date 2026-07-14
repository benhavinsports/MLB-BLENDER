# services/environment.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 1 — GAME ENVIRONMENT ENGINE
#
# Purpose:
# Determine if the HR environment can support events.
#
# No hitter selection.
# No survivor logic.
# ==========================================================



def build_environment_card(game):


    """
    Builds HR environment profile.

    Inputs:
    - park factor
    - wind
    - temperature
    - humidity
    """



    park_factor = game.get(
        "park_factor",
        1.0
    )


    wind_speed = game.get(
        "wind_speed",
        0
    )


    wind_direction = game.get(
        "wind_direction",
        "unknown"
    )


    temperature = game.get(
        "temperature",
        70
    )


    humidity = game.get(
        "humidity",
        50
    )



    score = calculate_environment_score(

        park_factor,

        wind_speed,

        wind_direction,

        temperature,

        humidity

    )



    return {


        "park_factor":

            park_factor,


        "wind_speed":

            wind_speed,


        "wind_direction":

            wind_direction,


        "temperature":

            temperature,


        "humidity":

            humidity,


        "environment_score":

            score,


        "hr_flag":

            environment_flag(
                score
            )

    }





# ==========================================================
# ENVIRONMENT SCORE
# ==========================================================


def calculate_environment_score(

    park_factor,

    wind_speed,

    wind_direction,

    temperature,

    humidity

):


    score = 0



    # Park

    if park_factor >= 1.05:

        score += 2


    elif park_factor < .95:

        score -= 1



    # Wind

    direction = str(
        wind_direction
    ).lower()



    if "out" in direction:

        score += 2


    elif "in" in direction and wind_speed >= 10:

        score -= 2



    # Temperature

    if temperature >= 80:

        score += 1


    elif temperature <= 55:

        score -= 1



    # Humidity

    if humidity >= 60:

        score += .5



    return round(
        score,
        2
    )





# ==========================================================
# ENVIRONMENT STATUS
# ==========================================================


def environment_flag(score):


    if score >= 3:

        return "HR_BOOST"


    if score >= 1:

        return "HR_NEUTRAL_PLUS"


    if score < 0:

        return "HR_SUPPRESSION"


    return "NEUTRAL"
