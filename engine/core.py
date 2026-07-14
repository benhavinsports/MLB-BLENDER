# engine/core.py

# ==========================================================
# MLB HR BLENDER vFINAL
# TRUE EVENT ENGINE CONTROLLER
#
# Pipeline:
#
# Slate
#  ↓
# Gate 0 Target Layer
#  ↓
# Hitter Pool
#  ↓
# Gates 1-18
#  ↓
# Ownership
#  ↓
# Final Lock
#
# ==========================================================


from engine.target_layer import (
    rank_offense_targets,
    lock_side
)

from engine.decoy import (
    transfer_event,
    remove_false_chalk
)

from engine.ownership import (
    assign_event_ownership,
    get_owner
)

from engine.final_lock import (
    final_lock
)



# ==========================================================
# GATE LOGGER
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
# GATE EXECUTION
# ==========================================================


def run_gates(players):


    logs = []


    current = players.copy()



    # -------------------------
    # GATE 1 PULL
    # -------------------------

    before = len(current)


    survivors = []


    for p in current:


        pull = p.get(
            "pull"
        )


        if pull is None:

            survivors.append(p)


        elif pull >= 50:

            survivors.append(p)



    current = survivors


    logs.append(
        gate_log(
            1,
            before,
            len(current)
        )
    )



    # -------------------------
    # GATE 2 HARD HIT
    # -------------------------

    before = len(current)


    survivors = []


    for p in current:


        hh = p.get(
            "hard_hit"
        )


        if hh is None:

            survivors.append(p)


        elif hh >= 40:

            survivors.append(p)



    current = survivors


    logs.append(
        gate_log(
            2,
            before,
            len(current)
        )
    )



    # -------------------------
    # GATE 3 COMBO TRIGGER
    # -------------------------

    for p in current:


        pull = p.get(
            "pull"
        )

        hh = p.get(
            "hard_hit"
        )


        if (

            pull is not None

            and hh is not None

        ):


            if pull >= 70 and hh >= 45:

                p["hr_model_score"] = 100


            elif pull >= 65 and hh >= 50:

                p["hr_model_score"] = 90


            else:

                p["hr_model_score"] = 50




    logs.append(

        gate_log(

            3,

            len(current),

            len(current)

        )

    )



    # Remaining gates pass through
    # until data fields are connected.


    return current, logs




# ==========================================================
# MAIN BLENDER
# ==========================================================


def run_blender(games):


    results = []



    for game in games:


        # --------------------------------
        # Gate 0 Target Layer
        # --------------------------------


        targets = rank_offense_targets(
            games
        )


        target = next(

            (

                t for t in targets

                if t["game_id"]

                == game.get("game_id")

            ),

            None

        )


        if not target:


            continue



        locked = lock_side(
            target
        )



        # --------------------------------
        # HITTER POOL PLACEHOLDER
        #
        # Connected when lineup
        # service is added.
        # --------------------------------


        hitters = game.get(
            "hitters",
            []
        )



        survivors, logs = run_gates(
            hitters
        )



        # --------------------------------
        # DECOY
        # --------------------------------


        survivors = transfer_event(
            survivors
        )


        survivors = remove_false_chalk(
            survivors
        )



        # --------------------------------
        # OWNERSHIP
        # --------------------------------


        survivors = assign_event_ownership(
            survivors
        )



        owner = get_owner(
            survivors
        )



        final = final_lock(

            game,

            [owner] if owner else []

        )



        final["gate_log"] = logs

        final["target_side"] = locked


        results.append(
            final
        )



    return results
