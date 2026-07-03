import requests

PLAYER_CACHE = {}


def clean_player_id(player_id):
    """
    Converts:
    player_824659_1 → 824659
    """
    if not player_id:
        return None

    if isinstance(player_id, int):
        return str(player_id)

    if isinstance(player_id, str):
        player_id = player_id.replace("player_", "")
        player_id = player_id.split("_")[0]

        digits = "".join([c for c in player_id if c.isdigit()])
        return digits if digits else None

    return None


def get_player_name(player_id):

    player_id = clean_player_id(player_id)

    if not player_id:
        return None

    if player_id in PLAYER_CACHE:
        return PLAYER_CACHE[player_id]

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}"
        data = requests.get(url, timeout=10).json()

        people = data.get("people", [])

        if not people:
            return None

        name = people[0].get("fullName")

        if name:
            PLAYER_CACHE[player_id] = name

        return name

    except:
        return None
