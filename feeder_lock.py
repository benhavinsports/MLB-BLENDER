import pandas as pd
def audit_feed(df):
    if df is None or df.empty: return False, ["No parsed player rows."]
    issues=[]
    fake=df["team"].astype(str).str.match(r"^Team\s+\d+$",na=False).any() or df["pitcher"].astype(str).str.match(r"^Pitcher\s+\d+$",na=False).any() or df["game"].astype(str).str.contains("Unknown Game",na=False).any()
    if fake: issues.append("Team/pitcher feed not locked.")
    if df["team"].replace("",pd.NA).dropna().nunique()<2: issues.append("Team extraction low.")
    if df["pitcher"].replace("",pd.NA).dropna().nunique()<2: issues.append("Pitcher extraction low.")
    return len(issues)==0, issues
