from services.player_map import get_player_name


def normalize_lineup(raw_lineup, roster_map=None):

    """
    LINEUP NORMALIZATION LAYER (FIXED)
    Now resolves player names immediately instead of passing IDs forward
    """

    normalized = []

    for p in raw_lineup:

        player_id = p.get("id")

        # 🔥 FIX: ALWAYS resolve real name here
        player_name = (
            p.get("name")
            or (get_player_name(player_id) if player_id else None)
            or player_id
        )

        # -------------------------
        # SLOT
        # -------------------------
        slot = p.get("slot") or 9

        # -------------------------
        # HANDEDNESS
        # -------------------------
        handedness = p.get("handedness") or "R"

        # -------------------------
        # SIDE
        # -------------------------
        side = p.get("side", "home")

        # -------------------------
        # ROLE MAPPING
        # -------------------------
        if slot <= 2:
            role = "table_setter"
        elif slot <= 5:
            role = "middle_core"
        else:
            role = "bottom_order"

        # -------------------------
        # FINAL STRUCTURE
        # -------------------------
        normalized.append({
            "id": player_id,
            "name": player_name,   # 🔥 FIXED HERE
            "slot": slot,
            "handedness": handedness,
            "side": side,
            "role": role
        })

    return normalized
