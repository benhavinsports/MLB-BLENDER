import pandas as pd

def audit_feed(df):
    if df is None or df.empty:
        return False, ["No parsed player rows."]

    issues=[]

    team_col = df["team"].fillna("").astype(str).str.strip()
    pitcher_col = df["pitcher"].fillna("").astype(str).str.strip()
    game_col = df["game"].fillna("").astype(str).str.strip()

    fake_team = team_col.str.match(r"^Team\s+\d+$", na=False).any()
    fake_pitcher = pitcher_col.str.match(r"^Pitcher\s+\d+$", na=False).any()
    unknown_game = game_col.str.contains("Unknown Game", na=False).any()

    blank_team_rows = int((team_col == "").sum())
    blank_pitcher_rows = int((pitcher_col == "").sum())

    if fake_team or fake_pitcher or unknown_game:
        issues.append("Fake/unknown team-pitcher labels detected.")

    if blank_team_rows > 0:
        issues.append(f"Team missing on {blank_team_rows} rows.")

    if blank_pitcher_rows > 0:
        issues.append(f"Pitcher missing on {blank_pitcher_rows} rows.")

    # IMPORTANT:
    # A single-game update PDF is valid with 1 team and 1 pitcher.
    # Do not fail just because unique team/pitcher count is 1.
    # Fail only if the rows are blank/fake/unknown.

    return len(issues)==0, issues
