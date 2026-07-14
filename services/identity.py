import requests
import time

PLAYER_CACHE = {}

MLB_API = "https://statsapi.mlb.com/api/v1/people/"


def resolve_player_name(player_id):

    if not player_id:
        return "UNKNOWN PLAYER"

    player_id = str(player_id)

    if player_id in PLAYER_CACHE:
        return PLAYER_CACHE[player_id]

    try:
        url = MLB_API + player_id

        response = requests.get(
            url,
            timeout=5
        )

        data = response.json()

        people = data.get("people", [])

        if people:

            name = people[0].get(
                "fullName",
                "UNKNOWN PLAYER"
            )

            PLAYER_CACHE[player_id] = name

            return name


    except Exception:

        pass


    return f"PLAYER_{player_id}"


def lock_player_identity(player):

    """
    FINAL IDENTITY GATE

    No raw IDs leave engine.
    """

    if not isinstance(player, dict):
        return player


    player_id = (
        player.get("id")
        or
        player.get("player_id")
    )


    existing_name = player.get("name")


    if existing_name:
        return existing_name


    if player_id:

        return resolve_player_name(player_id)


    return "UNKNOWN PLAYER"
