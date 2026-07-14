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
# ENGINE CONTROLLER
# ==========================================================


def run_blender(games):

    results = []

    for game in games:

        results.append(
            process_game(game)
        )

    return results



# ==========================================================
# SINGLE GAME
# ==========================================================


def process_game(game):

    audit = []


    # -------------------------
    # LOAD LINEUP
    # -------------------------

    hitters = get_game_lineup(
        game.get("game_id")
    )


    audit.append({
        "stage": "LINEUP",
        "count": len(hitters)
    })



    # -------------------------
    # ATTACH STATS
    # -------------------------

    hitters = attach_stats(
        hitters
    )


    audit.append({
        "stage": "STATS",
        "count": len(hitters)
    })



    survivors = hitters



    # -------------------------
    # GATE 1-18 ORDER
    # -------------------------

    gate_chain = [

        ("Gate 1 Pull", gate_pull),

        ("Gate 2 Damage", gate_hard_hit),

        ("Gate 3 Trigger", gate_combined),

        ("Gate 4 Condition", gate_condition),

        ("Gate 5 Pitch Edge", gate_pitch_edge),

        ("Gate 6 Damage Profile", gate_damage),

        ("Gate 7 Finisher", gate_finisher),

        ("Gate 8 Conversion", gate_pass),

        ("Gate 9 Environment", gate_pass),

        ("Gate 10 Opportunity", gate_pass),

        ("Gate 10.5 Decoy Transfer", gate_pass),

        ("Gate 11 Bullpen", gate_pass),

        ("Gate 12 Event Ownership", gate_pass),

        ("Gate 13 Numerology", gate_pass),

        ("Gate 14 Protection", gate_pass),

        ("Gate 15 Finisher Check", gate_pass),

        ("Gate 16 Last Elimination", gate_pass),

        ("Gate 17 Audit", gate_pass)

    ]



    for name, gate in gate_chain:


        before = len(
            survivors
        )


        survivors = [

            hitter

            for hitter in survivors

            if gate(hitter)

        ]


        after = len(
            survivors
        )


        audit.append({

            "gate":
                name,

            "before":
                before,

            "after":
                after

        })



    # -------------------------
    # GATE 18 FINAL LOCK
    # -------------------------

    survivor = final_lock(
        survivors
    )



    return {

        "game":
            f"{game['away']} vs {game['home']}",


        "survivor":
            survivor,


        "status":
            "LOCKED",


        "audit":
            audit

    }




# ==========================================================
# FINAL EVENT OWNER
# ==========================================================


def final_lock(players):

    if not players:

        return "NO SURVIVOR"


    # temporary deterministic lock
    # ranking layer comes later

    return players[0].get(
        "name",
        "UNKNOWN"
    )
