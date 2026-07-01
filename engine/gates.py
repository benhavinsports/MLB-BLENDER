from services.role_filter import is_valid_hitter


def apply_elimination_gates(players):

    survivors = []

    for p in players:

        # -----------------------------
        # GATE 0 — ROLE FILTER
        # -----------------------------
        if not is_valid_hitter(p):
            continue

        # -----------------------------
        # GATE 1 — BASIC VALIDITY
        # -----------------------------
        if not p.get("name"):
            continue

        # -----------------------------
        # GATE 2 — SLOT CHECK (LIGHT WEIGHT ONLY)
        # -----------------------------
        slot = p.get("slot", 9)

        if slot < 1 or slot > 9:
            continue

        # -----------------------------
        # PASS THROUGH (NO SCORING)
        # -----------------------------
        survivors.append(p)

    return survivors
