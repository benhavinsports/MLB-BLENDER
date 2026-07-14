# engine/core.py

from services.lineup import get_game_lineup


# ==========================================================
# MLB HR BLENDER vFINAL
# ENGINE CONTROLLER
# ==========================================================


def run_blender(games):

    results = []

    for game in games:

        result = process_game(game)

        results.append(result)

    return results



# ==========================================================
# PROCESS SINGLE GAME
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

        "stage":
            "LINEUP",

        "hitters_loaded":
            len(hitters)

    })


    # -------------------------
    # GATE 0
    # -------------------------

    audit.append(
        gate_0_target_layer(game)
    )


    # -------------------------
    # GATE PIPELINE
    # -------------------------

    survivors = hitters


    gates = [

        gate_1_environment,

        gate_2_pool_build,

        gate_3_pull,

        gate_4_damage,

        gate_5_pitch_matchup,

        gate_6_slot_weakness,

        gate_7_rhythm,

        gate_8_conversion,

        gate_9_environment_check,

        gate_10_opportunity,

        gate_10_5_decoy,

        gate_11_bullpen,

        gate_12_event_owner,

        gate_13_numerology,

        gate_14_protection,

        gate_15_finisher

    ]


    for gate in gates:

        survivors = apply_gate(
            survivors,
            gate,
            audit
        )



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
# GATE RUNNER
# ==========================================================


def apply_gate(players, gate, audit):

    before = len(players)


    after_players = []


    for player in players:

        if gate(player):

            after_players.append(player)



    audit.append({

        "gate":
            gate.__name__,

        "before":
            before,

        "after":
            len(after_players)

    })


    return after_players




# ==========================================================
# GATES
# ==========================================================


def gate_0_target_layer(game):

    return {

        "gate":0,

        "status":"PASS"

    }



def gate_1_environment(player):
    return True



def gate_2_pool_build(player):
    return True



def gate_3_pull(player):

    pull = player.get(
        "pull",
        65
    )

    return pull >= 50



def gate_4_damage(player):

    hh = player.get(
        "hard_hit",
        45
    )

    return hh >= 40



def gate_5_pitch_matchup(player):
    return True



def gate_6_slot_weakness(player):
    return True



def gate_7_rhythm(player):
    return True



def gate_8_conversion(player):
    return True



def gate_9_environment_check(player):
    return True



def gate_10_opportunity(player):
    return True



def gate_10_5_decoy(player):
    return True



def gate_11_bullpen(player):
    return True



def gate_12_event_owner(player):
    return True



def gate_13_numerology(player):
    return True



def gate_14_protection(player):
    return True



def gate_15_finisher(player):
    return True




# ==========================================================
# FINAL LOCK
# ==========================================================


def final_lock(players):

    if not players:

        return "NO SURVIVOR"


    return players[0].get(
        "name",
        "UNKNOWN"
    )
