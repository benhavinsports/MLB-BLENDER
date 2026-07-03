def apply_elimination_gates(lineup, pitcher_profile):
    """
    BLENDER V3 — PURE SCORING ENGINE (NO EARLY EXITS)
    """

    enriched = []

    for p in lineup:

        slot = p.get("slot", 9)
        gate_log = []

        # =========================
        # GATE 0 — SLOT VALUE
        # =========================
        slot_score = max(1, 10 - slot)

        gate_log.append({
            "gate": 0,
            "score": slot_score,
            "pass": slot_score >= 1
        })

        # =========================
        # GATE 1 — PLATOON
        # =========================
        platoon = 1 if pitcher_profile and (
            (pitcher_profile.get("weak_vs_right") and p.get("handedness") == "R") or
            (pitcher_profile.get("weak_vs_left") and p.get("handedness") == "L")
        ) else 0.5

        gate_log.append({"gate": 1, "score": platoon})

        # =========================
        # GATE 2 — PARK FACTOR
        # =========================
        park = pitcher_profile.get("park_factor", 1)

        gate_log.append({"gate": 2, "score": park})

        # =========================
        # GATE 3 — LINEUP VALUE
        # =========================
        lineup_score = max(1, 8 - slot)

        gate_log.append({"gate": 3, "score": lineup_score})

        # =========================
        # GATE 4 — HARD HIT
        # =========================
        hh = (p.get("hardhit_pct", 40) / 100)

        gate_log.append({"gate": 4, "score": hh})

        # =========================
        # GATE 5 — EXIT VELOCITY
        # =========================
        ev = (p.get("exit_velocity", 88) - 85) / 10

        gate_log.append({"gate": 5, "score": ev})

        # =========================
        # GATE 6 — BARREL
        # =========================
        barrel = p.get("barrel_pct", 10) / 100

        gate_log.append({"gate": 6, "score": barrel})

        # =========================
        # GATE 7 — RHYTHM
        # =========================
        rhythm = (p.get("hr_last10", 0) * 2) + p.get("barrels_last10", 0)

        gate_log.append({"gate": 7, "score": rhythm})

        # =========================
        # GATE 8 — CONVERSION
        # =========================
        pa = max(1, p.get("pa", 1))
        conversion = p.get("hr_season", 0) / pa

        gate_log.append({"gate": 8, "score": conversion})

        # =========================
        # GATE 9 — ENVIRONMENT
        # =========================
        env = pitcher_profile.get("park_factor", 1)

        gate_log.append({"gate": 9, "score": env})

        # =========================
        # GATE 10 — OPPORTUNITY
        # =========================
        opp = (8 - slot) + (pa / 4)

        gate_log.append({"gate": 10, "score": opp})

        # =========================
        # GATE 11 — DECOY
        # =========================
        decoy = p.get("decoy_score", 0)

        gate_log.append({"gate": 11, "score": decoy})

        # =========================
        # GATE 12 — BULLPEN
        # =========================
        bullpen = pitcher_profile.get("bullpen_hr9", 1)

        gate_log.append({"gate": 12, "score": bullpen})

        # =========================
        # GATE 13 — OWNERSHIP
        # =========================
        ownership = slot_score + ev + barrel

        gate_log.append({"gate": 13, "score": ownership})

        # =========================
        # GATE 14 — NUMERICAL
        # =========================
        jersey = p.get("jersey", 0)
        num = abs((jersey % 9) - slot)

        gate_log.append({"gate": 14, "score": num})

        # =========================
        # GATE 15 — PROTECTION
        # =========================
        prot = p.get("protection_rating", 50)

        gate_log.append({"gate": 15, "score": prot})

        # =========================
        # GATE 16 — FINISHER
        # =========================
        finisher = hh + barrel + ev

        gate_log.append({"gate": 16, "score": finisher})

        # =========================
        # GATE 17 — COLLAPSE
        # =========================
        collapse = (ev + barrel) / 2

        gate_log.append({"gate": 17, "score": collapse})

        # =========================
        # GATE 18 — FINAL SCORE
        # =========================
        final_score = (
            slot_score +
            ev +
            barrel +
            rhythm +
            ownership +
            finisher
        )

        gate_log.append({"gate": 18, "score": final_score})

        enriched.append({
            "id": p["id"],
            "name": p.get("name", p["id"]),
            "slot": slot,
            "final_score": final_score,
            "gates": gate_log
        })

    return enriched
