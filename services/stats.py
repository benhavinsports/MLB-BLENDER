# services/stats.py

import requests

# ==========================================================
# MLB HR BLENDER vFINAL
# MASTER PLAYER DATA LAYER
# ==========================================================

CACHE = {}

MLB_API = "https://statsapi.mlb.com/api/v1/people"


def get_player_stats(player_id):

    """
    Returns ONE standardized player profile.

    Every gate reads from this.

    Never rename these keys.
    """

    if not player_id:
        return {}

    if player_id in CACHE:
        return CACHE[player_id]

    try:

        url = (
            f"{MLB_API}/{player_id}"
            "?hydrate=stats(group=[hitting,pitching],type=[season])"
        )

        data = requests.get(
            url,
            timeout=10
        ).json()

    except Exception:

        return {}

    people = data.get(
        "people",
        []
    )

    if not people:
        return {}

    person = people[0]

    profile = {

        # -------------------------
        # Identity
        # -------------------------

        "id": player_id,

        "name":
            person.get(
                "fullName",
                "UNKNOWN"
            ),

        # -------------------------
        # Gate Inputs
        # -------------------------

        "pull": None,

        "hard_hit": None,

        "barrel": None,

        "exit_velocity": None,

        "blast": None,

        "squared_up": None,

        "sweet_spot": None,

        "bat_speed": None,

        "pitch_edge": None,

        "cond": None,

        "hr_heat": None,

        "hr_pa": None,

        "iso": None,

        "slg": None,

        "woba": None,

        "fb": None,

        "pull_barrel": None,

        "pua": None,

        "fast_swing": None

    }

    CACHE[player_id] = profile

    return profile


# ==========================================================
# ATTACH TO LINEUP
# ==========================================================

def attach_stats(players):

    enriched = []

    for player in players:

        stats = get_player_stats(
            player["id"]
        )

        enriched.append({

            **player,

            **stats

        })

    return enriched
