from engine.core import run_slate
from engine.core3 import build_core3
from services.slate_stable import get_mlb_slate_stable


def main():

    print("⚾ BLENDER V4.1 REAL DATA ENGINE")
    print("Stable MLB pipeline — schedule → engine → elimination system\n")

    # -------------------------
    # LOAD SLATE
    # -------------------------
    print("Loading MLB Slate...")

    games = get_mlb_slate_stable()

    print("✅ Loaded", len(games), "games\n")

    # -------------------------
    # RUN ENGINE
    # -------------------------
    print("Running Blender Engine...\n")

    results = run_slate(games)

    print("⚾ RESULTS")

    for r in results:

        print(r["game"])
        print("SURVIVOR:", r["survivor"])
        print("WHY:", r["why"])
        print()

    # -------------------------
    # CORE 3 AGGREGATION LAYER
    # -------------------------
    print("⚾ CORE 3 FINAL POOL\n")

    core3 = build_core3(results)

    for p in core3:

        print(f"{p['rank']}. {p['player']} ({p['game']})")
        print(f"   WHY: {p['reason']}\n")


if __name__ == "__main__":
    main()
