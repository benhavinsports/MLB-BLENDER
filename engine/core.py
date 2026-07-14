# engine/core.py

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
