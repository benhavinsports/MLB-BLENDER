from services.role_filter import is_valid_hitter


def apply_elimination_gates(players, pitcher_profile):

    survivors = []

    weakness = pitcher_profile.get("weakness", "none")

    for p in players:

        # -------------------------
        # GATE 0 — ROLE FILTER
        # -------------------------
        if not is_valid_hitter(p):
            continue

        slot = p.get("slot", 9)

        # -------------------------
        # GATE 1 — SIMPLE ELIMINATION RULES
        # -------------------------

        # pitcher weakness logic (binary pass/fail)

        if weakness == "power_hitters":
            if slot > 4:
                continue  # eliminated

        elif weakness == "timing_hitters":
            if slot > 6:
                continue  # eliminated

        # -------------------------
        # PASS THROUGH ONLY
        # -------------------------
        survivors.append(p)

    return survivors
