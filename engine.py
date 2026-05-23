
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
    meta={"input_rows":0 if df is None else len(df),"games":actual_game_count(df),"owners_locked":0,"survivor_rows":0,"no_play_games":0,"message":"","engine_version":"v109_TODAY_TEST_READY"}
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
        # v100: do not promote 0-score malformed/team rows into Core tickets.
        viable = survivors[(survivors.get("score", 0).astype(float) >= 25) & (~survivors.get("player", "").astype(str).str.lower().isin([t.lower() for t in TEAM_ABBR.keys()]))].copy() if "score" in survivors.columns else pd.DataFrame()
        if not viable.empty:
            owners=viable.head(1).copy()
            owners["official_core_role"]="Recovery"; owners["archetype"]="Visible Recovery / Parse Audit"
            meta["owners_locked"]=len(owners)
    core,alt,chaos=build_tickets_from_owners(owners,survivors)
    proxy_note = " · PUBLIC PROXY MODE" if ("public_proxy" in df.columns and df["public_proxy"].astype(str).str.lower().eq("true").any()) else ""
    meta["message"]=f"Blender complete: {len(owners)} owners from {meta['games']} games. Rows={meta['input_rows']}{proxy_note}."
    res={"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"meta":meta}
    save_locked_results(res); return res

def run_recap_check(results=None):
    return {"status":"ready","message":"Recap hook ready."}



# -------------------- v105 PUBLIC BLENDER UNBLOCKED --------------------
# Public mode now creates actual hitter rows instead of only 30/32 team/pitcher rows.
# It uses MLB Stats API roster + season hitting stats when available.
# These are PUBLIC PROXY metrics, not StarTool-grade metrics.

import urllib.request

TEAM_IDS_V105 = {
    "Arizona Diamondbacks":109, "Atlanta Braves":144, "Baltimore Orioles":110, "Boston Red Sox":111,
    "Chicago Cubs":112, "Chicago White Sox":145, "Cincinnati Reds":113, "Cleveland Guardians":114,
    "Colorado Rockies":115, "Detroit Tigers":116, "Houston Astros":117, "Kansas City Royals":118,
    "Los Angeles Angels":108, "Los Angeles Dodgers":119, "Miami Marlins":146, "Milwaukee Brewers":158,
    "Minnesota Twins":142, "New York Mets":121, "New York Yankees":147, "Athletics":133,
    "Oakland Athletics":133, "Philadelphia Phillies":143, "Pittsburgh Pirates":134, "San Diego Padres":135,
    "San Francisco Giants":137, "Seattle Mariners":136, "St. Louis Cardinals":138, "Tampa Bay Rays":139,
    "Texas Rangers":140, "Toronto Blue Jays":141, "Washington Nationals":120,
}

def _http_json_v105(url, timeout=8):
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))

def _safe_float_v105(x, default=0.0):
    try:
        if x in [None, "", "-", ".---"]:
            return default
        return float(str(x).replace("%",""))
    except Exception:
        return default

def _fetch_team_hitters_v105(team_name, team_id, limit=9):
    """
    Public fallback hitter builder:
    - active roster hitters
    - season hitting stats
    - ranks by HR, SLG, OPS, AB volume
    """
    rows = []
    try:
        roster_url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=active"
        roster = _http_json_v105(roster_url)
        people = []
        for item in roster.get("roster", []):
            pos_type = item.get("position", {}).get("type", "")
            pos_abbr = item.get("position", {}).get("abbreviation", "")
            if pos_type == "Pitcher" or pos_abbr == "P":
                continue
            p = item.get("person", {})
            if p.get("id") and p.get("fullName"):
                people.append((p["id"], p["fullName"], pos_abbr))

        for pid, name, pos in people[:22]:
            try:
                stats_url = f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&group=hitting"
                stats = _http_json_v105(stats_url)
                splits = stats.get("stats", [{}])[0].get("splits", [])
                st = splits[0].get("stat", {}) if splits else {}
                ab = _safe_float_v105(st.get("atBats"))
                pa = _safe_float_v105(st.get("plateAppearances"), ab)
                hr = _safe_float_v105(st.get("homeRuns"))
                ops = _safe_float_v105(st.get("ops"))
                slg = _safe_float_v105(st.get("slg"))
                avg = _safe_float_v105(st.get("avg"))
                doubles = _safe_float_v105(st.get("doubles"))
                triples = _safe_float_v105(st.get("triples"))
                # Skip empty/no-bat players
                if pa < 25 and hr == 0:
                    continue

                hr_pa = round((hr / max(pa, 1)) * 100, 2)
                hpi = round(min(80, max(18, hr * 2.2 + slg * 55 + ops * 18)), 1)
                dmg = round(min(3.2, max(0.7, slg * 2.4 + hr_pa * 0.10)), 3)

                # Public proxy only. Pull/sweet/barrel/hard are estimated from HR/SLG/extra-base output.
                pull = round(min(48, max(24, 28 + hr_pa * 2.2 + hr * 0.15)), 1)
                sweet = round(min(36, max(18, 20 + slg * 16 + hr_pa * 0.65)), 1)
                barrel = round(min(17, max(4, 4.5 + hr_pa * 1.25 + slg * 4)), 1)
                hard = round(min(58, max(30, 34 + slg * 22 + hr_pa * 1.4)), 1)

                rows.append({
                    "player": name,
                    "team": team_name,
                    "position": pos,
                    "public_proxy": True,
                    "source_layer": "mlb_stats_public_proxy",
                    "parse_note": "public_proxy_metrics_from_mlb_stats",
                    "lineup_slot": None,
                    "pull_pct": pull,
                    "sweet_spot_pct": sweet,
                    "barrel_pct": barrel,
                    "hard_hit_pct": hard,
                    "dmg": dmg,
                    "hr_pa": hr_pa,
                    "hpi": hpi,
                    "pitch_edge": None,
                    "hr_alert": hr_pa >= 3.0 or hr >= 10,
                    "season_hr": hr,
                    "season_pa": pa,
                    "season_ops": ops,
                    "season_slg": slg,
                    "season_avg": avg,
                    "season_xbh": doubles + triples + hr,
                })
            except Exception:
                continue
    except Exception:
        return []
    rows = sorted(rows, key=lambda r: (r.get("season_hr",0), r.get("dmg",0), r.get("hpi",0), r.get("season_pa",0)), reverse=True)
    return rows[:limit]

def fetch_live_public_slate(date_iso=None):
    if date_iso is None:
        date_iso = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    rows = []
    meta = {"source":"MLB Stats API", "date":date_iso, "games":0, "rows":0, "mode":"slate_context"}
    try:
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_iso}&hydrate=probablePitcher,team"
        data = _http_json_v105(url)
        for d in data.get("dates", []):
            for g in d.get("games", []):
                teams = g.get("teams", {})
                away = teams.get("away", {}).get("team", {}).get("name", "")
                home = teams.get("home", {}).get("team", {}).get("name", "")
                away_id = teams.get("away", {}).get("team", {}).get("id")
                home_id = teams.get("home", {}).get("team", {}).get("id")
                away_p = teams.get("away", {}).get("probablePitcher", {}).get("fullName", "")
                home_p = teams.get("home", {}).get("probablePitcher", {}).get("fullName", "")
                game = f"{away} vs {home}"
                rows.append({"game":game, "team":away, "team_id":away_id, "opponent":home, "pitcher":home_p, "source":"PUBLIC_SLATE"})
                rows.append({"game":game, "team":home, "team_id":home_id, "opponent":away, "pitcher":away_p, "source":"PUBLIC_SLATE"})
        df = normalize_game_frame(pd.DataFrame(rows))
        meta["games"] = actual_game_count(df)
        meta["rows"] = len(df)
        return df, meta
    except Exception as e:
        meta["error"] = str(e)
        return pd.DataFrame(), meta

def fetch_live_public_hitter_pool(date_iso=None, max_hitters_per_team=9):
    slate, meta = fetch_live_public_slate(date_iso)
    out = []
    if slate is None or slate.empty:
        meta["mode"] = "public_proxy_failed_no_slate"
        return pd.DataFrame(), meta

    # Build hitters for BOTH teams in each game, then attach opponent pitcher context.
    for _, s in slate.iterrows():
        team = str(s.get("team",""))
        team_id = s.get("team_id", None)
        if not team_id or str(team_id) == "nan":
            team_id = TEAM_IDS_V105.get(team)
        if not team_id:
            continue
        hitters = _fetch_team_hitters_v105(team, int(team_id), limit=max_hitters_per_team)
        for h in hitters:
            h["game"] = s.get("game","")
            h["game_key"] = s.get("game_key","")
            h["opponent"] = s.get("opponent","")
            h["pitcher"] = s.get("pitcher","")
            h["team_id"] = team_id
            out.append(h)

    df = normalize_game_frame(pd.DataFrame(out))
    meta["mode"] = "public_proxy_hitter_pool"
    meta["rows"] = len(df)
    meta["metric_rows"] = len(df)
    meta["games"] = actual_game_count(df)
    meta["warning"] = "Public mode uses MLB season-stat proxy metrics. StarTool/PDF upload remains strongest mode."
    return df, meta



# -------------------- v106 TICKET STRUCTURE LOCK --------------------
# Official tickets are no longer filled by Recovery/soft-flag players.
# CORE 3 identity is locked:
#   1 Primary, 1 Adjacent/Transfer, 1 WHO/Chaos
# A player must PASS that bucket's gate to enter that bucket.

def _gate_text_v106(row):
    return str(row.get("gate_path", "")) + " " + str(row.get("soft_fails", "")) + " " + str(row.get("hard_fails", "")) + " " + str(row.get("archetype", "")) + " " + str(row.get("official_core_role", ""))

def _is_recovery_v106(row):
    return str(row.get("official_core_role","")).lower() == "recovery" or "recovery" in str(row.get("archetype","")).lower() or "audit survivor" in str(row.get("archetype","")).lower()

def _clean_ticket_candidate_v106(row):
    if _is_recovery_v106(row):
        return False
    if str(row.get("hard_fails","")).strip():
        return False
    try:
        if float(row.get("score", 0) or 0) < 50:
            return False
    except Exception:
        return False
    return True

def _primary_pass_v106(row):
    if not _clean_ticket_candidate_v106(row):
        return False
    path = str(row.get("gate_path","")).lower()
    soft = str(row.get("soft_fails","")).lower()
    # Primary must be a real finisher/pull-air candidate, not soft in those exact gates.
    if "5 pull-air" in soft or "5 pull-air: weak" in path:
        return False
    if "16 finisher" in soft or "16 finisher: weak" in path:
        return False
    return True

def _adjacent_pass_v106(row):
    if not _clean_ticket_candidate_v106(row):
        return False
    path = str(row.get("gate_path","")).lower()
    soft = str(row.get("soft_fails","")).lower()
    # Must actually pass 10.5 Adjacent, not weak/soft.
    if "10.5 adjacent: pass" not in path:
        return False
    if "10.5 adjacent" in soft or "10.5 adjacent: weak" in path:
        return False
    return True

def _who_pass_v106(row):
    if not _clean_ticket_candidate_v106(row):
        return False
    path = str(row.get("gate_path","")).lower()
    soft = str(row.get("soft_fails","")).lower()
    # Must actually pass WHO/Chaos, not weak/soft.
    if "11 who/chaos: pass" not in path:
        return False
    if "11 who/chaos" in soft or "11 who/chaos: weak" in path:
        return False
    return True

def _assign_ticket_role_v106(row):
    if _who_pass_v106(row):
        return "WHO"
    if _adjacent_pass_v106(row):
        return "Adjacent"
    if _primary_pass_v106(row):
        return "Primary"
    return "Audit"

def _pick_one_v106(df, mask_func, used_players):
    if df is None or df.empty:
        return pd.DataFrame()
    pool = df[df.apply(mask_func, axis=1)].copy()
    if "player" in pool.columns:
        pool = pool[~pool["player"].astype(str).isin(used_players)]
    if pool.empty:
        return pd.DataFrame()
    return pool.sort_values("score", ascending=False).head(1).copy()

def build_tickets_from_owners(owners, survivors=None):
    """
    v106 strict ticket construction:
    CORE 3 = exactly one Primary + one Adjacent/Transfer + one WHO/Chaos if available.
    ALT 3 = next clean pass candidates, no Recovery.
    CHAOS 3 = WHO/Chaos PASS only. Soft-WHO players cannot enter Chaos.
    Recovery/Audit rows stay on Game Board only.
    """
    if owners is None or owners.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = owners.copy()
    if "score" not in df.columns:
        df["score"] = 0
    df["ticket_bucket"] = df.apply(_assign_ticket_role_v106, axis=1)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)

    used = set()
    core_parts = []

    primary = _pick_one_v106(df, _primary_pass_v106, used)
    if not primary.empty:
        primary["official_core_role"] = "Primary"
        primary["archetype"] = primary["archetype"].replace("", "Primary HR Owner")
        core_parts.append(primary)
        used.update(primary["player"].astype(str).tolist())

    adjacent = _pick_one_v106(df, _adjacent_pass_v106, used)
    if not adjacent.empty:
        adjacent["official_core_role"] = "Adjacent"
        adjacent["archetype"] = "Adjacent / Transfer Owner"
        core_parts.append(adjacent)
        used.update(adjacent["player"].astype(str).tolist())

    who = _pick_one_v106(df, _who_pass_v106, used)
    if not who.empty:
        who["official_core_role"] = "WHO"
        who["archetype"] = "WHO / Chaos Owner"
        core_parts.append(who)
        used.update(who["player"].astype(str).tolist())

    core = pd.concat(core_parts, ignore_index=True) if core_parts else pd.DataFrame()

    # ALT = clean ticket candidates only, never Recovery/Audit.
    alt_pool = df[df.apply(_clean_ticket_candidate_v106, axis=1)].copy()
    if "player" in alt_pool.columns:
        alt_pool = alt_pool[~alt_pool["player"].astype(str).isin(used)]
    alt = alt_pool.sort_values("score", ascending=False).head(3).copy()
    if not alt.empty:
        alt["official_core_role"] = "ALT"
    used.update(alt["player"].astype(str).tolist() if not alt.empty and "player" in alt else [])

    # CHAOS = WHO pass only, no soft WHO, no Recovery.
    chaos_pool = df[df.apply(_who_pass_v106, axis=1)].copy()
    # Keep chaos ticket as its own WHO pass list; do not include soft placeholders.
    chaos = chaos_pool.sort_values("score", ascending=False).head(3).copy()
    if not chaos.empty:
        chaos["official_core_role"] = "WHO"
        chaos["archetype"] = "WHO / Chaos Owner"

    return core.reset_index(drop=True), alt.reset_index(drop=True), chaos.reset_index(drop=True)



# -------------------- v109 FINAL TEST-RUN TICKET LOCK --------------------
def _v109_path(row):
    return str(row.get("gate_path","")).lower()

def _v109_soft(row):
    return str(row.get("soft_fails","")).lower()

def _v109_hard(row):
    return str(row.get("hard_fails","")).strip()

def _v109_score(row):
    try:
        return float(row.get("score",0) or 0)
    except Exception:
        return 0.0

def _v109_is_recovery(row):
    txt = (str(row.get("official_core_role","")) + " " + str(row.get("archetype",""))).lower()
    return "recovery" in txt or "audit" in txt or "data-recovery" in txt

def _v109_clean(row):
    return (not _v109_is_recovery(row)) and (not _v109_hard(row)) and _v109_score(row) >= 50

def _v109_gate_pass(row, gate):
    return f"{gate.lower()}: pass" in _v109_path(row)

def _v109_gate_soft(row, gate):
    return gate.lower() in _v109_soft(row) or f"{gate.lower()}: weak" in _v109_path(row)

def _v109_primary_ok(row):
    if not _v109_clean(row): return False
    if _v109_gate_soft(row, "5 Pull-air"): return False
    if _v109_gate_soft(row, "16 Finisher"): return False
    return True

def _v109_adjacent_ok(row):
    if not _v109_clean(row): return False
    return _v109_gate_pass(row, "10.5 Adjacent") and not _v109_gate_soft(row, "10.5 Adjacent")

def _v109_who_ok(row):
    if not _v109_clean(row): return False
    return _v109_gate_pass(row, "11 WHO/Chaos") and not _v109_gate_soft(row, "11 WHO/Chaos")

def _v109_pick(df, func, used):
    pool = df[df.apply(func, axis=1)].copy()
    if "player" in pool.columns:
        pool = pool[~pool["player"].astype(str).isin(used)]
    if pool.empty:
        return pd.DataFrame()
    return pool.sort_values("score", ascending=False).head(1).copy()

def build_tickets_from_owners(owners, survivors=None):
    if owners is None or owners.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = owners.copy()
    if "score" not in df.columns:
        df["score"] = 0
    df = df.sort_values("score", ascending=False).reset_index(drop=True)

    used = set()
    core_parts = []

    primary = _v109_pick(df, _v109_primary_ok, used)
    if not primary.empty:
        primary["official_core_role"] = "Primary"
        primary["archetype"] = "Primary HR Owner"
        core_parts.append(primary)
        used.update(primary["player"].astype(str).tolist())

    adjacent = _v109_pick(df, _v109_adjacent_ok, used)
    if not adjacent.empty:
        adjacent["official_core_role"] = "Adjacent"
        adjacent["archetype"] = "Adjacent / Transfer Owner"
        core_parts.append(adjacent)
        used.update(adjacent["player"].astype(str).tolist())

    who = _v109_pick(df, _v109_who_ok, used)
    if not who.empty:
        who["official_core_role"] = "WHO"
        who["archetype"] = "WHO / Chaos Owner"
        core_parts.append(who)
        used.update(who["player"].astype(str).tolist())

    core = pd.concat(core_parts, ignore_index=True) if core_parts else pd.DataFrame()

    alt_pool = df[df.apply(_v109_clean, axis=1)].copy()
    if "player" in alt_pool.columns:
        alt_pool = alt_pool[~alt_pool["player"].astype(str).isin(used)]
    alt = alt_pool.sort_values("score", ascending=False).head(3).copy()
    if not alt.empty:
        alt["official_core_role"] = "ALT"
        alt["archetype"] = alt["archetype"].fillna("Clean Blender Alternate")
    used.update(alt["player"].astype(str).tolist() if not alt.empty and "player" in alt.columns else [])

    chaos_pool = df[df.apply(_v109_who_ok, axis=1)].copy()
    if "player" in chaos_pool.columns and not core.empty and "player" in core.columns:
        chaos_pool = chaos_pool[~chaos_pool["player"].astype(str).isin(core["player"].astype(str).tolist())]
    chaos = chaos_pool.sort_values("score", ascending=False).head(3).copy()
    if not chaos.empty:
        chaos["official_core_role"] = "WHO"
        chaos["archetype"] = "WHO / Chaos Owner"

    return core.reset_index(drop=True), alt.reset_index(drop=True), chaos.reset_index(drop=True)



# -------------------- v110 GAME COUNT / GAME KEY DEDUPE FIX --------------------
# Fixes inflated game counts from PDF/public context merges.

def _v110_clean_name(x):
    return re.sub(r"\s+", " ", str(x or "").strip())

def _v110_pitcher_key(x):
    s = _v110_clean_name(x).lower()
    s = re.sub(r"^vs\s+", "", s)
    s = re.sub(r"[^a-z0-9\s\.\'-]", "", s)
    return re.sub(r"\s+", " ", s).strip()

def _v110_team_key(x):
    s = _v110_clean_name(x).lower()
    s = s.replace("oakland athletics", "athletics")
    return re.sub(r"[^a-z0-9\s]", "", s).strip()

def canonical_game_key(game_or_team, opponent=None, pitcher=None):
    team = _v110_team_key(game_or_team)
    pit = _v110_pitcher_key(pitcher)
    if pit and team:
        return f"{team}__vs_pitcher__{pit}"
    game = _v110_clean_name(game_or_team)
    low = game.lower()
    low = re.sub(r"\s+vs\.?\s+", " vs ", low)
    low = re.sub(r"\s+@\s+", " vs ", low)
    low = re.sub(r"[^a-z0-9\s]", "", low)
    parts = [p.strip() for p in low.split(" vs ") if p.strip()]
    if len(parts) >= 2:
        return "__vs__".join(sorted(parts[:2]))
    if opponent:
        return "__vs__".join(sorted([team, _v110_team_key(opponent)]))
    return low.strip()

def normalize_game_frame(df):
    if df is None or df.empty:
        return pd.DataFrame()
    out = df.copy()
    for c in ["team","opponent","pitcher","game","player"]:
        if c not in out.columns:
            out[c] = ""
    out["team"] = out["team"].astype(str).map(_v110_clean_name)
    out["opponent"] = out["opponent"].astype(str).map(_v110_clean_name)
    out["pitcher"] = out["pitcher"].astype(str).map(_v110_clean_name)
    out["game"] = out["game"].astype(str).map(_v110_clean_name)

    # Canonical key must come from team+pitcher for StarTool-style team attack rows.
    out["game_key"] = out.apply(lambda r: canonical_game_key(r.get("team",""), r.get("opponent",""), r.get("pitcher","")), axis=1)

    # Dedupe repeated extraction/merge copies but keep different hitters in same game.
    subset = [c for c in ["game_key","player","team","pitcher"] if c in out.columns]
    if subset:
        if "_metric_count" in out.columns:
            out = out.sort_values("_metric_count", ascending=False)
        elif "score" in out.columns:
            out = out.sort_values("score", ascending=False)
        out = out.drop_duplicates(subset=subset, keep="first")
    return out.reset_index(drop=True)

def actual_game_count(df):
    if df is None or df.empty:
        return 0
    work = normalize_game_frame(df)
    # If raw PUBLIC_SLATE context has home/away team rows, count unique matchup strings when available.
    if "source" in work.columns and work["source"].astype(str).str.contains("PUBLIC_SLATE", case=False, na=False).any():
        if "game" in work.columns:
            games = work["game"].dropna().astype(str).map(lambda x: canonical_game_key(x)).replace("", pd.NA).dropna().nunique()
            if games:
                return int(games)
    if "game_key" in work.columns:
        return int(work["game_key"].replace("", pd.NA).dropna().nunique())
    return 0

def _v110_dedupe_results(res):
    if not isinstance(res, dict):
        return res
    for k in ["owners","core","alt","chaos","survivors"]:
        df = res.get(k)
        if df is not None and hasattr(df, "empty") and not df.empty:
            df = normalize_game_frame(df)
            if k in ["owners"]:
                df = df.sort_values("score", ascending=False).drop_duplicates(subset=["game_key"], keep="first")
            res[k] = df.reset_index(drop=True)
    if "meta" in res and isinstance(res["meta"], dict):
        base_df = res.get("survivors")
        own_df = res.get("owners")
        ref = base_df if base_df is not None and hasattr(base_df, "empty") and not base_df.empty else own_df
        res["meta"]["games"] = actual_game_count(ref)
        res["meta"]["owners_locked"] = 0 if own_df is None or not hasattr(own_df, "empty") or own_df.empty else len(own_df)
        res["meta"]["survivor_rows"] = 0 if base_df is None or not hasattr(base_df, "empty") or base_df.empty else len(base_df)
    return res

try:
    _run_true_blender_pre_v110 = run_true_blender
    def run_true_blender(df, *args, **kwargs):
        fixed = normalize_game_frame(df)
        res = _run_true_blender_pre_v110(fixed, *args, **kwargs)
        res = _v110_dedupe_results(res)
        if isinstance(res, dict) and "meta" in res:
            res["meta"]["engine_version"] = "v110_GAME_COUNT_DEDUPE_FIX"
            res["meta"]["input_rows"] = len(fixed)
            res["meta"]["message"] = f"Blender complete: {res['meta'].get('owners_locked',0)} owners from {res['meta'].get('games',0)} games. Rows={len(fixed)}."
        return res
except NameError:
    pass

try:
    _fetch_live_public_hitter_pool_pre_v110 = fetch_live_public_hitter_pool
    def fetch_live_public_hitter_pool(date_iso=None, max_hitters_per_team=9):
        df, meta = _fetch_live_public_hitter_pool_pre_v110(date_iso, max_hitters_per_team)
        df = normalize_game_frame(df)
        if meta is None:
            meta = {}
        meta["rows"] = len(df)
        meta["games"] = actual_game_count(df)
        meta["mode"] = meta.get("mode", "public_proxy_hitter_pool") + "_v110_deduped"
        return df, meta
except NameError:
    pass

try:
    _fetch_live_public_slate_pre_v110 = fetch_live_public_slate
    def fetch_live_public_slate(date_iso=None):
        df, meta = _fetch_live_public_slate_pre_v110(date_iso)
        df = normalize_game_frame(df)
        if meta is None:
            meta = {}
        meta["rows"] = len(df)
        meta["games"] = actual_game_count(df)
        meta["mode"] = meta.get("mode", "slate_context") + "_v110_deduped"
        return df, meta
except NameError:
    pass
