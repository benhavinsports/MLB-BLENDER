from services.statcast import get_statcast_profile

def apply_gates(hitters):

    survivors = []

    for h in hitters:

        if not h.get("name"):
            continue

        stats = get_statcast_profile(h["name"])

        ev = stats["ev"]
        barrel = stats["barrel_pct"]
        xwoba = stats["xwoba"]

        # 🔥 STATCAST DERIVED METRICS

        pull_pct = min(0.75, (ev - 85) / 30 + 0.45)
        hh_pct = min(0.65, barrel * 5 + 0.35)

        pitch_edge = (xwoba - 0.300) * 2

        h["pull_pct"] = pull_pct
        h["hh_pct"] = hh_pct
        h["pitch_edge"] = pitch_edge

        # 🔒 GATES (NOW POWERED BY STATCAST)

        if pull_pct < 0.45:
            continue

        if hh_pct < 0.35:
            continue

        if pitch_edge < -0.10:
            continue

        survivors.append(h)

    return survivors
