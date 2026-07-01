def is_valid_hitter(player):

    name = player.get("name", "").lower()

    # 🚫 only true hard exclusions
    if any(x in name for x in [
        "pitcher",
        "p-",
        "sp",
        "rp"
    ]):
        return False

    return True
