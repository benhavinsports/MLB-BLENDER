# services/stats.py

import requests


# ==========================================================
# MLB HR BLENDER vFINAL
# PLAYER STAT INJECTION LAYER
# ==========================================================


CACHE = {}



def get_player_stats(player_id):

    """
    Returns player data for Blender.

    This layer ONLY collects data.

    Gates decide later.
    """


    if not player_id:
        return {}



    if player_id in CACHE:
        return CACHE[player_id]



    stats = {

        "id": player_id,

        # Identity
        "name": None,

        # HR profile
        "pull": None,
        "pull_barrel": None,
        "pua": None,
        "fb": None,

        # Damage
        "hard_hit": None,
        "barrel": None,
        "exit_velocity": None,
        "blast": None,
        "squared_up": None,
        "sweet_spot": None,
        "bat_speed": None,

        # Conversion
        "iso": None,
        "hr_pa": None,

        # Matchup
        "pitch_edge": None,

        # Recent pressure
        "hr_heat": False,

        # Opportunity
        "slot": 9

    }



    # MLB identity lookup

    try:

        url = (
            f"https://statsapi.mlb.com/api/v1/people/{player_id}"
        )


        response = requests.get(
            url,
            timeout=10
        )


        data = response.json()


        people = data.get(
            "people",
            []
        )


        if people:

            stats["name"] = people[0].get(
                "fullName"
            )


    except Exception:

        pass



    CACHE[player_id] = stats


    return stats




def attach_stats(players):

    """
    Merge player identity + stat fields
    into lineup objects.
    """


    output = []



    for player in players:


        stat_data = get_player_stats(
            player.get("id")
        )


        merged = {

            **player,

            **stat_data

        }


        # preserve lineup slot

        if player.get("slot"):

            merged["slot"] = player["slot"]



        output.append(
            merged
        )



    return output
