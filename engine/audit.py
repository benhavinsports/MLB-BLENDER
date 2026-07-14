# engine/audit.py

# ==========================================================
# MLB HR BLENDER vFINAL
# AUDIT LOGGER
# ==========================================================


def log_gate(
    audit,
    gate,
    before,
    after,
    removed=None
):

    audit.append({

        "gate": gate,

        "before": before,

        "after": after,

        "removed": removed or []

    })



def log_player_removal(
    removed,
    player,
    reason
):

    removed.append({

        "player":
            player.get(
                "name",
                "UNKNOWN"
            ),

        "reason":
            reason

    })



def print_audit(audit):

    for item in audit:

        print(
            f"{item['gate']}: "
            f"{item['before']} → {item['after']}"
        )
