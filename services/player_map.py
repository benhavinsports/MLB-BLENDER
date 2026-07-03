import requests
import re

PLAYER_CACHE = {}

def extract_mlb_id(player_id):

    """
    Extract numeric MLB id from mixed engine IDs
    """

    if not player_id:
        return None

    # if already numeric
    if str(player_id).isdigit():
        return str(player_id)

    # extract last numeric chunk from player_824659_1
    match = re.findall(r"\d+", str(player_id))

    if not match:
        return None

    # take middle chunk (usually real MLB id)
    return match[-1]


def get_player_name(player_id):

    if not player_id:
        return "Unknown"

    cache_key = str(player_id)

    if cache_key in PLAYER_CACHE:
        return PLAYER_CACHE[cache_key]

    mlb_id = extract_mlb_id(player_id)

    if not mlb_id:
        return cache_key

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{mlb_id}"
        data = requests.get(url, timeout=10).json()

        people = data.get("people", [])

        if not people:
            name = cache_key
        else:
            name = people[0].get("fullName") or cache_key

        PLAYER_CACHE[cache_key] = name

        return name

    except:
        return cache_key
