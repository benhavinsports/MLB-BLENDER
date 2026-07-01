from services.pitch_profile import get_pitch_profile

def apply_gates(hitters, pitcher_name="unknown"):

    profile = get_pitch_profile(pitcher_name)

    survivors = []

    for h in hitters:

        if not h.get("name"):
            continue

        base = h.get("matchup_score", 0.4)

        # 🔥 PITCH SEQUENCE EFFECT
        seq_boost = 0.0

        if profile["sequence"] == "fastball_heavy":
            if "power" in h.get("style", "balanced"):
                seq_boost += 0.12

        if profile["sequence"] == "breaking_ball_heavy":
            seq_boost += 0.08  # timing hitters benefit slightly

        # 🎯 ZONE WEAKNESS EFFECT
        zone_boost = 0.0

        if profile["zone_weakness"] == "high_fastball":
            zone_boost += 0.10

        if profile["zone_weakness"] == "low_outside":
            zone_boost += 0.07

        total = base + seq_boost + zone_boost

        h["final_score"] = total

        # 🔒 STABLE ELIMINATION RULE
        if total < 0.34:
            continue

        survivors.append(h)

    return survivors
