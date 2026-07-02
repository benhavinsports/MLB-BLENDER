def pitcher_strength(pitcher_name):

    if not pitcher_name:
        return 0.5  # neutral fallback

    weak = ["rookie", "bullpen", "opener"]
    strong = ["ace", "elite"]

    name = pitcher_name.lower()

    if any(w in name for w in weak):
        return 0.8
    if any(s in name for s in strong):
        return 0.3

    return 0.5
