def apply_elimination_gates(lineup, pitcher_profile):

    survivors = []

    for p in lineup:

        slot = p.get("slot", 9)
        handed = p.get("handedness", "R")

        gate_log = []

        # -------------------------
        # GATE 0 — SLOT HARD FILTER
        # -------------------------
        if slot > 6:
            continue
        gate_log.append("PASS Gate 0")

        # -------------------------
        # GATE 1 — HAND MATCH
        # -------------------------
        if pitcher_profile:
            weak_r = pitcher_profile.get("weak_vs_right")
            weak_l = pitcher_profile.get("weak_vs_left")

            if (weak_r and handed == "R") or (weak_l and handed == "L"):
                gate_log.append("PASS Gate 1")
            else:
                continue
        else:
            continue

        # -------------------------
        # GATE 2 — PARK CHECK
        # -------------------------
        if pitcher_profile.get("park_factor", 1) < 0.92:
            continue
        gate_log.append("PASS Gate 2")

        survivors.append({
            "id": p["id"],
            "name": p.get("name", p["id"]),
            "slot": slot,
            "gate_history": gate_log
        })

    return survivors
