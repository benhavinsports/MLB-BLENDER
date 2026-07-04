import requests

PLAYER_CACHE = {}

def get_player_name(player_id):
    """
    LOCKED IDENTITY LAYER
    Always returns clean fullName or fallback
    """

    if not player_id:
        return "Unknown Player"

    player_id = str(player_id)

    if player_id in PLAYER_CACHE:
        return PLAYER_CACHE[player_id]

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}"
        res = requests.get(url, timeout=10)

        if res.status_code != 200:
            fallback = f"Unknown Player {player_id}"
            PLAYER_CACHE[player_id] = fallback
            return fallback

        data = res.json()
        people = data.get("people", [])

        if not people:
            fallback = f"Unknown Player {player_id}"
            PLAYER_CACHE[player_id] = fallback
            return fallback

        name = people[0].get("fullName")

        if not name:
            name = f"Unknown Player {player_id}"

        PLAYER_CACHE[player_id] = name
        return name

    except Exception:
        fallback = f"Unknown Player {player_id}"
        PLAYER_CACHE[player_id] = fallback
        return fallback
