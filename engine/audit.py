# engine/audit.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 17 — FINAL AUDIT ENGINE
#
# Checks the Blender output before final lock.
#
# ==========================================================



def run_audit(
    survivors,
    logs
):


    audit = {

        "passed": True,

        "issues": []

    }



    # ======================================================
    # CHECK 1 — GATE COMPLETION
    # ======================================================


    gate_check = check_gates(
        logs
    )


    if not gate_check:


        audit["passed"] = False


        audit["issues"].append(

            "MISSING_GATE_EXECUTION"

        )



    # ======================================================
    # CHECK 2 — EMPTY SURVIVOR
    # ======================================================


    if not survivors:


        audit["passed"] = False


        audit["issues"].append(

            "NO_SURVIVOR"

        )



    # ======================================================
    # CHECK 3 — DUPLICATE ARCHETYPE
    # ======================================================


    duplicate = duplicate_profiles(
        survivors
    )


    if duplicate:


        audit["passed"] = False


        audit["issues"].append(

            "DUPLICATE_ARCHETYPE"

        )



    return audit





# ==========================================================
# GATE CHECK
# ==========================================================


def check_gates(logs):


    if not logs:

        return False



    executed = set()



    for item in logs:


        gate = item.get(
            "gate"
        )


        if gate:

            executed.add(
                gate
            )



    required = set(
        range(1,19)
    )


    return required.issubset(
        executed
    )





# ==========================================================
# DUPLICATE PROFILE CHECK
# ==========================================================


def duplicate_profiles(
    survivors
):


    archetypes = []


    for hitter in survivors:


        archetype = hitter.get(
            "archetype"
        )


        if not archetype:

            continue



        if archetype in archetypes:

            return True



        archetypes.append(
            archetype
        )



    return False





# ==========================================================
# AUDIT SUMMARY
# ==========================================================


def audit_message(
    audit
):


    if audit["passed"]:


        return "AUDIT PASSED"



    return (

        "AUDIT FAILED: "

        +

        ", ".join(

            audit["issues"]

        )

    )
