from services.player_map import get_player_name

def normalize_lineup(raw_lineup, roster_map=None):

    normalized = []

    for p in raw_lineup:

        player_id = p.get("id")
        slot = p.get("slot") or 9
        handedness = p.get("handedness") or "R"
        side = p.get("side") or "home"

        # 🔥 HARD LOCK NAME RESOLUTION (NO EXCEPTIONS)
        name = p.get("name")

        if not name or str(name).isdigit() or str(name).startswith("player_"):
            name = get_player_name(player_id)

        # role
        if slot <= 2:
            role = "table_setter"
        elif slot <= 5:
            role = "middle_core"
        else:
            role = "bottom_order"

        normalized.append({
            "id": player_id,
            "name": name,   # 🔥 ALWAYS CLEAN NAME HERE
            "slot": slot,
            "handedness": handedness,
            "side": side,
            "role": role
        })

    return normalized
