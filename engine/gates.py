def apply_elimination_gates(lineup, pitcher_profile):

    survivors = []

    for p in lineup:

        gate_history = []

        slot = p.get("slot", 9)

        # -------------------------
        # GATE 0 — SLOT (STRICT ELIMINATION)
        # -------------------------
        if slot <= 5:
            gate_history.append("PASS Gate 0")
        else:
            continue   # HARD ELIMINATION

        # -------------------------
        # GATE 1 — HANDEDNESS MATCH
        # -------------------------
        if pitcher_profile:
            if pitcher_profile.get("weak_vs_right") and p.get("handedness") == "R":
                gate_history.append("PASS Gate 1")
            elif pitcher_profile.get("weak_vs_left") and p.get("handedness") == "L":
                gate_history.append("PASS Gate 1")
            else:
                gate_history.append("PASS Gate 1 neutral")

        # -------------------------
        # GATE 2 — ENVIRONMENT CHECK
        # -------------------------
        if pitcher_profile.get("park_factor", 1) < 0.95:
            continue   # ELIMINATE

        gate_history.append("PASS Gate 2")

        survivors.append({
            "id": p["id"],
            "name": p.get("name", p["id"]),
            "slot": slot,
            "handedness": p.get("handedness"),
            "gate_history": gate_history
        })

    return survivors
