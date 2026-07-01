from services.statcast import get_statcast_profile

def apply_gates(hitters):

    survivors = []

    for h in hitters:

        if not h.get("name"):
            continue

        stats = get_statcast_profile(h["name"])

        ev = stats["ev"]
        barrel = stats["barrel"]
        x = stats["x"]

        # 🔥 ACCURACY SIGNAL ENGINE
        power_score = (ev - 85) / 10
        barrel_score = barrel * 4
        matchup_score = x - 0.300

        total_score = power_score + barrel_score + matchup_score

        h["score"] = total_score

        # ⚖️ GATES (STABLE BUT NOW INFORMED)
        if total_score < 0.25:
            continue

        survivors.append(h)

    return survivors
