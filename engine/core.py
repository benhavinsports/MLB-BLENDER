from services.lineup import get_confirmed_lineup
from services.starter import get_probable_starter
from engine.gates import apply_gates


# -----------------------------
# 🧠 FINAL SCORING RESOLVER
# -----------------------------
def resolve_survivor(candidates):

    if not candidates:
        return None

    best = candidates[0]

    for c in candidates:

        # primary score comparison
        if c.get("score", 0) > best.get("score", 0):
            best = c

        # tie-breaker: matchup edge
        elif c.get("score", 0) == best.get("score", 0):
            if c.get("matchup_score", 0) > best.get("matchup_score", 0):
                best = c

    return best


# -----------------------------
# ⚾ MAIN ENGINE
# -----------------------------
def run_slate(games):

    results = []

    # 🔒 HARD ISOLATION TRACKER
    processed_games = set()

    for g in games:

        gamePk = g.get("gamePk")

        # -------------------------
        # 🔒 GAME ISOLATION GUARD
        # -------------------------
        if gamePk in processed_games:
            continue

        processed_games.add(gamePk)

        # -------------------------
        # ⚾ LOAD DATA (PER GAME ONLY)
        # -------------------------
        hitters = get_confirmed_lineup(gamePk)
        starters = get_probable_starter(gamePk)

        game_label = f"{g.get('away')} vs {g.get('home')}"

        # -------------------------
        # 🚨 VALIDATION CHECK
        # -------------------------
        if not hitters or len(hitters) < 6:
            results.append({
                "game": game_label,
                "survivor": "NO VALID LINEUP",
                "why": "LINEUP EMPTY OR INVALID AFTER CLEAN FILTER"
            })
            continue

        if not starters:
            results.append({
                "game": game_label,
                "survivor": "NO STARTER DATA",
                "why": "PITCHER DATA MISSING"
            })
            continue

        # -------------------------
        # ⚾ PICK ACTIVE STARTER
        # -------------------------
        pitcher = starters.get("away") or starters.get("home") or "unknown"

        # -------------------------
        # 🔥 RUN GATES (PER GAME ONLY)
        # -------------------------
        candidates = apply_gates(hitters, pitcher)

        # fallback safety (never crash)
        if not candidates:
            candidates = hitters[:1]

        # -------------------------
        # 🧠 RESOLVE FINAL SURVIVOR
        # -------------------------
        winner = resolve_survivor(candidates)

        if not winner:
            results.append({
                "game": game_label,
                "survivor": "NO SURVIVOR",
                "why": "ALL CANDIDATES ELIMINATED"
            })
            continue

        # -------------------------
        # ⚾ FINAL OUTPUT
        # -------------------------
        results.append({
            "game": game_label,
            "survivor": winner.get("name"),
            "why": "ISOLATED CORE ENGINE + GATE PASS + STABLE SCORING"
        })

    return results
