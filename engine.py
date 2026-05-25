from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import numpy as np

from official_mlb_slate import fetch_official_mlb_slate, attach_official_slate_to_feed, official_game_count
from feeder import actual_game_count

DATA_DIR = Path("data")
LOCK_PATH = DATA_DIR / "locked_owners.json"


def _txt(x):
    try:
        if x is None or pd.isna(x): return ""
    except Exception: pass
    return str(x).strip()


def _num(x, default=0.0):
    try:
        if x is None or pd.isna(x): return default
        return float(x)
    except Exception:
        return default


def gate_strength(x, floor, elite, pts):
    x = _num(x, np.nan)
    if pd.isna(x) or x < floor: return 0.0
    if x >= elite: return float(pts)
    return float(pts) * (x - floor) / max(1, elite - floor)


def fetch_live_public_slate(date_str=None):
    return fetch_official_mlb_slate(date_str)


def fetch_live_public_hitter_pool(date_str=None):
    return fetch_official_mlb_slate(date_str)


def attach_slate_matchup_context(df, public_context=None):
    return attach_official_slate_to_feed(df, public_context)


def merge_public_context(df, public_context=None):
    return attach_slate_matchup_context(df, public_context)


def slate_game_count_from_public_context(ctx=None, df=None):
    return official_game_count(ctx if ctx is not None else df)


def attack_pool_count(df):
    return actual_game_count(df)


def recalc_adaptive_weights_from_history(*args, **kwargs):
    return {"ok": True, "message": "Weights recalibration placeholder preserved."}


def evaluate_hitter(row):
    pull = _num(row.get("pull_pct")); hard = _num(row.get("hard_hit_pct")); barrel = _num(row.get("barrel_pct"))
    sweet = _num(row.get("sweet_spot_pct")); dmg = _num(row.get("dmg")); hpi = _num(row.get("hpi")); hr = _num(row.get("hr_lane")); edge = _num(row.get("pitch_edge"), -99); slot = _num(row.get("lineup_slot"))
    metric_count = int(row.get("metric_count", 0) or 0)
    notes = _txt(row.get("notes")).lower()
    gates = []
    def add(step, gate, score, max_score, verdict=None, reason=""):
        if verdict is None: verdict = "PASS" if score > 0 else "KILL"
        gates.append({"step":step,"gate":gate,"verdict":verdict,"gate_score":round(max(0,float(score)),2),"max_score":float(max_score),"reason":reason})

    if metric_count < 1:
        add(0,"PDF row metric recovery",0,10,"KILL","No numeric Blender metric recovered")
        return False, 0.0, 0.0, "NO PICK", "Audit only", gates

    add(0,"Correct PDF row only",10,10,"PASS","Current upload row accepted")
    add(1,"Official slate attached",10 if bool(row.get("official_slate_attached", False)) else 4,10,"PASS" if bool(row.get("official_slate_attached", False)) else "WEAK", _txt(row.get("game_key")))
    add(2,"Pitcher HR lane",max(gate_strength(hr,.8,2.2,10),gate_strength(edge,0,15,10),gate_strength(dmg,.8,2.0,10),gate_strength(hpi,20,70,10)),10)
    add(3,"Pitch-type kill switch",8 if edge>=0 else 2,8,"PASS" if edge>=0 else "WEAK",f"edge={edge}")
    add(4,"Pull-air / launch",max(gate_strength(pull,30,52,12),gate_strength(sweet,20,35,12),gate_strength(barrel,5,14,12)),12)
    add(5,"Damage / barrel",max(gate_strength(dmg,.8,2.2,12),gate_strength(barrel,5,14,12),gate_strength(hpi,20,70,12)),12)
    add(6,"True HR conversion",max(gate_strength(hpi,20,70,12),gate_strength(hr,.8,2.2,12),gate_strength(dmg,.8,2.2,12)),12)
    add(7,"Opportunity / lineup",7 if slot==0 or slot<=7 else 2,7,"PASS" if slot==0 or slot<=7 else "WEAK",f"slot={slot}")
    add(8,"Hard-hit support",max(gate_strength(hard,30,55,7),gate_strength(barrel,5,14,7),gate_strength(dmg,.8,2.0,7)),7)
    add(9,"Adjacent / decoy",5 if any(x in notes for x in ["adjacent","decoy","transfer","weak slot"]) else 2,5,"PASS" if any(x in notes for x in ["adjacent","decoy","transfer","weak slot"]) else "WEAK")
    add(10,"WHO / chaos",6 if ("who" in notes or "chaos" in notes or (pull>=30 and hard>=30 and hpi<45)) else 2,6,"PASS" if ("who" in notes or "chaos" in notes or (pull>=30 and hard>=30 and hpi<45)) else "WEAK")
    add(11,"Trap audit",8 if "trap" not in notes else 0,8)
    fin=0
    if pull>=35 or pd.isna(row.get("pull_pct")):
        fin=max(gate_strength(hard,30,55,12),gate_strength(barrel,5,14,12),gate_strength(dmg,.8,2.0,12),gate_strength(hpi,20,70,12))
    add(12,"Finisher gate",fin,12)
    add(13,"Final model confirmation",max(gate_strength(pull,30,52,10),gate_strength(hard,30,55,10),gate_strength(dmg,.8,2.0,10),gate_strength(hpi,20,70,10),gate_strength(hr,.8,2.2,10),gate_strength(barrel,5,14,10)),10)

    raw=sum(g["gate_score"] for g in gates); mx=sum(g["max_score"] for g in gates)
    blender=round(max(1,min(100,(raw/mx)*100)),1)
    support=round(max(1,min(100,min(pull,65)*.16+min(hard,70)*.12+min(barrel,25)*.5+min(dmg,8)*2.8+min(hpi,100)*.10+min(hr,6)*2.0+(max(min(edge,30),-20)*.2 if edge!=-99 else 0))),1)

    primary=gate_strength(pull,35,52,20)+gate_strength(barrel,6,14,20)+gate_strength(dmg,1,2.2,20)+gate_strength(hpi,25,70,15)+gate_strength(hr,1,2.5,15)+gate_strength(edge,0,20,10)
    adjacent=(35 if any(x in notes for x in ["adjacent","decoy","transfer","weak slot"]) else 0)+gate_strength(pull,30,45,18)+gate_strength(hard,30,48,18)+gate_strength(dmg,.8,1.8,14)+gate_strength(hpi,20,55,10)
    who=(35 if ("who" in notes or "chaos" in notes) else 0)+gate_strength(pull,28,40,15)+gate_strength(hard,30,45,15)+gate_strength(hr,.8,1.8,15)+gate_strength(edge,0,12,10)+(10 if hpi<45 else 0)
    role_scores={"Primary":primary,"Adjacent":adjacent,"WHO":who}
    role=max(role_scores,key=role_scores.get)
    if blender < 38: role="NO PICK"
    arch={"Primary":"Primary HR Owner","Adjacent":"Adjacent / Decoy Transfer","WHO":"WHO / Chaos Owner"}.get(role,"Audit only")
    return role!="NO PICK", blender, support, role, arch, gates


def run_true_blender(df, *args, **kwargs):
    if df is None or not isinstance(df,pd.DataFrame) or df.empty:
        return empty_results("No usable feed rows loaded.")
    work=df.copy()
    survivors=[]; board=[]; role_rows=[]
    for idx,r in work.iterrows():
        row=r.to_dict()
        ok,b,s,role,arch,gates=evaluate_hitter(row)
        row.update({"row_id":idx,"blender_eligible":ok,"blender_score":b,"support_score":s,"score":b,"official_core_role":role,"archetype":arch,"final_reason":f"{role} survived true gate path" if ok else "NO PICK"})
        survivors.append(row)
        for g in gates:
            board.append({"game_pk":row.get("game_pk",""),"game_key":row.get("game_key",""),"player":row.get("player",""),"role":role,**g,"blender_score":b})
        role_rows.append({"game_pk":row.get("game_pk",""),"game_key":row.get("game_key",""),"player":row.get("player",""),"assigned_role":role,"archetype":arch,"blender_score":b,"support_score":s})
    survivors=pd.DataFrame(survivors); game_board=pd.DataFrame(board); role_board=pd.DataFrame(role_rows)
    group_col="game_pk" if "game_pk" in survivors.columns and survivors["game_pk"].dropna().astype(str).str.strip().replace("",pd.NA).dropna().nunique()>0 else "game_key"
    owners=[]
    for game,g in survivors.groupby(group_col,dropna=False):
        eg=g[g["blender_eligible"]==True].copy()
        if eg.empty: continue
        p=eg.sort_values(["blender_score","support_score"],ascending=[False,False]).iloc[0].to_dict()
        p["game_owner"]=p.get("game_key",game); owners.append(p)
    owners=pd.DataFrame(owners)
    if not owners.empty:
        owners=owners.sort_values(["blender_score","support_score"],ascending=[False,False]).drop_duplicates(["player"],keep="first").reset_index(drop=True)
    core=build_core(owners)
    used=set(core["player"].astype(str)) if not core.empty and "player" in core else set()
    alt=owners[~owners["player"].astype(str).isin(used)].head(3).copy() if not owners.empty and "player" in owners else pd.DataFrame()
    if not alt.empty: alt["ticket_role"]="ALT"
    used.update(alt["player"].astype(str).tolist() if not alt.empty and "player" in alt else [])
    chaos=owners[(owners["official_core_role"]=="WHO") & (~owners["player"].astype(str).isin(used))].head(3).copy() if not owners.empty and "player" in owners else pd.DataFrame()
    if chaos.empty and not owners.empty and "player" in owners:
        chaos=owners[~owners["player"].astype(str).isin(used)].head(3).copy()
    if not chaos.empty: chaos["ticket_role"]="WHO"
    games=official_game_count(work) or actual_game_count(work)
    meta={"engine_version":"V148_FULL_FIX","games":int(games),"input_rows":int(len(work)),"eligible_rows":int(survivors["blender_eligible"].sum()),"owners_locked":int(len(owners)),"core_count":int(len(core)),"message":f"Blender complete: {len(owners)} owners from {games} official games. Rows={len(work)}."}
    results={"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"game_board":game_board,"role_board":role_board,"meta":meta}
    try: save_locked_results(results)
    except Exception: pass
    return results


def build_core(owners):
    if owners is None or not isinstance(owners,pd.DataFrame) or owners.empty: return pd.DataFrame()
    used=set(); parts=[]
    for role in ["Primary","Adjacent","WHO"]:
        pool=owners[(owners["official_core_role"]==role) & (~owners["player"].astype(str).isin(used))].copy()
        if not pool.empty:
            p=pool.sort_values(["blender_score","support_score"],ascending=[False,False]).head(1)
            parts.append(p); used.update(p["player"].astype(str).tolist())
    core=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    if len(core)<3:
        refill=owners[~owners["player"].astype(str).isin(used)].head(3-len(core)) if "player" in owners else owners.head(3-len(core))
        if not refill.empty: core=pd.concat([core,refill],ignore_index=True)
    if not core.empty: core=core.head(3).copy(); core["ticket_role"]="CORE"
    return core


def empty_results(msg):
    return {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"game_board":pd.DataFrame(),"role_board":pd.DataFrame(),"meta":{"engine_version":"V148_FULL_FIX","games":0,"owners_locked":0,"message":msg}}


def safe_results(x):
    if not isinstance(x,dict): return empty_results("Invalid results object.")
    for k in ["owners","core","alt","chaos","survivors","game_board","role_board"]:
        if k not in x or x[k] is None: x[k]=pd.DataFrame()
        elif not isinstance(x[k],pd.DataFrame): x[k]=pd.DataFrame(x[k])
    if "meta" not in x or not isinstance(x["meta"],dict): x["meta"]={}
    return x


def csv_bytes(df):
    if df is None or not isinstance(df,pd.DataFrame): df=pd.DataFrame()
    return df.to_csv(index=False).encode("utf-8")


def save_locked_results(results):
    DATA_DIR.mkdir(exist_ok=True)
    payload={}
    for k,v in safe_results(results).items():
        payload[k]=v.to_dict(orient="records") if isinstance(v,pd.DataFrame) else v
    LOCK_PATH.write_text(json.dumps(payload,default=str))


def load_locked_results():
    if not LOCK_PATH.exists(): return empty_results("No locked results saved yet.")
    payload=json.loads(LOCK_PATH.read_text())
    for k in ["owners","core","alt","chaos","survivors","game_board","role_board"]:
        payload[k]=pd.DataFrame(payload.get(k,[]))
    payload["meta"]=payload.get("meta",{})
    return payload
