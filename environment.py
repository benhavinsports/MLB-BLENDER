
def apply_environment(state, slate):

    games = slate["games"]

    allowed = set()

    for g in games:
        if g.get("total", 0) >= 7.5:
            allowed.add(g["home"])
            allowed.add(g["away"])

    state["active_pool"] = [
        h for h in state["active_pool"] if h["team"] in allowed
    ]

    state["trace"].append({"step": "env", "remaining": len(state["active_pool"])})

    return state
