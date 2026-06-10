
def gate(state, i):

    survivors = []

    for h in state["active_pool"]:
        score = h.get("pull_rate", 0) + h.get("hard_hit", 0)

        if score > 0.7:
            survivors.append(h)

    state["trace"].append({
        "gate": i,
        "remaining": len(survivors)
    })

    state["active_pool"] = survivors
    return state
