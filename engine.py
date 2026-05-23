
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json, re, urllib.request
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
LOCKED_RESULTS_FILE = DATA_DIR / "locked_results.json"

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

def _num(x, default=0.0):
    try:
        if x is None or pd.isna(x): return default
        s=str(x).replace("%","").replace(",","").strip()
        if s=="" or s.lower() in {"nan","none","-","—"}: return default
        m=re.search(r"-?\d+(?:\.\d+)?",s)
        return float(m.group()) if m else default
    except Exception:
        return default

def _present(r,k):
    try:
        v=r.get(k)
        return v is not None and not pd.isna(v) and str(v).strip() not in {"","nan","None","-","—"}
    except Exception:
        return False

def team_abbr(team):
    s=str(team or "").strip()
    if s.upper() in ABBR_TEAM: return s.upper()
    if s in TEAM_ABBR: return TEAM_ABBR[s]
    return "".join(c for c in s.upper() if c.isalpha())[:3] or "UNK"

def canonical_game_key(team, opponent=None, pitcher=None):
    t1=team_abbr(team); t2=team_abbr(opponent)
    if t2 and t2!="UNK" and t2!=t1: return "_".join(sorted([t1,t2]))
    p="".join(c for c in str(pitcher or "").upper() if c.isalpha())[:10]
    return f"{t1}_VS_{p or 'UNK'}"

def normalize_game_frame(df):
    if df is None or df.empty: return pd.DataFrame()
    out=df.copy()
    for c in ["game","game_key","team","opponent","pitcher","player"]:
        if c not in out.columns: out[c]=""
    for c in ["game","game_key","team","opponent","pitcher","player"]:
        out[c]=out[c].fillna("").astype(str)
    # fallback team from game if blank impossible; still preserve player rows
    out["game_key"]=out.apply(lambda r: r["game_key"] if str(r["game_key"]).strip() else canonical_game_key(r["team"],r["opponent"],r["pitcher"]),axis=1)
    out["game"]=out.apply(lambda r: r["game"] if str(r["game"]).strip() else f"{r['team']} vs {r['pitcher']}",axis=1)
    return out.drop_duplicates(subset=["game_key","team","pitcher","player"], keep="first").reset_index(drop=True)

def actual_game_count(df):
    if df is None or df.empty: return 0
    return int(df["game_key"].nunique()) if "game_key" in df.columns else int(df["game"].nunique()) if "game" in df.columns else 0

def is_player_name_safe(x):
    s=str(x or "").strip()
    bad={"low effort","medium effort","high effort","effort","player","team","pitcher","pull","hpi","dmg"}
    return len(s)>2 and s.lower() not in bad and not any(ch.isdigit() for ch in s)

def _slot_match(r):
    slot=_num(r.get("lineup_slot"), None)
    if slot is None: return False
    vals=[v.strip() for v in str(r.get("weak_slots","")).split(",") if v.strip()]
    return str(int(slot)) in vals

def csv_bytes(df):
    if df is None: df=pd.DataFrame()
    return df.to_csv(index=False).encode("utf-8")

def save_locked_results(results):
    try:
        serial={}
        for k,v in results.items():
            serial[k]=v.to_dict("records") if isinstance(v,pd.DataFrame) else v
        LOCKED_RESULTS_FILE.write_text(json.dumps(serial,indent=2,default=str))
    except Exception:
        pass

def load_locked_results():
    empty={"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"meta":{}}
    try:
        if not LOCKED_RESULTS_FILE.exists(): return empty
        raw=json.loads(LOCKED_RESULTS_FILE.read_text())
        out={k:pd.DataFrame(raw.get(k,[])) for k in ["owners","core","alt","chaos","survivors"]}
        out["meta"]=raw.get("meta",{})
        return out
    except Exception:
        return empty

def fetch_live_public_slate(date_iso=None):
    if date_iso is None: date_iso=datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    rows=[]; meta={"source":"MLB Stats API","date":date_iso,"games":0,"rows":0}
    try:
        url=f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_iso}&hydrate=probablePitcher,team"
        with urllib.request.urlopen(url, timeout=8) as resp: data=json.loads(resp.read().decode("utf-8"))
        for d in data.get("dates",[]):
            for g in d.get("games",[]):
                teams=g.get("teams",{})
                away=teams.get("away",{}).get("team",{}).get("name","")
                home=teams.get("home",{}).get("team",{}).get("name","")
                away_p=teams.get("away",{}).get("probablePitcher",{}).get("fullName","")
                home_p=teams.get("home",{}).get("probablePitcher",{}).get("fullName","")
                game=f"{away} vs {home}"
                rows.append({"game":game,"team":away,"opponent":home,"pitcher":home_p,"player":"","source":"PUBLIC_SLATE"})
                rows.append({"game":game,"team":home,"opponent":away,"pitcher":away_p,"player":"","source":"PUBLIC_SLATE"})
    except Exception as e:
        meta["error"]=str(e); return pd.DataFrame(), meta
    df=normalize_game_frame(pd.DataFrame(rows)); meta["games"]=actual_game_count(df); meta["rows"]=len(df)
    return df,meta

def fetch_live_public_hitter_pool(date_iso=None, max_hitters_per_team=9):
    slate,meta=fetch_live_public_slate(date_iso)
    # Live pool cannot fully score without metrics; create rows for display only, not fake picks
    return slate, meta

def merge_public_context(feed_df, public_df):
    feed=normalize_game_frame(feed_df)
    if public_df is None or public_df.empty: return feed
    pub=normalize_game_frame(public_df)
    try:
        ctx=pub.drop_duplicates("team")[[c for c in ["team","opponent","pitcher","game","game_key"] if c in pub.columns]]
        out=feed.merge(ctx,on="team",how="left",suffixes=("","_pub"))
        for c in ["opponent","pitcher","game","game_key"]:
            pc=c+"_pub"
            if pc in out.columns:
                out[c]=out[c].where(out[c].astype(str).str.strip().ne(""),out[pc])
                out=out.drop(columns=[pc])
        return normalize_game_frame(out)
    except Exception:
        return feed

def recalc_adaptive_weights_from_history():
    return {"status":"ready","pull":1.0,"launch":1.0,"damage":1.0,"conversion":1.0}

def _score(row):
    pull=_num(row.get("pull_pct")); sweet=_num(row.get("sweet_spot_pct")); barrel=_num(row.get("barrel_pct"))
    hh=_num(row.get("hard_hit_pct")); dmg=_num(row.get("dmg")); hrpa=_num(row.get("hr_pa")); hpi=_num(row.get("hpi")); pe=_num(row.get("pitch_edge"))
    score=0
    score += min(18,max(0,(pull-25)*.75))
    score += min(12,max(0,(sweet-18)*.6))
    score += min(10,max(0,(barrel-5)*1.25))
    score += min(8,max(0,(hh-34)*.45))
    score += 13 if dmg>=2.2 else 10 if dmg>=1.8 else 7 if dmg>=1.5 else 4 if dmg>=1.2 else 0
    score += 10 if hrpa>=4 else 8 if hrpa>=3 else 6 if hrpa>=2 else 3 if hrpa>=1.3 else 0
    score += 10 if hpi>=50 else 8 if hpi>=42 else 5 if hpi>=35 else 2 if hpi>=28 else 0
    if _present(row,"pitch_edge"): score += 12 if pe>=15 else 9 if pe>=8 else 5 if pe>=0 else -12
    else: score += 1
    if _slot_match(row): score += 6
    elif _present(row,"lineup_slot") and 1 <= _num(row.get("lineup_slot")) <= 5: score += 4
    if pull < 25: score -= 10
    if dmg < 1 and hrpa < 1 and hpi < 25: score -= 8
    return round(max(0,min(92,score)),1)

def _eval(row):
    pull=_num(row.get("pull_pct")); sweet=_num(row.get("sweet_spot_pct")); barrel=_num(row.get("barrel_pct"))
    hh=_num(row.get("hard_hit_pct")); dmg=_num(row.get("dmg")); hrpa=_num(row.get("hr_pa")); hpi=_num(row.get("hpi")); pe=_num(row.get("pitch_edge"))
    metric_count=sum(_present(row,k) for k in ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi","pitch_edge"])
    legal=is_player_name_safe(row.get("player")) and metric_count>=1
    env=bool(str(row.get("team","")).strip()) or bool(str(row.get("pitcher","")).strip()) or bool(str(row.get("game","")).strip())
    pull_air=pull>=38 or (pull>=30 and sweet>=27) or (pull>=28 and dmg>=1.5)
    launch=sweet>=24 or barrel>=9 or hh>=42 or dmg>=1.65
    damage=dmg>=1.45 or hrpa>=2 or hpi>=38
    conv=hpi>=34 or hrpa>=1.5 or dmg>=1.45
    pitch_ok=(pe>=0) if _present(row,"pitch_edge") else True
    anti=not bool(row.get("chalk_trap"))
    finisher=pull_air and damage and conv
    gates=[
        ("0 Environment",env,False),("1 Pool legality",legal,True),("2 Side lock",env,False),
        ("3 Pitcher lane",pitch_ok or damage,False),("4 Pitch type",pitch_ok,False),
        ("5 Pull-air",pull_air,False),("6 Launch",launch,False),("7 Damage",damage,False),
        ("8 Conversion",conv,False),("9 Opportunity",_present(row,"lineup_slot") or _slot_match(row),False),
        ("10 Hard-hit",hh>=38 or barrel>=8 or dmg>=1.5,False),("10.5 Adjacent",_slot_match(row),False),
        ("11 WHO/Chaos",bool(row.get("hr_alert")) and damage,False),("12 Game script",True,False),
        ("13 Recap DNA",sum([pull>=38,dmg>=1.45,hpi>=34,hrpa>=1.5,sweet>=24,barrel>=9,hh>=42])>=3,False),
        ("14 Anti-chalk",anti,True),("15 Bullpen",True,False),("16 Finisher",finisher,False),
        ("17 Owner isolation",True,True),("18 Final audit",True,True),("19 Model confirm",finisher or conv,False)
    ]
    hard=[n for n,p,h in gates if h and not p]
    soft=[n for n,p,h in gates if not h and not p]
    grade=round(sum(1 for _,p,_ in gates if p)/len(gates)*100,1)
    return gates,hard,soft,grade

def _path(gates,hard,soft):
    parts=[f"{n}: {'PASS' if p else ('KILL' if h else 'WEAK')}" for n,p,h in gates]
    if hard: parts.append("HARD FAILS: "+", ".join(hard))
    if soft: parts.append("SOFT FLAGS: "+", ".join(soft))
    return " | ".join(parts)

def _run_game(gdf):
    rows=[]
    for _,r in gdf.iterrows():
        row=r.to_dict()
        gates,hard,soft,grade=_eval(row)
        score=_score(row)
        clean=(not hard) and score>=50
        if clean:
            role="Primary"; arch="Elite Converter" if score>=78 else "Primary HR Owner"
        elif is_player_name_safe(row.get("player")):
            role="Recovery"; arch="Audit Survivor / Data-Recovery Profile"; score=max(40,min(68,score))
        else:
            role="NO PLAY"; arch="No Clean Owner"; score=min(39,score)
        row.update({"score":score,"official_core_role":role,"archetype":arch,"gate_grade":grade,
                    "hard_fails":", ".join(hard),"soft_fails":", ".join(soft),"gate_path":_path(gates,hard,soft)})
        rows.append(row)
    out=pd.DataFrame(rows)
    if out.empty: return out
    return out.sort_values(["official_core_role","score"], ascending=[True,False]).sort_values("score",ascending=False).head(1)

def build_tickets_from_owners(owners,survivors=None):
    if owners is None or owners.empty: return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    df=owners.sort_values("score",ascending=False).reset_index(drop=True)
    core=df.head(3).copy()
    used=set(core["player"]) if "player" in core else set()
    alt=df[~df["player"].isin(used)].head(3).copy() if "player" in df else pd.DataFrame()
    used.update(alt["player"] if not alt.empty and "player" in alt else [])
    chaos=df[(~df["player"].isin(used)) & (df["archetype"].astype(str).str.contains("Recovery|WHO|Chaos",case=False,na=False))].head(3).copy() if "player" in df else pd.DataFrame()
    if chaos.empty and "player" in df: chaos=df[~df["player"].isin(used)].head(3).copy()
    return core,alt,chaos

def run_true_blender(df,*args,**kwargs):
    df=normalize_game_frame(df)
    meta={"input_rows":0 if df is None else len(df),"games":actual_game_count(df),"owners_locked":0,"survivor_rows":0,"no_play_games":0,"message":"","engine_version":"v97_PDF_FEED_FIXED"}
    if df is None or df.empty:
        meta["message"]="No usable player rows parsed. Check PDF/text extraction."
        res={"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"meta":meta}; save_locked_results(res); return res
    survivors=[]; owners=[]; group_col="game_key" if "game_key" in df.columns else "game"
    for game,gdf in df.groupby(group_col,dropna=False):
        top=_run_game(gdf)
        if top is None or top.empty: continue
        top=top.assign(game_owner=game)
        survivors.append(top)
        if top.iloc[0].get("official_core_role")!="NO PLAY": owners.append(top.iloc[0].to_dict())
    survivors=pd.concat(survivors,ignore_index=True) if survivors else pd.DataFrame()
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    meta["survivor_rows"]=len(survivors); meta["owners_locked"]=len(owners)
    if owners.empty and not survivors.empty:
        # visible recovery fallback so user can inspect actual parse, never blank
        owners=survivors.head(1).copy()
        owners["official_core_role"]="Recovery"; owners["archetype"]="Visible Recovery / Parse Audit"
        meta["owners_locked"]=len(owners)
    core,alt,chaos=build_tickets_from_owners(owners,survivors)
    meta["message"]=f"Blender complete: {len(owners)} owners from {meta['games']} games. Rows={meta['input_rows']}."
    res={"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"meta":meta}
    save_locked_results(res); return res

def run_recap_check(results=None):
    return {"status":"ready","message":"Recap hook ready."}
