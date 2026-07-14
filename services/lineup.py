# services/lineup.py

import requests


# ==========================================================
# MLB HR BLENDER vFINAL
# LINEUP IDENTITY LAYER
# REAL PLAYER NAMES
# ==========================================================


CACHE = {}


def resolve_player_name(player_id):

    """
    Convert MLB ID -> real name.

    Names are locked here.
    Blender never sees raw IDs.
    """

    if not player_id:
        return "UNKNOWN"


    if player_id in CACHE:
        return CACHE[player_id]


    try:

        url = (
            f"https://statsapi.mlb.com/api/v1/people/{player_id}"
        )


        data = requests.get(
            url,
            timeout=10
        ).json()


        people = data.get(
            "people",
            []
        )


        if people:

            name = people[0].get(
                "fullName",
                "UNKNOWN"
            )

            CACHE[player_id] = name

            return name


    except Exception:

        pass


    return f"UNKNOWN_{player_id}"



# ==========================================================
# NORMALIZE LINEUP
# ==========================================================

def normalize_lineup(raw_players, team):


    lineup = []


    for p in raw_players:


        player_id = p.get(
            "id"
        )


        name = p.get(
            "name"
        )


        if not name or name == player_id:

            name = resolve_player_name(
                player_id
            )


        lineup.append({

            "id":
                player_id,


            "name":
                name,


            "team":
                team,


            "slot":
                p.get(
                    "battingOrder",
                    9
                ),


            "handedness":
                p.get(
                    "handedness",
                    "R"
                )


        })


    return lineup



# ==========================================================
# LOAD GAME LINEUP
# ==========================================================

def get_game_lineup(game):


    """
    Placeholder connection point.

    This returns confirmed starters only.

    The data source plugs in here.
    """


    players = []


    # Real lineup endpoint connects here.


    return players
