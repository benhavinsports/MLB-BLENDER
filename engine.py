
import re, json
import pandas as pd
import numpy as np

APP_ENGINE_VERSION = "v149_RESTORED_BLENDER_EXPERIENCE"

BOARD_GATES = [("START","start"),("Pool","pool"),("Weak Slot","weakslot"),("Pitcher Lane","pitcher"),("Pitch Type","pitch"),("Pull-Air","pull"),("Launch","launch"),("Damage","damage"),("Conversion","conversion"),("Opportunity","opportunity"),("Hard-Hit","hardhit"),("Adjacent Pressure","adjacent"),("WHO Trigger","who"),("Game Script","script"),("Finisher","finisher"),("Event Isolation","isolation"),("OWNER","owner")]
RECENT_REPEAT_NAMES = {"kyle schwarber","austin riley","byron buxton","james wood","nick kurtz","jac caglianone","kazuma okamoto"}

def _clean(s): return re.sub(r"\s+", " ", str(s or "").strip())
def _key(s): return _clean(s).lower()
def _num(row, col, default=0.0):
    try:
        v = row.get(col, default)
        return default if pd.isna(v) else float(v)
    except Exception:
        return default
def _text(row): return " ".join(str(row.get(c,"")) for c in ["tags","gate_path","soft_fails","hard_fails","event_note","archetype","event_role"]).lower()

def csv_bytes(df):
    try:
        return (df if df is not None else pd.DataFrame()).to_csv(index=False).encode("utf-8")
    except Exception:
        return b""
def json_bytes(obj):
    try: return json.dumps(obj, default=str, indent=2).encode("utf-8")
    except Exception: return b"{}"
def empty_results():
    return {"owners":pd.DataFrame(),"survivors":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"sgp":pd.DataFrame(),"meta":{"engine_version":APP_ENGINE_VERSION}}
def safe_results(res=None):
    out=empty_results()
    if isinstance(res,dict): out.update(res)
    return out

def normalize_game_frame(df):
    if df is None: return pd.DataFrame()
    out=df.copy()
    for c in ["player","team","pitcher","game","tags","gate_path"]:
        if c not in out.columns: out[c]=""
    for c in ["player","team","pitcher","game","tags","gate_path"]:
        out[c]=out[c].astype(str).map(_clean)
    out["game"]=out.apply(lambda r: r.get("game") if _clean(r.get("game")) else f"{r.get('team','')} vs {r.get('pitcher','')}",axis=1)
    return out
normalize_feed=normalize_columns=merge_public_context=attach_slate_matchup_context=normalize_game_frame

def attack_pool_count(df):
    d=normalize_game_frame(df)
    return 0 if d.empty else int(d["game"].replace("",np.nan).dropna().nunique())
actual_game_count=attack_pool_count
def slate_game_count_from_public_context(public_context=None, fallback_df=None): return attack_pool_count(fallback_df) if fallback_df is not None else 0

def _ensure_numeric(out):
    aliases={"opponent_pitcher":"pitcher","pitcher_matchup":"pitcher","hr_pct_pa":"hr_pa","hr_pa_pct":"hr_pa","line":"line_drive_pct","line_pct":"line_drive_pct","cond":"cond_pct","pitch_edge":"pitch_edge_pct","hr_edge":"hr_edge_pct","sweet":"sweet_spot_pct","sweet_spot":"sweet_spot_pct","pull":"pull_pct","barrel":"barrel_pct"}
    for a,b in aliases.items():
        if a in out.columns and b not in out.columns: out[b]=out[a]
    for c in ["hr_pa","dmg","hpi","line_drive_pct","cond_pct","hr_edge_pct","pitch_edge_pct","effort","sweet_spot_pct","pull_pct","barrel_pct","score"]:
        if c not in out.columns: out[c]=np.nan
        out[c]=pd.to_numeric(out[c],errors="coerce")
    return out

def prepare_candidates(df):
    out=_ensure_numeric(normalize_game_frame(df))
    if out.empty: return out
    for c in ["hard_fails","soft_fails","official_core_role","archetype"]:
        if c not in out.columns: out[c]=""
    out=out[out["player"].str.split().str.len().ge(2)]
    out=out[out["team"].str.len().gt(1)&out["pitcher"].str.len().gt(1)]
    metrics=["hr_pa","dmg","hpi","line_drive_pct","cond_pct","hr_edge_pct"]
    out=out[out[metrics].notna().any(axis=1)].copy()
    bad={"weak slot","star roll","low effort","high effort","line drive","parse audit"}
    out=out[~out["player"].str.lower().isin(bad)]
    return out.drop_duplicates(subset=["team","pitcher","player"],keep="first").reset_index(drop=True)

def _metric_score(row):
    hrpa=_num(row,"hr_pa"); dmg=_num(row,"dmg"); hpi=_num(row,"hpi"); line=_num(row,"line_drive_pct"); cond=_num(row,"cond_pct"); he=_num(row,"hr_edge_pct"); pe=_num(row,"pitch_edge_pct"); sweet=_num(row,"sweet_spot_pct"); tags=_text(row)
    score=min(35,hrpa*6)+min(30,dmg*16)+min(20,hpi*.4)+(8 if line>=25 else 4 if line>=18 else 0)+(7 if cond>=20 else 0)+(6 if sweet>=50 else 3 if sweet>=35 else 0)+(8 if he>0 else -4 if he<-10 else 0)+(8 if pe>10 else -4 if pe<-10 else 0)
    score+=6 if "weak slot" in tags else 0
    score+=5 if "laser" in tags else 0
    score+=4 if ("rakes rhp" in tags or "eats lhp" in tags) else 0
    score+=4 if "platoon" in tags else 0
    return round(max(0,min(100,score)),1)

def _role(row):
    score=_metric_score(row); tags=_text(row); dmg=_num(row,"dmg"); hrpa=_num(row,"hr_pa")
    if _key(row.get("player")) in RECENT_REPEAT_NAMES and score < 68: return "ROTATED"
    if score>=62 and dmg>=1.25: return "Primary"
    if score>=50 or ("weak slot" in tags and score>=45) or ("laser" in tags and score>=45): return "Adjacent"
    if score>=40 and (hrpa>=2.0 or "chaos" in tags or "who" in tags): return "WHO"
    return "CUT"

def _gate_status(row,label,key):
    role=str(row.get("event_role","")); tags=_text(row)
    if key in ["start","pool"]: return "PASS"
    if key=="weakslot": return "PASS" if "weak slot" in tags else "SOFT"
    if key=="pull": return "PASS" if _num(row,"pull_pct")>=30 else "SOFT" if pd.isna(row.get("pull_pct",np.nan)) else "CUT"
    if key=="launch": return "PASS" if _num(row,"sweet_spot_pct")>=50 else "SOFT" if _num(row,"sweet_spot_pct")>=35 else "CUT"
    if key=="damage": return "PASS" if _num(row,"dmg")>=1.35 else "SOFT" if _num(row,"dmg")>=1.0 else "CUT"
    if key=="conversion": return "PASS" if _num(row,"hr_pa")>=2.0 else "SOFT" if _num(row,"hr_pa")>=1.0 else "CUT"
    if key=="opportunity": return "PASS" if _num(row,"hpi")>=40 else "SOFT" if _num(row,"hpi")>=25 else "CUT"
    if key=="hardhit": return "SOFT"
    if key=="adjacent": return "PASS" if role=="Adjacent" else "SOFT" if ("weak slot" in tags or "laser" in tags) else "CUT"
    if key=="who": return "PASS" if role=="WHO" else "SOFT" if (_num(row,"hr_pa")>=2.0 or "chaos" in tags) else "CUT"
    if key in ["finisher","isolation","owner"]: return "PASS" if role in ["Primary","Adjacent","WHO"] else "CUT"
    return "PASS" if role in ["Primary","Adjacent","WHO"] else "SOFT"

def apply_board_memory(df):
    if df is None or df.empty: return df
    out=df.copy(); fulls=[]; passes=[]; softs=[]; cuts=[]
    for _,row in out.iterrows():
        full=[];p=[];s=[];c=[]
        for label,key in BOARD_GATES:
            st=_gate_status(row,label,key); full.append(f"{label}: {st}")
            (p if st=="PASS" else s if st=="SOFT" else c).append(label)
        fulls.append(" | ".join(full)); passes.append(", ".join(p)); softs.append(", ".join(s)); cuts.append(", ".join(c))
    out["gate_trace_full"]=fulls; out["pass_gates"]=passes; out["soft_gates"]=softs; out["cut_gates"]=cuts
    out["pass_count"]=[len(x.split(", ")) if x else 0 for x in passes]; out["soft_count"]=[len(x.split(", ")) if x else 0 for x in softs]; out["cut_count"]=[len(x.split(", ")) if x else 0 for x in cuts]
    out["board_lane_label"]=out.apply(lambda r:f"{str(r.get('event_role') or r.get('official_core_role') or 'Audit')} lane • PASS {int(r.get('pass_count',0))} / SOFT {int(r.get('soft_count',0))} / CUT {int(r.get('cut_count',0))}",axis=1)
    out["lane_note"]=out["board_lane_label"]
    return out

def evaluate_candidates(df):
    out=prepare_candidates(df)
    if out.empty: return out
    out["score"]=out.apply(_metric_score,axis=1)
    out["event_role"]=out.apply(_role,axis=1)
    out["ownership_eligible"]=out["event_role"].isin(["Primary","Adjacent","WHO"])
    out["event_note"]=out["event_role"].map({"Primary":"PRIMARY_EVENT_OWNER","Adjacent":"ADJACENT_TRANSFER_EVENT_OWNER","WHO":"WHO_CHAOS_EVENT_OWNER","ROTATED":"ROTATED_OUT_REPEAT","CUT":"CUT_BY_SCORE"})
    out["archetype"]=out["event_role"].map({"Primary":"Primary Event Owner","Adjacent":"Adjacent / Transfer Event Owner","WHO":"WHO / Chaos Event Owner","ROTATED":"Rotated Repeat Audit","CUT":"Audit / Cut"})
    return apply_board_memory(out.sort_values("score",ascending=False).reset_index(drop=True))

def _take(pool,used,n=1):
    if pool is None or pool.empty: return pd.DataFrame()
    d=pool.copy()
    if "player" in d.columns: d=d[~d["player"].str.lower().str.strip().isin(used)]
    return d.sort_values("score",ascending=False).drop_duplicates(subset=["player"],keep="first").head(n).copy() if not d.empty else pd.DataFrame()

def build_tickets_from_owners(owners,survivors=None):
    ranked=owners if owners is not None and hasattr(owners,"empty") and not owners.empty else survivors
    if ranked is None or ranked.empty: return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    eligible=ranked[ranked.get("ownership_eligible",False).astype(bool)].copy() if "ownership_eligible" in ranked.columns else ranked.copy()
    if eligible.empty: return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    used=set(); parts=[]
    for role,arch in [("Primary","Primary Event Owner"),("Adjacent","Adjacent / Transfer Event Owner"),("WHO","WHO / Chaos Event Owner")]:
        one=_take(eligible[eligible["event_role"].eq(role)].copy(),used,1); source="TRUE_ROLE"
        if one.empty: one=_take(eligible,used,1); source="ROLE_SUPPORT_FALLBACK"
        if not one.empty:
            one["official_core_role"]=role; one["archetype"]=arch if source=="TRUE_ROLE" else f"{role} Support Fallback"; one["core_slot_source"]=source
            used.update(one["player"].astype(str).str.lower().str.strip().tolist()); parts.append(one)
    core=pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()
    if not core.empty:
        core["__order"]=core["official_core_role"].map({"Primary":0,"Adjacent":1,"WHO":2}).fillna(9); core=core.sort_values("__order").drop(columns=["__order"]).reset_index(drop=True)
    alt=_take(eligible,used,3)
    if not alt.empty: alt["official_core_role"]="ALT"; alt["archetype"]="Unified Alternate"
    chaos=_take(eligible[eligible["event_role"].eq("WHO")].copy(),used,3)
    if not chaos.empty: chaos["official_core_role"]="WHO"; chaos["archetype"]="WHO / Chaos Event Owner"
    return apply_board_memory(core),apply_board_memory(alt),apply_board_memory(chaos)

def run_true_blender(df,*args,**kwargs):
    survivors=evaluate_candidates(df)
    owners=survivors[survivors["ownership_eligible"].astype(bool)].copy() if "ownership_eligible" in survivors.columns and not survivors.empty else pd.DataFrame()
    core,alt,chaos=build_tickets_from_owners(owners,survivors)
    return {"owners":owners,"survivors":survivors,"core":core,"alt":alt,"chaos":chaos,"sgp":identify_sgp_candidates({"owners":owners}),"meta":{"engine_version":APP_ENGINE_VERSION,"pipeline":"correct_clean_runtime","players":int(len(prepare_candidates(df))),"owners":int(len(owners)),"core":int(len(core)),"games":int(attack_pool_count(df))}}

def get_game_board(results): return apply_board_memory(safe_results(results).get("survivors",pd.DataFrame()))
def clean_results_for_display(results):
    res=safe_results(results)
    for k in ["owners","survivors","core","alt","chaos"]:
        d=res.get(k)
        if d is not None and hasattr(d,"empty") and not d.empty: res[k]=apply_board_memory(d)
    return res
def get_ticket_frames(results):
    res=safe_results(results); return res.get("core",pd.DataFrame()),res.get("alt",pd.DataFrame()),res.get("chaos",pd.DataFrame())
def export_results_csv(results):
    res=safe_results(results); parts=[]
    for name in ["core","alt","chaos","owners","survivors"]:
        d=res.get(name,pd.DataFrame())
        if d is not None and not d.empty:
            x=d.copy(); x.insert(0,"section",name); parts.append(x)
    return pd.concat(parts,ignore_index=True) if parts else pd.DataFrame()

def _time_to_minutes(value):
    try:
        if value is None or str(value).strip()=="": return None
        s=str(value).strip().lower().replace("et","").replace("est","").replace("edt","").strip(); ampm=None
        if s.endswith("am") or s.endswith("pm"): ampm=s[-2:]; s=s[:-2].strip()
        h,m=(s.split(":",1)+["0"])[:2] if ":" in s else (s,"0")
        h=int(re.sub(r"[^0-9]","",h) or 0); m=int(re.sub(r"[^0-9]","",m) or 0)
        if ampm=="pm" and h!=12: h+=12
        if ampm=="am" and h==12: h=0
        return h*60+m
    except Exception: return None
def add_time_bucket(df):
    if df is None or df.empty: return df
    out=df.copy(); out["game_minutes"]=out.apply(lambda r:_time_to_minutes(r.get("game_time",r.get("start_time",r.get("time","")))),axis=1)
    out["time_bucket"]=out["game_minutes"].apply(lambda x:"Early" if pd.notna(x) and x<960 else ("Late" if pd.notna(x) and x>=960 else "Unknown"))
    return out
def filter_results_by_timeframe(results,timeframe="Full slate",custom_start=None,custom_end=None):
    res=safe_results(results)
    for k in ["owners","survivors"]:
        d=add_time_bucket(res.get(k,pd.DataFrame()))
        if d is None or d.empty: res[k]=pd.DataFrame(); continue
        if timeframe=="Early games": d=d[d["time_bucket"].eq("Early")]
        elif timeframe=="Late games": d=d[d["time_bucket"].eq("Late")]
        res[k]=d.reset_index(drop=True)
    res["core"],res["alt"],res["chaos"]=build_tickets_from_owners(res.get("owners"),res.get("survivors"))
    res["sgp"]=identify_sgp_candidates(res)
    return clean_results_for_display(res)
def identify_sgp_candidates(results,min_game_owners=2):
    owners=safe_results(results).get("owners",pd.DataFrame())
    if owners is None or owners.empty: return pd.DataFrame()
    rows=[]
    for game,g in owners.groupby("game",dropna=False):
        if len(g)<min_game_owners: continue
        roles=set(g["event_role"].astype(str).tolist()) if "event_role" in g.columns else set()
        avg=float(pd.to_numeric(g.get("score",0),errors="coerce").fillna(0).mean())
        env=round(avg+(8 if "WHO" in roles else 0)+(5 if "Adjacent" in roles else 0),1)
        if env>=60 or ("WHO" in roles and "Adjacent" in roles):
            top=g.sort_values("score",ascending=False).head(4)
            rows.append({"game":game,"sgp_type":"Blender SGP Environment","environment_score":env,"legs":" + ".join(top["player"].astype(str).tolist()),"roles":", ".join(sorted(roles)),"why":"Blender-qualified same-game environment"})
    return pd.DataFrame(rows).sort_values("environment_score",ascending=False).reset_index(drop=True) if rows else pd.DataFrame()
def run_ticket_view(results,timeframe="Full slate",custom_start=None,custom_end=None): return filter_results_by_timeframe(results,timeframe,custom_start,custom_end)

# compatibility
def run_blender(df,*a,**k): return run_true_blender(df,*a,**k)
def run_public_blender(*a,**k): return run_true_blender(k.get("df",pd.DataFrame()))
def score_candidates(df,*a,**k): return evaluate_candidates(df)
def enrich_feed(df,*a,**k): return normalize_game_frame(df)
def build_feed_from_public(*a,**k): return pd.DataFrame()
def load_public_slate(*a,**k): return pd.DataFrame()
def fetch_live_public_slate(*a,**k): return pd.DataFrame(),{"source":"disabled"}
def fetch_live_public_hitter_pool(*a,**k): return pd.DataFrame(),{"source":"disabled"}
def get_current_feed_summary(df): return {"players":int(len(prepare_candidates(df))),"games":attack_pool_count(df)}
def make_summary(df): return get_current_feed_summary(df)
def summarize_feed(df): return get_current_feed_summary(df)
def calibrate_model_weights(*a,**k): return {"ok":True}
def recalibrate_model_weights(*a,**k): return {"ok":True}
def apply_model_calibration(df,*a,**k): return df
def reset_model_calibration(*a,**k): return True
def explain_candidate(row): return str(row.get("event_note","")) if hasattr(row,"get") else ""
def player_team_integrity_guard(df): return normalize_game_frame(df)
def validate_player_team_integrity(df): return normalize_game_frame(df)
def role_locked_ticket_builder(owners,survivors=None): return build_tickets_from_owners(owners,survivors)
def event_isolation_engine(df): return evaluate_candidates(df)
def apply_event_isolation(df): return evaluate_candidates(df)
def anti_repeat_engine(df): return evaluate_candidates(df)
def rotation_redistribution_engine(df): return evaluate_candidates(df)
def repeat_cut_refill_engine(df): return evaluate_candidates(df)
