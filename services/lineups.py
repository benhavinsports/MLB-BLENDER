# services/lineups.py

import requests


# ==========================================================
# MLB HR BLENDER vFINAL
# REAL LINEUP INJECTION LAYER
#
# Purpose:
# - Load actual batting-order players from MLB game data
# - Return Blender-ready hitter objects
# - Exclude pitchers, bench players, and duplicates
#
# No gate logic.
# No rankings.
# No selections.
# ==========================================================


MLB_BOXSCORE_URL = (
    "https://statsapi.mlb.com/api/v1/game/{game_id}/boxscore"
)


# ==========================================================
# PUBLIC ENTRY
# ==========================================================


def build_game_pool(game):

    """
    Builds the full hitter pool for one game.

    First uses preloaded lineups if they exist.

    Otherwise fetches the MLB boxscore using game_id.

    Returns:

    [
        {
            "id": 123456,
            "name": "Player Name",
            "team": "Team Name",
            "side": "away",
            "slot": 1,
            "handedness": None,
            "position": "RF",
            "starter": True,
            "stats": {}
        }
    ]
    """

    if not isinstance(game, dict):

        return []


    away_name = game.get(
        "away",
        "UNKNOWN AWAY"
    )


    home_name = game.get(
        "home",
        "UNKNOWN HOME"
    )


    # ------------------------------------------------------
    # USE PRELOADED LINEUPS WHEN AVAILABLE
    # ------------------------------------------------------

    away_lineup = game.get(
        "away_lineup"
    )


    home_lineup = game.get(
        "home_lineup"
    )


    if away_lineup or home_lineup:

        hitters = []


        hitters.extend(

            normalize_lineup(

                away_lineup or [],

                away_name,

                "away"

            )

        )


        hitters.extend(

            normalize_lineup(

                home_lineup or [],

                home_name,

                "home"

            )

        )


        return deduplicate_hitters(
            hitters
        )


    # ------------------------------------------------------
    # FETCH LINEUPS USING THE MLB GAME ID
    # ------------------------------------------------------

    game_id = (

        game.get("game_id")

        or

        game.get("gamePk")

    )


    if not game_id:

        print(
            "LINEUP ERROR: GAME ID MISSING"
        )

        return []


    boxscore = fetch_boxscore(
        game_id
    )


    if not boxscore:

        return []


    teams = boxscore.get(
        "teams",
        {}
    )


    away_data = teams.get(
        "away",
        {}
    )


    home_data = teams.get(
        "home",
        {}
    )


    hitters = []


    hitters.extend(

        extract_team_hitters(

            team_data=away_data,

            team_name=away_name,

            side="away"

        )

    )


    hitters.extend(

        extract_team_hitters(

            team_data=home_data,

            team_name=home_name,

            side="home"

        )

    )


    return deduplicate_hitters(
        hitters
    )


# ==========================================================
# MLB BOXSCORE FETCH
# ==========================================================


def fetch_boxscore(game_id):

    """
    Loads one MLB game boxscore.

    Returns an empty dictionary on failure.
    """

    url = MLB_BOXSCORE_URL.format(
        game_id=game_id
    )


    try:

        response = requests.get(

            url,

            timeout=15

        )


        response.raise_for_status()


        data = response.json()


        if not isinstance(data, dict):

            return {}


        return data


    except Exception as error:

        print(

            "LINEUP LOAD ERROR:",

            error

        )


        return {}


# ==========================================================
# TEAM HITTER EXTRACTION
# ==========================================================


def extract_team_hitters(
    team_data,
    team_name,
    side
):

    """
    Extracts actual batting-order players from one team.

    The team_data["batters"] list preserves batting-order
    membership and avoids loading the entire bench roster.
    """

    if not isinstance(team_data, dict):

        return []


    players_map = team_data.get(
        "players",
        {}
    )


    batter_ids = team_data.get(
        "batters",
        []
    )


    hitters = []


    # ------------------------------------------------------
    # PRIMARY PATH:
    # MLB-provided batter ID list
    # ------------------------------------------------------

    if batter_ids:

        for index, player_id in enumerate(
            batter_ids,
            start=1
        ):

            player_data = get_player_record(

                players_map,

                player_id

            )


            hitter = build_hitter_record(

                player_data=player_data,

                player_id=player_id,

                team_name=team_name,

                side=side,

                fallback_slot=index

            )


            if hitter:

                hitters.append(
                    hitter
                )


        return hitters


    # ------------------------------------------------------
    # FALLBACK PATH:
    # Find records with a real batting order
    # ------------------------------------------------------

    ordered_records = []


    for player_data in players_map.values():

        if not isinstance(
            player_data,
            dict
        ):

            continue


        batting_order = player_data.get(
            "battingOrder"
        )


        if batting_order in (
            None,
            "",
            0,
            "0"
        ):

            continue


        ordered_records.append(
            player_data
        )


    ordered_records.sort(

        key=lambda record:

            convert_batting_slot(

                record.get(
                    "battingOrder"
                ),

                99

            )

    )


    for index, player_data in enumerate(
        ordered_records,
        start=1
    ):

        person = player_data.get(
            "person",
            {}
        )


        player_id = person.get(
            "id"
        )


        hitter = build_hitter_record(

            player_data=player_data,

            player_id=player_id,

            team_name=team_name,

            side=side,

            fallback_slot=index

        )


        if hitter:

            hitters.append(
                hitter
            )


    return hitters


# ==========================================================
# PLAYER RECORD LOOKUP
# ==========================================================


def get_player_record(
    players_map,
    player_id
):

    """
    MLB boxscore player dictionaries commonly use keys such as:

        ID660271

    This handles string and integer forms safely.
    """

    if not isinstance(
        players_map,
        dict
    ):

        return {}


    possible_keys = [

        f"ID{player_id}",

        str(player_id),

        player_id

    ]


    for key in possible_keys:

        if key in players_map:

            record = players_map.get(
                key
            )


            if isinstance(
                record,
                dict
            ):

                return record


    # Last-resort identity scan

    for record in players_map.values():

        if not isinstance(
            record,
            dict
        ):

            continue


        person = record.get(
            "person",
            {}
        )


        if str(
            person.get("id")
        ) == str(
            player_id
        ):

            return record


    return {}


# ==========================================================
# BLENDER HITTER RECORD
# ==========================================================


def build_hitter_record(
    player_data,
    player_id,
    team_name,
    side,
    fallback_slot
):

    """
    Converts one MLB boxscore player into the exact object
    expected by services/stats.py and engine/core.py.
    """

    if not isinstance(
        player_data,
        dict
    ):

        return None


    person = player_data.get(
        "person",
        {}
    )


    resolved_id = (

        person.get("id")

        or

        player_id

    )


    name = (

        person.get("fullName")

        or

        person.get("name")

        or

        player_data.get("name")

    )


    if not resolved_id:

        return None


    if not name:

        return None


    position_data = player_data.get(
        "position",
        {}
    )


    position = (

        position_data.get("abbreviation")

        or

        position_data.get("code")

        or

        "UNKNOWN"

    )


    # Pitchers must never enter the HR hitter pool.

    if str(position).upper() in {
        "P",
        "SP",
        "RP"
    }:

        return None


    slot = convert_batting_slot(

        player_data.get(
            "battingOrder"
        ),

        fallback_slot

    )


    if slot < 1 or slot > 9:

        return None


    handedness = extract_handedness(
        player_data,
        person
    )


    return {

        "id":
            resolved_id,


        "name":
            name,


        "player":
            name,


        "team":
            team_name,


        "side":
            side,


        "slot":
            slot,


        "handedness":
            handedness,


        "position":
            position,


        "starter":
            True,


        # Stat profile gets filled by services/stats.py.

        "stats":
            player_data.get(
                "blender_stats",
                {}
            ) or {}

    }


# ==========================================================
# PRELOADED LINEUP NORMALIZER
# ==========================================================


def normalize_lineup(
    lineup,
    team_name,
    side
):

    """
    Normalizes a lineup already attached to the game object.
    """

    if not isinstance(
        lineup,
        list
    ):

        return []


    hitters = []


    for index, player in enumerate(
        lineup,
        start=1
    ):

        if not valid_lineup_hitter(
            player
        ):

            continue


        name = (

            player.get("name")

            or

            player.get("fullName")

            or

            player.get("player")

        )


        player_id = (

            player.get("id")

            or

            player.get("player_id")

        )


        position = player.get(
            "position",
            "UNKNOWN"
        )


        if str(position).upper() in {
            "P",
            "SP",
            "RP"
        }:

            continue


        slot = convert_batting_slot(

            player.get(
                "slot"
            )

            or

            player.get(
                "battingOrder"
            ),

            index

        )


        if not name:

            continue


        hitters.append({

            "id":
                player_id,


            "name":
                name,


            "player":
                name,


            "team":
                team_name,


            "side":
                side,


            "slot":
                slot,


            "handedness":

                player.get("handedness")

                or

                player.get("hand")

                or

                player.get("bats"),


            "position":
                position,


            "starter":
                True,


            "stats":
                player.get(
                    "stats",
                    {}
                ) or {}

        })


    return hitters


# ==========================================================
# BATTING ORDER CONVERSION
# ==========================================================


def convert_batting_slot(
    batting_order,
    fallback
):

    """
    Handles values such as:

        100 -> slot 1
        200 -> slot 2
        "300" -> slot 3
        4 -> slot 4
    """

    if batting_order in (
        None,
        ""
    ):

        return fallback


    try:

        numeric_order = int(
            str(batting_order)
        )


        if numeric_order >= 100:

            slot = numeric_order // 100

        else:

            slot = numeric_order


        if 1 <= slot <= 9:

            return slot


    except (
        TypeError,
        ValueError
    ):

        pass


    return fallback


# ==========================================================
# HANDEDNESS
# ==========================================================


def extract_handedness(
    player_data,
    person
):

    possible_values = [

        player_data.get(
            "batSide"
        ),

        person.get(
            "batSide"
        ),

        player_data.get(
            "handedness"
        ),

        player_data.get(
            "bats"
        )

    ]


    for value in possible_values:

        if isinstance(
            value,
            dict
        ):

            code = value.get(
                "code"
            )


            if code:

                return code


        elif value:

            return str(value)


    return None


# ==========================================================
# VALIDATION
# ==========================================================


def valid_lineup_hitter(
    hitter
):

    """
    Removes bench, inactive, and pinch-hit-only entries.
    """

    if not isinstance(
        hitter,
        dict
    ):

        return False


    if hitter.get(
        "starter",
        True
    ) is False:

        return False


    status = str(

        hitter.get(
            "status",
            ""
        )

    ).lower()


    if status in {
        "bench",
        "inactive",
        "out",
        "pinch hitter",
        "pinch-hit"
    }:

        return False


    return True


# ==========================================================
# DUPLICATE REMOVAL
# ==========================================================


def deduplicate_hitters(
    hitters
):

    cleaned = []

    seen = set()


    for hitter in hitters:

        player_id = hitter.get(
            "id"
        )


        name = hitter.get(
            "name"
        )


        identity = (

            str(player_id)

            if player_id

            else

            str(name).strip().lower()

        )


        if not identity:

            continue


        if identity in seen:

            continue


        seen.add(
            identity
        )


        cleaned.append(
            hitter
        )


    return cleaned
