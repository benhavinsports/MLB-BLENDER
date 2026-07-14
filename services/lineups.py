# services/lineups.py

# ==========================================================
# MLB HR BLENDER vFINAL
# LINEUP NORMALIZER
#
# Converts raw lineup data into Blender hitter pool.
#
# Removes:
# - bench players
# - duplicates
# - missing hitters
#
# Adds:
# - lineup slot
# - team
# - handedness
#
# ==========================================================



def normalize_lineup(team, lineup):


    """
    Input example:

    [
        {
            "name": "Player",
            "id": 123,
            "slot": 1,
            "starter": True
        }
    ]

    Output:
    Blender-ready hitter pool

    """



    hitters = []

    seen_ids = set()



    for player in lineup:


        player_id = player.get(
            "id"
        )


        name = player.get(
            "name"
        )



        # -------------------------
        # REMOVE BAD DATA
        # -------------------------


        if not player_id:

            continue



        if not name:

            continue



        if player_id in seen_ids:

            continue



        if player.get(
            "starter",
            True
        ) is False:

            continue



        seen_ids.add(
            player_id
        )



        hitters.append({


            "id":

                player_id,


            "name":

                name,


            "team":

                team,


            "slot":

                player.get(
                    "slot",
                    0
                ),


            "bats":

                player.get(
                    "bats"
                ),



            # Blender fields
            # filled later by stats layer


            "pull":

                player.get(
                    "pull"
                ),


            "hard_hit":

                player.get(
                    "hard_hit"
                ),


            "barrel":

                player.get(
                    "barrel"
                ),


            "ev":

                player.get(
                    "ev"
                ),


            "hr":

                player.get(
                    "hr"
                )

        })



    return hitters




# ==========================================================
# BUILD FULL GAME HITTER POOL
# ==========================================================


def build_game_pool(game):


    hitters = []



    away = normalize_lineup(

        game.get(
            "away"
        ),

        game.get(
            "away_lineup",
            []
        )

    )



    home = normalize_lineup(

        game.get(
            "home"
        ),

        game.get(
            "home_lineup",
            []
        )

    )



    hitters.extend(
        away
    )


    hitters.extend(
        home
    )


    return hitters
