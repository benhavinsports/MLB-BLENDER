import pandas as pd

def audit_feed(df):
    if df is None or df.empty:
        return False, ["No legal hitter rows parsed."]

    issues = []
    team = df["team"].fillna("").astype(str).str.strip()
    pitcher = df["pitcher"].fillna("").astype(str).str.strip()
    game = df["game"].fillna("").astype(str).str.strip()

    blank_team = int((team == "").sum())
    blank_pitcher = int((pitcher == "").sum())
    unknown_game = int(game.str.contains("Unknown Game", na=False).sum())

    if blank_team:
        issues.append(f"Team missing on {blank_team} rows.")
    if blank_pitcher:
        issues.append(f"Pitcher missing on {blank_pitcher} rows.")
    if unknown_game:
        issues.append(f"Unknown game label on {unknown_game} rows.")

    if len(df) >= 80 and game.nunique() < 6:
        issues.append("Full-slate game separation failed.")
    if len(df) >= 80 and team.nunique() < 6:
        issues.append("Full-slate team separation failed.")
    if len(df) >= 80 and pitcher.nunique() < 6:
        issues.append("Full-slate pitcher separation failed.")

    metric_cols = ["pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]
    metric_blank = int(df[metric_cols].isna().all(axis=1).sum())
    if metric_blank:
        issues.append(f"{metric_blank} rows have no usable hitter metrics.")

    return len(issues) == 0, issues
