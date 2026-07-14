# services/lineup.py

import requests

from services.players import get_player_name


MLB_GAME_URL = (
    "https://statsapi.mlb.com/api/v1/game"
)



def get_game_lineup(game_id):

    """
    Loads official MLB lineup.

    Returns only hitters.

    Example:

    [
        {
            id: 123,
            name: "Player Name",
            slot: 1,
            side: "home",
            handedness: "R"
        }
    ]

    """

    if not game_id:
        return []


    try:

        url = (
            f"{MLB_GAME_URL}/{game_id}/boxscore"
        )


        data = requests.get(
            url,
            timeout=10
        ).json()


    except Exception as e:

        print(
            "LINEUP ERROR:",
            e
        )

        return []



    hitters = []



    teams = data.get(
        "teams",
        {}
    )


    for side in [
        "home",
        "away"
    ]:


        team = teams.get(
            side,
            {}
        )


        players = team.get(
            "players",
            {}
        )


        for player_data in players.values():


            person = player_data.get(
                "person",
                {}
            )


            player_id = person.get(
                "id"
            )


            position = player_data.get(
                "position",
                {}
            ).get(
                "abbreviation"
            )


            # REMOVE PITCHERS

            if position == "P":

                continue



            name = person.get(
                "fullName"
            )


            if not name:

                name = get_player_name(
                    player_id
                )



            hitters.append({

                "id":
                    player_id,


                "name":
                    name,


                "slot":
                    player_data.get(
                        "battingOrder",
                        9
                    ),


                "side":
                    side,


                "position":
                    position

            })



    return hitters
