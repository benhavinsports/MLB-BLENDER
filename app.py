import re, io, time, math, random
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
"ARI":"Arizona Diamondbacks","ATL":"Atlanta Braves","BAL":"Baltimore Orioles","BOS":"Boston Red Sox","CHC":"Chicago Cubs",
"CHW":"Chicago White Sox","CIN":"Cincinnati Reds","CLE":"Cleveland Guardians","COL":"Colorado Rockies","DET":"Detroit Tigers",
"HOU":"Houston Astros","KC":"Kansas City Royals","KCR":"Kansas City Royals","LAA":"Los Angeles Angels","LAD":"Los Angeles Dodgers",
"MIA":"Miami Marlins","MIL":"Milwaukee Brewers","MIN":"Minnesota Twins","NYM":"New York Mets","NYY":"New York Yankees",
"OAK":"Athletics","ATH":"Athletics","PHI":"Philadelphia Phillies","PIT":"Pittsburgh Pirates","SD":"San Diego Padres",
"SF":"San Francisco Giants","SEA":"Seattle Mariners","STL":"St. Louis Cardinals","TB":"Tampa Bay Rays","TBR":"Tampa Bay Rays",
"TEX":"Texas Rangers","TOR":"Toronto Blue Jays","WSH":"Washington Nationals","WAS":"Washington Nationals"
}
TEAM_COLORS = {
"red sox":"#BD3039","yankees":"#0C2340","mets":"#FF5910","dodgers":"#005A9C","padres":"#2F241D","phillies":"#E81828",
"reds":"#C6011F","mariners":"#005C5C","braves":"#CE1141","twins":"#002B5C","astros":"#EB6E1F","blue jays":"#134A8E",
"orioles":"#DF4601","rays":"#092C5C","royals":"#004687","cubs":"#0E3386","cardinals":"#C41E3A","rockies":"#33006F",
"angels":"#BA0021","giants":"#FD5A1E","diamondbacks":"#A71930","tigers":"#0C2340","guardians":"#E50022","athletics":"#003831",
"white sox":"#27251F","pirates":"#FDB827","brewers":"#FFC52F","marlins":"#00A3E0","nationals":"#AB0003","rangers":"#003278"
}
BAD_PLAYER_TOKENS = set("VS PROJECTED PITCHER TEAM LINEUP SLOT BATS HAND ALERT DMG HPI PULL SWEET STAR TOOL DATA PAGE HOME AWAY NONE SUMMARY DETAILS WEAK COND LINE".split())
ALIASES = {
"player":["player","name","batter","hitter","player_name","batter_name"],"team":["team","tm","bat_team","batter_team"],
"pitcher":["pitcher","opp_pitcher","opposing_pitcher","starter","sp"],"game":["game","matchup","game_key"],
"lineup_slot":["lineup_slot","slot","batting_order","order","lineup","bo"],"pull_pct":["pull_pct","pull%","pull","pull_percent"],
"barrel_pct":["barrel_pct","barrel%","barrel"],"sweet_spot_pct":["sweet_spot_pct","sweet%","sweet_spot","line","launch","launch_pct"],
"hard_hit_pct":["hard_hit_pct","hardhit%","hard_hit","hh","hh%"],"hpi":["hpi","hr_power_index","power","ult","adj"],
"dmg":["dmg","damage","dmg_score"],"hr_pa":["hr_pa","hr/pa","hr_pa_pct","hr%","hr_rate"],"pitch_edge":["pitch_edge","edge","pitch_matchup","pitch_type_edge"],
"pitch_type":["pitch_type","pitch","primary_pitch"],"weak_slots":["weak_slots","weak_slot","pitcher_weak_slots"],"odds":["odds","hr_odds","anytime_odds"],
"public_pct":["public_pct","public","ownership","owned"],"weather_score":["weather_score","weather","park","env"],"bullpen_dmg":["bullpen_dmg","bullpen","bp_dmg"],
"hr_alert":["hr_alert","alert"],"cond_up":["cond_up","condition_up","cond"],"weak_slot_tag":["weak_slot_tag","weakslot"],"laser":["laser"],"rakes":["rakes"],"platoon":["platoon"],
"confirmed_lineup":["confirmed_lineup","confirmed","starting"],"notes":["notes","note","raw"]
}

def css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Rajdhani:wght@700&display=swap');
:root{--cream:#f5ead8;--acid:#d9ff2f;--green:#00ff73;--orange:#ff9900;--red:#ff355c;--line:rgba(245,234,216,.16)}
.stApp{background:radial-gradient(circle at 14% 7%,rgba(217,255,47,.18),transparent 24%),radial-gradient(circle at 90% 30%,rgba(255,153,0,.10),transparent 24%),linear-gradient(180deg,#030303,#090908,#030303);color:var(--cream)}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(rgba(245,234,216,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(245,234,216,.04) 1px,transparent 1px);background-size:34px 34px}
.block-container{max-width:1180px;padding:1rem 1rem 4rem}
.hero,.machine,.card,.ticket,.board{border:1px solid var(--line);border-radius:30px;background:linear-gradient(155deg,rgba(23,22,21,.97),rgba(5,5,5,.98));padding:18px;margin:12px 0;box-shadow:0 18px 50px rgba(0,0,0,.35)}
.title,.card-name,.score,.section-title{font-family:'Black Ops One'}
.title{font-size:clamp(46px,8vw,90px);line-height:.84}.hot{color:var(--acid)}
.chip,.role,.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:8px 11px;margin:5px;font-family:Rajdhani;background:rgba(245,234,216,.035)}
.stButton>button{min-height:72px;width:100%;border:0;border-radius:22px;font-family:'Black Ops One';font-size:24px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange));color:#050505}
div[data-baseweb="tab-list"]{gap:8px;background:rgba(16,16,15,.88);border:1px solid var(--line);border-radius:20px;padding:8px}
div[data-baseweb="tab"]{font-family:Rajdhani;font-size:18px}
div[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(90deg,var(--acid),var(--green))!important;color:#050505!important;border-radius:14px}
.blender-wrap{position:relative;height:470px;border-radius:34px;border:1px solid var(--line);background:radial-gradient(circle at center,rgba(217,255,47,.13),rgba(0,0,0,.97));overflow:hidden;margin-top:12px}
.blender-base{position:absolute;left:50%;bottom:28px;width:380px;height:72px;transform:translateX(-50%);border-radius:28px;background:linear-gradient(180deg,rgba(245,234,216,.12),rgba(0,0,0,.95));border:2px solid rgba(245,234,216,.16);box-shadow:0 15px 40px rgba(0,0,0,.5)}
.jar{position:absolute;left:50%;top:47%;width:350px;height:350px;transform:translate(-50%,-50%);border-radius:56px 56px 120px 120px;border:3px solid rgba(245,234,216,.18);background:linear-gradient(180deg,rgba(245,234,216,.08),rgba(0,0,0,.38));box-shadow:inset 0 0 65px rgba(217,255,47,.14),0 0 38px rgba(0,255,115,.08)}
.blade{position:absolute;left:50%;top:54%;width:270px;height:270px;margin:-135px;border-radius:50%;background:conic-gradient(transparent 0deg,var(--acid) 32deg,transparent 74deg,var(--green) 148deg,transparent 205deg,var(--orange) 268deg,transparent 320deg);animation:spin .62s linear infinite;filter:blur(.25px);z-index:2}
.blade:after{content:"";position:absolute;inset:56px;border-radius:50%;background:rgba(0,0,0,.72);border:1px solid rgba(245,234,216,.18)}
.center{position:absolute;left:50%;top:54%;width:118px;height:118px;margin:-59px;border-radius:50%;background:#050505;border:2px solid rgba(245,234,216,.32);display:grid;place-items:center;font-family:'Black Ops One';color:var(--acid);z-index:5;box-shadow:0 0 25px rgba(217,255,47,.18)}
.float{position:absolute;font-family:Rajdhani;background:rgba(245,234,216,.13);border:1px solid rgba(245,234,216,.22);border-radius:999px;padding:8px 12px;color:var(--cream);max-width:160px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;animation:dropmix 4s ease-in-out infinite;z-index:6}
.f1{top:82px;left:7%;animation-delay:.1s}.f2{top:88px;right:7%;animation-delay:.7s}.f3{bottom:128px;left:8%;animation-delay:1.1s}.f4{bottom:124px;right:8%;animation-delay:1.5s}.f5{top:34px;left:38%;animation-delay:2s}.f6{bottom:68px;left:36%;animation-delay:2.4s}
.feed-slot{position:absolute;left:50%;top:12px;transform:translateX(-50%);font-family:'Black Ops One';background:linear-gradient(90deg,var(--acid),var(--green));color:#050505;padding:13px 24px;border-radius:999px;z-index:8;box-shadow:0 0 30px rgba(217,255,47,.25)}
.output-slot{position:absolute;left:50%;bottom:0;transform:translateX(-50%);font-family:'Black Ops One';letter-spacing:1px;color:#ecffc1;background:rgba(5,5,5,.94);width:100%;text-align:center;padding:16px 10px;z-index:9}
.chute{position:absolute;left:50%;top:50px;width:90px;height:84px;transform:translateX(-50%);border-radius:0 0 34px 34px;border:2px solid rgba(245,234,216,.16);background:linear-gradient(180deg,rgba(217,255,47,.14),rgba(245,234,216,.04));z-index:1}
@keyframes dropmix{0%{transform:translateY(-44px) scale(.92);opacity:.30}35%{transform:translateY(88px) scale(1);opacity:.95}70%{transform:translateY(178px) scale(.78);opacity:.30}100%{transform:translateY(-44px) scale(.92);opacity:.30}}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes bob{50%{transform:translateY(-26px) scale(.92);opacity:.65}}
.card{position:relative;overflow:hidden}.card:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}
.card-name{font-size:34px;margin:12px 0}.meta{font-family:Rajdhani;color:#aaa}.score{font-size:48px}.bar{height:12px;background:rgba(245,234,216,.09);border-radius:999px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.stat{border:1px solid rgba(245,234,216,.10);border-radius:14px;padding:9px}.stat b{font-size:20px}.stat span{display:block;font-family:Rajdhani;color:#aaa}
.status{border:1px solid rgba(0,255,115,.25);background:rgba(0,255,115,.08);border-radius:16px;padding:12px;margin:12px 0}.warn{border:1px solid rgba(255,153,0,.30);background:rgba(255,153,0,.09);border-radius:16px;padding:12px;margin:12px 0}
.leg{display:flex;justify-content:space-between;border-bottom:1px solid rgba(245,234,216,.1);padding:12px 0}.odds{background:rgba(217,255,47,.10);border:1px solid rgba(217,255,47,.24);border-radius:10px;padding:6px 9px;color:#ecffc1}
</style>
""", unsafe_allow_html=True)

def team_color(team):
    t=str(team).lower()
    for key,val in TEAM_COLORS.items():
        if key in t: return val
    return "#d9ff2f"

def normalize_team(text):
    u=re.sub(r"[^A-Z .'-]","",str(text).upper()).strip()
    if not u: return ""
    if u in TEAM_ABBR: return TEAM_ABBR[u]
    if u in {"ATHLETICS","A'S","AS"}: return "Athletics"
    for name in TEAM_NAMES:
        if name.upper()==u or name.upper() in u: return name
    return ""

def is_team_token(text):
    u=str(text).strip().upper()
    return bool(u in TEAM_ABBR or normalize_team(u))

def nfloat(x):
    if x is None or pd.isna(x): return None
    if isinstance(x,(int,float)): return float(x)
    s=str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    if s in ["","-","—","None","nan","NaN"]: return None
    try: return float(s)
    except Exception: return None

def nbool(x):
    if isinstance(x,bool): return x
    return str(x).strip().lower() in {"true","1","yes","y","alert","hot","x","confirmed","✅","up"}

def is_player_name(text):
    s=str(text).strip(); u=s.upper()
    if len(s)<3 or re.search(r"\d",s): return False
    if u in BAD_PLAYER_TOKENS: return False
    if is_team_token(s): return False
    parts=s.split()
    if not (1 <= len(parts) <= 4): return False
    return all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts)

def normalize_df(df, source="structured"):
    if df is None or df.empty: return pd.DataFrame(columns=CANON)
    df=df.copy()
    norm={c:re.sub(r"[^a-z0-9]+","_",str(c).lower()).strip("_") for c in df.columns}
    ren={}
    for canon, aliases in ALIASES.items():
        opts=[re.sub(r"[^a-z0-9]+","_",a.lower()).strip("_") for a in aliases]
        for c,n in norm.items():
            if n in opts: ren[c]=canon
    df=df.rename(columns=ren)
    for c in CANON:
        if c not in df.columns: df[c]=None
    if df["player"].isna().all() or (df["player"].astype(str).str.strip()=="").all():
        for c in df.columns:
            vals=df[c].dropna().astype(str).head(200)
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
    # Quarantine non-metric rows from cards. Do not crash.
    df=df[df[metric_cols].notna().any(axis=1)].copy()
    df.loc[df["game"].str.strip()=="","game"]=df["team"]+" vs "+df["pitcher"]
    df.loc[df["game"].str.strip()==" vs ","game"]="Unknown Game"
    for c in CANON:
        if c not in df.columns: df[c]=None
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
    if not s or len(s)>55: return ""
    bad=["PROJECTED","DMG","HPI","HR/PA","LINEUP SLOT","WEAK","ALERT","PULL","COND","BATS"]
    if any(x in s.upper() for x in bad): return ""
    parts=s.split()
    if 1<=len(parts)<=4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts): return s
    return ""

def detect_header(lines):
    # text PDFs only. Image-only PDFs will not produce text without OCR.
    for i,line in enumerate(lines[:55]):
        joined=" ".join(lines[max(0,i-10):min(len(lines),i+16)])
        if "PROJECTED" not in joined.upper() and " VS " not in joined.upper():
            continue
        team=""
        pitcher=""
        for b in range(0,15):
            j=i-b
            if j>=0:
                team=normalize_team(lines[j])
                if team: break
        m=re.search(r"\bv(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)",joined,re.I)
        if m: pitcher=clean_pitcher(m.group(1))
        if not pitcher:
            for f in range(1,16):
                j=i+f
                if j<len(lines):
                    cand=maybe_pitcher(lines[j])
                    if cand and not normalize_team(cand):
                        pitcher=cand; break
        if team or pitcher:
            return team,pitcher
    return "",""

def metric_block(block):
    def grab(patterns):
        for pat in patterns:
            m=re.search(pat,block,re.I)
            if m: return nfloat(m.group(1))
        return None
    slot=None
    sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
    if sm: slot=int(sm.group(1))
    pull=grab([r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?"])
    if pull is None:
        vals=[]
        for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block):
            v=nfloat(pv)
            if v is not None and 5<=abs(v)<=75: vals.append(v)
        if vals: pull=vals[0]
    sweet=grab([r"(?:LINE|Sweet|Sweet Spot)\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?"])
    hrpa=grab([r"([0-9]+(?:\.\d+)?)%\s+HR/PA"])
    dmg=grab([r"([0-9]+(?:\.\d+)?)\s+DMG"])
    hpi=grab([r"HPI\s*\+?\s*(\d+)"])
    if hpi is None:
        pluses=[int(x) for x in re.findall(r"\+\s*(\d+)",block) if 10<=int(x)<=90]
        if pluses: hpi=float(pluses[-1])
    pitch_edge=None; pitch_type=None
    pairs=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
    pairs=[(nfloat(a),b) for a,b in pairs if b.lower() not in {"hr","line","cond","pull","park"}]
    pairs=[p for p in pairs if p[0] is not None]
    if pairs: pitch_edge,pitch_type=pairs[-1]
    return {"lineup_slot":slot,"pull_pct":pull,"sweet_spot_pct":sweet,"hr_pa":hrpa,"dmg":dmg,"hpi":hpi,"pitch_edge":pitch_edge,"pitch_type":pitch_type,
            "hr_alert":"ALERT" in block or "HR ALERT" in block,"cond_up":"COND ↑" in block or "COND UP" in block.upper(),
            "weak_slot_tag":"Weak Slot" in block,"laser":"Laser" in block,"rakes":"Rakes" in block,"platoon":"Platoon" in block}

def player_blocks(lines):
    out=[]; i=0
    while i<len(lines):
        line=lines[i].strip()
        player=""; start=i
        if re.fullmatch(r"\d+",line) and i+1<len(lines) and is_player_name(lines[i+1]):
            player=lines[i+1].strip(); start=i+1
        if not player:
            m=re.match(r"^(\d+)\s+([A-Z][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?",line)
            if m and is_player_name(m.group(2)):
                player=m.group(2).strip(); start=i
        if not player and is_player_name(line):
            nxt=" ".join(lines[i:i+12])
            prev=lines[i-1].strip() if i>0 else ""
            if re.fullmatch(r"\d+",prev) or ("HR/PA" in nxt and ("DMG" in nxt or "ALERT" in nxt or "★★★★★" in nxt)):
                player=line; start=i
        if player:
            out.append({"player":player,"raw_block":" ".join(lines[start:start+46])})
            i+=8; continue
        i+=1
    return out

def parse_pdf(file_bytes):
    pages=pdf_pages(file_bytes)
    rows=[]; raw="\n".join(p["text"] for p in pages)
    active_team=""; active_pitcher=""
    for page in pages:
        team,pitcher=detect_header(page["lines"])
        if team: active_team=team
        if pitcher: active_pitcher=pitcher
        for blk in player_blocks(page["lines"]):
            row={c:None for c in CANON}
            row.update({"source":"pdf","page":page["page"],"team":active_team,"pitcher":active_pitcher,
                        "game":f"{active_team} vs {active_pitcher}" if active_team and active_pitcher else "Unknown Game",
                        "player":blk["player"],"raw_block":blk["raw_block"],"notes":f"page={page['page']}"})
            row.update(metric_block(blk["raw_block"]))
            rows.append(row)
    df=normalize_df(pd.DataFrame(rows),source="pdf")
    return df, raw

def read_file(name, data):
    n=name.lower()
    if n.endswith(".pdf"):
        return parse_pdf(data)
    if n.endswith(".csv"):
        return normalize_df(pd.read_csv(io.BytesIO(data)),source="csv"),""
    return normalize_df(pd.read_excel(io.BytesIO(data)),source="xlsx"),""

def clean_for_run(df):
    if df is None or df.empty: return pd.DataFrame(), pd.DataFrame()
    team=df["team"].fillna("").astype(str).str.strip()
    pitcher=df["pitcher"].fillna("").astype(str).str.strip()
    game=df["game"].fillna("").astype(str).str.strip()
    metric_cols=["pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]
    has_metric=df[metric_cols].notna().any(axis=1)
    # Run on rows with metrics and real player. If game/team/pitcher is missing, create a holding game instead of blocking.
    run=df[has_metric].copy()
    bad=df[~has_metric].copy()
    run.loc[run["team"].fillna("").astype(str).str.strip()=="","team"]="Unknown Team"
    run.loc[run["pitcher"].fillna("").astype(str).str.strip()=="","pitcher"]="Unknown Pitcher"
    run.loc[run["game"].fillna("").astype(str).str.contains("Unknown Game",na=False),"game"]=run["team"]+" vs "+run["pitcher"]
    return run,bad

def role_type(r):
    if bool(r.get("weak_slot_tag")) or bool(r.get("laser")) or bool(r.get("rakes")): return "Transfer"
    if (r.get("dmg") or 0)>=1.7 and (r.get("hr_pa") or 0)>=4: return "Chaos"
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
    return round(max(0,min(100,score)),1)

def run_game(gdf):
    alive=gdf.copy()
    def cut(mask):
        nonlocal alive
        if len(alive)>1:
            alive=alive[mask].copy()
    cut(alive.pull_pct.isna() | (alive.pull_pct>=20))
    cut(alive.pitch_edge.isna() | (alive.pitch_edge>=0))
    cut(alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=24))
    cut(alive.hr_pa.isna() | (alive.hr_pa>=2) | alive.hr_alert)
    cut(alive.dmg.isna() | (alive.dmg>=.5) | alive.hr_alert)
    cut(alive.hpi.isna() | (alive.hpi>=18) | alive.hr_alert)
    if alive.empty: alive=gdf.copy()
    alive["role"]=alive.apply(role_type,axis=1)
    alive["score"]=alive.apply(score_row,axis=1)
    return alive.sort_values("score",ascending=False)

def run_blender(df):
    run,bad=clean_for_run(df)
    owners=[]; survivors=[]
    for game,gdf in run.groupby("game",dropna=False):
        alive=run_game(gdf)
        survivors.append(alive.assign(game_owner=game))
        if not alive.empty:
            owners.append(alive.iloc[0].to_dict())
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    survivors=pd.concat(survivors,ignore_index=True) if survivors else pd.DataFrame()
    if owners.empty:
        return owners,pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),survivors,bad
    owners=owners.sort_values("score",ascending=False).reset_index(drop=True)
    core=[]; used=set()
    for role in ["Primary","Transfer","Chaos"]:
        for _,r in owners[owners.role==role].iterrows():
            if r.game not in used:
                core.append(r.to_dict()); used.add(r.game); break
    for _,r in owners.iterrows():
        if len(core)>=3: break
        if r.game not in used:
            core.append(r.to_dict()); used.add(r.game)
    core=pd.DataFrame(core[:3]) if core else pd.DataFrame()
    alt=[]; alt_used=set(used)
    for _,r in owners.iterrows():
        if r.player not in (core.player.tolist() if not core.empty else []) and r.game not in alt_used:
            alt.append(r.to_dict()); alt_used.add(r.game)
        if len(alt)>=3: break
    alt=pd.DataFrame(alt[:3]) if alt else pd.DataFrame()
    chaos=owners[owners.role=="Chaos"].head(3).copy()
    if chaos.empty:
        chaos=owners.sort_values("dmg",ascending=False).head(3).copy()
    return owners,core,alt,chaos,survivors,bad

def fmt(x):
    if x is None or pd.isna(x): return "—"
    return f"{x:.1f}" if isinstance(x,float) else str(x)

def pct(x):
    try: return max(2,min(100,int(float(x or 0))))
    except Exception: return 0

def card(r):
    p=pct(r.get("score")); color=team_color(r.get("team",""))
    fire="🔥 " if p>=75 else ""
    st.markdown(f"""<div class="card" style="border-color:{color}99"><span class="role">{r.get('role','Primary')}</span><div class="card-name">{fire}{r.get('player','')}</div><div class="meta"><span style="color:{color};font-weight:900">{r.get('team','')}</span> vs {r.get('pitcher','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small style="display:block;font-family:Rajdhani;color:#aaa;font-size:13px">TRUE BLEND SCORE</small></div><div class="bar"><div class="fill" style="width:{p}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><span class="badge">CONF {p}%</span><span class="badge">NO REVIVAL</span></div>""", unsafe_allow_html=True)

def blender_visual(names=None, status="READY"):
    names=(names or ["Upload Feed","Players In","Gates Spin","Owners Out"])
    names=(names+names+names)[:6]
    floats="".join([f"<div class='float f{i+1}'>{str(n)[:22]}</div>" for i,n in enumerate(names)])
    st.markdown(f"""<div class="machine"><div class="blender-wrap"><div class="feed-slot">FEED PLAYERS</div><div class="chute"></div><div class="jar"><div class="blade"></div><div class="center">{status}</div>{floats}</div><div class="blender-base"></div><div class="output-slot">RESULTS POP OUT → CORE / ALT / CHAOS</div></div></div>""", unsafe_allow_html=True)

def safe_table(df,height=360):
    if df is None or df.empty:
        st.info("No data.")
        return
    show=df.copy()
    for c in show.columns:
        if show[c].dtype=="object": show[c]=show[c].astype(str)
    st.dataframe(show,use_container_width=True,height=height)

def csv_bytes(df):
    if df is None or df.empty: return b""
    return df.to_csv(index=False).encode("utf-8")

st.set_page_config(page_title="THE BLENDER",page_icon="🔥",layout="wide",initial_sidebar_state="collapsed")
css()
st.markdown("""<div class="hero"><div class="title">THE <span class="hot">BLENDER</span><br/>MACHINE</div></div>""", unsafe_allow_html=True)

tabs=st.tabs(["Blender Machine","Tickets","Game Board"])

with tabs[0]:
    blender_visual([r.get("player","") for r in st.session_state.get("owners",pd.DataFrame()).head(6).to_dict("records")] if "owners" in st.session_state else None, "READY" if "owners" not in st.session_state else "LOCKED")
    up=st.file_uploader("Feed the Blender",type=["pdf","csv","xlsx"])
    if up:
        try:
            df,raw=read_file(up.name,up.read())
        except Exception as e:
            st.warning(f"Machine read issue: {e}")
            df,raw=pd.DataFrame(columns=CANON),""
        run,bad=clean_for_run(df)
        st.session_state["df"]=df
        st.session_state["run_df"]=run
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Players Read",len(df))
        c2.metric("Runnable",len(run))
        c3.metric("Games",run.game.nunique() if not run.empty else 0)
        c4.metric("Quarantined",len(bad))
        st.markdown("<div class='status'>MACHINE READY — weak rows quarantined silently</div>", unsafe_allow_html=True)
        if st.button("CLICK THE BLENDER"):
            if run.empty:
                st.warning("No readable hitter rows came out of this file. If the PDF is image-only, it needs OCR/exported table data.")
            else:
                bar=st.progress(0); msg=st.empty()
                for i,t in enumerate(["PLAYERS DROPPING IN","BLADES SPINNING","GATES FIRING","OWNERS LOCKING","TICKETS POPPING OUT"]):
                    msg.info(t); bar.progress((i+1)/5); time.sleep(.15)
                owners,core,alt,chaos,survivors,bad=run_blender(df)
                st.session_state.update({"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"bad":bad})
                st.success("RESULTS POPPED OUT")
                st.download_button("Download Core CSV", csv_bytes(core), "core.csv", "text/csv")

with tabs[1]:
    st.markdown("<div class='section-title' style='font-size:34px'>TICKETS</div>", unsafe_allow_html=True)
    for label,key in [("CORE 3","core"),("ALT 3","alt"),("CHAOS 3","chaos")]:
        st.markdown(f"<div class='ticket'><h2>{label}</h2>", unsafe_allow_html=True)
        df=st.session_state.get(key,pd.DataFrame())
        if df is None or df.empty:
            st.info("Run the Blender first.")
        else:
            for _,r in df.iterrows():
                st.markdown(f"<div class='leg'><span><b>{r.get('player','')}</b><br><small>{r.get('team','')} vs {r.get('pitcher','')}</small></span><span class='odds'>{int(r.get('score',0))}%</span></div>", unsafe_allow_html=True)
            st.download_button(f"Download {label}", csv_bytes(df), f"{label.lower().replace(' ','_')}.csv", "text/csv")
        st.markdown("</div>", unsafe_allow_html=True)

with tabs[2]:
    st.markdown("<div class='section-title' style='font-size:34px'>GAME BOARD — SURVIVORS BY GAME</div>", unsafe_allow_html=True)
    owners=st.session_state.get("owners",pd.DataFrame())
    survivors=st.session_state.get("survivors",pd.DataFrame())
    if owners is None or owners.empty:
        st.info("Run the Blender first.")
    else:
        for _,r in owners.iterrows():
            card(r)
        with st.expander("All Survivors Table"):
            safe_table(survivors,420)
        st.download_button("Download Game Board CSV", csv_bytes(owners), "game_board.csv", "text/csv")
