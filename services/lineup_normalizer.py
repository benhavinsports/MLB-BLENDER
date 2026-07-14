# services/lineup_normalizer.py

from typing import List, Dict


def normalize_lineup(raw_lineup: List[Dict]) -> List[Dict]:
    """
    Blender Identity Layer

    Converts raw lineup data into one consistent format.

    Required output:

    {
        id,
        name,
        slot,
        handedness,
        side,
        role
    }

    NO fake names.
    NO player_xxxxx IDs.
    """

    normalized = []

    for i, player in enumerate(raw_lineup):

        player_id = (
            player.get("id")
            or player.get("player_id")
            or player.get("mlb_id")
        )

        name = (
            player.get("name")
            or player.get("fullName")
            or player.get("full_name")
            or player.get("player_name")
        )

        # If a real name doesn't exist,
        # skip the player completely.
        if not name:
            continue

        slot = (
            player.get("slot")
            or player.get("batting_order")
            or i + 1
        )

        handedness = (
            player.get("handedness")
            or player.get("batSide")
            or player.get("bat_side")
            or "R"
        )

        side = player.get("side", "")

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

    normalized.sort(key=lambda x: x["slot"])

    return normalized
