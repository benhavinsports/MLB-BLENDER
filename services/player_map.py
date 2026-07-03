import requests

PLAYER_CACHE = {}

def get_player_name(player_id):

    if not player_id:
        return None

    player_id = str(player_id)

    if player_id in PLAYER_CACHE:
        return PLAYER_CACHE[player_id]

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}"

        resp = requests.get(url, timeout=10)

        # 🔥 SAFETY CHECK (IMPORTANT FIX)
        if resp.status_code != 200:
            return None

        data = resp.json()

        people = data.get("people", [])

        if not people:
            return None

        name = people[0].get("fullName")

        if not name:
            return None

        PLAYER_CACHE[player_id] = name

        return name

    except Exception:
        return None
