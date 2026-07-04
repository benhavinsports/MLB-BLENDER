import requests
import re

PLAYER_CACHE = {}

def clean_id(player_id):
    """
    Converts:
    player_824659_1 → 824659
    824659 → 824659
    """

    if not player_id:
        return None

    player_id = str(player_id)

    # extract numeric ID
    match = re.search(r"(\d{4,7})", player_id)

    if match:
        return match.group(1)

    return player_id


def get_player_name(player_id):

    clean = clean_id(player_id)

    if not clean:
        return None

    if clean in PLAYER_CACHE:
        return PLAYER_CACHE[clean]

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{clean}"
        data = requests.get(url, timeout=10).json()

        people = data.get("people", [])

        if not people:
            return None

        name = people[0].get("fullName")

        if name:
            PLAYER_CACHE[clean] = name

        return name

    except:
        return None


def normalize_lineup(raw_lineup, roster_map=None):

    normalized = []

    for p in raw_lineup:

        raw_id = p.get("id")
        player_id = clean_id(raw_id)

        # 🔥 FORCE NAME RESOLUTION ALWAYS
        name = p.get("name")

        if not name or str(name).startswith("player_") or name == raw_id:
            name = get_player_name(player_id)

        if not name:
            name = f"Unknown_{player_id}"

        slot = p.get("slot") or 9

        handedness = p.get("handedness") or "R"
        side = p.get("side") or "home"

        if slot <= 2:
            role = "table_setter"
        elif slot <= 5:
            role = "middle_core"
        else:
            role = "bottom_order"

        normalized.append({
            "id": player_id,
            "name": name,
            "slot": slot,
            "handedness": handedness,
            "side": side,
            "role": role
        })

    return normalized
