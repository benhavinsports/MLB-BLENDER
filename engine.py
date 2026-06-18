from mlb_api import MLBAPI
from gates import run_gates


class BlenderEngine:

    def __init__(self):
        self.api = MLBAPI()

    def run_today(self):

        schedule = self.api.get_schedule()
        results = []

        for game in schedule:
            results.append(self.run_game(game))

        return results

    def run_game(self, game):

        game_id = game["game_id"]

        try:
            lineup = self.api.get_starting_lineup(game_id)
            box = self.api.get_boxscore(game_id)
        except Exception as e:
            return {"game_id": game_id, "error": str(e)}

        hitters = []

        for side in ["home", "away"]:

            for p in lineup.get(side, []):

                player_id = p.get("player_id")
                name = p.get("name")

                if not player_id or not name:
                    continue

                logs = self.api.get_player_game_logs(player_id)

                hitters.append({
                    "player_id": player_id,
                    "name": name,
                    "team_side": side,
                    "lineup_slot": p.get("lineup_slot", 99),
                    "game_logs": logs
                })

        if not hitters:
            return {
                "game_id": game_id,
                "matchup": f"{game['away_team_name']} @ {game['home_team_name']}",
                "error": "No hitters found"
            }

        result = run_gates(
            lineup=hitters,
            game_bundle=game,
            pitcher_stats={}
        )

        return {
            "game_id": game_id,
            "matchup": f"{game['away_team_name']} @ {game['home_team_name']}",
            **result
        }


def run_blender():
    return BlenderEngine().run_today()
