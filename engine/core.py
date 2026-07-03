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
        # ENGINE
        # -------------------------
        enriched = apply_elimination_gates(lineup, pitcher_profile)

        if not enriched:
            continue

        # -------------------------
        # SORT
        # -------------------------
        enriched.sort(key=lambda x: x.get("final_score", 0), reverse=True)

        winner = enriched[0]

        raw_id = winner.get("id")

        # =========================
        # 🔥 FIX: FORCE NAME RESOLUTION (THIS WAS YOUR ISSUE)
        # =========================
        survivor_name = get_player_name(raw_id)

        # fallback safety
        if not survivor_name or "Unknown" in survivor_name:
            survivor_name = winner.get("name") or f"Player_{raw_id}"

        results.append({
            "game": label,
            "survivor": survivor_name,   # 🔥 NOW ALWAYS NAME
            "id": raw_id,
            "gates": winner.get("gates", []),
            "final_score": winner.get("final_score", 0)
        })

    return results
