def fallback_hitters(gamePk):

    # stable structure so system NEVER breaks
    return [
        {"id": f"{gamePk}-A1", "slot": 1},
        {"id": f"{gamePk}-A2", "slot": 2},
        {"id": f"{gamePk}-A3", "slot": 3},
    ]
