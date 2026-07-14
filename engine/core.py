# engine/core.py

from services.lineup import get_game_lineup
from services.stats import attach_stats


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
# SINGLE GAME PROCESS
# ==========================================================


def process_game(game):

    audit = []


    # -------------------------
    # LOAD HITTABLE POOL
    # -------------------------

    hitters = get_game_lineup(
        game.get("game_id")
    )


    audit.append({
        "step": "LINEUP LOAD",
        "count": len(hitters)
    })



    # -------------------------
    # ATTACH PLAYER DATA
    # -------------------------

    hitters = attach_stats(
        hitters
    )


    audit.append({
        "step": "STATS ATTACHED",
        "count": len(hitters)
    })



    # -------------------------
    # GATE 0
    # -------------------------

    audit.append({

        "gate": 0,

        "target":
            game.get("away")
            + " offense"

    })



    survivors = hitters



    # -------------------------
    # GATES 1-18
    # -------------------------

    gates = [

        gate_1_pull,

        gate_2_damage,

        gate_3_combined_trigger,

        gate_4_condition,

        gate_5_pitch_edge,

        gate_6_hr_heat,

        gate_7_finisher_profile,

        gate_8_opportunity,

        gate_9_environment,

        gate_10_decoy,

        gate_11_bullpen,

        gate_12_event_owner,

        gate_13_numerology,

        gate_14_protection,

        gate_15_finisher,

        gate_16_last_man,

        gate_17_audit,

        gate_18_lock

    ]



    for number, gate in enumerate(gates, 1):

        before = len(survivors)


        survivors = [
            p for p in survivors
            if gate(p)
        ]


        audit.append({

            "gate":
                number,

            "before":
                before,

            "after":
                len(survivors)

        })



    final = choose_survivor(
        survivors
    )



    return {

        "game":
            f"{game['away']} vs {game['home']}",

        "survivor":
            final,

        "audit":
            audit,

        "status":
            "LOCKED"

    }



# ==========================================================
# GATE FUNCTIONS
# ==========================================================


def gate_1_pull(p):

    pull = p.get("pull")

    if pull is None:
        return True

    return pull >= 50



def gate_2_damage(p):

    hh = p.get("hard_hit")

    if hh is None:
        return True

    return hh >= 40



def gate_3_combined_trigger(p):

    pull = p.get("pull")

    hh = p.get("hard_hit")


    if pull is None or hh is None:
        return True


    return (
        pull >= 65
        and hh >= 40
    )



def gate_4_condition(p):
    return True



def gate_5_pitch_edge(p):

    edge = p.get(
        "pitch_edge"
    )

    if edge is None:
        return True

    return edge >= 0



def gate_6_hr_heat(p):
    return True



def gate_7_finisher_profile(p):
    return True



def gate_8_opportunity(p):
    return True



def gate_9_environment(p):
    return True



def gate_10_decoy(p):
    return True



def gate_11_bullpen(p):
    return True



def gate_12_event_owner(p):
    return True



def gate_13_numerology(p):
    return True



def gate_14_protection(p):
    return True



def gate_15_finisher(p):
    return True



def gate_16_last_man(p):
    return True



def gate_17_audit(p):
    return True



def gate_18_lock(p):
    return True



# ==========================================================
# FINAL OUTPUT
# ==========================================================


def choose_survivor(players):

    if not players:
        return "NO SURVIVOR"


    return players[0].get(
        "name",
        "UNKNOWN"
    )
