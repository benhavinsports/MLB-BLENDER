from services.role_filter import is_valid_hitter


def apply_gates(hitters, pitcher_name):
    """
    ROLE-SAFE MLB BLENDER GATES
    - hitter-only enforcement
    - stable scoring
    - no over-elimination
    """

    survivors = []

    for h in hitters:

        # -----------------------------
        # 🚨 GATE 0 — ROLE VALIDATION
        # -----------------------------
        if not is_valid_hitter(h):
            continue

        # -----------------------------
        # ⚙️ BASE SCORE
        # -----------------------------
        base = 0.50

        name = h.get("name", "").lower()

        # -----------------------------
        # ⚡ SIMPLE PITCHER CONTEXT BOOST
        # -----------------------------
        pitcher = (pitcher_name or "").lower()

        if any(x in pitcher for x in ["fastball", "burnes", "cole", "strider"]):
            base += 0.08

        if any(x in pitcher for x in ["snell", "kirby", "gallen"]):
            base += 0.05

        # -----------------------------
        # 🔥 SLOT VALUE (LINEUP POSITION)
        # -----------------------------
        slot = h.get("slot", 9)

        if slot <= 2:
            base += 0.05
        elif slot <= 6:
            base += 0.03
        else:
            base += 0.00

        # -----------------------------
        # 🧠 STABILITY CHECK (SAFE PASS ONLY)
        # -----------------------------
        h["score"] = base
        h["matchup_score"] = base * 0.2

        # -----------------------------
        # ❌ ELIMINATION RULE (SOFT)
        # -----------------------------
        # IMPORTANT: do NOT hard-kill too aggressively
        if base < 0.45:
            continue

        survivors.append(h)

    return survivors
