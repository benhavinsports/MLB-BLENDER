from services.lineup import get_confirmed_lineup
from services.starter import get_probable_starter
from services.pitcher import get_pitcher_profile
from services.player_map import get_player_name
from engine.gates import apply_elimination_gates
from services.lineup_normalizer import normalize_lineup


def run_slate(games):

    results = []

    for g in games:

        gamePk = g.get("gamePk")
        label = f"{g.get('away')} vs {g.get('home')}"

        # =========================
        # LOAD LINEUP
        # =========================
        raw_lineup = get_confirmed_lineup(gamePk)
        lineup = normalize_lineup(raw_lineup)

        if not lineup:
            continue

        # =========================
        # LOAD STARTER
        # =========================
        starters = get_probable_starter(gamePk)
        pitcher_name = starters.get("away") or starters.get("home")

        if not pitcher_name:
            continue

        pitcher_profile = get_pitcher_profile(pitcher_name)

        # =========================
        # RUN ELIMINATION ENGINE
        # =========================
        enriched = apply_elimination_gates(lineup, pitcher_profile)

        if not enriched:
            continue

        # =========================
        # SORT BY FINAL SCORE
        # =========================
        enriched.sort(
            key=lambda x: x.get("final_score", 0),
            reverse=True
        )

        winner = enriched[0]

        player_id = winner.get("id")

        # =========================
        # 🔥 FORCE REAL NAME RESOLUTION (CRITICAL FIX)
        # =========================
        player_name = winner.get("name")

        if (
            not player_name
            or str(player_name).startswith("player_")
            or player_name.isdigit()
        ):
            player_name = get_player_name(player_id)

        # FINAL FALLBACK SAFETY
        if not player_name:
            player_name = f"Unknown_{player_id}"

        # =========================
        # STORE RESULT
        # =========================
        results.append({
            "game": label,
            "survivor": player_name,
            "id": player_id,
            "gates": winner.get("gates", []),
            "final_score": winner.get("final_score", 0)
        })

    return results
