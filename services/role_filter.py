def is_valid_hitter(player):

    name = player["name"].lower()

    # 🚫 pitcher's list (extend as needed)
    pitcher_keywords = [
        "pitcher", "p", "sp", "rp",
        "valdez", "bieber", "abreu", "rodriguez"
    ]

    if any(x in name for x in pitcher_keywords):
        return False

    return True
