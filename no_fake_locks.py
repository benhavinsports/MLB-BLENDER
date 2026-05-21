def has_fake_labels(df):
    if df is None or df.empty:
        return True
    fake_team = df["team"].astype(str).str.match(r"^Team\s+\d+$", na=False).any()
    fake_pitcher = df["pitcher"].astype(str).str.match(r"^Pitcher\s+\d+$", na=False).any()
    unknown_game = df["game"].astype(str).str.contains("Unknown Game", na=False).any()
    return bool(fake_team or fake_pitcher or unknown_game)
