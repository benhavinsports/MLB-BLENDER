import re, io, time
import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

CANON = [
    "source","page","game","team","opponent","pitcher","player","bats","lineup_slot",
    "pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa",
    "pitch_type","pitch_edge","hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon",
    "weak_slots","odds","public_pct","weather_score","bullpen_dmg","confirmed_lineup",
    "dob","jersey","result_hr","raw_block","notes"
]

TEAM_NAMES = [
"Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox",
"Cincinnati Reds","Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals",
"Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets",
"New York Yankees","Athletics","Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres","San Francisco Giants",
"Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers","Toronto Blue Jays","Washington Nationals"
]

TEAM_ABBR = {
"ARI":"Arizona Diamondbacks","ATL":"Atlanta Braves","BAL":"Baltimore Orioles","BOS":"Boston Red Sox",
"CHC":"Chicago Cubs","CHW":"Chicago White Sox","CIN":"Cincinnati Reds","CLE":"Cleveland Guardians",
"COL":"Colorado Rockies","DET":"Detroit Tigers","HOU":"Houston Astros","KC":"Kansas City Royals","KCR":"Kansas City Royals",
"LAA":"Los Angeles Angels","LAD":"Los Angeles Dodgers","MIA":"Miami Marlins","MIL":"Milwaukee Brewers",
"MIN":"Minnesota Twins","NYM":"New York Mets","NYY":"New York Yankees","OAK":"Athletics","ATH":"Athletics",
"PHI":"Philadelphia Phillies","PIT":"Pittsburgh Pirates","SD":"San Diego Padres","SF":"San Francisco Giants",
"SEA":"Seattle Mariners","STL":"St. Louis Cardinals","TB":"Tampa Bay Rays","TBR":"Tampa Bay Rays",
"TEX":"Texas Rangers","TOR":"Toronto Blue Jays","WSH":"Washington Nationals","WAS":"Washington Nationals"
}

TEAM_COLORS = {
"red sox":"#BD3039","yankees":"#0C2340","mets":"#FF5910","dodgers":"#005A9C","padres":"#2F241D",
"phillies":"#E81828","reds":"#C6011F","mariners":"#005C5C","braves":"#CE1141","twins":"#002B5C",
"astros":"#EB6E1F","blue jays":"#134A8E","orioles":"#DF4601","rays":"#092C5C","royals":"#004687",
"cubs":"#0E3386","cardinals":"#C41E3A","rockies":"#33006F","angels":"#BA0021","giants":"#FD5A1E",
"diamondbacks":"#A71930","tigers":"#0C2340","guardians":"#E50022","athletics":"#003831",
"white sox":"#27251F","pirates":"#FDB827","brewers":"#FFC52F","marlins":"#00A3E0",
"nationals":"#AB0003","rangers":"#003278"
}

BAD_PLAYER_TOKENS = {
"VS","PROJECTED","PITCHER","TEAM","LINEUP","SLOT","BATS","HAND","ALERT","DMG","HPI","PULL","SWEET",
"STAR","TOOL","DATA","PAGE","HOME","AWAY","NONE","SUMMARY","DETAILS","WEAK","COND","LINE"
}

ALIASES = {
"player":["player","name","batter","hitter","player_name","batter_name"],
"team":["team","tm","bat_team","batter_team"],
"pitcher":["pitcher","opp_pitcher","opposing_pitcher","starter","sp"],
"game":["game","matchup","game_key"],
"lineup_slot":["lineup_slot","slot","batting_order","order","lineup","bo"],
"pull_pct":["pull_pct","pull%","pull","pull_percent"],
"barrel_pct":["barrel_pct","barrel%","barrel"],
"sweet_spot_pct":["sweet_spot_pct","sweet%","sweet_spot","line","launch","launch_pct"],
"hard_hit_pct":["hard_hit_pct","hardhit%","hard_hit","hh","hh%"],
"hpi":["hpi","hr_power_index","power","ult","adj"],
"dmg":["dmg","damage","dmg_score"],
"hr_pa":["hr_pa","hr/pa","hr_pa_pct","hr%","hr_rate"],
"pitch_edge":["pitch_edge","edge","pitch_matchup","pitch_type_edge"],
"pitch_type":["pitch_type","pitch","primary_pitch"],
"weak_slots":["weak_slots","weak_slot","pitcher_weak_slots"],
"odds":["odds","hr_odds","anytime_odds"],
"public_pct":["public_pct","public","ownership","owned"],
"weather_score":["weather_score","weather","park","env"],
"bullpen_dmg":["bullpen_dmg","bullpen","bp_dmg"],
"hr_alert":["hr_alert","alert"],
"cond_up":["cond_up","condition_up","cond"],
"weak_slot_tag":["weak_slot_tag","weakslot"],
"laser":["laser"],"rakes":["rakes"],"platoon":["platoon"],
"confirmed_lineup":["confirmed_lineup","confirmed","starting"],"notes":["notes","note","raw"]
}

def team_color(team):
    t=str(team).lower()
    for key,val in TEAM_COLORS.items():
        if key in t:
            return val
    return "#d9ff2f"

def normalize_team(text):
    raw=str(text).strip()
    u=re.sub(r"[^A-Z .'-]","",raw.upper()).strip()
    if not u:
        return ""
    if u in TEAM_ABBR:
        return TEAM_ABBR[u]
    if u in {"ATHLETICS","A'S","AS"}:
        return "Athletics"
    for name in TEAM_NAMES:
        if name.upper()==u or name.upper() in u:
            return name
    return ""

def is_team_token(text):
    u=str(text).strip().upper()
    return bool(u in TEAM_ABBR or normalize_team(u))

def nfloat(x):
    if x is None or pd.isna(x):
        return None
    if isinstance(x,(int,float)):
        return float(x)
    s=str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    if s in ["","-","—","None","nan","NaN"]:
        return None
    try:
        return float(s)
    except Exception:
        return None

def nbool(x):
    if isinstance(x,bool):
        return x
    return str(x).strip().lower() in {"true","1","yes","y","alert","hot","x","confirmed","✅","up"}

def is_player_name(text):
    s=str(text).strip()
    u=s.upper()
    if len(s)<3 or re.search(r"\d",s):
        return False
    if u in BAD_PLAYER_TOKENS:
        return False
    if is_team_token(s):
        return False
    parts=s.split()
    if not (1 <= len(parts) <= 4):
        return False
    return all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts)

def map_structured_columns(df):
    df=df.copy()
    norm={c:re.sub(r"[^a-z0-9]+","_",str(c).lower()).strip("_") for c in df.columns}
    rename={}
    for canon, aliases in ALIASES.items():
        opts=[re.sub(r"[^a-z0-9]+","_",a.lower()).strip("_") for a in aliases]
        for c,n in norm.items():
            if n in opts:
                rename[c]=canon
    df=df.rename(columns=rename)
    for c in CANON:
        if c not in df.columns:
            df[c]=None
    return df

def normalize_df(df, source="structured"):
    if df is None or df.empty:
        return pd.DataFrame(columns=CANON)
    df=map_structured_columns(df)

    if "player" not in df or df["player"].isna().all():
        for c in df.columns:
            vals=df[c].dropna().astype(str).head(100)
            if sum(is_player_name(v) for v in vals) >= 4:
                df["player"]=df[c]
                break

    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","odds","public_pct","weather_score","bullpen_dmg","jersey"]:
        df[c]=df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","confirmed_lineup","result_hr"]:
        df[c]=df[c].apply(nbool)
    for c in ["team","pitcher","game","player"]:
        df[c]=df[c].fillna("").astype(str).str.strip()

    df["source"]=source
    df["team"]=df["team"].apply(lambda x: normalize_team(x) or x)
    df=df[df["player"].apply(is_player_name)].copy()

    metric_cols=["pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]
    df=df[df[metric_cols].notna().any(axis=1)].copy()

    df.loc[df["game"].str.strip()=="","game"]=df["team"]+" vs "+df["pitcher"]
    df.loc[df["game"].str.strip()==" vs ","game"]="Unknown Game"
    for c in CANON:
        if c not in df.columns:
            df[c]=None
    return df[CANON]

def pdf_pages(file_bytes):
    if fitz is None:
        return []
    doc=fitz.open(stream=file_bytes,filetype="pdf")
    out=[]
    for idx,page in enumerate(doc,start=1):
        text=page.get_text("text")
        lines=[x.strip() for x in text.splitlines() if x.strip()]
        out.append({"page":idx,"text":text,"lines":lines})
    return out

def clean_pitcher(text):
    s=str(text).strip()
    s=re.sub(r"^[vV][sS]\.?\s+","",s)
    s=re.sub(r"\s+[~|].*$","",s)
    s=re.sub(r"\s+\d+-\d+K.*$","",s)
    s=re.sub(r"\s+[LR]$","",s)
    return re.sub(r"\s{2,}"," ",s).strip()

def maybe_pitcher(text):
    s=clean_pitcher(text)
    if not s or len(s)>55:
        return ""
    bad=["PROJECTED","DMG","HPI","HR/PA","LINEUP SLOT","WEAK","ALERT","PULL","COND","BATS"]
    if any(x in s.upper() for x in bad):
        return ""
    parts=s.split()
    if 1 <= len(parts) <= 4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts):
        return s
    return ""

def detect_page_header(lines):
    for i,line in enumerate(lines[:45]):
        joined=" ".join(lines[max(0,i-8):min(len(lines),i+14)])
        if "PROJECTED" not in joined.upper():
            continue
        team=""
        pitcher=""
        for b in range(0,12):
            j=i-b
            if j>=0:
                team=normalize_team(lines[j])
                if team:
                    break
        m=re.search(r"\bv(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)",joined,re.I)
        if m:
            pitcher=clean_pitcher(m.group(1))
        if not pitcher:
            for f in range(1,16):
                j=i+f
                if j<len(lines):
                    cand=maybe_pitcher(lines[j])
                    if cand and not normalize_team(cand):
                        pitcher=cand
                        break
        if team and pitcher:
            return team,pitcher
    return "",""

def metric_block(block):
    def grab(patterns):
        for pat in patterns:
            m=re.search(pat,block,re.I)
            if m:
                return nfloat(m.group(1))
        return None
    slot=None
    sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
    if sm:
        slot=int(sm.group(1))
    pull=grab([r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?"])
    if pull is None:
        vals=[]
        for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block):
            v=nfloat(pv)
            if v is not None and 5 <= abs(v) <= 75:
                vals.append(v)
        if vals:
            pull=vals[0]
    sweet=grab([r"(?:LINE|Sweet|Sweet Spot)\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?"])
    hrpa=grab([r"([0-9]+(?:\.\d+)?)%\s+HR/PA"])
    dmg=grab([r"([0-9]+(?:\.\d+)?)\s+DMG"])
    hpi=grab([r"HPI\s*\+?\s*(\d+)"])
    if hpi is None:
        pluses=[int(x) for x in re.findall(r"\+\s*(\d+)",block) if 10 <= int(x) <= 90]
        if pluses:
            hpi=float(pluses[-1])
    pitch_edge=None
    pitch_type=None
    pairs=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
    pairs=[(nfloat(a),b) for a,b in pairs if b.lower() not in {"hr","line","cond","pull","park"}]
    pairs=[p for p in pairs if p[0] is not None]
    if pairs:
        pitch_edge,pitch_type=pairs[-1]
    return {
        "lineup_slot":slot,"pull_pct":pull,"sweet_spot_pct":sweet,"hr_pa":hrpa,
        "dmg":dmg,"hpi":hpi,"pitch_edge":pitch_edge,"pitch_type":pitch_type,
        "hr_alert":"ALERT" in block or "HR ALERT" in block,
        "cond_up":"COND ↑" in block or "COND UP" in block.upper(),
        "weak_slot_tag":"Weak Slot" in block,
        "laser":"Laser" in block,
        "rakes":"Rakes" in block,
        "platoon":"Platoon" in block,
    }

def player_blocks(lines):
    out=[]
    i=0
    while i < len(lines):
        line=lines[i].strip()
        player=""
        start=i
        if re.fullmatch(r"\d+",line) and i+1<len(lines) and is_player_name(lines[i+1]):
            player=lines[i+1].strip()
            start=i+1
        if not player:
            m=re.match(r"^(\d+)\s+([A-Z][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?",line)
            if m and is_player_name(m.group(2)):
                player=m.group(2).strip()
                start=i
        if not player and is_player_name(line):
            nxt=" ".join(lines[i:i+12])
            prev=lines[i-1].strip() if i>0 else ""
            if re.fullmatch(r"\d+",prev) or ("HR/PA" in nxt and ("DMG" in nxt or "ALERT" in nxt or "★★★★★" in nxt)):
                player=line
                start=i
        if player:
            block=" ".join(lines[start:start+42])
            out.append({"player":player,"raw_block":block})
            i += 8
            continue
        i += 1
    return out

def parse_pdf(file_bytes):
    pages=pdf_pages(file_bytes)
    rows=[]
    raw_text="\n".join(p["text"] for p in pages)
    debug=[]
    active_team=""
    active_pitcher=""
    for page in pages:
        pno=page["page"]
        lines=page["lines"]
        team,pitcher=detect_page_header(lines)
        if team and pitcher:
            active_team,active_pitcher=team,pitcher
        debug.append({"page":pno,"team":active_team,"pitcher":active_pitcher,"line_count":len(lines)})
        for blk in player_blocks(lines):
            row={c:None for c in CANON}
            metrics=metric_block(blk["raw_block"])
            row.update({
                "source":"pdf","page":pno,
                "game":f"{active_team} vs {active_pitcher}" if active_team and active_pitcher else "Unknown Game",
                "team":active_team,"opponent":"","pitcher":active_pitcher,
                "player":blk["player"],"raw_block":blk["raw_block"],"notes":f"page={pno}"
            })
            row.update(metrics)
            rows.append(row)
    df=normalize_df(pd.DataFrame(rows),source="pdf")
    return df,raw_text,debug

def read_csv(file_bytes):
    raw=pd.read_csv(io.BytesIO(file_bytes))
    return normalize_df(raw,source="csv"),"",[]

def read_xlsx(file_bytes):
    raw=pd.read_excel(io.BytesIO(file_bytes))
    return normalize_df(raw,source="xlsx"),"",[]

def read_file(name,file_bytes):
    n=name.lower()
    if n.endswith(".pdf"):
        return parse_pdf(file_bytes)
    if n.endswith(".csv"):
        return read_csv(file_bytes)
    return read_xlsx(file_bytes)


def split_feed_quality(df):
    """Return clean rows that can run + quarantined rows that are missing game/team/pitcher."""
    if df is None or df.empty:
        return pd.DataFrame(), pd.DataFrame()
    team=df["team"].fillna("").astype(str).str.strip()
    pitcher=df["pitcher"].fillna("").astype(str).str.strip()
    game=df["game"].fillna("").astype(str).str.strip()
    metric_cols=["pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]
    has_metric=df[metric_cols].notna().any(axis=1)
    good=(team!="") & (pitcher!="") & (~game.str.contains("Unknown Game",na=False)) & has_metric
    return df[good].copy(), df[~good].copy()

def audit_feed(df):
    if df is None or df.empty:
        return False, ["No legal hitter rows parsed."], pd.DataFrame(), df

    clean, bad = split_feed_quality(df)
    issues=[]

    if clean.empty:
        return False, ["No runnable clean rows after quarantine."], clean, bad

    team=clean["team"].fillna("").astype(str).str.strip()
    pitcher=clean["pitcher"].fillna("").astype(str).str.strip()
    game=clean["game"].fillna("").astype(str).str.strip()

    if len(df) >= 80 and game.nunique() < 6:
        issues.append("Full-slate game separation failed.")
    if len(df) >= 80 and team.nunique() < 6:
        issues.append("Full-slate team separation failed.")
    if len(df) >= 80 and pitcher.nunique() < 6:
        issues.append("Full-slate pitcher separation failed.")

    if len(bad):
        issues.append(f"Quarantined {len(bad)} incomplete rows; running on {len(clean)} clean rows.")

    hard_fail = any("failed" in x.lower() for x in issues)
    return not hard_fail, issues, clean, bad

def role_type(r):
    if bool(r.get("weak_slot_tag")) or bool(r.get("laser")) or bool(r.get("rakes")):
        return "Transfer"
    if (r.get("dmg") or 0) >= 1.7 and (r.get("hr_pa") or 0) >= 4:
        return "WHO"
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
    return max(0,min(100,score))

def run_gates(gdf):
    alive=gdf.copy()
    logs=[]
    def cut(name,mask):
        nonlocal alive,logs
        before=len(alive)
        dead=alive.loc[~mask,"player"].tolist()
        alive=alive[mask].copy()
        logs.append({"Gate":name,"Before":before,"Cut":len(dead),"After":len(alive),"Cut names":", ".join(dead[:16]),"Alive after":", ".join(alive.player.tolist()[:16])})
    logs.append({"Gate":"0","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16])})
    cut("1 Pull-Air", alive.pull_pct.isna() | (alive.pull_pct>=20))
    if len(alive)>1: cut("2 Pitch Edge", alive.pitch_edge.isna() | (alive.pitch_edge>=0))
    if len(alive)>1: cut("3 Slot/Zone", alive.weak_slot_tag | alive.lineup_slot.notna() | alive.pitch_edge.notna())
    if len(alive)>1: cut("4 Sweet/Launch", alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=24))
    if len(alive)>1: cut("5 HR/PA", alive.hr_pa.isna() | (alive.hr_pa>=2) | alive.hr_alert)
    if len(alive)>1: cut("6 DMG", alive.dmg.isna() | (alive.dmg>=.5) | alive.hr_alert)
    if len(alive)>1: cut("7 HPI", alive.hpi.isna() | (alive.hpi>=18) | alive.hr_alert)
    for gate in ["8 Recency","9 Context","10 Public/Book","10.5 Transfer","11 Bullpen","12 Script","13 Numerology","14 Chaos","15 Finisher","16 Ownership","17 Audit","18 Lock"]:
        if len(alive)>1:
            logs.append({"Gate":gate,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16])})
    return alive,pd.DataFrame(logs)

def build_core_alt(owners):
    if owners.empty:
        return pd.DataFrame(),pd.DataFrame()
    owners=owners.sort_values("score",ascending=False).reset_index(drop=True)
    core=[]
    used=set()
    for role in ["Primary","Transfer","WHO"]:
        for _,r in owners[owners.role==role].iterrows():
            if r["game"] not in used:
                core.append(r.to_dict())
                used.add(r["game"])
                break
    for _,r in owners.iterrows():
        if len(core)>=3:
            break
        if r["game"] not in used:
            core.append(r.to_dict())
            used.add(r["game"])
    core_df=pd.DataFrame(core[:3]) if core else pd.DataFrame()
    alt=[]
    alt_used=set(used)
    for _,r in owners.iterrows():
        if r["player"] not in (core_df["player"].tolist() if not core_df.empty else []) and r["game"] not in alt_used:
            alt.append(r.to_dict())
            alt_used.add(r["game"])
        if len(alt)>=3:
            break
    return core_df,pd.DataFrame(alt[:3])

def run_machine(df):
    owners=[]
    logs=[]
    survivors=[]
    for game,gdf in df.groupby("game",dropna=False):
        alive,lg=run_gates(gdf)
        if not lg.empty:
            lg.insert(0,"Game",game)
            logs.append(lg)
        if not alive.empty:
            alive=alive.copy()
            alive["role"]=alive.apply(role_type,axis=1)
            alive["score"]=alive.apply(score_row,axis=1)
            alive=alive.sort_values("score",ascending=False)
            owners.append(alive.iloc[0].to_dict())
            survivors.append(alive)
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    logs=pd.concat(logs,ignore_index=True) if logs else pd.DataFrame()
    survivors=pd.concat(survivors,ignore_index=True) if survivors else pd.DataFrame()
    core,alt=build_core_alt(owners)
    return owners,core,alt,logs,survivors

def css():
    st.markdown("""<style>@import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Rajdhani:wght@700&display=swap');:root{--cream:#f5ead8;--acid:#d9ff2f;--green:#00ff73;--orange:#ff9900;--red:#ff355c;--line:rgba(245,234,216,.15)}.stApp{background:radial-gradient(circle at 15% 5%,rgba(217,255,47,.16),transparent 24%),linear-gradient(180deg,#050505,#090908);color:var(--cream)}.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(rgba(245,234,216,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(245,234,216,.04) 1px,transparent 1px);background-size:34px 34px}.block-container{max-width:1180px;padding:1rem 1rem 4rem}.hero,.panel,.card,.ticket{border:1px solid var(--line);border-radius:28px;background:linear-gradient(160deg,rgba(23,22,21,.96),rgba(5,5,5,.98));padding:18px;margin:12px 0}.title,.card-name,.score{font-family:'Black Ops One'}.title{font-size:clamp(42px,7vw,82px);line-height:.86}.hot{color:var(--acid)}.chip,.role,.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:8px 11px;margin:5px;font-family:Rajdhani}.stButton>button{min-height:60px;width:100%;border:0;border-radius:18px;font-family:'Black Ops One';font-size:20px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange));color:#050505}.blade-stage{position:relative;height:300px;border-radius:24px;border:1px solid var(--line);overflow:hidden;background:#050505}.blade{position:absolute;left:50%;top:50%;width:230px;height:230px;margin:-115px;border-radius:50%;background:conic-gradient(transparent 0deg,var(--acid) 38deg,transparent 78deg,var(--green) 155deg,transparent 200deg,var(--orange) 265deg,transparent 320deg);animation:spin .95s linear infinite}.center{position:absolute;left:50%;top:50%;width:112px;height:112px;margin:-56px;border-radius:50%;background:#050505;border:2px solid rgba(245,234,216,.25);display:grid;place-items:center;font-family:'Black Ops One';color:var(--acid)}@keyframes spin{to{transform:rotate(360deg)}}.card{position:relative;overflow:hidden}.card:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}.card-name{font-size:32px;margin:12px 0}.meta{font-family:Rajdhani;color:#aaa}.score{font-size:44px}.bar{height:12px;background:rgba(245,234,216,.09);border-radius:999px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.stat{border:1px solid rgba(245,234,216,.10);border-radius:14px;padding:9px}.stat b{font-size:20px}.stat span{display:block;font-family:Rajdhani;color:#aaa}.bad{border:1px solid rgba(255,53,92,.35);background:rgba(255,53,92,.10);border-radius:16px;padding:12px}.good{border:1px solid rgba(0,255,115,.28);background:rgba(0,255,115,.08);border-radius:16px;padding:12px}</style>""", unsafe_allow_html=True)

def hero():
    st.markdown("""<div class="hero"><div class="title">THE <span class="hot">BLENDER</span><br/>LOCK ROOM</div><span class="chip">FEEDER FIRST</span><span class="chip">0 → 18</span><span class="chip">10.5 IN SEQUENCE</span><span class="chip">ONE OWNER PER GAME</span></div>""", unsafe_allow_html=True)

def wheel(status="READY"):
    st.markdown(f"""<div class="panel"><h3 style="font-family:Black Ops One">BLENDER MACHINE</h3><div class="blade-stage"><div class="blade"></div><div class="center">{str(status)[:16]}</div></div></div>""", unsafe_allow_html=True)

def safe_table(df,height=360):
    if df is None or df.empty:
        st.info("No data.")
        return
    show=df.copy()
    for c in show.columns:
        show[c]=show[c].apply(lambda x: str(x) if isinstance(x,(list,tuple,dict,set)) else x)
        if show[c].dtype=="object":
            show[c]=show[c].astype(str)
    st.dataframe(show,use_container_width=True,height=height)

def fmt(x):
    if x is None or pd.isna(x): return "—"
    return f"{x:.1f}" if isinstance(x,float) else str(x)

def pct(x):
    try: return max(2,min(100,int(float(x or 0))))
    except Exception: return 0

def player_card(r):
    p=pct(r.get("score"))
    color=team_color(r.get("team",""))
    st.markdown(f"""<div class="card" style="border-color:{color}99"><span class="role">{r.get('role','Primary')}</span><div class="card-name">{r.get('player','')}</div><div class="meta"><span style="color:{color};font-weight:900">{r.get('team','')}</span> vs {r.get('pitcher','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small style="display:block;font-family:Rajdhani;color:#aaa;font-size:13px">TRUE BLEND SCORE</small></div><div class="bar"><div class="fill" style="width:{p}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><span class="badge">CONF {p}%</span><span class="badge">NO REVIVAL</span></div>""", unsafe_allow_html=True)

def csv_bytes(df):
    if df is None or df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")

st.set_page_config(page_title="THE BLENDER",page_icon="🔥",layout="wide",initial_sidebar_state="collapsed")
css()
hero()

tabs=st.tabs(["Launch","Feeder Lab","Machine","Game Board","Tickets","Kill Feed","Exports"])

with tabs[0]:
    wheel("READY")
    uploaded=st.file_uploader("Manual feed",type=["pdf","csv","xlsx"])
    if uploaded:
        try:
            df,raw_text,debug=read_file(uploaded.name,uploaded.read())
        except Exception as e:
            st.error(f"Feeder crash: {e}")
            df,raw_text,debug=pd.DataFrame(),"",[]
        st.session_state.update({"df":df,"raw_text":raw_text,"debug":debug})
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Rows",len(df))
        c2.metric("Games",df.game.nunique() if not df.empty else 0)
        c3.metric("Teams",df.team.replace("",pd.NA).dropna().nunique() if not df.empty else 0)
        c4.metric("Pitchers",df.pitcher.replace("",pd.NA).dropna().nunique() if not df.empty else 0)
        ok,issues,clean_df,bad_df=audit_feed(df)
        if ok:
            st.markdown("<div class='good'>FEEDER LOCKED — BAD ROWS QUARANTINED</div>",unsafe_allow_html=True)
        else:
            st.markdown("<div class='bad'>FEEDER NOT LOCKED — RESULTS BLOCKED</div>",unsafe_allow_html=True)
            st.write(issues)
            if "bad_df" in locals() and bad_df is not None and not bad_df.empty:
                with st.expander("Quarantined Rows"):
                    safe_table(bad_df, 240)
        if st.button("ENGAGE BLENDER"):
            if not ok:
                st.error("No fake locks. Fix feed first in Feeder Lab.")
            else:
                msg=st.empty()
                progress=st.progress(0)
                for i,step in enumerate(["FEED VERIFIED","GATES LOADED","10.5 CHECKED","OWNERS LOCKED","TICKETS BUILT"]):
                    msg.info(step)
                    progress.progress((i+1)/5)
                    time.sleep(.12)
                owners,core,alt,logs,survivors=run_machine(clean_df)
                st.session_state.update({"owners":owners,"core":core,"alt":alt,"logs":logs,"survivors":survivors})
                st.success("MACHINE COMPLETE")

with tabs[1]:
    st.subheader("Feeder Lab")
    if "df" in st.session_state:
        safe_table(st.session_state["df"],420)
        st.download_button("Download feeder rows CSV",csv_bytes(st.session_state["df"]),"feeder_rows.csv","text/csv")
        if st.session_state.get("debug"):
            with st.expander("Page Section Debug"):
                safe_table(pd.DataFrame(st.session_state["debug"]),320)
        with st.expander("Raw text sample"):
            st.text("\n".join(str(st.session_state.get("raw_text","")).splitlines()[:250]) if st.session_state.get("raw_text") else "No raw text.")
    else:
        st.info("Upload a feed first.")

with tabs[2]:
    wheel("LOCKED" if "owners" in st.session_state else "READY")

with tabs[3]:
    if "owners" in st.session_state and not st.session_state["owners"].empty:
        for _,r in st.session_state["owners"].iterrows():
            player_card(r)
    else:
        st.info("Run a locked feed first.")

with tabs[4]:
    if "core" in st.session_state and not st.session_state["core"].empty:
        st.markdown("<div class='ticket'><h2>CORE 3</h2>",unsafe_allow_html=True)
        for _,r in st.session_state["core"].iterrows():
            st.markdown(f"<p><b>{r['player']}</b> — {r.get('team','')} vs {r.get('pitcher','')} — {int(r.get('score',0))}%</p>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
        if not st.session_state["alt"].empty:
            st.markdown("<div class='ticket'><h2>ALT 3</h2>",unsafe_allow_html=True)
            for _,r in st.session_state["alt"].iterrows():
                st.markdown(f"<p><b>{r['player']}</b> — {r.get('team','')} vs {r.get('pitcher','')} — {int(r.get('score',0))}%</p>",unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)
    else:
        st.info("Run a locked feed first.")

with tabs[5]:
    if "logs" in st.session_state:
        safe_table(st.session_state["logs"],520)
    else:
        st.info("Run a locked feed first.")

with tabs[6]:
    if "df" in st.session_state:
        st.download_button("Download Full Feed CSV",csv_bytes(st.session_state["df"]),"full_feed.csv","text/csv")
    if "owners" in st.session_state:
        st.download_button("Download Owners CSV",csv_bytes(st.session_state["owners"]),"owners.csv","text/csv")
        st.download_button("Download Core CSV",csv_bytes(st.session_state["core"]),"core.csv","text/csv")
        st.download_button("Download Alt CSV",csv_bytes(st.session_state["alt"]),"alt.csv","text/csv")
