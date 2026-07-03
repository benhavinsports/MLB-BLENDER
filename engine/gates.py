def apply_elimination_gates(lineup, pitcher_profile):
    """
    BLENDER v1 TRUE GATE ENGINE

    RULE:
    - NO scoring
    - NO ranking inside gates
    - ONLY PASS / FAIL
    - MUST carry gate history
    """

    survivors = []

    for p in lineup:

        gate_history = []
        alive = True

        # -------------------------
        # GATE 0 — SLOT CHECK
        # -------------------------
        slot = p.get("slot", 9)

        if slot <= 3:
            gate_history.append("PASS Gate 0 - elite slot")
        elif slot <= 6:
            gate_history.append("PASS Gate 0 - mid slot")
        else:
            gate_history.append("FAIL Gate 0 - bottom order")
            alive = False

        if not alive:
            continue

        # -------------------------
        # GATE 1 — HANDEDNESS MATCH
        # -------------------------
        if pitcher_profile.get("weak_vs_right") and p.get("handedness") == "R":
            gate_history.append("PASS Gate 1 - platoon advantage")
        elif pitcher_profile.get("weak_vs_left") and p.get("handedness") == "L":
            gate_history.append("PASS Gate 1 - platoon advantage")
        else:
            gate_history.append("PASS Gate 1 - neutral matchup")

        # -------------------------
        # GATE 2 — ENVIRONMENT
        # -------------------------
        if pitcher_profile.get("park_factor", 1) > 1.05:
            gate_history.append("PASS Gate 2 - hitter park")
        else:
            gate_history.append("PASS Gate 2 - neutral park")

        # -------------------------
        # FINAL DECISION
        # -------------------------
        survivors.append({
            "id": p["id"],
            "name": p.get("name", p["id"]),
            "slot": slot,
            "handedness": p.get("handedness"),
            "gate_history": gate_history
        })

    return survivors
