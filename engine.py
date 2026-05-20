
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

def component_scores(r):
    pull = 0 if pd.isna(r.get("pull_pct")) else min(100, max(0, (r["pull_pct"]-20)*3.0))
    pitch = 0 if pd.isna(r.get("pitch_edge")) else min(100, max(0, 50 + r["pitch_edge"]))
    dmg = 0 if pd.isna(r.get("dmg")) else min(100, max(0, r["dmg"]*35))
    hrpa = 0 if pd.isna(r.get("hr_pa")) else min(100, max(0, r["hr_pa"]*16))
    hpi = 0 if pd.isna(r.get("hpi")) else min(100, max(0, r["hpi"]*2))
    sweet = 0 if pd.isna(r.get("sweet_spot_pct")) else min(100, max(0, (r["sweet_spot_pct"]-20)*4))
    role = 10 if r.get("weak_slot_tag") else 0
    alert = 10 if r.get("hr_alert") else 0
    cond = 6 if r.get("cond_up") else 0
    return dict(pull=pull,pitch=pitch,dmg=dmg,hrpa=hrpa,hpi=hpi,sweet=sweet,role=role,alert=alert,cond=cond)

def true_score(r):
    c=component_scores(r)
    score = c["pull"]*.18 + c["pitch"]*.12 + c["dmg"]*.18 + c["hrpa"]*.18 + c["hpi"]*.13 + c["sweet"]*.11 + c["role"] + c["alert"] + c["cond"]
    if pd.isna(r.get("dmg")) and pd.isna(r.get("hr_pa")) and pd.isna(r.get("hpi")): score -= 30
    if not pd.isna(r.get("hr_pa")) and r["hr_pa"] == 0 and not r.get("hr_alert"): score -= 20
    if not pd.isna(r.get("dmg")) and r["dmg"] < 0.5: score -= 12
    return max(0, min(100, score))

def apply_gate(alive,name,mask,reason,logs):
    before=alive.player.tolist(); cut=alive.loc[~mask,"player"].tolist(); alive=alive[mask].copy()
    logs.append({"Gate":name,"Before":len(before),"Cut":len(cut),"After":len(alive),"Cut names":", ".join(cut[:16]),"Alive after":", ".join(alive.player.tolist()[:16]),"Reason":reason})
    return alive

def has_one_of(df, cols):
    mask=pd.Series(False,index=df.index)
    for c in cols: mask = mask | df[c].notna()
    return mask

def run_game(gdf):
    alive=gdf.copy(); logs=[]
    logs.append({"Gate":"0 Game / Pitcher Viability","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16]),"Reason":"Game enters machine."})
    alive=apply_gate(alive,"1 Pull / Air DNA", alive.pull_pct.isna() | (alive.pull_pct>=20), "Pull must not be dead when available.", logs)
    if len(alive)>1: alive=apply_gate(alive,"2 Pitch Edge", alive.pitch_edge.isna() | (alive.pitch_edge>=0), "Negative pitch edge removed.", logs)
    if len(alive)>1: alive=apply_gate(alive,"3 Weak Slot", alive.apply(slot_ok,axis=1), "Weak slot alignment when available.", logs)
    if len(alive)>1: alive=apply_gate(alive,"4 Launch Window", alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=24), "Launch window must pass when listed.", logs)
    if len(alive)>1: alive=apply_gate(alive,"5 Conversion", alive.hr_pa.isna() | (alive.hr_pa>=2.0) | (alive.barrel_pct.fillna(0)>=8) | alive.hr_alert, "Must show HR/PA, barrel, or alert.", logs)
    if len(alive)>1: alive=apply_gate(alive,"6 DMG", alive.dmg.isna() | (alive.dmg>=0.5) | alive.hr_alert, "Low damage removed unless alert.", logs)
    if len(alive)>1: alive=apply_gate(alive,"7 HPI", alive.hpi.isna() | (alive.hpi>=18) | alive.hr_alert, "Weak HPI removed unless alert.", logs)
    if len(alive)>1: alive=apply_gate(alive,"8 Alert / Condition", alive.hr_alert | alive.cond_up | has_one_of(alive,["dmg","hr_pa","hpi","pull_pct"]), "Needs valid pressure signal.", logs)
    if len(alive)>1: alive=apply_gate(alive,"9 No Empty Bat", ~(alive.hr_pa.fillna(1).eq(0) & alive.dmg.fillna(1).lt(0.5) & ~alive.hr_alert), "Zero HR profile removed.", logs)
    for g in ["10 Ownership Pressure","10.5 Adjacent / Decoy Transfer","11 Lineup Protection","12 Bullpen Continuation","13 Numerology Overlay","14 Chaos / WHO","15 Finisher Gate","16 Event Likelihood","17 No-Fluke Audit","18 True HR Event Likelihood"]:
        if len(alive)>1:
            logs.append({"Gate":g,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16]),"Reason":"Audit/tie-break; dead players do not return."})
    if alive.empty: return alive,pd.DataFrame(logs)
    alive=alive.copy(); alive["role"]=alive.apply(role_type,axis=1); alive["score"]=alive.apply(true_score,axis=1)
    return alive.sort_values("score",ascending=False),pd.DataFrame(logs)

def run_machine(df):
    owners=[]; logs=[]; all_survivors=[]
    for g,gdf in df.groupby("game",dropna=False):
        surv,lg=run_game(gdf)
        if not lg.empty: lg.insert(0,"Game",g); logs.append(lg)
        if not surv.empty:
            all_survivors.append(surv.assign(game_group=g))
            owners.append(surv.iloc[0].to_dict())
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    logs=pd.concat(logs,ignore_index=True) if logs else pd.DataFrame()
    survivors=pd.concat(all_survivors,ignore_index=True) if all_survivors else pd.DataFrame()
    core=[]
    if not owners.empty:
        owners=owners.sort_values("score",ascending=False)
        core_source=owners[owners["score"]>=25]
        if core_source.empty: core_source=owners
        for role in ["Primary","Transfer","WHO"]:
            p=core_source[core_source.role==role]
            if not p.empty: core.append(p.iloc[0].to_dict())
        for _,r in core_source.iterrows():
            if len(core)>=3: break
            if r.player not in [x["player"] for x in core]: core.append(r.to_dict())
    core=pd.DataFrame(core[:3]) if core else pd.DataFrame()
    alt=[]
    for _,r in owners.iterrows() if not owners.empty else []:
        if core.empty or r.player not in core.player.tolist(): alt.append(r.to_dict())
        if len(alt)>=3: break
    return owners,core,pd.DataFrame(alt),logs,survivors
