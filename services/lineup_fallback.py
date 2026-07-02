def fallback_hitters(game):

    # simple stable structure so engine NEVER breaks
    return [
        {"id": f"{game['gamePk']}-1", "slot": 1, "side": "away"},
        {"id": f"{game['gamePk']}-2", "slot": 2, "side": "away"},
        {"id": f"{game['gamePk']}-3", "slot": 3, "side": "away"},
    ]
