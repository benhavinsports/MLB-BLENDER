# services/players.py

import requests


PLAYER_CACHE = {}


MLB_PLAYER_URL = (
    "https://statsapi.mlb.com/api/v1/people/"
)



def get_player_name(player_id):

    """
    Converts MLB player ID
    into real name.

    Example:

    592450
       ↓
    Juan Soto

    """

    if not player_id:
        return "UNKNOWN"


    if player_id in PLAYER_CACHE:
        return PLAYER_CACHE[player_id]


    try:

        response = requests.get(
            f"{MLB_PLAYER_URL}{player_id}",
            timeout=10
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


        if not name:

            name = f"UNKNOWN_{player_id}"


        PLAYER_CACHE[player_id] = name


        return name


    except Exception:

        return f"UNKNOWN_{player_id}"



def resolve_player(player):

    """
    Takes any hitter object.

    Forces name field.

    """

    if player.get("name"):

        return player


    player_id = player.get(
        "id"
    )


    player["name"] = get_player_name(
        player_id
    )


    return player
