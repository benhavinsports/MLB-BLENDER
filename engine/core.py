# engine/core.py

from services.lineup import get_game_lineup
from services.stats import attach_stats

from engine.audit import (
    log_gate,
    log_player_removal
)

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
# CORE CONTROLLER
# ==========================================================


def run_blender(games):

    results = []

    for game in games:

        players = get_game_lineup(
            game["game_id"]
        )

        players = attach_stats(players)

        audit = []

        # --------------------------
        # Gate execution order
        # --------------------------

        gate_sequence = [

            ("Gate 1 Pull", gate_pull),

            ("Gate 2 Hard Hit", gate_hard_hit),

            ("Gate 3 Combined", gate_combined),

            ("Gate 4 Condition", gate_condition),

            ("Gate 5 Pitch Edge", gate_pitch_edge),

            ("Gate 6 Damage", gate_damage),

            ("Gate 7 Finisher", gate_finisher),

            ("Gate 8", gate_pass),

            ("Gate 9", gate_pass),

            ("Gate 10", gate_pass),

            ("Gate 11", gate_pass),

            ("Gate 12", gate_pass),

            ("Gate 13", gate_pass),

            ("Gate 14", gate_pass),

            ("Gate 15", gate_pass),

            ("Gate 16", gate_pass),

            ("Gate 17", gate_pass),

            ("Gate 18", gate_pass)

        ]

        # --------------------------
        # Run every gate
        # --------------------------

        for gate_name, gate in gate_sequence:

            before = len(players)

            removed = []

            survivors = []

            for player in players:

                if gate(player):

                    survivors.append(player)

                else:

                    log_player_removal(

                        removed,

                        player,

                        gate_name

                    )

            players = survivors

            after = len(players)

            log_gate(

                audit,

                gate_name,

                before,

                after,

                removed

            )

            if len(players) <= 1:

                break

        # --------------------------
        # Final survivor
        # --------------------------

        if players:

            survivor = players[0]["name"]

        else:

            survivor = "NO SURVIVOR"

        results.append({

            "game": f"{game['away']} vs {game['home']}",

            "survivor": survivor,

            "audit": audit

        })

    return results
