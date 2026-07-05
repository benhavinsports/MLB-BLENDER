def gate_0_to_18(hitter, pitcher, game, weak_slot_map):

    # 🔴 GATE 0
    if game["invalid"]:
        return {"pass": False}

    # 🟡 GATE 1 ENVIRONMENT
    if not game["env_ok"]:
        return {"pass": False}

    # 🟠 GATE 2 POOL
    if hitter["is_bench"]:
        return {"pass": False}

    # 🔵 GATE 3 PULL
    if hitter["pull_pct"] < 65:
        return {"pass": False}

    # 🔴 GATE 4 DAMAGE
    if hitter["hard_hit"] < 38:
        return {"pass": False}

    # 🔵 GATE 5 MATCHUP
    if hitter["bad_vs_pitch"] == pitcher["primary_pitch"]:
        return {"pass": False}

    # 🟡 GATE 6 SLOT WEAKNESS (HARD RULE)
    if weak_slot_map[hitter["slot"]] == "PROTECTED":
        return {"pass": False}

    # 🔄 GATE 7 RHYTHM
    if hitter["last10_hr"] + hitter["barrels"] < 3:
        return {"pass": False}

    # ⚡ GATE 8 CONVERSION
    if hitter["hr_per_pa"] < 0.045:
        return {"pass": False}

    # 🌎 GATE 9 ENVIRONMENT CONFIRM
    if not game["park_ok"]:
        return {"pass": False}

    # 🎯 GATE 10 OPPORTUNITY
    if hitter["pa_projection"] < 4.5:
        return {"pass": False}

    # 🧲 GATE 10.5 DECOY TRANSFER FLAG (NOT SCORE)
    decoy = False
    if hitter["is_chalk"] and game["gap"] < 10:
        decoy = True

    # 🧱 GATE 11 BULLPEN
    if pitcher["bullpen_hr9"] < 1.0:
        return {"pass": False}

    # 🎯 GATE 12 EVENT OWNERSHIP (CORE DECISION POINT)
    ownership_score = calculate_event_ownership(hitter, pitcher, game)

    # 🧨 GATE 13 NUMERICAL ONLY IF NEEDED (tie-break only)

    # 🧱 GATE 14 PROTECTION
    if hitter["isolated"]:
        return {"pass": False}

    # 🧾 GATE 15 FINISHER
    if not hitter["finisher_profile"]:
        return {"pass": False}

    # 🧨 GATE 16 COLLAPSE RULE (IMPORTANT)
    if decoy and hitter["is_strongest_profile"]:
        return {"pass": False}

    # 🔴 GATE 17 AUDIT
    if hitter["invalid_state"]:
        return {"pass": False}

    # 🏁 GATE 18 FINAL LOCK OUTPUT
    return {
        "pass": True,
        "hitter": hitter,
        "alignment_score": ownership_score
    }
