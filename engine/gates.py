from services.pitcher import get_pitcher_profile

def apply_gates(hitters, pitcher_name="unknown"):

    pitcher = get_pitcher_profile(pitcher_name)

    survivors = []

    for h in hitters:

        if not h.get("name"):
            continue

        stats = h.get("score", 0.4)

        # 🎯 MATCHUP WEIGHT (NEW LAYER)
        matchup_boost = 0.0

        # power hitters vs power fastball pitchers
        if pitcher["weakness"] == "power_hitters" and stats > 0.5:
            matchup_boost += 0.15

        # timing hitters vs offspeed pitchers
        if pitcher["weakness"] == "timing_hitters" and stats > 0.45:
            matchup_boost += 0.12

        total_score = stats + matchup_boost

        h["matchup_score"] = total_score

        # 🔒 FINAL GATE LOGIC (STABLE)
        if total_score < 0.30:
            continue

        survivors.append(h)

    return survivors
