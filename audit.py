import pandas as pd

def audit_feed(df):
    if df is None or df.empty:
        return False, ["No parsed player rows."]

    issues=[]

    team_col=df["team"].fillna("").astype(str).str.strip()
    pitcher_col=df["pitcher"].fillna("").astype(str).str.strip()
    game_col=df["game"].fillna("").astype(str).str.strip()

    fake_team=team_col.str.match(r"^Team\s+\d+$",na=False).any()
    fake_pitcher=pitcher_col.str.match(r"^Pitcher\s+\d+$",na=False).any()
    unknown_game=game_col.str.contains("Unknown Game",na=False).any()

    blank_team=int((team_col=="").sum())
    blank_pitcher=int((pitcher_col=="").sum())

    if fake_team or fake_pitcher or unknown_game:
        issues.append("Fake/unknown team-pitcher labels detected.")
    if blank_team>0:
        issues.append(f"Team missing on {blank_team} rows.")
    if blank_pitcher>0:
        issues.append(f"Pitcher missing on {blank_pitcher} rows.")

    # Full-slate sanity: if there are many players but only 1 team/pitcher, parser did not section the PDF.
    if len(df) >= 80 and team_col.nunique() < 6:
        issues.append("Full slate sectioning failed: too few teams extracted.")
    if len(df) >= 80 and pitcher_col.nunique() < 6:
        issues.append("Full slate sectioning failed: too few pitchers extracted.")

    return len(issues)==0, issues
