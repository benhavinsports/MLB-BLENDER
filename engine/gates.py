# engine/gates.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 1-18 EXECUTION ENGINE
#
# Every gate logs:
# BEFORE -> AFTER
#
# Undefined data:
# PASS THROUGH
#
# ==========================================================



def gate_log(
    gate,
    before,
    after
):

    return {

        "gate": gate,

        "before": before,

        "after": after

    }




# ==========================================================
# GATE RUNNER
# ==========================================================


def run_all_gates(
    hitters,
    game,
    target_side
):


    survivors = hitters.copy()

    audit = []



    # ======================================================
    # GATE 1 — PULL %
    # ======================================================

    before = len(survivors)


    survivors = [

        h for h in survivors

        if pull_gate(h)

    ]


    audit.append(

        gate_log(
            1,
            before,
            len(survivors)
        )

    )



    # ======================================================
    # GATE 2 — HARD HIT %
    # ======================================================

    before = len(survivors)


    survivors = [

        h for h in survivors

        if hard_hit_gate(h)

    ]


    audit.append(

        gate_log(
            2,
            before,
            len(survivors)
        )

    )



    # ======================================================
    # GATE 3 — COMBINED TRIGGER
    # ======================================================

    for hitter in survivors:

        hitter["hr_trigger"] = (
            combined_trigger(
                hitter
            )
        )


    audit.append(

        gate_log(
            3,
            len(survivors),
            len(survivors)
        )

    )



    # ======================================================
    # GATE 4-18
    #
    # Pass-through until connected
    # to full data sources.
    #
    # ======================================================


    for gate in range(4,19):


        audit.append(

            gate_log(

                gate,

                len(survivors),

                len(survivors)

            )

        )



    return survivors, audit





# ==========================================================
# GATE 1
# ==========================================================


def pull_gate(hitter):


    pull = hitter.get(
        "pull"
    )


    if pull is None:

        return True


    if pull < 50:

        return False


    return True





# ==========================================================
# GATE 2
# ==========================================================


def hard_hit_gate(hitter):


    hh = hitter.get(
        "hard_hit"
    )


    if hh is None:

        return True


    if hh < 40:

        return False


    return True





# ==========================================================
# GATE 3
# ==========================================================


def combined_trigger(hitter):


    pull = hitter.get(
        "pull"
    )


    hh = hitter.get(
        "hard_hit"
    )



    if pull is None or hh is None:

        return "PASS THROUGH"



    if pull >= 70 and hh >=45:

        return "AUTO CORE LOCK"



    if pull >=65 and hh >=50:

        return "SECONDARY PASS"



    if pull >=60 and hh >=40:

        return "WHO PASS"



    return "NEUTRAL"
