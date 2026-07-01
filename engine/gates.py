from services.role_filter import is_valid_hitter


def apply_gates(hitters, pitcher_name):

    survivors = []

    for h in hitters:

        # 🔥 ROLE SAFETY
        if not is_valid_hitter(h):
            continue

        base = 0.50

        name = h.get("name", "").lower()

        pitcher = (pitcher_name or "").lower()

        # ⚡ simple matchup bump (safe version)
        if "fastball" in pitcher:
            base += 0.05

        if "slider" in pitcher:
            base += 0.03

        # ⚾ lineup slot value
        slot = h.get("slot", 9)

        if slot <= 2:
            base += 0.04
        elif slot <= 6:
            base += 0.02

        h["score"] = base
        h["matchup_score"] = base * 0.2

        # ❌ soft elimination only (IMPORTANT FIX)
        if base < 0.40:
            continue

        survivors.append(h)

    return survivors
