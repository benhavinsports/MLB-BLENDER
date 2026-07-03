def apply_elimination_gates(lineup, pitcher_profile):
    """
    BLENDER GATES V2 — FULL 18 GATE ENGINE (RESTORED)
    OUTPUT: survivors per game (NOT collapsed inside engine)
    """

    survivors = []

    for p in lineup:

        slot = p.get("slot", 9)
        gate_log = []

        # =========================
        # GATE 0 — SLOT SCORE
        # =========================
        SLOT_SCORE = max(0, (6 - slot))

        gate_log.append({
            "gate": 0,
            "formula": "SLOT_SCORE = max(0, 6 - slot)",
            "score": SLOT_SCORE,
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
            "formula": "PLATOON ADVANTAGE",
            "score": platoon,
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
            "score": PARK_SCORE,
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
            "score": LINEUP_SCORE,
            "pass": LINEUP_SCORE >= 1
        })

        if LINEUP_SCORE < 1:
            continue

        # =========================
        # GATE 4 — HARD HIT
        # =========================
        hh = p.get("hardhit_pct", 0) / 100

        gate_log.append({
            "gate": 4,
            "formula": "HARDHIT_SCORE = hardhit_pct / 100",
            "score": hh,
            "pass": hh >= 0.38
        })

        if hh < 0.38:
            continue

        # =========================
        # GATE 5 — EXIT VELOCITY
        # =========================
        ev = (p.get("exit_velocity", 85) - 85) / 10

        gate_log.append({
            "gate": 5,
            "formula": "EV_SCORE = (EV - 85) / 10",
            "score": ev,
            "pass": ev >= 0.2
        })

        if ev < 0.2:
            continue

        # =========================
        # GATE 6 — BARREL RATE
        # =========================
        barrel = p.get("barrel_pct", 0) / 100

        gate_log.append({
            "gate": 6,
            "formula": "BARREL_SCORE = barrel_pct / 100",
            "score": barrel,
            "pass": barrel >= 0.10
        })

        if barrel < 0.10:
            continue

        # =========================
        # GATE 7 — RHYTHM
        # =========================
        hr10 = p.get("hr_last10", 0)
        barrels10 = p.get("barrels_last10", 0)
        rhythm = (hr10 * 3) + (barrels10 * 2)

        gate_log.append({
            "gate": 7,
            "formula": "RHYTHM = HR*3 + BARRELS*2",
            "score": rhythm,
            "pass": rhythm >= 5
        })

        if rhythm < 5:
            continue

        # =========================
        # GATE 8 — CONVERSION
        # =========================
        hr = p.get("hr_season", 0)
        pa = max(1, p.get("pa", 1))
        conversion = hr / pa

        gate_log.append({
            "gate": 8,
            "formula": "CONVERSION = HR / PA",
            "score": conversion,
            "pass": conversion >= 0.045
        })

        if conversion < 0.045:
            continue

        # =========================
        # GATE 9 — ENVIRONMENT
        # =========================
        env = pitcher_profile.get("park_factor", 1)

        gate_log.append({
            "gate": 9,
            "formula": "ENV = park_factor",
            "score": env,
            "pass": env >= 0.95
        })

        if env < 0.95:
            continue

        # =========================
        # GATE 10 — OPPORTUNITY
        # =========================
        opp = max(0, 7 - slot) + (p.get("pa", 4) / 4)

        gate_log.append({
            "gate": 10,
            "formula": "OPP = (7-slot) + PA/4",
            "score": opp,
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
            "formula": "DECOY SCORE",
            "score": decoy,
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
            "formula": "BULLPEN HR/9",
            "score": bullpen,
            "pass": bullpen >= 1.2
        })

        if bullpen < 1.2:
            continue

        # =========================
        # GATE 12 — OWNERSHIP
        # =========================
        ownership = SLOT_SCORE + ev + barrel

        gate_log.append({
            "gate": 12,
            "formula": "OWNERSHIP = SLOT + EV + BARREL",
            "score": ownership,
            "pass": ownership >= 1.5
        })

        if ownership < 1.5:
            continue

        # =========================
        # GATE 13 — NUMERICAL
        # =========================
        jersey = p.get("jersey", 0)
        num = abs((jersey % 9) - slot)

        gate_log.append({
            "gate": 13,
            "formula": "NUM = abs((jersey % 9) - slot)",
            "score": num,
            "pass": num <= 6
        })

        if num > 6:
            continue

        # =========================
        # GATE 14 — PROTECTION
        # =========================
        prot = p.get("protection_rating", 50)

        gate_log.append({
            "gate": 14,
            "formula": "PROTECTION RATING",
            "score": prot,
            "pass": prot >= 45
        })

        if prot < 45:
            continue

        # =========================
        # GATE 15 — FINISHER
        # =========================
        finisher = hh + barrel + ev

        gate_log.append({
            "gate": 15,
            "formula": "FINISHER = HH + BARREL + EV",
            "score": finisher,
            "pass": finisher >= 0.9
        })

        if finisher < 0.9:
            continue

        # =========================
        # GATE 16 — COLLAPSE
        # =========================
        collapse = (ev + barrel) / 2

        gate_log.append({
            "gate": 16,
            "formula": "COLLAPSE = (EV + BARREL)/2",
            "score": collapse,
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
            "score": audit,
            "pass": audit >= 2.5
        })

        if audit < 2.5:
            continue

        # =========================
        # GATE 18 — FINAL SCORE
        # =========================
        final_score = audit + rhythm

        gate_log.append({
            "gate": 18,
            "formula": "FINAL = AUDIT + RHYTHM",
            "score": final_score,
            "pass": True
        })

        survivors.append({
            "id": p["id"],
            "name": p.get("name", p["id"]),
            "slot": slot,
            "final_score": final_score,
            "gate_history": gate_log
        })

    return survivors
