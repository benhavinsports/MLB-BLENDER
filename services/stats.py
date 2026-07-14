# services/stats.py

import requests


# ==========================================================
# MLB HR BLENDER vFINAL
# STAT DATA LAYER
# ==========================================================


STAT_API = (
    "https://statsapi.mlb.com/api/v1/people"
)



CACHE = {}



def get_player_stats(player_id):

    """
    Returns hitter/pitcher data.

    Blender consumes this.

    No decisions happen here.
    """

    if not player_id:
        return {}



    if player_id in CACHE:
        return CACHE[player_id]



    try:

        url = (
            f"{STAT_API}/{player_id}"
            "?hydrate=stats(group=[hitting,pitching])"
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



    stats = {

        "id":
            player_id,


        "name":
            person.get(
                "fullName",
                "UNKNOWN"
            ),


        # HR PROFILE PLACEHOLDERS
        # Filled from real stat feeds later

        "pull":
            None,


        "hard_hit":
            None,


        "barrel":
            None,


        "exit_velocity":
            None,


        "iso":
            None,


        "hr_pa":
            None,


        "pitch_edge":
            None

    }



    CACHE[player_id] = stats


    return stats




def attach_stats(players):

    """
    Adds stat fields to lineup players.
    """

    updated = []


    for player in players:

        stats = get_player_stats(
            player.get("id")
        )


        merged = {
            **player,
            **stats
        }


        updated.append(
            merged
        )


    return updated
