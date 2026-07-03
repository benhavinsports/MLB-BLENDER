import requests

PLAYER_CACHE = {}

def get_player_name(player_id):

    if not player_id:
        return "Unknown"

    player_id = str(player_id)

    if player_id in PLAYER_CACHE:
        return PLAYER_CACHE[player_id]

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}"
        data = requests.get(url, timeout=10).json()

        people = data.get("people", [])

        if not people:
            name = f"Unknown_{player_id}"
        else:
            name = people[0].get("fullName") or f"Unknown_{player_id}"

        PLAYER_CACHE[player_id] = name

        return name

    except:
        return f"Unknown_{player_id}"
