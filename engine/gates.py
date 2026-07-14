# engine/gates.py


# ==========================================================
# MLB HR BLENDER vFINAL
# GATE MATH ENGINE
# ==========================================================


def pass_through(value):

    return value is None



# ==========================================================
# GATE 1 — PULL %
# ==========================================================

def gate_pull(player):

    pull = player.get(
        "pull"
    )

    if pull is None:
        return True


    if pull < 50:
        return False


    return True




# ==========================================================
# GATE 2 — HARD HIT %
# ==========================================================

def gate_hard_hit(player):

    hh = player.get(
        "hard_hit"
    )


    if hh is None:
        return True


    if hh < 40:
        return False


    return True




# ==========================================================
# GATE 3 — COMBINED TRIGGER
# ==========================================================

def gate_combined(player):

    pull = player.get(
        "pull"
    )

    hh = player.get(
        "hard_hit"
    )


    if pull is None or hh is None:
        return True


    auto_pass = (
        pull >= 70
        and hh >= 45
    )


    secondary = (
        pull >= 65
        and hh >= 50
    )


    return auto_pass or secondary




# ==========================================================
# GATE 4 — CONDITION
# ==========================================================

def gate_condition(player):

    cond = player.get(
        "cond"
    )


    if cond is None:
        return True


    # boost only
    return True




# ==========================================================
# GATE 5 — PITCH EDGE
# ==========================================================

def gate_pitch_edge(player):

    edge = player.get(
        "pitch_edge"
    )


    if edge is None:
        return True


    if edge < 0:
        return False


    return True




# ==========================================================
# GATE 6 — DAMAGE ENGINE
# STRENGTHENED
# ==========================================================

def gate_damage(player):

    checks = []


    for key in [

        "hard_hit",
        "barrel",
        "exit_velocity",
        "blast",
        "squared_up",
        "sweet_spot",
        "bat_speed"

    ]:

        value = player.get(
            key
        )

        if value is not None:

            checks.append(value)



    # if data missing, pass through

    if not checks:
        return True



    damage_points = 0



    if player.get("hard_hit",0) >= 45:
        damage_points += 1


    if player.get("barrel",0) >= 12:
        damage_points += 1


    if player.get("exit_velocity",0) >= 89:
        damage_points += 1


    if player.get("blast",0) >= 14:
        damage_points += 1


    if player.get("squared_up",0) >= 30:
        damage_points += 1


    if player.get("sweet_spot",0) >= 34:
        damage_points += 1


    if player.get("bat_speed",0) >= 72:
        damage_points += 1



    return damage_points >= 2




# ==========================================================
# GATE 7 — FINISHER PROFILE
# STRENGTHENED
# ==========================================================

def gate_finisher(player):

    passed = 0



    if player.get("pull",0) >= 65:
        passed += 1


    if player.get("hard_hit",0) >= 45:
        passed += 1


    if player.get("pitch_edge",0) >= 0:
        passed += 1


    if player.get("hr_heat"):

        passed += 1


    if player.get("slot",9) <= 5:

        passed += 1



    return passed >= 4




# ==========================================================
# GATE 8-18
# PASS THROUGH UNTIL DATA MODULES CONNECT
# ==========================================================


def gate_pass(player):

    return True
