from services.handedness import get_handedness_profile

def apply_gates(hitters, pitcher_name="unknown", pitcher_hand="RHP"):

    survivors = []

    for h in hitters:

        if not h.get("name"):
            continue

        hitter_hand = get_handedness_profile(h["name"])

        base_score = h.get("matchup_score", 0.4)

        # ⚖️ HANDEDNESS EDGE LOGIC
        hand_boost = 0.0

        # LHH vs RHP advantage
        if hitter_hand == "LHH" and pitcher_hand == "RHP":
            hand_boost += 0.10

        # RHH vs LHP advantage
        if hitter_hand == "RHH" and pitcher_hand == "LHP":
            hand_boost += 0.10

        # same-side penalty
        if hitter_hand == "RHH" and pitcher_hand == "RHP":
            hand_boost -= 0.05

        if hitter_hand == "LHH" and pitcher_hand == "LHP":
            hand_boost -= 0.05

        total_score = base_score + hand_boost

        h["hand_score"] = total_score

        # 🔒 STABLE THRESHOLD
        if total_score < 0.32:
            continue

        survivors.append(h)

    return survivors
