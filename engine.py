
import re
import pandas as pd

def slot_ok(r):
    slots=[int(x) for x in re.findall(r"\d+",str(r.get("weak_slots") or ""))]
    if not slots or pd.isna(r.get("lineup_slot")): return True
    return int(r["lineup_slot"]) in slots or bool(r.get("weak_slot_tag"))

def role_type(r):
    if bool(r.get("weak_slot_tag")) or bool(r.get("laser")) or bool(r.get("rakes")): return "Transfer"
    if (r.get("dmg") or 0)>=1.7 and (r.get("hr_pa") or 0)>=4: return "WHO"
    return "Primary"

def score_row(r):
    pull = 0 if pd.isna(r.get("pull_pct")) else min(100, max(0, (r["pull_pct"]-20)*3))
    pitch = 0 if pd.isna(r.get("pitch_edge")) else min(100, max(0, 50+r["pitch_edge"]))
    dmg = 0 if pd.isna(r.get("dmg")) else min(100, max(0, r["dmg"]*35))
    hrpa = 0 if pd.isna(r.get("hr_pa")) else min(100, max(0, r["hr_pa"]*16))
    hpi = 0 if pd.isna(r.get("hpi")) else min(100, max(0, r["hpi"]*2))
    sweet = 0 if pd.isna(r.get("sweet_spot_pct")) else min(100, max(0, (r["sweet_spot_pct"]-20)*4))
    score = pull*.18 + pitch*.12 + dmg*.18 + hrpa*.18 + hpi*.13 + sweet*.11
    score += 10 if r.get("weak_slot_tag") else 0
    score += 10 if r.get("hr_alert") else 0
    score += 6 if r.get("cond_up") else 0
    if pd.isna(r.get("dmg")) and pd.isna(r.get("hr_pa")) and pd.isna(r.get("hpi")): score -= 30
    if not pd.isna(r.get("hr_pa")) and r["hr_pa"] == 0 and not r.get("hr_alert"): score -= 20
    if not pd.isna(r.get("dmg")) and r["dmg"] < 0.5: score -= 12
    return max(0,min(100,score))

def apply_gate(alive,name,mask,reason,logs):
    before=alive.player.tolist()
    cut=alive.loc[~mask,"player"].tolist()
    alive=alive[mask].copy()
    logs.append({"Gate":name,"Before":len(before),"Cut":len(cut),"After":len(alive),"Cut names":", ".join(cut[:16]),"Alive after":", ".join(alive.player.tolist()[:16]),"Reason":reason})
    return alive

def run_game(gdf):
    alive=gdf.copy(); logs=[]
    logs.append({"Gate":"0","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16]),"Reason":"Game enters."})
    alive=apply_gate(alive,"1",alive.pull_pct.isna() | (alive.pull_pct>=20),"Pull",logs)
    if len(alive)>1: alive=apply_gate(alive,"2",alive.pitch_edge.isna() | (alive.pitch_edge>=0),"Pitch",logs)
    if len(alive)>1: alive=apply_gate(alive,"3",alive.apply(slot_ok,axis=1),"Slot",logs)
    if len(alive)>1: alive=apply_gate(alive,"4",alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=24),"Launch",logs)
    if len(alive)>1: alive=apply_gate(alive,"5",alive.hr_pa.isna() | (alive.hr_pa>=2) | alive.hr_alert,"Conversion",logs)
    if len(alive)>1: alive=apply_gate(alive,"6",alive.dmg.isna() | (alive.dmg>=0.5) | alive.hr_alert,"DMG",logs)
    if len(alive)>1: alive=apply_gate(alive,"7",alive.hpi.isna() | (alive.hpi>=18) | alive.hr_alert,"HPI",logs)
    for g in ["8","9","10","10.5","11","12","13","14","15","16","17","18"]:
        if len(alive)>1:
            logs.append({"Gate":g,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16]),"Reason":"Audit"})
    if alive.empty: return alive,pd.DataFrame(logs)
    alive=alive.copy()
    alive["role"]=alive.apply(role_type,axis=1)
    alive["score"]=alive.apply(score_row,axis=1)
    return alive.sort_values("score",ascending=False),pd.DataFrame(logs)

def run_machine(df):
    owners=[]; logs=[]; survivors=[]
    for g,gdf in df.groupby("game",dropna=False):
        surv,lg=run_game(gdf)
        if not lg.empty:
            lg.insert(0,"Game",g)
            logs.append(lg)
        if not surv.empty:
            survivors.append(surv.assign(game_group=g))
            owners.append(surv.iloc[0].to_dict())
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    logs=pd.concat(logs,ignore_index=True) if logs else pd.DataFrame()
    survivors=pd.concat(survivors,ignore_index=True) if survivors else pd.DataFrame()
    core=[]
    if not owners.empty:
        owners=owners.sort_values("score",ascending=False)
        pool=owners[owners["score"]>=25]
        if pool.empty: pool=owners
        for role in ["Primary","Transfer","WHO"]:
            p=pool[pool.role==role]
            if not p.empty: core.append(p.iloc[0].to_dict())
        for _,r in pool.iterrows():
            if len(core)>=3: break
            if r.player not in [x["player"] for x in core]: core.append(r.to_dict())
    core=pd.DataFrame(core[:3]) if core else pd.DataFrame()
    alt=[]
    for _,r in owners.iterrows() if not owners.empty else []:
        if core.empty or r.player not in core.player.tolist(): alt.append(r.to_dict())
        if len(alt)>=3: break
    return owners,core,pd.DataFrame(alt),logs,survivors
