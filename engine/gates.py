# engine/gates.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE ENGINE
#
# Every gate:
# PASS = keep player
# FAIL = eliminate player
#
# No rankings.
# No star bias.
# ==========================================================



def value(player, key, default=0):

    data = player.get(key)

    if data is None:
        return default

    return data



# ==========================================================
# GATE 1
# PULL PROFILE
# ==========================================================


def gate_pull(player):

    pull = value(
        player,
        "pull"
    )


    if pull < 50:

        return False


    return True



# ==========================================================
# GATE 2
# HARD HIT DAMAGE
# ==========================================================


def gate_hard_hit(player):

    hh = value(
        player,
        "hard_hit"
    )


    if hh < 40:

        return False


    return True



# ==========================================================
# GATE 3
# COMBINED TRIGGER
# ==========================================================


def gate_combined(player):

    pull = value(
        player,
        "pull"
    )

    hh = value(
        player,
        "hard_hit"
    )


    auto_pass = (

        pull >= 70

        and

        hh >= 45

    )


    secondary = (

        pull >= 65

        and

        hh >= 50

    )


    if auto_pass or secondary:

        return True



    # pass through if missing data

    if pull == 0 or hh == 0:

        return True



    return False



# ==========================================================
# GATE 4
# CONDITION PROFILE
# BOOST ONLY
# ==========================================================


def gate_condition(player):

    return True




# ==========================================================
# GATE 5
# PITCH EDGE
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
# GATE 6
# DAMAGE PROFILE
# ==========================================================


def gate_damage(player):

    barrel = value(
        player,
        "barrel"
    )


    ev = value(
        player,
        "exit_velocity"
    )


    hh = value(
        player,
        "hard_hit"
    )


    damage = (

        barrel * 0.4

        +

        ev * 0.3

        +

        hh * 0.3

    )


    if damage >= 45:

        return True



    # missing data pass-through

    if barrel == 0 and ev == 0:

        return True



    return False




# ==========================================================
# GATE 7
# FINISHER PROFILE
# ==========================================================


def gate_finisher(player):


    checks = 0



    if value(player,"pull") >= 65:

        checks += 1



    if value(player,"hard_hit") >= 45:

        checks += 1



    if value(player,"pitch_edge") >= 0:

        checks += 1



    if player.get(
        "hr_heat"
    ):

        checks += 1



    if value(player,"slot",9) <= 5:

        checks += 1



    return checks >= 4




# ==========================================================
# GATE 8-18
# PASS THROUGH UNTIL DATA EXISTS
# ==========================================================


def gate_pass(player):

    return True
