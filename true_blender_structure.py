
# true_blender_structure.py
# True Blender result structure: visible pass/cut gates, owner isolation, Core 3 roles.

import json, re
import pandas as pd
import numpy as np

def txt(x):
    try:
        if x is None or pd.isna(x): return ""
    except Exception:
        pass
    return str(x).strip()

def num(x, d=np.nan):
    try:
        if x is None or pd.isna(x): return d
        s=str(x).replace("%","").replace("+","").replace(",","").strip()
        if s.lower() in {"","nan","none","null","-","—"}: return d
        m=re.search(r"[-+]?\d*\.?\d+",s)
        return float(m.group(0)) if m else d
    except Exception:
        return d

def strength(x, floor, elite, pts):
    if x is None or pd.isna(x): return 0.0
    x=float(x)
    if x < floor: return 0.0
    if x >= elite: return float(pts)
    return float(pts)*(x-floor)/max(1, elite-floor)

def metric(row, names, d=np.nan):
    compact={str(k).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-",""):k for k in row.keys()}
    for n in names:
        nn=str(n).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")
        if nn in compact: return num(row.get(compact[nn]), d)
    for n in names:
        nn=str(n).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")
        for ck, real in compact.items():
            if nn in ck or ck in nn:
                return num(row.get(real), d)
    return d

def get_metrics(row):
    vals={
        "pull":metric(row,["pull_pct","pull%","pull"],0),
        "hard":metric(row,["hard_hit_pct","hardhit%","hard hit%","hh%","hard"],0),
        "barrel":metric(row,["barrel_pct","barrel%","brl%","barrel"],0),
        "sweet":metric(row,["sweet_spot_pct","sweet%","launch","la"],0),
        "dmg":metric(row,["dmg","damage","ult","adj"],0),
        "hpi":metric(row,["hpi","model","rating","hr score"],0),
        "hr":metric(row,["hr_lane","hr_pa","hr/pa","hr9","hr/9"],0),
        "edge":metric(row,["pitch_edge","edge"],-99),
        "slot":metric(row,["lineup_slot","slot","order","bo"],0)
    }
    vals["metric_count"]=sum(1 for k,v in vals.items() if k!="edge" and v is not None and not pd.isna(v) and float(v)!=0) + (0 if vals["edge"]==-99 else 1)
    return vals

def gate_eval(row):
    vals=get_metrics(row)
    pull,hard,barrel,sweet,dmg,hpi,hr,edge,slot=[vals[k] for k in ["pull","hard","barrel","sweet","dmg","hpi","hr","edge","slot"]]
    notes=" ".join([txt(row.get(k)) for k in row.keys() if "note" in str(k).lower() or "tag" in str(k).lower()]).lower()
    player=txt(row.get("player"))
    game=txt(row.get("game_key") or row.get("game"))
    team=txt(row.get("team"))
    pitcher=txt(row.get("pitcher"))

    gates=[]
    def add(step,name,passed,score,max_score,reason,cut=False):
        gates.append({
            "step":step,"gate":name,"result":"PASS" if passed else "CUT",
            "score":round(max(0,float(score)),2),"max_score":float(max_score),
            "reason":reason,"cut":bool(cut or not passed)
        })

    # Ordered gate machine, visible pass/cut.
    add(0,"Current PDF row", bool(player and game), 10 if player and game else 0, 10, f"player={player}; game={game}", cut=not(player and game))
    metric_ok=vals["metric_count"]>=3
    trigger=(pull>=30 or hard>=30 or barrel>=5 or dmg>=.8 or hpi>=20 or hr>=.8 or edge>=0)
    add(1,"Metric survival", metric_ok and trigger, 10 if metric_ok and trigger else 0, 10, f"metrics={vals['metric_count']}; trigger={trigger}", cut=not(metric_ok and trigger))
    add(2,"Pitcher/game lane", bool(team and pitcher), 8 if team and pitcher else 0, 8, f"{team} vs {pitcher}", cut=not(team and pitcher))
    add(3,"Pitch edge / HR lane", max(strength(hr,.8,2.2,10),strength(edge,0,12,10),strength(dmg,.8,2.0,10)), 10, 10, f"hr_lane={hr}; edge={edge}; dmg={dmg}")
    pa=max(strength(pull,30,52,12),strength(sweet,20,35,12),strength(barrel,5,14,12))
    add(4,"Pull-air / launch", pa>0, pa, 12, f"pull={pull}; sweet={sweet}; barrel={barrel}", cut=pa<=0)
    dmgscore=max(strength(dmg,.8,2.2,12),strength(barrel,5,14,12),strength(hpi,20,70,12))
    add(5,"Damage / barrel conversion", dmgscore>0, dmgscore, 12, f"dmg={dmg}; barrel={barrel}; hpi={hpi}", cut=dmgscore<=0)
    conv=max(strength(hpi,20,70,12),strength(hr,.8,2.2,12),strength(dmg,.8,2.2,12))
    add(6,"True HR conversion", conv>0, conv, 12, f"hpi={hpi}; hr_lane={hr}; dmg={dmg}", cut=conv<=0)
    add(7,"Opportunity / slot", slot==0 or slot<=7, 7 if slot==0 or slot<=7 else 0, 7, f"slot={slot}", cut=not(slot==0 or slot<=7))
    hh=max(strength(hard,30,55,7),strength(barrel,5,14,7),strength(dmg,.8,2.0,7))
    add(8,"Hard-hit support", hh>0, hh, 7, f"hard={hard}; barrel={barrel}; dmg={dmg}", cut=hh<=0)
    adj_note=any(x in notes for x in ["adjacent","decoy","transfer"])
    add(9,"Adjacent/decoy check", True, 5 if adj_note else 2, 5, "adjacent trigger" if adj_note else "checked; no hard trigger")
    who_note=("who" in notes or "chaos" in notes or (pull>=30 and hard>=30 and hpi<45))
    add(10,"WHO/chaos check", True, 6 if who_note else 2, 6, "WHO/chaos trigger" if who_note else "checked; no hard trigger")
    trap=("trap" in notes or "red flag" in notes)
    add(11,"Trap audit", not trap, 8 if not trap else 0, 8, "no trap tag" if not trap else "trap/red flag", cut=trap)
    fin=0
    if pull>=35:
        fin=max(strength(hard,30,55,12),strength(barrel,5,14,12),strength(dmg,.8,2.0,12),strength(hpi,20,70,12))
    add(12,"Finisher gate", fin>0, fin, 12, f"pull={pull}; hard={hard}; barrel={barrel}; dmg={dmg}; hpi={hpi}", cut=fin<=0)
    final=max(strength(pull,30,52,10),strength(hard,30,55,10),strength(dmg,.8,2.0,10),strength(hpi,20,70,10),strength(hr,.8,2.2,10))
    add(13,"Gate 19 model confirmation", final>0, final, 10, f"final blend strength={round(final,2)}", cut=final<=0)

    hard_cut=any(g["cut"] and g["step"] in [0,1,2,4,5,6,7,8,11,12,13] for g in gates)
    score=sum(g["score"] for g in gates)/max(1,sum(g["max_score"] for g in gates))*100
    blender_score=round(max(1,min(100,score)),1) if not hard_cut else round(max(1,min(60,score)),1)
    support=round(max(1,min(100,min(pull,65)*.16+min(hard,70)*.12+min(barrel,25)*.5+min(dmg,8)*2.8+min(hpi,100)*.10+min(hr,6)*2.0+(max(min(edge,30),-20)*.2 if edge!=-99 else 0))),1)

    primary=strength(pull,35,52,20)+strength(barrel,6,14,20)+strength(dmg,1,2.2,20)+strength(hpi,25,70,15)+strength(hr,1,2.5,15)+strength(edge,0,20,10)
    adjacent=(35 if adj_note else 0)+strength(pull,30,45,18)+strength(hard,30,48,18)+strength(dmg,.8,1.8,14)+strength(hpi,20,55,10)
    who=(35 if who_note else 0)+strength(pull,28,40,15)+strength(hard,30,45,15)+strength(hr,.8,1.8,15)+strength(edge,0,12,10)+(10 if hpi<45 else 0)
    role_scores={"Primary":round(primary,1),"Adjacent":round(adjacent,1),"WHO":round(who,1)}
    role=max(role_scores,key=role_scores.get)
    eligible=not hard_cut and blender_score>=55
    if not eligible:
        role="CUT"
    archetype={"Primary":"Primary HR Owner","Adjacent":"Adjacent / Decoy Transfer","WHO":"WHO / Chaos Owner","CUT":"Cut by gates"}[role]
    return eligible, blender_score, support, role, archetype, gates, role_scores

def run_true_blender_structure(df):
    if not isinstance(df,pd.DataFrame) or df.empty:
        return {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"cuts":pd.DataFrame(),"game_board":pd.DataFrame(),"role_board":pd.DataFrame(),"meta":{"message":"No feed loaded.","owners_locked":0,"games":0}}
    data=df.copy()
    if "game_key" not in data.columns:
        data["game_key"]=data["game"] if "game" in data.columns else ""
    survivors=[]; board=[]; roles=[]
    for idx,r in data.iterrows():
        row=r.to_dict()
        eligible,b,s,role,arch,gates,role_scores=gate_eval(row)
        row.update({"row_id":idx,"blender_eligible":eligible,"blender_score":b,"support_score":s,"score":b,"official_core_role":role,"archetype":arch,"final_reason": f"{role} survived all hard gates" if eligible else "CUT — see gate trace","gate_trace_json":json.dumps(gates),"role_scores_json":json.dumps(role_scores)})
        survivors.append(row)
        for g in gates:
            board.append({"game_key":row.get("game_key",""),"player":row.get("player",""),"role":role,**g,"blender_score":b})
        roles.append({"game_key":row.get("game_key",""),"player":row.get("player",""),"assigned_role":role,"Primary_score":role_scores.get("Primary",0),"Adjacent_score":role_scores.get("Adjacent",0),"WHO_score":role_scores.get("WHO",0),"blender_score":b,"support_score":s})
    survivors=pd.DataFrame(survivors)
    cuts=survivors[survivors["blender_eligible"]!=True].copy()
    pass_rows=survivors[survivors["blender_eligible"]==True].copy()
    owners=[]
    for game,g in pass_rows.groupby("game_key",dropna=False):
        pick=g.sort_values(["blender_score","support_score"],ascending=[False,False]).iloc[0].to_dict()
        pick["game_owner"]=game
        owners.append(pick)
    owners=pd.DataFrame(owners)
    if not owners.empty:
        owners=owners.sort_values(["blender_score","support_score"],ascending=[False,False]).reset_index(drop=True)
    # Core 3 structure: Primary + Adjacent + WHO, no overlap; refill from best owners if role missing.
    used=set(); core_parts=[]
    for role in ["Primary","Adjacent","WHO"]:
        pool=owners[(owners["official_core_role"]==role)&(~owners["player"].astype(str).isin(used))].copy() if not owners.empty else pd.DataFrame()
        if not pool.empty:
            p=pool.sort_values(["blender_score","support_score"],ascending=[False,False]).head(1)
            core_parts.append(p); used.update(p["player"].astype(str).tolist())
    core=pd.concat(core_parts,ignore_index=True) if core_parts else pd.DataFrame()
    if not owners.empty and len(core)<3:
        refill=owners[~owners["player"].astype(str).isin(used)].head(3-len(core))
        if not refill.empty:
            core=pd.concat([core,refill],ignore_index=True)
    if not core.empty:
        core=core.head(3).copy(); core["ticket_role"]="CORE"
    used=set(core["player"].astype(str).tolist()) if not core.empty and "player" in core else set()
    alt=owners[~owners["player"].astype(str).isin(used)].head(3).copy() if not owners.empty and "player" in owners else pd.DataFrame()
    if not alt.empty: alt["ticket_role"]="ALT"
    used.update(alt["player"].astype(str).tolist() if not alt.empty and "player" in alt else [])
    chaos=owners[(owners["official_core_role"]=="WHO")&(~owners["player"].astype(str).isin(used))].head(3).copy() if not owners.empty and "player" in owners else pd.DataFrame()
    if chaos.empty and not owners.empty and "player" in owners:
        chaos=owners[~owners["player"].astype(str).isin(used)].head(3).copy()
    if not chaos.empty: chaos["ticket_role"]="WHO"
    games=int(data["game_key"].dropna().astype(str).replace("",pd.NA).dropna().nunique()) if "game_key" in data.columns else 0
    meta={"engine_version":"TRUE_BLENDER_STRUCTURE_V149","games":games,"input_rows":len(data),"passed_rows":len(pass_rows),"cut_rows":len(cuts),"owners_locked":len(owners),"core_count":len(core),"message":f"True Blender complete: {len(owners)} owners, {len(pass_rows)} pass rows, {len(cuts)} cuts. Core structured as Primary/Adjacent/WHO with refill."}
    return {"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"cuts":cuts,"game_board":pd.DataFrame(board),"role_board":pd.DataFrame(roles),"meta":meta}
