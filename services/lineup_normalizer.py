def normalize_lineup(raw_lineup, roster_map=None):

    """
    LINEUP NORMALIZATION LAYER
    Converts raw MLB feed into gate-ready structured players
    """

    normalized = []

    for p in raw_lineup:

        player_id = p.get("id")

        # -------------------------
        # SLOT (batting order position)
        # -------------------------
        slot = p.get("slot", None)

        if slot is None:
            # fallback: unknown slot goes bottom order
            slot = 9

        # -------------------------
        # HANDEDNESS (SAFE FALLBACK)
        # -------------------------
        handedness = p.get("handedness")

        if not handedness:
            # fallback if missing
            handedness = "R"

        # -------------------------
        # SIDE
        # -------------------------
        side = p.get("side", "home")

        # -------------------------
        # ROLE MAPPING (IMPORTANT FOR CORE 3)
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
            "name": p.get("name", player_id),
            "slot": slot,
            "handedness": handedness,
            "side": side,
            "role": role
        })

    return normalized
