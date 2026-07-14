# engine/gates.py

# ==========================================================
# MLB HR BLENDER vFINAL
# TRUE ELIMINATION ENGINE
# GATES 1–18
# ==========================================================


# ==========================================================
# GATE 1
# PULL %
# ==========================================================

def gate_1(players):

    survivors = []

    for p in players:

        pull = p.get("pull")

        if pull is None:
            survivors.append(p)
            continue

        if pull >= 65:
            survivors.append(p)

    return survivors


# ==========================================================
# GATE 2
# HARD HIT
# ==========================================================

def gate_2(players):

    survivors = []

    for p in players:

        hh = p.get("hard_hit")

        if hh is None:
            survivors.append(p)
            continue

        if hh >= 45:
            survivors.append(p)

    return survivors


# ==========================================================
# GATE 3
# COMBINED TRIGGER
# ==========================================================

def gate_3(players):

    survivors = []

    for p in players:

        pull = p.get("pull")
        hh = p.get("hard_hit")

        if pull is None or hh is None:
            survivors.append(p)
            continue

        if pull >= 70 and hh >= 45:
            survivors.append(p)

        elif pull >= 65 and hh >= 50:
            survivors.append(p)

    return survivors


# ==========================================================
# GATE 4
# CONDITION
# ==========================================================

def gate_4(players):

    return players


# ==========================================================
# GATE 5
# PITCH EDGE
# ==========================================================

def gate_5(players):

    survivors = []

    for p in players:

        edge = p.get("pitch_edge")

        if edge is None:
            survivors.append(p)
            continue

        if edge >= 0:
            survivors.append(p)

    return survivors


# ==========================================================
# GATE 6
# DAMAGE PROFILE
# ==========================================================

def gate_6(players):

    survivors = []

    for p in players:

        barrel = p.get("barrel")
        ev = p.get("exit_velocity")

        if barrel is None or ev is None:
            survivors.append(p)
            continue

        if barrel >= 12 and ev >= 89:
            survivors.append(p)

    return survivors


# ==========================================================
# GATE 7
# FINISHER PROFILE
# ==========================================================

def gate_7(players):

    survivors = []

    for p in players:

        checks = 0

        if (p.get("pull") or 0) >= 65:
            checks += 1

        if (p.get("hard_hit") or 0) >= 45:
            checks += 1

        if (p.get("pitch_edge") or 0) >= 0:
            checks += 1

        if p.get("hr_heat"):
            checks += 1

        if (p.get("slot") or 9) <= 5:
            checks += 1

        if checks >= 4:
            survivors.append(p)

    return survivors


# ==========================================================
# PASS THROUGH GATES
# (Until real data is connected)
# ==========================================================

def gate_8(players):
    return players


def gate_9(players):
    return players


def gate_10(players):
    return players


def gate_10_5(players):
    return players


def gate_11(players):
    return players


def gate_12(players):
    return players


def gate_13(players):
    return players


def gate_14(players):
    return players


def gate_15(players):
    return players


def gate_16(players):
    return players


def gate_17(players):
    return players


# ==========================================================
# GATE 18
# FINAL LOCK
# ==========================================================

def gate_18(players):

    if not players:
        return None

    return players[0]


# ==========================================================
# MASTER EXECUTION
# ==========================================================

def run_all_gates(players):

    audit = []

    gates = [

        ("Gate 1", gate_1),
        ("Gate 2", gate_2),
        ("Gate 3", gate_3),
        ("Gate 4", gate_4),
        ("Gate 5", gate_5),
        ("Gate 6", gate_6),
        ("Gate 7", gate_7),
        ("Gate 8", gate_8),
        ("Gate 9", gate_9),
        ("Gate 10", gate_10),
        ("Gate 10.5", gate_10_5),
        ("Gate 11", gate_11),
        ("Gate 12", gate_12),
        ("Gate 13", gate_13),
        ("Gate 14", gate_14),
        ("Gate 15", gate_15),
        ("Gate 16", gate_16),
        ("Gate 17", gate_17)

    ]

    survivors = players

    for name, gate in gates:

        before = len(survivors)

        survivors = gate(survivors)

        after = len(survivors)

        audit.append({

            "gate": name,
            "before": before,
            "after": after

        })

    winner = gate_18(survivors)

    return winner, audit
