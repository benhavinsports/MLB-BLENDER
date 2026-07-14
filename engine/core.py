# engine/core.py

from services.lineup import get_game_lineup
from services.stats import attach_stats

from engine.gates import (
    gate_pull,
    gate_hard_hit,
    gate_combined,
    gate_condition,
    gate_pitch_edge,
    gate_damage,
    gate_finisher,
    gate_pass
)


# ==========================================================
# MLB HR BLENDER vFINAL
# SINGLE ENGINE CONTROLLER
# ==========================================================


def run_blender(games):

    results = []


    for game in games:

        results.append(
            run_game(game)
        )


    return results




def run_game(game):


    audit = []


    # -------------------------
    # STEP 1
    # LINEUP LOAD
    # -------------------------

    hitters = get_game_lineup(
        game.get("game_id")
    )


    audit.append({

        "stage":
        "LINEUP",

        "players":
        len(hitters)

    })



    # -------------------------
    # STEP 2
    # STAT ATTACHMENT
    # -------------------------

    hitters = attach_stats(
        hitters
    )


    audit.append({

        "stage":
        "STATS",

        "players":
        len(hitters)

    })



    survivors = hitters



    # -------------------------
    # GATE 1-18
    # -------------------------

    pipeline = [

        ("Gate 1 Pull", gate_pull),

        ("Gate 2 Hard Hit", gate_hard_hit),

        ("Gate 3 Combined", gate_combined),

        ("Gate 4 Condition", gate_condition),

        ("Gate 5 Pitch Edge", gate_pitch_edge),

        ("Gate 6 Damage", gate_damage),

        ("Gate 7 Finisher", gate_finisher),

        ("Gate 8 Conversion", gate_pass),

        ("Gate 9 Environment", gate_pass),

        ("Gate 10 Opportunity", gate_pass),

        ("Gate 10.5 Decoy", gate_pass),

        ("Gate 11 Bullpen", gate_pass),

        ("Gate 12 Ownership", gate_pass),

        ("Gate 13 Numerology", gate_pass),

        ("Gate 14 Protection", gate_pass),

        ("Gate 15 Finish", gate_pass),

        ("Gate 16 Last Elimination", gate_pass),

        ("Gate 17-18 Audit Lock", gate_pass)

    ]



    for name, gate in pipeline:


        before = len(
            survivors
        )


        survivors = [

            player

            for player in survivors

            if gate(player)

        ]


        audit.append({

            "gate":
            name,

            "before":
            before,

            "after":
            len(survivors)

        })



    # -------------------------
    # FINAL LOCK
    # -------------------------

    survivor = lock_survivor(
        survivors
    )



    return {

        "game":
        f"{game['away']} vs {game['home']}",


        "survivor":
        survivor,


        "audit":
        audit,


        "status":
        "LOCKED"

    }




# ==========================================================
# FINAL EVENT OWNER
# ==========================================================


def lock_survivor(players):


    if not players:

        return "NO SURVIVOR"



    # temporary deterministic lock
    # ranking layer comes later

    return players[0].get(
        "name",
        "UNKNOWN"
    )
