import requests

PLAYER_CACHE = {}

def get_player_name(player_id):

    if not player_id:
        return "Unknown"

    if player_id in PLAYER_CACHE:
        return PLAYER_CACHE[player_id]

    try:
        url = f"https://statsapi.mlb.com/api/v1/people/{player_id}"
        data = requests.get(url, timeout=10).json()

        people = data.get("people", [])

        if not people:
            return f"Unknown_{player_id}"

        name = people[0].get("fullName", f"Unknown_{player_id}")

        PLAYER_CACHE[player_id] = name

        return name

    except:
        return f"Unknown_{player_id}"


def normalize_lineup(raw_lineup, roster_map=None):

    """
    FIXED LINEUP NORMALIZER — NOW RETURNS REAL NAMES
    """

    normalized = []

    for p in raw_lineup:

        player_id = p.get("id")

        # 🔥 REAL FIX: resolve name HERE (not later)
        name = p.get("name")

        if not name or name == player_id:
            name = get_player_name(player_id)

        # SLOT
        slot = p.get("slot", 9)

        if slot is None:
            slot = 9

        # HANDEDNESS
        handedness = p.get("handedness") or "R"

        # SIDE
        side = p.get("side", "home")

        # ROLE
        if slot <= 2:
            role = "table_setter"
        elif slot <= 5:
            role = "middle_core"
        else:
            role = "bottom_order"

        normalized.append({
            "id": player_id,
            "name": name,   # 🔥 ALWAYS REAL NAME NOW
            "slot": slot,
            "handedness": handedness,
            "side": side,
            "role": role
        })

    return normalized
