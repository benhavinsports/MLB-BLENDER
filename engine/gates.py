def apply_elimination_gates(lineup, pitcher_profile):
    """
    BLENDER GATES V2 — STRUCTURED TRACEABLE ENGINE

    OUTPUT:
        FULL gate-by-gate structured audit per hitter
    """

    survivors = []

    for p in lineup:

        slot = p.get("slot", 9)

        gate_log = []
        eliminated = False

        # =========================
        # GATE 0 — SLOT SCORE
        # =========================
        SLOT_SCORE = max(0, (6 - slot))

        gate_log.append({
            "gate": 0,
            "formula": "SLOT_SCORE = max(0, 6 - slot)",
            "input": slot,
            "score": SLOT_SCORE,
            "threshold": 1,
            "pass": SLOT_SCORE >= 1
        })

        if SLOT_SCORE < 1:
            continue

        # =========================
        # GATE 1 — PLATOON MATCH
        # =========================
        platoon = 0

        if pitcher_profile:
            if pitcher_profile.get("weak_vs_right") and p.get("handedness") == "R":
                platoon = 1
            elif pitcher_profile.get("weak_vs_left") and p.get("handedness") == "L":
                platoon = 1

        gate_log.append({
            "gate": 1,
            "formula": "PLATOON = 1 if matchup advantage else 0",
            "input": p.get("handedness"),
            "score": platoon,
            "threshold": 1,
            "pass": platoon == 1
        })

        if platoon == 0:
            continue

        # =========================
        # GATE 2 — PARK FACTOR
        # =========================
        park = pitcher_profile.get("park_factor", 1)

        PARK_SCORE = (park - 1) * 10

        gate_log.append({
            "gate": 2,
            "formula": "PARK_SCORE = (park_factor - 1) * 10",
            "input": park,
            "score": PARK_SCORE,
            "threshold": -1,
            "pass": PARK_SCORE >= -1
        })

        if PARK_SCORE < -1:
            continue

        # =========================
        # GATE 3 — LINEUP SLOT VALUE
        # =========================
        LINEUP_SCORE = max(0, 7 - slot)

        gate_log.append({
            "gate": 3,
            "formula": "LINEUP_SCORE = max(0, 7 - slot)",
            "input": slot,
            "score": LINEUP_SCORE,
            "threshold": 1,
            "pass": LINEUP_SCORE >= 1
        })

        if LINEUP_SCORE < 1:
            continue

        # =========================
        # GATE 4 — HARD HIT
        # =========================
        hh = p.get("hardhit_pct", 0)
        HARDHIT_SCORE = hh / 100

        gate_log.append({
            "gate": 4,
            "formula": "HARDHIT_SCORE = hardhit_pct / 100",
            "input": hh,
            "score": HARDHIT_SCORE,
            "threshold": 0.38,
            "pass": HARDHIT_SCORE >= 0.38
        })

        if HARDHIT_SCORE < 0.38:
            continue

        # =========================
        # GATE 5 — EXIT VELOCITY
        # =========================
        ev = p.get("exit_velocity", 85)
        EV_SCORE = (ev - 85) / 10

        gate_log.append({
            "gate": 5,
            "formula": "EV_SCORE = (exit_velocity - 85) / 10",
            "input": ev,
            "score": EV_SCORE,
            "threshold": 0.2,
            "pass": EV_SCORE >= 0.2
        })

        if EV_SCORE < 0.2:
            continue

        # =========================
        # GATE 6 — BARREL RATE
        # =========================
        barrel = p.get("barrel_pct", 0)
        BARREL_SCORE = barrel / 100

        gate_log.append({
            "gate": 6,
            "formula": "BARREL_SCORE = barrel_pct / 100",
            "input": barrel,
            "score": BARREL_SCORE,
            "threshold": 0.10,
            "pass": BARREL_SCORE >= 0.10
        })

        if BARREL_SCORE < 0.10:
            continue

        # =========================
        # GATE 7 — RHYTHM
        # =========================
        hr10 = p.get("hr_last10", 0)
        barrels10 = p.get("barrels_last10", 0)

        RHYTHM_SCORE = (hr10 * 3) + (barrels10 * 2)

        gate_log.append({
            "gate": 7,
            "formula": "RHYTHM = (HR_last10*3) + (Barrels_last10*2)",
            "input": {"hr10": hr10, "barrels10": barrels10},
            "score": RHYTHM_SCORE,
            "threshold": 5,
            "pass": RHYTHM_SCORE >= 5
        })

        if RHYTHM_SCORE < 5:
            continue

        # =========================
        # GATE 8 — CONVERSION
        # =========================
        hr = p.get("hr_season", 0)
        pa = p.get("pa", 1)

        CONVERSION = hr / pa

        gate_log.append({
            "gate": 8,
            "formula": "CONVERSION = HR / PA",
            "input": {"hr": hr, "pa": pa},
            "score": CONVERSION,
            "threshold": 0.045,
            "pass": CONVERSION >= 0.045
        })

        if CONVERSION < 0.045:
            continue

        # =========================
        # GATE 9 — ENVIRONMENT
        # =========================
        env = pitcher_profile.get("park_factor", 1)
        ENV_SCORE = env * 10

        gate_log.append({
            "gate": 9,
            "formula": "ENV_SCORE = park_factor * 10",
            "input": env,
            "score": ENV_SCORE,
            "threshold": 9,
            "pass": ENV_SCORE >= 9
        })

        if ENV_SCORE < 9:
            continue

        # =========================
        # GATE 10 — OPPORTUNITY
        # =========================
        opp = max(0, 7 - slot) + (p.get("pa", 4) / 4)

        gate_log.append({
            "gate": 10,
            "formula": "OPP = (7 - slot) + (PA/4)",
            "input": {"slot": slot, "pa": p.get("pa", 4)},
            "score": opp,
            "threshold": 4,
            "pass": opp >= 4
        })

        if opp < 4:
            continue

        # =========================
        # GATE 10.5 — DECOY
        # =========================
        decoy = p.get("decoy_score", 0)

        gate_log.append({
            "gate": "10.5",
            "formula": "DECOY = model risk score (0-1)",
            "input": decoy,
            "score": decoy,
            "threshold": 0.8,
            "pass": decoy <= 0.8
        })

        if decoy > 0.8:
            continue

        # =========================
        # GATE 11 — BULLPEN
        # =========================
        bullpen = pitcher_profile.get("bullpen_hr9", 1)

        gate_log.append({
            "gate": 11,
            "formula": "BULLPEN = bullpen_hr9",
            "input": bullpen,
            "score": bullpen,
            "threshold": 1.2,
            "pass": bullpen >= 1.2
        })

        if bullpen < 1.2:
            continue

        # =========================
        # GATE 12 — OWNERSHIP
        # =========================
        ownership = SLOT_SCORE + EV_SCORE + BARREL_SCORE

        gate_log.append({
            "gate": 12,
            "formula": "OWNERSHIP = SLOT + EV + BARREL",
            "input": None,
            "score": ownership,
            "threshold": 1.5,
            "pass": ownership >= 1.5
        })

        if ownership < 1.5:
            continue

        # =========================
        # GATE 13 — NUMERICAL
        # =========================
        jersey = p.get("jersey", 0)
        NUM_SCORE = abs((jersey % 9) - slot)

        gate_log.append({
            "gate": 13,
            "formula": "NUM_SCORE = abs((jersey % 9) - slot)",
            "input": {"jersey": jersey},
            "score": NUM_SCORE,
            "threshold": 6,
            "pass": NUM_SCORE <= 6
        })

        if NUM_SCORE > 6:
            continue

        # =========================
        # GATE 14 — PROTECTION
        # =========================
        prot = p.get("protection_rating", 50)

        gate_log.append({
            "gate": 14,
            "formula": "PROTECTION = lineup protection rating",
            "input": prot,
            "score": prot,
            "threshold": 45,
            "pass": prot >= 45
        })

        if prot < 45:
            continue

        # =========================
        # GATE 15 — FINISHER
        # =========================
        finisher = HARDHIT_SCORE + BARREL_SCORE + EV_SCORE

        gate_log.append({
            "gate": 15,
            "formula": "FINISHER = HARDHIT + BARREL + EV",
            "input": None,
            "score": finisher,
            "threshold": 0.9,
            "pass": finisher >= 0.9
        })

        if finisher < 0.9:
            continue

        # =========================
        # GATE 16 — COLLAPSE
        # =========================
        collapse = (EV_SCORE + BARREL_SCORE) / 2

        gate_log.append({
            "gate": 16,
            "formula": "COLLAPSE = (EV + BARREL) / 2",
            "input": None,
            "score": collapse,
            "threshold": 0.25,
            "pass": collapse >= 0.25
        })

        if collapse < 0.25:
            continue

        # =========================
        # GATE 17 — AUDIT
        # =========================
        audit = finisher + ownership

        gate_log.append({
            "gate": 17,
            "formula": "AUDIT = FINISHER + OWNERSHIP",
            "input": None,
            "score": audit,
            "threshold": 2.5,
            "pass": audit >= 2.5
        })

        if audit < 2.5:
            continue

        # =========================
        # GATE 18 — FINAL SCORE
        # =========================
        final_score = audit + RHYTHM_SCORE

        gate_log.append({
            "gate": 18,
            "formula": "FINAL = AUDIT + RHYTHM",
            "input": None,
            "score": final_score,
            "threshold": None,
            "pass": True
        })

        survivors.append({
            "id": p["id"],
            "name": p.get("name", p["id"]),
            "slot": slot,
            "final_score": final_score,
            "gates": gate_log
        })

    if not survivors:
        return []

    return [max(survivors, key=lambda x: x["final_score"])]
