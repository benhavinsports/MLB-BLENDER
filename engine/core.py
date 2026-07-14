# engine/core.py

"""
MLB HR BLENDER vFINAL

TRUE EVENT ENGINE

Pipeline:

Slate
 ↓
Gate 0
 ↓
Gate 1
 ↓
Gate 2
 ↓
...
Gate 18
 ↓
Final Survivor
"""


# ==========================================================
# MAIN ENTRY
# ==========================================================


def run_blender(games):

    """
    Receives slate from app.py

    Returns:

    [
        {
            "game": "...",
            "survivor": "...",
            "status": "LOCKED",
            "audit": [...]
        }
    ]

    """

    results = []


    for game in games:

        result = process_game(game)

        results.append(result)


    return results



# ==========================================================
# GAME PROCESSOR
# ==========================================================


def process_game(game):

    audit = []


    # --------------------------
    # GATE 0
    # TARGET LAYER
    # --------------------------

    gate0 = gate_0_target_layer(game)

    audit.append(gate0)



    # --------------------------
    # GATE 1
    # ENVIRONMENT
    # --------------------------

    gate1 = gate_1_environment(game)

    audit.append(gate1)



    # --------------------------
    # GATE 2
    # POOL BUILD
    # --------------------------

    hitters = gate_2_pool_build(game)

    audit.append({
        "gate": 2,
        "status": "PASS",
        "count": len(hitters)
    })



    # --------------------------
    # GATES 3-15
    # --------------------------
    #
    # Each gate will eliminate
    # or pass hitters.
    #
    # No reranking.
    # No star bias.
    #


    survivors = hitters


    survivors = run_gate(
        3,
        survivors,
        gate_3_pull
    )


    survivors = run_gate(
        4,
        survivors,
        gate_4_damage
    )


    survivors = run_gate(
        5,
        survivors,
        gate_5_pitch_matchup
    )


    survivors = run_gate(
        6,
        survivors,
        gate_6_slot_weakness
    )


    survivors = run_gate(
        7,
        survivors,
        gate_7_rhythm
    )


    survivors = run_gate(
        8,
        survivors,
        gate_8_conversion
    )


    survivors = run_gate(
        9,
        survivors,
        gate_9_environment
    )


    survivors = run_gate(
        10,
        survivors,
        gate_10_opportunity
    )


    survivors = run_gate(
        "10.5",
        survivors,
        gate_10_5_decoy
    )


    survivors = run_gate(
        11,
        survivors,
        gate_11_bullpen
    )


    survivors = run_gate(
        12,
        survivors,
        gate_12_event_owner
    )


    survivors = run_gate(
        13,
        survivors,
        gate_13_numerology
    )


    survivors = run_gate(
        14,
        survivors,
        gate_14_protection
    )


    survivors = run_gate(
        15,
        survivors,
        gate_15_finisher
    )



    # --------------------------
    # FINAL ISOLATION
    # --------------------------

    survivor = gate_18_final_lock(
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
# HELPERS
# ==========================================================


def run_gate(number, hitters, gate):

    output = []

    for hitter in hitters:

        if gate(hitter):

            output.append(hitter)


    return output



# ==========================================================
# GATE STUBS
# ==========================================================
# Logic gets built here.
# Nothing lives outside core.py.


def gate_0_target_layer(game):
    return {
        "gate": 0,
        "status": "PASS"
    }


def gate_1_environment(game):
    return {
        "gate": 1,
        "status": "PASS"
    }


def gate_2_pool_build(game):

    # temporary until lineup injection exists
    return game.get(
        "hitters",
        []
    )



def gate_3_pull(hitter):
    return True


def gate_4_damage(hitter):
    return True


def gate_5_pitch_matchup(hitter):
    return True


def gate_6_slot_weakness(hitter):
    return True


def gate_7_rhythm(hitter):
    return True


def gate_8_conversion(hitter):
    return True


def gate_9_environment(hitter):
    return True


def gate_10_opportunity(hitter):
    return True


def gate_10_5_decoy(hitter):
    return True


def gate_11_bullpen(hitter):
    return True


def gate_12_event_owner(hitter):
    return True


def gate_13_numerology(hitter):
    return True


def gate_14_protection(hitter):
    return True


def gate_15_finisher(hitter):
    return True



# ==========================================================
# FINAL LOCK
# ==========================================================


def gate_18_final_lock(hitters):

    if not hitters:

        return "NO SURVIVOR"


    # temporary deterministic lock
    # real ownership logic replaces this

    return hitters[0].get(
        "name",
        "UNKNOWN"
    )# engine/core.py

from services.identity import lock_player_identity


# ==========================================================
# MLB HR BLENDER vFINAL
# CORE ENGINE CONTROLLER
# ==========================================================


def run_slate(games):

    """
    MASTER ENGINE ENTRY

    app.py calls:

        results = run_slate(games)

    Returns:

        [
          {
            game,
            survivor,
            gates,
            why
          }
        ]

    """

    results = []


    for game in games:

        result = run_game(game)

        if result:

            results.append(result)


    return results



# ==========================================================
# SINGLE GAME ENGINE
# ==========================================================


def run_game(game):

    """
    Runs one matchup.

    NO cross-game mixing.
    ONE HR event owner per game.
    """

    away = game.get(
        "away",
        "UNKNOWN"
    )

    home = game.get(
        "home",
        "UNKNOWN"
    )


    game_name = (
        f"{away} vs {home}"
    )


    # ------------------------------------
    # BUILD PLAYER POOL
    # ------------------------------------

    hitters = build_hitter_pool(game)


    if not hitters:

        return {
            "game": game_name,
            "survivor": "NO SURVIVOR",
            "why": "No hitter pool",
            "gates": []
        }



    # ------------------------------------
    # RUN GATES 0-18
    # ------------------------------------

    survivors = []


    gate_log = []


    for hitter in hitters:


        passed, logs = run_gates(
            hitter,
            game
        )


        gate_log.extend(logs)


        if passed:

            survivors.append(
                hitter
            )



    # ------------------------------------
    # FINAL EVENT OWNERSHIP
    # ------------------------------------

    survivor = select_event_owner(
        survivors
    )


    # ------------------------------------
    # IDENTITY LOCK
    # ------------------------------------

    final_name = lock_player_identity(
        survivor
    )


    return {

        "game": game_name,

        "survivor": final_name,

        "why":
            "HR event recipient after Gate 0-18 elimination",

        "gates":
            gate_log

    }



# ==========================================================
# HITTER POOL
# ==========================================================


def build_hitter_pool(game):

    """
    Receives lineup data.

    Later this connects to:
    services.lineup.py

    For now it safely reads existing data.
    """


    hitters = (
        game.get("hitters")
        or
        game.get("lineup")
        or
        []
    )


    return hitters



# ==========================================================
# GATE CONTROLLER
# ==========================================================


def run_gates(hitter, game):


    logs = []


    survived = True



    for gate_number in range(0,19):


        before = survived


        survived = execute_gate(
            gate_number,
            hitter,
            game,
            survived
        )


        logs.append({

            "gate":
                gate_number,

            "before":
                before,

            "after":
                survived

        })



        # HARD ELIMINATION

        if not survived:

            break



    return survived, logs




# ==========================================================
# GATE PLACEHOLDER CONTROLLER
# ==========================================================


def execute_gate(
        gate_number,
        hitter,
        game,
        current_state
):

    """
    Gate logic gets moved here from old scattered files.

    Undefined data = PASS THROUGH

    No fake kills.
    No fake boosts.
    """


    if not current_state:

        return False



    # Until gates.py is merged,
    # everything passes through.

    return True




# ==========================================================
# EVENT OWNERSHIP
# ==========================================================


def select_event_owner(
        survivors
):

    """
    FINAL LOCK

    Not biggest star.
    Not highest name value.

    Uses available Blender score only.

    """


    if not survivors:

        return {
            "name":
                "NO SURVIVOR"
        }



    # Use existing score if available

    survivors = sorted(
        survivors,
        key=lambda x:
            x.get(
                "blender_score",
                0
            ),
        reverse=True
    )


    return survivors[0]
