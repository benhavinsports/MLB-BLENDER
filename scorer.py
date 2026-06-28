
def hr_score(f):
    return (
        0.22 * f.get("pull",0) +
        0.18 * f.get("hh",0) +
        0.18 * f.get("barrel",0) +
        0.12 * f.get("ev",0) +
        0.10 * f.get("iso",0) +
        0.10 * f.get("matchup",0) +
        0.10 * f.get("venue",0)
    )
