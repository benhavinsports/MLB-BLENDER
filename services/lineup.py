from services.role_filter import get_role_score


def project_lineup(game, player_pool):

    projected = []

    for player in player_pool:

        role_score = get_role_score(player, game)

        projected.append({
            "player": player,
            "role_score": role_score
        })

    # sort by batting order logic (role strength)
    projected.sort(key=lambda x: x["role_score"], reverse=True)

    return projected
