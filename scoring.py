import pandas as pd
def role_type(r):
    if bool(r.get("weak_slot_tag")) or bool(r.get("laser")) or bool(r.get("rakes")): return "Transfer"
    if (r.get("dmg") or 0)>=1.7 and (r.get("hr_pa") or 0)>=4: return "WHO"
    return "Primary"
def score_row(r):
    pull=0 if pd.isna(r.get("pull_pct")) else min(100,max(0,(r["pull_pct"]-20)*3))
    pitch=0 if pd.isna(r.get("pitch_edge")) else min(100,max(0,50+r["pitch_edge"]))
    dmg=0 if pd.isna(r.get("dmg")) else min(100,max(0,r["dmg"]*35))
    hrpa=0 if pd.isna(r.get("hr_pa")) else min(100,max(0,r["hr_pa"]*16))
    hpi=0 if pd.isna(r.get("hpi")) else min(100,max(0,r["hpi"]*2))
    sweet=0 if pd.isna(r.get("sweet_spot_pct")) else min(100,max(0,(r["sweet_spot_pct"]-20)*4))
    score=pull*.18+pitch*.12+dmg*.18+hrpa*.18+hpi*.13+sweet*.11
    score += 10 if r.get("weak_slot_tag") else 0
    score += 10 if r.get("hr_alert") else 0
    score += 6 if r.get("cond_up") else 0
    if pd.isna(r.get("dmg")) and pd.isna(r.get("hr_pa")) and pd.isna(r.get("hpi")): score-=30
    return max(0,min(100,score))
