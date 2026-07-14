# services/players.py

import requests


# ==========================================================
# MLB HR BLENDER vFINAL
# PLAYER IDENTITY LAYER
# ==========================================================


PLAYER_CACHE = {}



MLB_PERSON_URL = (
    "https://statsapi.mlb.com/api/v1/people"
)



def get_player_name(player_id):

    """
    Converts MLB ID -> real player name.

    Identity only.
    No stats.
    No gates.
    """



    if not player_id:

        return "UNKNOWN"



    if player_id in PLAYER_CACHE:

        return PLAYER_CACHE[player_id]



    try:

        response = requests.get(

            f"{MLB_PERSON_URL}/{player_id}",

            timeout=10

        )


        data = response.json()


        people = data.get(
            "people",
            []
        )


        if people:

            name = people[0].get(
                "fullName"
            )


            if name:

                PLAYER_CACHE[player_id] = name

                return name



    except Exception:

        pass



    return "UNKNOWN"




def attach_identity(player):

    """
    Guarantees every player object
    has a display name.
    """


    player_id = player.get(
        "id"
    )


    if not player.get("name"):

        player["name"] = get_player_name(
            player_id
        )


    return player




def normalize_players(players):

    """
    Final identity cleanup before Blender.
    """


    cleaned = []


    for player in players:


        cleaned.append(
            attach_identity(player)
        )


    return cleaned
