# services/environment.py

# ==========================================================
# MLB HR BLENDER vFINAL
# ENVIRONMENT ENGINE
#
# Park + Weather + HR Conditions
#
# No picks.
# No rankings.
# Data only.
# ==========================================================



def calculate_environment_score(environment):

    """
    ENV SCORE

    Park Factor      .30
    Weather Boost    .25
    Wind Direction   .20
    Temperature      .15
    Altitude         .10

    """

    park = environment.get(
        "park_factor",
        0
    )

    weather = environment.get(
        "weather_boost",
        0
    )

    wind = environment.get(
        "wind_score",
        0
    )

    temp = environment.get(
        "temperature_score",
        0
    )

    altitude = environment.get(
        "altitude",
        0
    )


    score = (

        park * .30

        +

        weather * .25

        +

        wind * .20

        +

        temp * .15

        +

        altitude * .10

    )


    return round(
        score,
        3
    )




# ==========================================================
# BUILD ENVIRONMENT CARD
# ==========================================================


def build_environment_card(game):


    return {


        "game_id":
            game.get(
                "game_id"
            ),


        "park":
            game.get(
                "park"
            ),


        "park_factor":
            game.get(
                "park_factor",
                0
            ),


        "wind_direction":
            game.get(
                "wind_direction"
            ),


        "wind_speed":
            game.get(
                "wind_speed",
                0
            ),


        "temperature":
            game.get(
                "temperature",
                0
            ),


        "humidity":
            game.get(
                "humidity",
                0
            ),


        "altitude":
            game.get(
                "altitude",
                0
            ),


        "weather_boost":
            game.get(
                "weather_boost",
                0
            ),


        "wind_score":
            game.get(
                "wind_score",
                0
            ),


        "temperature_score":
            game.get(
                "temperature_score",
                0
            ),


        "environment_score":
            calculate_environment_score(
                game
            )

    }



# ==========================================================
# HR ENVIRONMENT FLAGS
# ==========================================================


def environment_flag(environment):


    flags = []



    wind = environment.get(
        "wind_speed",
        0
    )

    temp = environment.get(
        "temperature",
        0
    )


    if wind >= 10:

        flags.append(
            "WIND ACTIVE"
        )


    if temp >= 80:

        flags.append(
            "HOT AIR BOOST"
        )


    if wind < -10:

        flags.append(
            "WIND SUPPRESSION"
        )


    return flags
