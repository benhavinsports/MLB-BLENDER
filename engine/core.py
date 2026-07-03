from services.lineup import get_confirmed_lineup
from services.starter import get_probable_starter
from services.pitcher import get_pitcher_profile
from services.player_map import get_player_name
from engine.gates import apply_elimination_gates
from services.lineup_normalizer import normalize_lineup


def score_survivor(p):
    """
    SIMPLE EVENT-WEIGHTED WINNER SELECTION
    (replaces broken slot-only logic)
    """
    score = 0

    # slot advantage (top order = better)
    slot = p.get("slot", 9)
    score += (10 - slot) * 2

    # gate strength bonus
    score += len(p.get("gate_history", [])) * 1.5

    # handedness minor bump (optional stabilizer)
    if p.get("handedness") == "R":
        score += 0.5

    return score


def run_slate(games):

    results = []

    for g in games:

        gamePk = g.get("gamePk")
        label = f"{g.get('away')} vs {g.get('home')}"

        # -------------------------
        # LINEUP
        # -------------------------
        raw_lineup = get_confirmed_lineup(gamePk)
        lineup = normalize_lineup(raw_lineup)

        if not lineup:
            continue

        # -------------------------
        # STARTER
        # -------------------------
        starters = get_probable_starter(gamePk)
        pitcher_name = starters.get("away") or starters.get("home")

        if not pitcher_name:
            continue

        pitcher_profile = get_pitcher_profile(pitcher_name)

        # -------------------------
        # GATES
        # -------------------------
        survivors = apply_elimination_gates(lineup, pitcher_profile)

        if not survivors:
            continue

        # -------------------------
        # WINNER SELECTION (FIXED LOGIC)
        # -------------------------
        survivors.sort(key=score_survivor, reverse=True)
        winner = survivors[0]

        results.append({
            "game": label,
            "survivor": winner.get("name"),
            "id": winner.get("id"),
            "slot": winner.get("slot"),
            "why": winner.get("gate_history", [])
        })

    return results
