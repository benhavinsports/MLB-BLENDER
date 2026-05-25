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


# === TRUE BLENDER STRUCTURE OVERRIDE V149 ===
from true_blender_structure import run_true_blender_structure
def run_true_blender(df, *args, **kwargs):
    results = run_true_blender_structure(df)
    try:
        save_locked_results(results)
    except Exception:
        pass
    return results


# === V150 TRUE BLENDER MACHINE OVERRIDE ===

def run_true_blender(df, *args, **kwargs):
    results = build_results(df)
    try:
        save_locked_results(results)
    except Exception:
        pass
    return results


# ===== FOLDED-IN V150 TRUE BLENDER MACHINE =====

# true_blender_machine_v150.py
# Locked Blender machine: PDF pool + Official slate context + visible gate pass/cut + structured Core 3.

import re, json
import pandas as pd
import numpy as np

def txt(x):
    try:
        if x is None or pd.isna(x): return ""
    except Exception:
        pass
    return str(x).strip()

def num(x, default=np.nan):
    try:
        if x is None or pd.isna(x): return default
        s=str(x).replace("%","").replace("+","").replace(",","").strip()
        if s.lower() in {"","nan","none","null","-","—"}: return default
        m=re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group(0)) if m else default
    except Exception:
        return default

def metric(row, names, default=np.nan):
    cmap={str(k).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-",""):k for k in row.keys()}
    for n in names:
        nn=str(n).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")
        if nn in cmap:
            return num(row.get(cmap[nn]), default)
    for n in names:
        nn=str(n).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")
        for ck, real in cmap.items():
            if nn in ck or ck in nn:
                return num(row.get(real), default)
    return default

def strength(x, floor, elite, pts):
    if x is None or pd.isna(x): return 0.0
    x=float(x)
    if x < floor: return 0.0
    if x >= elite: return float(pts)
    return float(pts)*(x-floor)/max(1, elite-floor)

def names_match_team_game(team, game_key):
    team=txt(team).lower()
    game=txt(game_key).lower()
    if not team or not game: return False
    # exact phrase or simplified token overlap for abbreviations/official attach
    if team in game: return True
    words=[w for w in re.split(r"[^a-z]+", team) if len(w)>2 and w not in {"the","and"}]
    return bool(words and any(w in game for w in words[-2:]))

def sanitize_feed(df):
    df = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    if df.empty: return df
    if "game_key" not in df.columns:
        df["game_key"] = df["game"] if "game" in df.columns else ""
    if "official_slate_attached" not in df.columns:
        df["official_slate_attached"] = False
    if "player" in df.columns and "pitcher" in df.columns:
        df = df[~(df["player"].astype(str).str.lower().str.strip() == df["pitcher"].astype(str).str.lower().str.strip())].copy()
    return df.reset_index(drop=True)

def get_vals(row):
    return {
        "pull": metric(row, ["pull_pct","pull%","pull"], 0),
        "hard": metric(row, ["hard_hit_pct","hardhit%","hard hit%","hh%"], 0),
        "barrel": metric(row, ["barrel_pct","barrel%","brl%"], 0),
        "sweet": metric(row, ["sweet_spot_pct","sweet%","launch","la"], 0),
        "dmg": metric(row, ["dmg","damage","ult","adj"], 0),
        "hpi": metric(row, ["hpi","rating","model","hr score"], 0),
        "hr": metric(row, ["hr_lane","hr_pa","hr/pa","hr9","hr/9"], 0),
        "edge": metric(row, ["pitch_edge","pitch edge","edge"], -99),
        "slot": metric(row, ["lineup_slot","slot","order","bo"], 0),
    }

def metric_count(vals):
    c=0
    for k,v in vals.items():
        if k=="edge":
            if v != -99: c+=1
        elif v is not None and not pd.isna(v):
            c+=1
    return c

def evaluate(row):
    vals=get_vals(row)
    pull,hard,barrel,sweet,dmg,hpi,hr,edge,slot=[vals[k] for k in ["pull","hard","barrel","sweet","dmg","hpi","hr","edge","slot"]]
    player=txt(row.get("player")); team=txt(row.get("team")); pitcher=txt(row.get("pitcher")); game=txt(row.get("game_key") or row.get("game"))
    notes=" ".join([txt(row.get(k)) for k in row.keys() if any(x in str(k).lower() for x in ["note","tag","raw","status"])]).lower()
    official=bool(row.get("official_slate_attached", False))
    gates=[]
    def add(step, gate, passed, score, max_score, reason, hard=True):
        gates.append({"step":step,"gate":gate,"result":"PASS" if passed else "CUT","score":round(max(0,float(score)),2),"max_score":float(max_score),"reason":reason,"hard_gate":bool(hard),"cut":bool(hard and not passed)})
    mc=metric_count(vals)
    trigger=(pull>=30 or hard>=30 or barrel>=5 or dmg>=.8 or hpi>=20 or hr>=.8 or edge>=0)
    matchup_ok = bool(player and game and (official or names_match_team_game(team, game)))
    add(0,"Correct current PDF row", bool(player), 8 if player else 0, 8, f"player={player}")
    add(1,"Official/current matchup integrity", matchup_ok, 10 if matchup_ok else 0, 10, f"team={team}; game={game}; official={official}")
    add(2,"Metric survival", mc>=3 and trigger, 10 if mc>=3 and trigger else 0, 10, f"metrics={mc}; trigger={trigger}")
    add(3,"Pitcher context", bool(pitcher), 6 if pitcher else 0, 6, f"pitcher={pitcher}")
    g4=max(strength(hr,.8,2.2,10), strength(edge,0,15,10), strength(dmg,.8,2.0,10), strength(hpi,20,70,10))
    add(4,"Pitcher HR lane / weakness", g4>0, g4, 10, f"hr={hr}; edge={edge}; dmg={dmg}; hpi={hpi}")
    g5=max(strength(pull,30,52,12), strength(sweet,20,35,12), strength(barrel,5,14,12))
    add(5,"Pull-air / launch window", g5>0, g5, 12, f"pull={pull}; sweet={sweet}; barrel={barrel}")
    g6=max(strength(dmg,.8,2.2,12), strength(barrel,5,14,12), strength(hpi,20,70,12))
    add(6,"Damage / barrel conversion", g6>0, g6, 12, f"dmg={dmg}; barrel={barrel}; hpi={hpi}")
    g7=max(strength(hpi,20,70,12), strength(hr,.8,2.2,12), strength(dmg,.8,2.2,12))
    add(7,"True HR conversion", g7>0, g7, 12, f"hpi={hpi}; hr={hr}; dmg={dmg}")
    add(8,"Opportunity / lineup slot", slot==0 or slot<=7, 7 if slot==0 or slot<=7 else 0, 7, f"slot={slot}", hard=False)
    g9=max(strength(hard,30,55,7), strength(barrel,5,14,7), strength(dmg,.8,2.0,7))
    add(9,"Hard-hit support", g9>0, g9, 7, f"hard={hard}; barrel={barrel}; dmg={dmg}", hard=False)
    adj_note=any(x in notes for x in ["adjacent","decoy","transfer","weak slot","coverage"])
    add(10,"Adjacent / decoy check", True, 5 if adj_note else 2, 5, "triggered" if adj_note else "checked", hard=False)
    who_note=("who" in notes or "chaos" in notes or (pull>=30 and hard>=30 and hpi<45))
    add(11,"WHO / chaos check", True, 6 if who_note else 2, 6, "triggered" if who_note else "checked", hard=False)
    trap=("trap" in notes or "red flag" in notes)
    add(12,"Trap audit", not trap, 8 if not trap else 0, 8, "no trap" if not trap else "trap/red flag")
    fin=0
    if pull>=35:
        fin=max(strength(hard,30,55,12), strength(barrel,5,14,12), strength(dmg,.8,2.0,12), strength(hpi,20,70,12))
    add(13,"Finisher gate", fin>0, fin, 12, f"pull={pull}; hard={hard}; barrel={barrel}; dmg={dmg}; hpi={hpi}")
    g14=max(strength(pull,30,52,10), strength(hard,30,55,10), strength(dmg,.8,2.0,10), strength(hpi,20,70,10), strength(hr,.8,2.2,10), strength(barrel,5,14,10))
    add(14,"Gate 19 confirmation", g14>0, g14, 10, f"model strength={round(g14,2)}")
    hard_cut=any(g["cut"] for g in gates)
    raw=sum(g["score"] for g in gates); mx=sum(g["max_score"] for g in gates)
    # Add small differentiation from metric shape so scores do not tie at a fake cap.
    diff=min(5, (pull/100)+(hard/100)+(barrel/50)+(dmg/5)+(hpi/200)+(hr/10))
    blender=round(max(1,min(100,(raw/mx)*100 + diff)),1)
    if hard_cut: blender=round(min(blender,64.9),1)
    support=round(max(1,min(100,min(pull,65)*.16+min(hard,70)*.12+min(barrel,25)*.5+min(dmg,8)*2.8+min(hpi,100)*.10+min(hr,6)*2.0+(max(min(edge,30),-20)*.2 if edge!=-99 else 0))),1)
    primary=strength(pull,35,52,20)+strength(barrel,6,14,20)+strength(dmg,1,2.2,20)+strength(hpi,25,70,15)+strength(hr,1,2.5,15)+strength(edge,0,20,10)
    adjacent=(35 if adj_note else 0)+strength(pull,30,45,18)+strength(hard,30,48,18)+strength(dmg,.8,1.8,14)+strength(hpi,20,55,10)
    who=(35 if who_note else 0)+strength(pull,28,40,15)+strength(hard,30,45,15)+strength(hr,.8,1.8,15)+strength(edge,0,12,10)+(10 if hpi<45 else 0)
    role_scores={"Primary":round(primary,1),"Adjacent":round(adjacent,1),"WHO":round(who,1)}
    role=max(role_scores,key=role_scores.get)
    eligible=not hard_cut and blender>=55
    if not eligible: role="CUT"
    archetype={"Primary":"Primary HR Owner","Adjacent":"Adjacent / Decoy Transfer","WHO":"WHO / Chaos Owner","CUT":"Cut by gates"}[role]
    return eligible, blender, support, role, archetype, gates, role_scores

def build_results(df):
    df=sanitize_feed(df)
    if df.empty:
        return {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"cuts":pd.DataFrame(),"game_board":pd.DataFrame(),"role_board":pd.DataFrame(),"meta":{"engine_version":"V150_TRUE_BLENDER_MACHINE","message":"No feed rows.","owners_locked":0}}
    surv=[]; board=[]; roles=[]
    for idx,r in df.iterrows():
        row=r.to_dict()
        ok,b,s,role,arch,gates,rs=evaluate(row)
        row.update({"row_id":idx,"blender_eligible":ok,"blender_score":b,"support_score":s,"score":b,"official_core_role":role,"archetype":arch,"final_reason":f"{role} survived all hard gates" if ok else "CUT — see pass/cut trace","gate_trace_json":json.dumps(gates),"role_scores_json":json.dumps(rs)})
        surv.append(row)
        for g in gates:
            board.append({"game_pk":row.get("game_pk",""),"game_key":row.get("game_key",""),"player":row.get("player",""),"role":role,**g,"blender_score":b})
        roles.append({"game_pk":row.get("game_pk",""),"game_key":row.get("game_key",""),"player":row.get("player",""),"assigned_role":role,"Primary_score":rs["Primary"],"Adjacent_score":rs["Adjacent"],"WHO_score":rs["WHO"],"blender_score":b,"support_score":s})
    survivors=pd.DataFrame(surv); cuts=survivors[survivors["blender_eligible"]!=True].copy(); passed=survivors[survivors["blender_eligible"]==True].copy()
    group_col="game_pk" if "game_pk" in survivors.columns and survivors["game_pk"].dropna().astype(str).str.strip().replace("",pd.NA).dropna().nunique()>0 else "game_key"
    owners=[]
    for game,g in passed.groupby(group_col,dropna=False):
        if str(game).strip()=="" or str(game).lower()=="nan": continue
        pick=g.sort_values(["blender_score","support_score"],ascending=[False,False]).iloc[0].to_dict()
        pick["game_owner"]=pick.get("game_key",game)
        owners.append(pick)
    owners=pd.DataFrame(owners)
    if not owners.empty:
        owners=owners.sort_values(["blender_score","support_score"],ascending=[False,False]).reset_index(drop=True)
    used=set(); core_parts=[]; core_slots=[]
    # Core is structured by role; role candidate can come from owners first, then passed rows same role.
    for role in ["Primary","Adjacent","WHO"]:
        pool=owners[(owners["official_core_role"]==role)&(~owners["player"].astype(str).isin(used))].copy() if not owners.empty else pd.DataFrame()
        if pool.empty:
            pool=passed[(passed["official_core_role"]==role)&(~passed["player"].astype(str).isin(used))].copy() if not passed.empty else pd.DataFrame()
        if not pool.empty:
            p=pool.sort_values(["blender_score","support_score"],ascending=[False,False]).head(1).copy()
            p["core_slot"]=role
            core_parts.append(p); used.update(p["player"].astype(str).tolist()); core_slots.append(role)
    core=pd.concat(core_parts,ignore_index=True) if core_parts else pd.DataFrame()
    if not owners.empty and len(core)<3:
        refill=owners[~owners["player"].astype(str).isin(used)].head(3-len(core)).copy()
        if not refill.empty:
            refill["core_slot"]="REFILL"
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
    games=int(df["game_pk"].dropna().astype(str).str.strip().replace("",pd.NA).dropna().nunique()) if "game_pk" in df.columns and df["game_pk"].dropna().astype(str).str.strip().replace("",pd.NA).dropna().nunique()>0 else int(df["game_key"].dropna().astype(str).str.strip().replace("",pd.NA).dropna().nunique())
    meta={"engine_version":"V150_TRUE_BLENDER_MACHINE","games":games,"input_rows":len(df),"passed_rows":len(passed),"cut_rows":len(cuts),"owners_locked":len(owners),"core_count":len(core),"core_slots":core.get("core_slot",pd.Series(dtype=str)).tolist() if not core.empty else [],"message":f"V150 Blender complete: {len(owners)} owners, {len(passed)} pass rows, {len(cuts)} cuts. Core slots={core.get('core_slot',pd.Series(dtype=str)).tolist() if not core.empty else []}."}
    return {"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"cuts":cuts,"game_board":pd.DataFrame(board),"role_board":pd.DataFrame(roles),"meta":meta}


# Final single-source V150 hook
def run_true_blender(df, *args, **kwargs):
    results = build_results(df)
    try:
        save_locked_results(results)
    except Exception:
        pass
    return results



# ============================================================
# V151 TRUE OUTPUT MACHINE — FINAL OVERRIDE
# Fixes:
# - no equal fake 94.6 scores
# - no all-Primary ownership
# - Core cannot be empty if owners exist
# - Core slots are structured Primary / Adjacent / WHO with refill
# - pass/cut board is same memory as tickets
# ============================================================

def _v151_txt(x):
    try:
        if x is None or pd.isna(x): return ""
    except Exception:
        pass
    return str(x).strip()

def _v151_num(x, d=0.0):
    try:
        if x is None or pd.isna(x): return d
        s = str(x).replace("%","").replace("+","").replace(",","").strip()
        if s.lower() in {"","nan","none","null","-","—"}: return d
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group(0)) if m else d
    except Exception:
        return d

def _v151_get(row, names, d=0.0):
    compact = {str(k).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-",""): k for k in row.keys()}
    for n in names:
        nn = str(n).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")
        if nn in compact:
            return _v151_num(row.get(compact[nn]), d)
    for n in names:
        nn = str(n).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")
        for ck, real in compact.items():
            if nn in ck or ck in nn:
                return _v151_num(row.get(real), d)
    return d

def _v151_strength(x, floor, elite, pts):
    if x is None:
        return 0.0
    x = float(x)
    if x < floor:
        return 0.0
    if x >= elite:
        return float(pts)
    return float(pts) * ((x - floor) / max(1, elite - floor))

def _v151_vals(row):
    return {
        "pull": _v151_get(row, ["pull_pct","pull%","pull"], 0),
        "hard": _v151_get(row, ["hard_hit_pct","hardhit%","hard_hit%","hard hit%","hh%"], 0),
        "barrel": _v151_get(row, ["barrel_pct","barrel%","brl%","barrel"], 0),
        "sweet": _v151_get(row, ["sweet_spot_pct","sweet%","sweet spot","launch","la"], 0),
        "dmg": _v151_get(row, ["dmg","damage","ult","ultimate","adj"], 0),
        "hpi": _v151_get(row, ["hpi","model","rating","hr score"], 0),
        "hr": _v151_get(row, ["hr_lane","hr_pa","hr/pa","hr9","hr/9"], 0),
        "edge": _v151_get(row, ["pitch_edge","pitch edge","edge"], -99),
        "slot": _v151_get(row, ["lineup_slot","slot","order","bo"], 0),
    }

def _v151_metric_count(vals):
    c = 0
    for k,v in vals.items():
        if k == "edge":
            if v != -99: c += 1
        elif v not in [None, 0] and not pd.isna(v):
            c += 1
    return c

def _v151_eval(row):
    vals = _v151_vals(row)
    pull, hard, barrel, sweet, dmg, hpi, hr, edge, slot = [vals[k] for k in ["pull","hard","barrel","sweet","dmg","hpi","hr","edge","slot"]]
    player = _v151_txt(row.get("player"))
    team = _v151_txt(row.get("team"))
    pitcher = _v151_txt(row.get("pitcher"))
    game = _v151_txt(row.get("game_key") or row.get("game"))
    notes = " ".join([_v151_txt(row.get(k)) for k in row.keys() if any(x in str(k).lower() for x in ["note","tag","raw","status"])]).lower()
    mc = _v151_metric_count(vals)

    gates = []
    def add(step, gate, passed, pts, max_pts, reason, hard_gate=True):
        gates.append({
            "step": step,
            "gate": gate,
            "result": "PASS" if passed else "CUT",
            "score": round(max(0.0, float(pts)), 2),
            "max_score": float(max_pts),
            "reason": reason,
            "hard_gate": bool(hard_gate),
            "cut": bool(hard_gate and not passed),
        })

    trigger = pull>=30 or hard>=30 or barrel>=5 or dmg>=0.8 or hpi>=20 or hr>=0.8 or edge>=0
    add(0, "Current PDF row", bool(player), 8 if player else 0, 8, f"player={player}")
    add(1, "Game/pitcher context", bool(game and team and pitcher), 8 if game and team and pitcher else 0, 8, f"{team} / {game} / {pitcher}")
    add(2, "Metric survival", mc>=3 and trigger, 10 if mc>=3 and trigger else 0, 10, f"metrics={mc}; trigger={trigger}")
    lane = max(_v151_strength(hr,.8,2.4,10), _v151_strength(edge,0,14,10), _v151_strength(dmg,.8,2.2,10), _v151_strength(hpi,20,75,10))
    add(3, "Pitcher HR lane", lane>0, lane, 10, f"hr={hr}; edge={edge}; dmg={dmg}; hpi={hpi}")
    launch = max(_v151_strength(pull,30,55,12), _v151_strength(sweet,20,38,12), _v151_strength(barrel,5,16,12))
    add(4, "Pull-air / launch", launch>0, launch, 12, f"pull={pull}; sweet={sweet}; barrel={barrel}")
    conv = max(_v151_strength(dmg,.8,2.4,12), _v151_strength(barrel,5,16,12), _v151_strength(hpi,20,80,12), _v151_strength(hr,.8,2.4,12))
    add(5, "Conversion / finisher DNA", conv>0, conv, 12, f"dmg={dmg}; barrel={barrel}; hpi={hpi}; hr={hr}")
    add(6, "Slot opportunity", slot==0 or slot<=7, 6 if slot==0 or slot<=7 else 2, 6, f"slot={slot}", hard_gate=False)
    support_gate = max(_v151_strength(hard,30,58,8), _v151_strength(barrel,5,16,8), _v151_strength(dmg,.8,2.4,8))
    add(7, "Hard-hit support", support_gate>0, support_gate, 8, f"hard={hard}; barrel={barrel}; dmg={dmg}", hard_gate=False)
    trap = "trap" in notes or "red flag" in notes
    add(8, "Trap audit", not trap, 8 if not trap else 0, 8, "no trap" if not trap else "trap/red flag")
    fin = 0
    if pull >= 34:
        fin = max(_v151_strength(hard,30,58,14), _v151_strength(barrel,5,16,14), _v151_strength(dmg,.8,2.4,14), _v151_strength(hpi,20,80,14), _v151_strength(hr,.8,2.4,14))
    add(9, "Final finisher gate", fin>0, fin, 14, f"pull={pull}; hard={hard}; barrel={barrel}; dmg={dmg}; hpi={hpi}; hr={hr}")
    add(10, "Book/adjacent audit", True, 5 if any(x in notes for x in ["adjacent","decoy","transfer","coverage"]) else 2, 5, "checked", hard_gate=False)
    add(11, "WHO/chaos audit", True, 6 if ("who" in notes or "chaos" in notes or (pull>=30 and hard>=30 and hpi<45)) else 2, 6, "checked", hard_gate=False)

    hard_cut = any(g["cut"] for g in gates)
    raw = sum(g["score"] for g in gates)
    mx = sum(g["max_score"] for g in gates)

    # True variable score — no fake universal 94.6.
    shape = (
        min(pull,70)*0.045 + min(hard,70)*0.035 + min(barrel,25)*0.22 +
        min(dmg,5)*0.75 + min(hpi,100)*0.025 + min(hr,5)*0.55 +
        (max(min(edge,25),-20)*0.035 if edge != -99 else 0)
    )
    blender = round(max(1, min(99.1, (raw / max(1,mx)) * 91 + shape)), 1)
    if hard_cut:
        blender = round(min(blender, 59.9), 1)

    support = round(max(1,min(100,min(pull,65)*.16+min(hard,70)*.12+min(barrel,25)*.5+min(dmg,8)*2.8+min(hpi,100)*.10+min(hr,6)*2.0+(max(min(edge,30),-20)*.20 if edge!=-99 else 0))),1)

    primary = _v151_strength(pull,36,55,22)+_v151_strength(barrel,7,16,20)+_v151_strength(dmg,1,2.4,18)+_v151_strength(hpi,30,80,15)+_v151_strength(hr,1,2.5,15)+_v151_strength(edge,0,20,10)
    adjacent = _v151_strength(pull,30,46,18)+_v151_strength(hard,30,52,18)+_v151_strength(dmg,.8,1.8,15)+_v151_strength(hpi,20,60,10)
    if any(x in notes for x in ["adjacent","decoy","transfer","coverage"]): adjacent += 35
    who = _v151_strength(pull,28,42,16)+_v151_strength(hard,30,48,16)+_v151_strength(hr,.8,1.8,16)+_v151_strength(edge,0,12,10)
    if ("who" in notes or "chaos" in notes or (pull>=30 and hard>=30 and hpi<45)): who += 35
    if hpi < 45: who += 8

    role_scores = {"Primary": round(primary,1), "Adjacent": round(adjacent,1), "WHO": round(who,1)}
    role = max(role_scores, key=role_scores.get)
    eligible = not hard_cut and blender >= 55
    if not eligible:
        role = "CUT"

    archetype = {"Primary":"Primary HR Owner","Adjacent":"Adjacent / Decoy Transfer","WHO":"WHO / Chaos Owner","CUT":"Cut by gates"}[role]
    return eligible, blender, support, role, archetype, gates, role_scores

def _v151_build_results(df):
    df = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
    if df.empty:
        return {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"cuts":pd.DataFrame(),"game_board":pd.DataFrame(),"role_board":pd.DataFrame(),"meta":{"engine_version":"V151_TRUE_OUTPUT_MACHINE","message":"No feed.","owners_locked":0}}
    if "game_key" not in df.columns:
        df["game_key"] = df["game"] if "game" in df.columns else ""
    if "player" in df.columns and "pitcher" in df.columns:
        df = df[~(df["player"].astype(str).str.lower().str.strip() == df["pitcher"].astype(str).str.lower().str.strip())].copy()

    survivors=[]; board=[]; roles=[]
    for idx, r in df.iterrows():
        row = r.to_dict()
        ok,b,s,role,arch,gates,role_scores = _v151_eval(row)
        row.update({
            "row_id": idx, "blender_eligible": ok, "blender_score": b, "support_score": s, "score": b,
            "official_core_role": role, "archetype": arch,
            "final_reason": f"{role} survived all hard gates" if ok else "CUT — see pass/cut trace",
            "gate_trace_json": json.dumps(gates), "role_scores_json": json.dumps(role_scores)
        })
        survivors.append(row)
        for g in gates:
            board.append({"game_key":row.get("game_key",""),"player":row.get("player",""),"role":role,**g,"blender_score":b})
        roles.append({"game_key":row.get("game_key",""),"player":row.get("player",""),"assigned_role":role,**role_scores,"blender_score":b,"support_score":s})
    survivors = pd.DataFrame(survivors)
    cuts = survivors[survivors["blender_eligible"] != True].copy()
    passed = survivors[survivors["blender_eligible"] == True].copy()

    group_col = "game_pk" if "game_pk" in passed.columns and passed["game_pk"].dropna().astype(str).str.strip().replace("",pd.NA).dropna().nunique()>0 else "game_key"
    owners=[]
    for game,g in passed.groupby(group_col, dropna=False):
        if str(game).strip()=="" or str(game).lower()=="nan": 
            continue
        pick = g.sort_values(["blender_score","support_score"], ascending=[False,False]).iloc[0].to_dict()
        pick["game_owner"] = pick.get("game_key", game)
        owners.append(pick)
    owners = pd.DataFrame(owners)
    if not owners.empty:
        owners = owners.sort_values(["blender_score","support_score"], ascending=[False,False]).reset_index(drop=True)

    # Structured core, with role slot labels, never blank if owners exist.
    used=set(); core_parts=[]
    for role in ["Primary","Adjacent","WHO"]:
        pool = owners[(owners["official_core_role"]==role)&(~owners["player"].astype(str).isin(used))].copy() if not owners.empty else pd.DataFrame()
        if pool.empty and not passed.empty:
            pool = passed[(passed["official_core_role"]==role)&(~passed["player"].astype(str).isin(used))].copy()
        if not pool.empty:
            p = pool.sort_values(["blender_score","support_score"], ascending=[False,False]).head(1).copy()
            p["core_slot"] = role
            core_parts.append(p)
            used.update(p["player"].astype(str).tolist())
    core = pd.concat(core_parts, ignore_index=True) if core_parts else pd.DataFrame()
    if not owners.empty and len(core) < 3:
        refill = owners[~owners["player"].astype(str).isin(used)].head(3-len(core)).copy()
        if not refill.empty:
            refill["core_slot"] = "REFILL"
            core = pd.concat([core, refill], ignore_index=True)
    if not core.empty:
        core = core.head(3).copy()
        core["ticket_role"] = "CORE"

    used=set(core["player"].astype(str).tolist()) if not core.empty and "player" in core else set()
    alt = owners[~owners["player"].astype(str).isin(used)].head(3).copy() if not owners.empty and "player" in owners else pd.DataFrame()
    if not alt.empty: alt["ticket_role"]="ALT"
    used.update(alt["player"].astype(str).tolist() if not alt.empty and "player" in alt else [])
    chaos = owners[(owners["official_core_role"]=="WHO")&(~owners["player"].astype(str).isin(used))].head(3).copy() if not owners.empty and "player" in owners else pd.DataFrame()
    if chaos.empty and not owners.empty and "player" in owners:
        chaos = owners[~owners["player"].astype(str).isin(used)].head(3).copy()
    if not chaos.empty: chaos["ticket_role"]="WHO"

    games = int(df["game_pk"].dropna().astype(str).str.strip().replace("",pd.NA).dropna().nunique()) if "game_pk" in df.columns and df["game_pk"].dropna().astype(str).str.strip().replace("",pd.NA).dropna().nunique()>0 else int(df["game_key"].dropna().astype(str).str.strip().replace("",pd.NA).dropna().nunique())
    meta = {
        "engine_version":"V151_TRUE_OUTPUT_MACHINE",
        "games":games, "input_rows":len(df), "passed_rows":len(passed), "cut_rows":len(cuts),
        "owners_locked":len(owners), "core_count":len(core),
        "core_slots": core.get("core_slot", pd.Series(dtype=str)).tolist() if not core.empty else [],
        "message": f"V151 Blender complete: {len(owners)} owners, {len(passed)} pass rows, {len(cuts)} cuts. Core slots={core.get('core_slot', pd.Series(dtype=str)).tolist() if not core.empty else []}."
    }
    return {"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"cuts":cuts,"game_board":pd.DataFrame(board),"role_board":pd.DataFrame(roles),"meta":meta}

# absolute final override
def run_true_blender(df, *args, **kwargs):
    results = _v151_build_results(df)
    try:
        save_locked_results(results)
    except Exception:
        pass
    return results
