from models.gates import gate_0_to_18

def run_blender(games):

    slate_results = []

    for game in games:

        survivors = []

        pitchers = game["pitchers"]
        hitters = game["hitters"]

        for pitcher in pitchers:

            pitcher_map = pitcher["weak_slot_map"]

            for hitter in hitters:

                # ⚠️ RUN FULL 18 GATES SEQUENTIALLY
                result = gate_0_to_18(
                    hitter=hitter,
                    pitcher=pitcher,
                    game=game,
                    weak_slot_map=pitcher_map
                )

                if not result["pass"]:
                    continue

                survivors.append(result)

        # 🔴 EVENT OWNERSHIP (NOT SCORE — FINAL COLLAPSE RULE)
        if survivors:

            event_owner = resolve_event_owner(survivors)

            slate_results.append({
                "game": game["label"],
                "event_owner": event_owner
            })

    # 🟣 CORE 3 = TOP EVENT OWNERS (NOT HITTERS)
    core3 = sorted(
        slate_results,
        key=lambda x: x["event_owner"]["alignment_score"],
        reverse=True
    )[:3]

    return {
        "games": slate_results,
        "core3": core3
    }
