
def pick_who(scored):
    if len(scored) < 3:
        return scored[-1]

    # adjacency logic simplified
    return scored[1]
