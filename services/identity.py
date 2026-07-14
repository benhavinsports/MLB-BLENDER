# services/identity.py

import requests


# ==========================================================
# PLAYER IDENTITY LOCK
# MLB ID  -> REAL PLAYER NAME
# ==========================================================


PLAYER_CACHE = {}



def lock_player_identity(player):

    """
    FINAL NAME RESOLUTION LAYER

    Input can be:

    {
        "id": 660271,
        "name": "Aaron Judge"
    }

    OR

    {
        "player_id": 660271
    }

    Returns:

    Real player name string
    """


    if not player:

        return "UNKNOWN"



    # Already has real name

    existing_name = player.get(
        "name"
    )


    if (
        existing_name
        and not str(existing_name).startswith("player_")
        and not str(existing_name).isdigit()
        and not str(existing_name).startswith("Unknown")
    ):

        return existing_name



    # Find ID

    player_id = (
        player.get("id")
        or
        player.get("player_id")
    )



    if not player_id:

        return "UNKNOWN"



    return get_player_name(
        player_id
    )




# ==========================================================
# MLB STATS API LOOKUP
# ==========================================================


def get_player_name(player_id):


    player_id = str(
        player_id
    )


    if player_id in PLAYER_CACHE:

        return PLAYER_CACHE[player_id]



    try:


        url = (
            "https://statsapi.mlb.com/api/v1/people/"
            f"{player_id}"
        )


        response = requests.get(
            url,
            timeout=5
        )


        data = response.json()



        people = data.get(
            "people",
            []
        )


        if not people:

            return f"UNKNOWN_{player_id}"



        name = people[0].get(
            "fullName"
        )



        if name:

            PLAYER_CACHE[player_id] = name

            return name



    except Exception:

        pass



    return f"UNKNOWN_{player_id}"




# ==========================================================
# BATCH NAME LOADER
# NO LAG VERSION
# ==========================================================


def preload_players(players):

    """
    Loads all names before Blender starts.

    Prevents:

    player_824659_1

    appearing in output.
    """


    for p in players:

        get_player_name(
            p.get("id")
            or
            p.get("player_id")
        )


    return True
