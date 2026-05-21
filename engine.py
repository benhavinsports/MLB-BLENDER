
import re
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

def gate(alive,name,mask,logs):
    cut=alive.loc[~mask,"player"].tolist(); before=len(alive)
    alive=alive[mask].copy()
    logs.append({"Gate":name,"Before":before,"Cut":len(cut),"After":len(alive),"Cut names":", ".join(cut[:16]),"Alive after":", ".join(alive.player.tolist()[:16])})
    return alive

def run_game(gdf):
    alive=gdf.copy(); logs=[]
    logs.append({"Gate":"0","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16])})
    alive=gate(alive,"1",alive.pull_pct.isna() | (alive.pull_pct>=20),logs)
    if len(alive)>1: alive=gate(alive,"2",alive.pitch_edge.isna() | (alive.pitch_edge>=0),logs)
    if len(alive)>1: alive=gate(alive,"4",alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=24),logs)
    if len(alive)>1: alive=gate(alive,"5",alive.hr_pa.isna() | (alive.hr_pa>=2) | alive.hr_alert,logs)
    if len(alive)>1: alive=gate(alive,"6",alive.dmg.isna() | (alive.dmg>=0.5) | alive.hr_alert,logs)
    if len(alive)>1: alive=gate(alive,"7",alive.hpi.isna() | (alive.hpi>=18) | alive.hr_alert,logs)
    for g in ["8","9","10","10.5","11","12","13","14","15","16","17","18"]:
        if len(alive)>1: logs.append({"Gate":g,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16])})
    if alive.empty: return alive,pd.DataFrame(logs)
    alive=alive.copy(); alive["role"]=alive.apply(role_type,axis=1); alive["score"]=alive.apply(score_row,axis=1)
    return alive.sort_values("score",ascending=False),pd.DataFrame(logs)


def run_machine(df):
    owners=[]; logs=[]
    for g,gdf in df.groupby("game",dropna=False):
        surv,lg=run_game(gdf)
        if not lg.empty:
            lg.insert(0,"Game",g)
            logs.append(lg)
        if not surv.empty:
            top=surv.iloc[0].to_dict()
            top["game_owner_key"]=g
            owners.append(top)

    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    logs=pd.concat(logs,ignore_index=True) if logs else pd.DataFrame()

    # CONSOLIDATED CORE RULE:
    # One owner per game. Never place two players from the same game into Core 3.
    core=[]
    used_games=set()
    if not owners.empty:
        owners=owners.sort_values("score",ascending=False).reset_index(drop=True)
        pool=owners[owners.score>=25].copy()
        if pool.empty:
            pool=owners.copy()

        # Preserve role balance, but game uniqueness wins.
        for role in ["Primary","Transfer","WHO"]:
            p=pool[pool.role==role]
            for _,r in p.iterrows():
                g=r.get("game_owner_key", r.get("game",""))
                if g not in used_games:
                    core.append(r.to_dict())
                    used_games.add(g)
                    break

        # Fill remaining Core spots by score, still one per game.
        for _,r in pool.iterrows():
            if len(core)>=3:
                break
            g=r.get("game_owner_key", r.get("game",""))
            if g not in used_games:
                core.append(r.to_dict())
                used_games.add(g)

    core=pd.DataFrame(core[:3]) if core else pd.DataFrame()

    # Alt 3 = next legal game owners, avoiding Core games first.
    alt=[]
    used_alt_games=set(used_games)
    if not owners.empty:
        for _,r in owners.iterrows():
            g=r.get("game_owner_key", r.get("game",""))
            if (core.empty or r.player not in core.player.tolist()) and g not in used_alt_games:
                alt.append(r.to_dict())
                used_alt_games.add(g)
            if len(alt)>=3:
                break

        # Fallback only for tiny slates.
        if len(alt)<3:
            for _,r in owners.iterrows():
                if core.empty or r.player not in core.player.tolist():
                    if r.player not in [x.get("player") for x in alt]:
                        alt.append(r.to_dict())
                if len(alt)>=3:
                    break

    return owners,core,pd.DataFrame(alt[:3]),logs,pd.DataFrame()

