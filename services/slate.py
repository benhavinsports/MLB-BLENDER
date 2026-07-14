# services/slate.py

import requests
from datetime import datetime


# ==========================================================
# MLB HR BLENDER vFINAL
# SLATE LOADER
# ==========================================================


MLB_SCHEDULE_URL = (
    "https://statsapi.mlb.com/api/v1/schedule"
)



def get_mlb_slate(date=None):

    """
    REAL MLB SLATE INJECTION

    Returns:

    [
        {
            game_id,
            away,
            home,
            away_id,
            home_id,
            away_pitcher,
            home_pitcher
        }
    ]

    Blender does not make decisions here.
    """


    if date is None:
        date = datetime.now().strftime(
            "%Y-%m-%d"
        )


    params = {

        "sportId": 1,

        "date": date,

        "hydrate":
            "team,probablePitcher"

    }


    try:

        response = requests.get(
            MLB_SCHEDULE_URL,
            params=params,
            timeout=10
        )

        data = response.json()


    except Exception as e:

        print(
            "SLATE LOAD ERROR:",
            e
        )

        return []



    games = []


    for day in data.get(
        "dates",
        []
    ):

        for game in day.get(
            "games",
            []
        ):


            teams = game.get(
                "teams",
                {}
            )


            away = teams.get(
                "away",
                {}
            )


            home = teams.get(
                "home",
                {}
            )


            away_team = away.get(
                "team",
                {}
            )


            home_team = home.get(
                "team",
                {}
            )



            games.append({

                "game_id":
                    game.get(
                        "gamePk"
                    ),


                "away":
                    away_team.get(
                        "name",
                        "UNKNOWN"
                    ),


                "home":
                    home_team.get(
                        "name",
                        "UNKNOWN"
                    ),


                "away_id":
                    away_team.get(
                        "id"
                    ),


                "home_id":
                    home_team.get(
                        "id"
                    ),


                "away_pitcher":
                    away.get(
                        "probablePitcher",
                        {}
                    ).get(
                        "fullName"
                    ),


                "home_pitcher":
                    home.get(
                        "probablePitcher",
                        {}
                    ).get(
                        "fullName"
                    ),


                "status":
                    game.get(
                        "status",
                        {}
                    ).get(
                        "abstractGameState"
                    )

            })



    return games
