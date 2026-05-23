
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import io
import urllib.request
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
LOCKED_RESULTS_FILE = DATA_DIR / "locked_results.json"
RECAP_LOG_FILE = DATA_DIR / "recap_log.csv"

try:
    from ai_oil import ai_field_mapper, ai_feed_validator, ai_chaos_who_detector
except Exception:
    ai_field_mapper = ai_feed_validator = ai_chaos_who_detector = None

TEAM_ABBR = {
    "Arizona Diamondbacks":"ARI","Atlanta Braves":"ATL","Baltimore Orioles":"BAL","Boston Red Sox":"BOS",
    "Chicago Cubs":"CHC","Chicago White Sox":"CHW","Cincinnati Reds":"CIN","Cleveland Guardians":"CLE",
    "Colorado Rockies":"COL","Detroit Tigers":"DET","Houston Astros":"HOU","Kansas City Royals":"KC",
    "Los Angeles Angels":"LAA","Los Angeles Dodgers":"LAD","Miami Marlins":"MIA","Milwaukee Brewers":"MIL",
    "Minnesota Twins":"MIN","New York Mets":"NYM","New York Yankees":"NYY","Athletics":"ATH",
    "Oakland Athletics":"ATH","Philadelphia Phillies":"PHI","Pittsburgh Pirates":"PIT","San Diego Padres":"SD",
    "San Francisco Giants":"SF","Seattle Mariners":"SEA","St. Louis Cardinals":"STL","Tampa Bay Rays":"TB",
    "Texas Rangers":"TEX","Toronto Blue Jays":"TOR","Washington Nationals":"WSH"
}
ABBR_TEAM = {v:k for k,v in TEAM_ABBR.items()}

def safe_num(x, default=0.0):
    try:
        if x is None or pd.isna(x):
            return default
        s = str(x).replace("%","").replace(",","").strip()
        if s == "" or s.lower() in {"nan","none","-"}:
            return default
        return float(s)
    except Exception:
        return default

def present(row, key):
    try:
        v = row.get(key)
        return v is not None and not pd.isna(v) and str(v).strip() not in {"","nan","None","-"}
    except Exception:
        return False

def team_abbr(team):
    s = str(team or "").strip()
    if not s:
        return "UNK"
    if s.upper() in ABBR_TEAM:
        return s.upper()
    if s in TEAM_ABBR:
        return TEAM_ABBR[s]
    return "".join(c for c in s.upper() if c.isalpha())[:3] or "UNK"

def canonical_game_key(team, opponent=None, pitcher=None, game=None):
    t1 = team_abbr(team)
    t2 = team_abbr(opponent) if str(opponent or "").strip() else ""
    if t2 and t2 != "UNK" and t2 != t1:
        return "_".join(sorted([t1,t2]))
    p = "".join(c for c in str(pitcher or "").upper() if c.isalpha())[:10]
    return f"{t1}_VS_{p or 'UNK'}"

def normalize_game_frame(df):
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    for c in ["game","game_key","team","opponent","pitcher","player"]:
        if c not in out.columns:
            out[c] = ""
    out["team"] = out["team"].fillna("").astype(str)
    out["opponent"] = out["opponent"].fillna("").astype(str)
    out["pitcher"] = out["pitcher"].fillna("").astype(str)
    out["player"] = out["player"].fillna("").astype(str)
    out["game"] = out["game"].fillna("").astype(str)
    out["game_key"] = out.apply(lambda r: r["game_key"] if str(r["game_key"]).strip() else canonical_game_key(r["team"], r["opponent"], r["pitcher"], r["game"]), axis=1)
    out["game"] = out.apply(lambda r: r["game"] if str(r["game"]).strip() else f"{r['team']} vs {r['pitcher']}", axis=1)
    return out.drop_duplicates(subset=["game_key","team","pitcher","player"], keep="first").reset_index(drop=True)

def actual_game_count(df):
    if df is None or df.empty:
        return 0
    return int(df["game_key"].nunique()) if "game_key" in df.columns else int(df["game"].nunique()) if "game" in df.columns else 0

def is_player_name_safe(x):
    s = str(x or "").strip()
    bad = {"low effort","medium effort","high effort","effort","home","away","fresh","hot","cold","primary","who","adjacent"}
    return len(s) > 2 and s.lower() not in bad and not s.replace(".","").isdigit()

def _slot_match(r):
    slot = safe_num(r.get("lineup_slot"), None)
    if slot is None:
        return False
    vals = [v.strip() for v in str(r.get("weak_slots","")).split(",") if v.strip()]
    return str(int(slot)) in vals

def csv_bytes(df):
    if df is None:
        df = pd.DataFrame()
    return df.to_csv(index=False).encode("utf-8")

def save_locked_results(results):
    try:
        serial = {}
        for k,v in results.items():
            if isinstance(v, pd.DataFrame):
                serial[k] = v.to_dict("records")
            else:
                serial[k] = v
        LOCKED_RESULTS_FILE.write_text(json.dumps(serial, indent=2, default=str))
    except Exception:
        pass

def load_locked_results():
    empty = {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"meta":{}}
    try:
        if not LOCKED_RESULTS_FILE.exists():
            return empty
        raw = json.loads(LOCKED_RESULTS_FILE.read_text())
        out = {}
        for k in ["owners","core","alt","chaos","survivors"]:
            out[k] = pd.DataFrame(raw.get(k, []))
        out["meta"] = raw.get("meta", {})
        return out
    except Exception:
        return empty

def fetch_live_public_slate(date_iso=None):
    if date_iso is None:
        date_iso = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    rows = []
    meta = {"source":"MLB Stats API","date":date_iso,"games":0,"rows":0}
    try:
        url=f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_iso}&hydrate=probablePitcher,team"
        with urllib.request.urlopen(url, timeout=8) as resp:
            data=json.loads(resp.read().decode("utf-8"))
        for d in data.get("dates", []):
            for g in d.get("games", []):
                teams=g.get("teams",{})
                away=teams.get("away",{}).get("team",{}).get("name","")
                home=teams.get("home",{}).get("team",{}).get("name","")
                away_p=teams.get("away",{}).get("probablePitcher",{}).get("fullName","")
                home_p=teams.get("home",{}).get("probablePitcher",{}).get("fullName","")
                game=f"{away} vs {home}"
                rows.append({"game":game,"team":away,"opponent":home,"pitcher":home_p,"player":"","source":"PUBLIC_SLATE"})
                rows.append({"game":game,"team":home,"opponent":away,"pitcher":away_p,"player":"","source":"PUBLIC_SLATE"})
    except Exception as e:
        meta["error"] = str(e)
        return pd.DataFrame(), meta
    df=normalize_game_frame(pd.DataFrame(rows))
    meta["games"]=actual_game_count(df); meta["rows"]=len(df)
    return df, meta

def fetch_team_roster_hitters(team_id):
    try:
        url=f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=active"
        with urllib.request.urlopen(url, timeout=8) as resp:
            data=json.loads(resp.read().decode("utf-8"))
        rows=[]
        for item in data.get("roster", []):
            if item.get("position",{}).get("abbreviation") == "P":
                continue
            p=item.get("person",{})
            if p.get("fullName"):
                rows.append({"player":p.get("fullName"),"mlb_id":p.get("id","")})
        return rows
    except Exception:
        return []

def fetch_live_public_hitter_pool(date_iso=None, max_hitters_per_team=9):
    slate, meta = fetch_live_public_slate(date_iso)
    if slate.empty:
        return pd.DataFrame(), meta
    if date_iso is None:
        date_iso = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    team_ids={}
    try:
        url=f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_iso}&hydrate=probablePitcher,team"
        with urllib.request.urlopen(url, timeout=8) as resp:
            data=json.loads(resp.read().decode("utf-8"))
        for d in data.get("dates", []):
            for g in d.get("games", []):
                for side in ["away","home"]:
                    t=g.get("teams",{}).get(side,{}).get("team",{})
                    if t.get("name") and t.get("id"):
                        team_ids[t.get("name")] = t.get("id")
    except Exception:
        pass
    rows=[]
    for _,s in slate.iterrows():
        hitters=fetch_team_roster_hitters(team_ids.get(s.get("team","")))[:max_hitters_per_team] if team_ids.get(s.get("team","")) else []
        for idx,h in enumerate(hitters, start=1):
            row=s.to_dict()
            row.update({"player":h["player"],"mlb_id":h.get("mlb_id",""),"lineup_slot":idx,"source":"LIVE_PUBLIC_POOL"})
            rows.append(row)
    df=normalize_game_frame(pd.DataFrame(rows))
    meta["hitter_rows"]=len(df); meta["metric_rows"]=0
    return df, meta

def merge_public_context(feed_df, public_df):
    try:
        feed=normalize_game_frame(feed_df)
        if public_df is None or public_df.empty:
            return feed
        pub=normalize_game_frame(public_df)
        ctx=pub.drop_duplicates("team")[[c for c in ["team","opponent","pitcher","game","game_key"] if c in pub.columns]]
        out=feed.merge(ctx,on="team",how="left",suffixes=("","_pub"))
        for c in ["opponent","pitcher","game","game_key"]:
            pc=c+"_pub"
            if pc in out.columns:
                if c not in out.columns:
                    out[c]=""
                out[c]=out[c].where(out[c].astype(str).str.strip().ne(""), out[pc])
                out=out.drop(columns=[pc])
        return normalize_game_frame(out)
    except Exception:
        return normalize_game_frame(feed_df)

def recalc_adaptive_weights_from_history():
    return {"pull":1.0,"launch":1.0,"damage":1.0,"conversion":1.0,"pitch":1.0}

def _apply_ai_oil(df):
    out = df.copy()
    try:
        if ai_field_mapper:
            out, _ = ai_field_mapper(out)
        if ai_chaos_who_detector:
            out = ai_chaos_who_detector(out)
    except Exception:
        pass
    return out

def evaluate_19_gates(r):
    pull=safe_num(r.get("pull_pct")); sweet=safe_num(r.get("sweet_spot_pct")); barrel=safe_num(r.get("barrel_pct"))
    hh=safe_num(r.get("hard_hit_pct")); dmg=safe_num(r.get("dmg")); hrpa=safe_num(r.get("hr_pa")); hpi=safe_num(r.get("hpi")); pe=safe_num(r.get("pitch_edge"))
    slot=safe_num(r.get("lineup_slot"), None)
    metric_hits=sum(present(r,k) for k in ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi"])
    env=bool(str(r.get("team","")).strip()) and bool(str(r.get("pitcher","")).strip())
    legal=is_player_name_safe(r.get("player")) and metric_hits >= 3
    pitch_known=present(r,"pitch_edge")
    pitch_ok=(pe>=0) if pitch_known else True
    pull_air=pull>=38 or (pull>=30 and sweet>=27) or (pull>=28 and dmg>=1.5)
    launch=sweet>=24 or barrel>=9 or hh>=42 or dmg>=1.65
    damage=dmg>=1.45 or hrpa>=2.0 or hpi>=38 or bool(r.get("hr_alert"))
    conversion=hpi>=34 or hrpa>=1.5 or dmg>=1.45
    opportunity=slot is not None or _slot_match(r) or bool(r.get("platoon"))
    hardhit=hh>=38 or barrel>=8 or dmg>=1.5 or sweet>=28
    adjacent=_slot_match(r) or bool(r.get("platoon")) or bool(r.get("adjacent_transfer"))
    chaos=bool(r.get("hr_alert")) and damage and conversion
    recap_dna=sum([pull>=38,dmg>=1.45,hpi>=34,hrpa>=1.5,sweet>=24,barrel>=9,hh>=42])>=3
    anti=not bool(r.get("chalk_trap"))
    finisher=pull_air and damage and conversion
    gates=[
        ("0 Environment",env,False),("1 Pool legality",legal,True),("2 Side lock",env,True),
        ("3 Pitcher weakness",pitch_ok or damage,False),("4 Pitch-type lane",pitch_ok,False),
        ("5 Pull-air",pull_air,True),("6 Launch",launch,False),("7 Damage",damage,True),
        ("8 Conversion",conversion,True),("9 Opportunity",opportunity,False),("10 Hard-hit",hardhit,False),
        ("10.5 Adjacent",adjacent,False),("11 WHO/Chaos",chaos,False),("12 Game script",True,False),
        ("13 Recap DNA",recap_dna,False),("14 Anti-chalk",anti,True),("15 Bullpen",True,False),
        ("16 Finisher",finisher,True),("17 Owner isolation",True,True),("18 Final audit",True,True),("19 Model confirm",recap_dna or finisher,False),
    ]
    hard=[n for n,p,h in gates if h and not p]
    soft=[n for n,p,h in gates if (not h) and not p]
    grade=round(sum(1 for _,p,_ in gates if p)/len(gates)*100,1)
    return {"gates":gates,"hard_failed":hard,"soft_failed":soft,"grade":grade,"clean_owner":len(hard)==0,"adjacent":adjacent,"chaos":chaos}

def blend_score(r):
    pull=safe_num(r.get("pull_pct")); sweet=safe_num(r.get("sweet_spot_pct")); barrel=safe_num(r.get("barrel_pct"))
    hh=safe_num(r.get("hard_hit_pct")); dmg=safe_num(r.get("dmg")); hrpa=safe_num(r.get("hr_pa")); hpi=safe_num(r.get("hpi")); pe=safe_num(r.get("pitch_edge"))
    slot=safe_num(r.get("lineup_slot"), None)
    score=0
    score += min(18,max(0,(pull-25)*.75))
    score += min(12,max(0,(sweet-18)*.6))
    score += min(10,max(0,(barrel-5)*1.25))
    score += min(8,max(0,(hh-34)*.45))
    score += 13 if dmg>=2.2 else 10 if dmg>=1.8 else 7 if dmg>=1.5 else 4 if dmg>=1.2 else 0
    score += 10 if hrpa>=4 else 8 if hrpa>=3 else 6 if hrpa>=2 else 3 if hrpa>=1.3 else 0
    score += 10 if hpi>=50 else 8 if hpi>=42 else 5 if hpi>=35 else 2 if hpi>=28 else 0
    if present(r,"pitch_edge"):
        score += 12 if pe>=15 else 9 if pe>=8 else 5 if pe>=0 else -12
    else:
        score += 1.5
    if _slot_match(r): score += 6
    elif slot is not None and 1 <= slot <= 5: score += 4
    elif slot is not None: score += 1.5
    if bool(r.get("hr_alert")): score += 3
    if bool(r.get("platoon")): score += 2
    if bool(r.get("adjacent_transfer")): score += 2
    if pull<25: score -= 12
    if sweet<20 and barrel<7: score -= 8
    if dmg<1 and hrpa<1 and hpi<25: score -= 12
    if bool(r.get("chalk_trap")): score -= 8
    return round(max(0,min(92,score)),1)

def _role_arch(r, e):
    if e["clean_owner"]:
        if e["chaos"]:
            return "WHO", "WHO / Chaos Finisher"
        if e["adjacent"]:
            return "Adjacent", "Adjacent / Transfer Owner"
        score=blend_score(r)
        if score>=78:
            return "Primary", "Elite Converter"
        return "Primary", "Primary HR Owner"
    return "Recovery", "Audit Survivor / Data-Recovery Profile"

def _gate_path(e):
    parts=[]
    for name,p,h in e["gates"]:
        parts.append(f"{name}: {'PASS' if p else ('KILL' if h else 'WEAK')}")
    if e["hard_failed"]:
        parts.append("HARD FAILS: "+", ".join(e["hard_failed"]))
    if e["soft_failed"]:
        parts.append("SOFT FLAGS: "+", ".join(e["soft_failed"]))
    return " | ".join(parts)

def _run_game(gdf):
    pool=gdf.copy()
    needed=["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi","pitch_edge","lineup_slot","weak_slots"]
    for c in needed:
        if c not in pool.columns:
            pool[c]=None
    rows=[]
    for _,r in pool.iterrows():
        e=evaluate_19_gates(r)
        row=r.to_dict()
        row["score"]=blend_score(r)
        role, arch=_role_arch(r,e)
        row["official_core_role"]=role
        row["archetype"]=arch
        row["gate_grade"]=e["grade"]
        row["hard_fails"]=", ".join(e["hard_failed"])
        row["soft_fails"]=", ".join(e["soft_failed"])
        row["gate_path"]=_gate_path(e)
        row["_clean"]=e["clean_owner"]
        rows.append(row)
    out=pd.DataFrame(rows)
    clean=out[out["_clean"]].copy()
    if clean.empty:
        out["_rank_score"]=out["score"] + out["gate_grade"]*.08
        best=out.sort_values("_rank_score",ascending=False).head(1).copy()
        if float(best.iloc[0]["score"]) >= 42 and is_player_name_safe(best.iloc[0]["player"]):
            best["score"]=best["score"].apply(lambda x:max(40,min(68,float(x))))
            best["official_core_role"]="Recovery"
            best["archetype"]="Audit Survivor / Data-Recovery Profile"
        else:
            best["score"]=best["score"].apply(lambda x:min(39,float(x)))
            best["official_core_role"]="NO PLAY"
            best["archetype"]="No Clean Owner"
        return best.drop(columns=[c for c in ["_clean","_rank_score"] if c in best.columns])
    clean["_rank_score"]=clean["score"] + clean["gate_grade"]*.05
    return clean.sort_values("_rank_score",ascending=False).drop(columns=[c for c in ["_clean","_rank_score"] if c in clean.columns])

def build_tickets_from_owners(owners, survivors=None):
    if owners is None or owners.empty:
        return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    df=owners.sort_values("score",ascending=False).reset_index(drop=True)
    clean=df[df["official_core_role"].isin(["Primary","Adjacent","WHO"])]
    recovery=df[df["official_core_role"].eq("Recovery")]
    core_pool=clean if len(clean)>=3 else pd.concat([clean,recovery],ignore_index=True)
    core=core_pool.head(3).copy()
    used=set(core["player"]) if not core.empty and "player" in core else set()
    alt=df[~df["player"].isin(used)].head(3).copy() if "player" in df else pd.DataFrame()
    used.update(alt["player"] if not alt.empty and "player" in alt else [])
    chaos=df[(~df["player"].isin(used)) & (df["archetype"].astype(str).str.contains("WHO|Chaos|Recovery|Transfer",case=False,na=False))].head(3).copy() if "player" in df else pd.DataFrame()
    if chaos.empty and "player" in df:
        chaos=df[~df["player"].isin(used)].head(3).copy()
    return core,alt,chaos

def run_true_blender(df, *args, **kwargs):
    df=normalize_game_frame(_apply_ai_oil(df))
    meta={"input_rows":len(df) if df is not None else 0,"games":actual_game_count(df),"owners_locked":0,"survivor_rows":0,"no_play_games":0,"message":"","engine_version":"v93_TRUE_427_RESET"}
    if df is None or df.empty:
        meta["message"]="No feed rows available."
        res={"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"meta":meta}
        save_locked_results(res); return res
    survivors=[]; owners=[]
    for game,gdf in df.groupby("game_key" if "game_key" in df.columns else "game", dropna=False):
        g=_run_game(gdf)
        if g is None or g.empty: continue
        g=g.assign(game_owner=game)
        survivors.append(g)
        top=g.iloc[0].to_dict()
        if top.get("official_core_role")!="NO PLAY":
            owners.append(top)
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    survivors=pd.concat(survivors,ignore_index=True) if survivors else pd.DataFrame()
    meta["owners_locked"]=len(owners); meta["survivor_rows"]=len(survivors)
    if not survivors.empty and "official_core_role" in survivors:
        meta["no_play_games"]=int((survivors["official_core_role"].astype(str)=="NO PLAY").sum())
    if owners.empty:
        meta["message"]="Blender complete: no qualified owners survived. Game Board shows gate kills."
        res={"owners":owners,"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":survivors,"meta":meta}
        save_locked_results(res); return res
    owners=owners.sort_values("score",ascending=False).drop_duplicates(subset=["player","team","pitcher"],keep="first").reset_index(drop=True)
    core,alt,chaos=build_tickets_from_owners(owners,survivors)
    clean=int((owners["official_core_role"].astype(str)!="Recovery").sum())
    recovery=int((owners["official_core_role"].astype(str)=="Recovery").sum())
    meta["message"]=f"Blender complete: {len(owners)} game owners locked from {meta['games']} games. Clean={clean} · Recovery={recovery}."
    res={"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"meta":meta}
    save_locked_results(res); return res

def run_recap_check(results=None):
    return {"status":"ready","message":"Recap hook ready."}
