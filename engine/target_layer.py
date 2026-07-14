# engine/target_layer.py

# ==========================================================
# MLB HR BLENDER vFINAL
# GATE 0 — TARGET LAYER
# PITCHER LEAK ENGINE
# ==========================================================


def calculate_leak_score(pitcher):

    """
    Gate 0

    Calculates HR leak score.

    Does NOT select hitters.

    Only identifies where HR resistance is weakest.
    """

    hr9 = pitcher.get("hr9", 0)

    barrel = pitcher.get("barrel_allowed", 0)

    xwoba = pitcher.get("xwoba_allowed", 0)

    hard_hit = pitcher.get("hard_hit_allowed", 0)

    strikeout = pitcher.get("k_percent", 0)

    predictability = pitcher.get("pitch_predictability", 0)


    leak = (

        (hr9 * 0.25)

        + (barrel * 0.25)

        + (xwoba * 0.20)

        + (hard_hit * 0.15)

        + (predictability * 0.15)

        - (strikeout * 0.08)

    )

    return round(leak, 3)



# ==========================================================
# RANK ALL PITCHERS
# ==========================================================

def build_target_map(games):

    """
    Returns one record per game.

    No hitter logic here.
    """

    targets = []

    for game in games:

        away_pitcher = game.get("away_pitcher_profile", {})

        home_pitcher = game.get("home_pitcher_profile", {})

        away_score = calculate_leak_score(away_pitcher)

        home_score = calculate_leak_score(home_pitcher)

        if away_score >= home_score:

            offense = game["home"]

            pitcher = game["away_pitcher"]

            leak = away_score

        else:

            offense = game["away"]

            pitcher = game["home_pitcher"]

            leak = home_score

        targets.append({

            "game": f"{game['away']} vs {game['home']}",

            "target_offense": offense,

            "target_pitcher": pitcher,

            "leak_score": leak

        })

    return targets
