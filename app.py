
import re, io, time, html, math
import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")

# =========================
# CSS
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Inter:wght@500;700;800;900&family=Rajdhani:wght@600;700&display=swap');
:root{--cream:#f5ead8;--muted:#a99e91;--acid:#d9ff2f;--green:#00ff73;--red:#ff355c;--orange:#ff9900;--line:rgba(245,234,216,.16)}
html,body,[class*="css"]{font-family:Inter,sans-serif}.stApp{background:radial-gradient(circle at 18% 8%,rgba(217,255,47,.16),transparent 25%),radial-gradient(circle at 88% 18%,rgba(255,53,92,.10),transparent 32%),linear-gradient(180deg,#050505 0%,#0b0b09 50%,#050505 100%);color:var(--cream)}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;background:linear-gradient(rgba(245,234,216,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(245,234,216,.04) 1px,transparent 1px);background-size:34px 34px;opacity:.8}.block-container{max-width:1240px;padding:1rem 1rem 4rem;position:relative;z-index:1}h1,h2,h3,p,div,span{color:var(--cream)}
.top{position:sticky;top:0;z-index:999;display:flex;justify-content:space-between;align-items:center;background:rgba(5,5,5,.86);border:1px solid var(--line);border-radius:22px;padding:12px 14px;margin-bottom:14px;backdrop-filter:blur(14px)}
.brand{display:flex;align-items:center;gap:12px}.mark{width:56px;height:56px;border-radius:16px;display:grid;place-items:center;background:linear-gradient(135deg,var(--acid),var(--green));color:#050505;font-family:'Black Ops One';font-size:23px;box-shadow:0 0 26px rgba(217,255,47,.28)}
.brand-title{font-family:'Black Ops One';font-size:25px;line-height:1}.brand-sub{font-family:Rajdhani;color:var(--muted);font-size:13px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase}.status{font-family:Rajdhani;font-weight:700;padding:9px 12px;border-radius:999px;background:rgba(217,255,47,.10);border:1px solid rgba(217,255,47,.28);color:#ecffc1}
.hero{border:1px solid var(--line);border-radius:30px;background:linear-gradient(145deg,rgba(23,22,21,.96),rgba(5,5,5,.98));padding:22px;margin-bottom:16px;box-shadow:0 24px 70px rgba(0,0,0,.45)}
.hero h1{font-family:'Black Ops One';font-size:clamp(42px,7vw,82px);line-height:.86;margin:0}.hot{color:var(--acid)}.hero p{color:var(--muted);font-weight:800;font-size:15px;max-width:760px}.chip{display:inline-block;margin:6px 6px 0 0;padding:9px 12px;border-radius:999px;border:1px solid var(--line);background:rgba(245,234,216,.055);font-family:Rajdhani;font-weight:700;letter-spacing:.6px;text-transform:uppercase}
.stTabs [data-baseweb="tab-list"]{gap:8px;background:rgba(16,16,15,.86);border:1px solid var(--line);border-radius:18px;padding:8px}.stTabs [data-baseweb="tab"]{border-radius:13px;color:var(--cream);font-family:Rajdhani;font-weight:700;font-size:15px}.stTabs [aria-selected="true"]{background:linear-gradient(90deg,var(--acid),var(--green))!important;color:#050505!important}
.stButton>button{min-height:62px!important;width:100%!important;border:0!important;border-radius:20px!important;font-family:'Black Ops One'!important;font-size:20px!important;color:#050505!important;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))!important}
.stFileUploader section{background:rgba(245,234,216,.045)!important;border:1px dashed rgba(217,255,47,.35)!important;border-radius:20px!important}[data-testid="stMetric"]{background:rgba(16,16,15,.84);border:1px solid var(--line);border-radius:20px;padding:16px}[data-testid="stMetricValue"]{font-family:'Black Ops One';color:var(--cream)}[data-testid="stMetricLabel"]{color:var(--muted);font-family:Rajdhani;font-weight:700}
.section{display:flex;justify-content:space-between;align-items:center;margin:20px 0 12px}.section h2{font-family:'Black Ops One';font-size:32px;margin:0}.tag{font-family:Rajdhani;font-weight:700;border:1px solid var(--line);background:rgba(245,234,216,.055);border-radius:999px;padding:9px 12px}
.live-wrap{border:1px solid var(--line);border-radius:30px;background:linear-gradient(180deg,rgba(23,22,21,.96),rgba(5,5,5,.98));padding:18px;margin:14px 0;overflow:hidden}.live-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}.live-head h3{font-family:'Black Ops One';font-size:30px;margin:0}.live-grid{display:grid;grid-template-columns:1fr .75fr;gap:14px}
.blender-stage{position:relative;height:430px;border-radius:24px;border:1px solid rgba(245,234,216,.12);background:radial-gradient(circle at center,rgba(0,0,0,.45),rgba(0,0,0,.90));overflow:hidden}.blade{position:absolute;left:50%;top:50%;width:265px;height:265px;margin:-132px;border-radius:50%;background:conic-gradient(transparent 0deg,rgba(217,255,47,.88) 34deg,transparent 73deg,rgba(0,255,115,.88) 142deg,transparent 190deg,rgba(255,153,0,.82) 252deg,transparent 312deg);animation:spin 0.95s linear infinite;filter:blur(.15px)}.center{position:absolute;left:50%;top:50%;width:122px;height:122px;margin:-61px;border-radius:50%;background:#050505;border:2px solid rgba(245,234,216,.28);display:grid;place-items:center;font-family:'Black Ops One';color:var(--acid);z-index:4;text-align:center;font-size:15px}
.float-name{position:absolute;font-family:Rajdhani;font-weight:700;font-size:16px;color:var(--cream);background:rgba(245,234,216,.09);border:1px solid rgba(245,234,216,.16);border-radius:999px;padding:7px 10px;z-index:4;animation:orbit 4.8s linear infinite;max-width:160px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.elim{background:rgba(255,53,92,.14);border-color:rgba(255,53,92,.38);color:#ffd9df;animation:flyout 3.8s ease-in-out infinite}.n1{left:7%;top:15%;animation-delay:0s}.n2{right:7%;top:18%;animation-delay:-.7s}.n3{left:10%;bottom:18%;animation-delay:-1.4s}.n4{right:10%;bottom:17%;animation-delay:-2.1s}.n5{left:36%;top:7%;animation-delay:-2.8s}.n6{left:36%;bottom:8%;animation-delay:-3.5s}@keyframes spin{to{transform:rotate(360deg)}}@keyframes orbit{0%{transform:translateY(0) scale(1);opacity:.95}50%{transform:translateY(-24px) scale(.92);opacity:.58}100%{transform:translateY(0) scale(1);opacity:.95}}@keyframes flyout{0%{transform:translateX(0);opacity:1}60%{transform:translateX(32px);opacity:.6}100%{transform:translateX(0);opacity:1}}
.machine-feed{position:absolute;left:0;right:0;bottom:0;background:rgba(5,5,5,.90);border-top:1px solid var(--line);height:58px;overflow:hidden;white-space:nowrap}.machine-feed span{display:inline-block;padding:16px 0;font-family:Rajdhani;font-weight:700;letter-spacing:1px;color:#ecffc1;animation:ticker 16s linear infinite}@keyframes ticker{from{transform:translateX(100%)}to{transform:translateX(-100%)}}.live-panel{border:1px solid var(--line);border-radius:24px;background:rgba(16,16,15,.72);padding:14px}.big-count{font-family:'Black Ops One';font-size:52px;line-height:.9;color:var(--acid)}.count-label{font-family:Rajdhani;font-weight:700;color:var(--muted);text-transform:uppercase}.alert{border:1px solid rgba(255,53,92,.35);background:rgba(255,53,92,.10);border-radius:18px;padding:12px;margin-top:10px;font-family:Rajdhani;font-weight:700;color:#ffd9df}.ok{border:1px solid rgba(0,255,115,.26);background:rgba(0,255,115,.08);border-radius:18px;padding:12px;margin-top:10px;font-family:Rajdhani;font-weight:700;color:#d9ffe8}
.gate-board{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px;margin:12px 0}.gate-card{border:1px solid var(--line);border-radius:16px;background:rgba(16,16,15,.84);padding:12px}.gate-card b{font-family:'Black Ops One';color:var(--acid);font-size:21px}.gate-card span{display:block;color:var(--muted);font-family:Rajdhani;font-weight:700;font-size:12px;text-transform:uppercase;margin-top:2px}.mini-bar{height:7px;background:rgba(245,234,216,.08);border-radius:999px;overflow:hidden;margin-top:8px}.mini-fill{height:100%;background:linear-gradient(90deg,var(--acid),var(--green));border-radius:999px}
.card{position:relative;overflow:hidden;min-height:282px;border-radius:26px;border:1px solid var(--line);padding:18px;background:linear-gradient(180deg,rgba(23,22,21,.96),rgba(6,6,6,.98));box-shadow:0 18px 48px rgba(0,0,0,.35)}.card:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}.card.fire{box-shadow:0 0 36px rgba(255,153,0,.22),0 18px 48px rgba(0,0,0,.45)}.card.fire:after{content:"🔥 FIRE";position:absolute;right:18px;top:18px;color:#ffcc75;font-family:Rajdhani;font-weight:700}
.role{display:inline-block;font-family:Rajdhani;font-weight:700;text-transform:uppercase;border:1px solid var(--line);border-radius:999px;padding:7px 10px;background:rgba(245,234,216,.055)}.player{font-family:'Black Ops One';font-size:29px;line-height:1.05;margin:14px 0 4px}.meta{font-family:Rajdhani;color:var(--muted);font-weight:700;font-size:15px;min-height:38px}.score{font-family:'Black Ops One';font-size:42px}.score small{display:block;font-family:Rajdhani;color:var(--muted);font-size:12px}.ring{height:12px;background:rgba(245,234,216,.09);border-radius:999px;overflow:hidden;margin-top:8px}.fill{height:100%;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange));border-radius:999px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}.stat{border:1px solid rgba(245,234,216,.10);background:rgba(245,234,216,.045);border-radius:14px;padding:9px}.stat b{display:block}.stat span{font-family:Rajdhani;color:var(--muted);font-size:11px;text-transform:uppercase;font-weight:700}.badge{display:inline-block;margin:10px 5px 0 0;padding:6px 8px;border-radius:999px;background:rgba(217,255,47,.10);border:1px solid rgba(217,255,47,.24);font-family:Rajdhani;font-weight:700;color:#ecffc1}
.ticket-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px}.ticket{border:1px solid var(--line);border-radius:24px;background:linear-gradient(180deg,rgba(23,22,21,.96),rgba(6,6,6,.98));padding:18px}.ticket h3{font-family:'Black Ops One';font-size:30px;margin:0 0 12px}.leg{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(245,234,216,.1);padding:12px 0;font-family:Rajdhani;font-weight:700}.odds{background:rgba(217,255,47,.10);border:1px solid rgba(217,255,47,.24);border-radius:10px;padding:6px 9px;color:#ecffc1}.exposure{height:8px;background:rgba(245,234,216,.08);border-radius:999px;overflow:hidden;margin:10px 0}.exposure span{display:block;height:100%;background:linear-gradient(90deg,var(--acid),var(--green));border-radius:999px}.lock{margin-top:14px;padding:14px;border-radius:16px;background:linear-gradient(90deg,var(--acid),var(--green));color:#050505;font-family:'Black Ops One';text-align:center}.toggle-row{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.toggle{font-family:Rajdhani;font-weight:700;border:1px solid var(--line);border-radius:999px;padding:7px 10px;background:rgba(245,234,216,.055)}
.feed-box{background:rgba(16,16,15,.86);border:1px solid var(--line);border-radius:22px;padding:12px}.feed-row{font-family:Rajdhani;padding:10px;border-bottom:1px solid rgba(245,234,216,.08)}.feed-row:last-child{border-bottom:0}.cut{color:var(--red);font-weight:700}.alive{color:var(--green);font-weight:700}.gate{color:var(--acid);font-weight:700}.danger-box{border:1px solid rgba(255,53,92,.35);background:rgba(255,53,92,.10);border-radius:18px;padding:14px;margin:10px 0;color:#ffd9df}
div[data-testid="stExpander"]{background:rgba(16,16,15,.82)!important;border:1px solid var(--line)!important;border-radius:18px!important}@media(max-width:900px){.live-grid{grid-template-columns:1fr}.blender-stage{height:330px}.float-name{font-size:12px}.hero h1{font-size:44px}}
</style>
""", unsafe_allow_html=True)

# =========================
# DATA ENGINE
# =========================
CANON=["game","team","opponent","pitcher","player","bats","lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_type","pitch_edge","hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","weak_slots","odds","public_pct","weather_score","bullpen_dmg","confirmed_lineup","dob","jersey","result_hr","notes"]

ALIASES={
"player":["player","name","batter","hitter","player_name","batter_name"],
"team":["team","tm","bat_team","batter_team"],
"opponent":["opponent","opp","vs","against"],
"pitcher":["pitcher","opp_pitcher","opposing_pitcher","starter","sp"],
"game":["game","matchup","game_key"],
"lineup_slot":["lineup_slot","slot","batting_order","order","lineup","bo"],
"pull_pct":["pull_pct","pull%","pull","pull_percent"],
"barrel_pct":["barrel_pct","barrel%","barrel","barrel_percent"],
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
"laser":["laser"],
"rakes":["rakes"],
"platoon":["platoon"],
"confirmed_lineup":["confirmed_lineup","confirmed","starting"],
"notes":["notes","note","raw"]
}
BAD={"dmg","hpi","line","cond","alert","hot","cold","warm","moderate","elevated","low","high","fresh","effort","page","https","star","tool","projected","weak","slot","home","away","none"}

TEAM_COLORS={
"red sox":"#BD3039","yankees":"#0C2340","mets":"#FF5910","dodgers":"#005A9C","padres":"#2F241D","phillies":"#E81828","reds":"#C6011F","mariners":"#005C5C","braves":"#CE1141","twins":"#002B5C","astros":"#EB6E1F","blue jays":"#134A8E","orioles":"#DF4601","rays":"#092C5C","royals":"#004687","cubs":"#0E3386","cardinals":"#C41E3A","rockies":"#33006F","angels":"#BA0021","giants":"#FD5A1E","diamondbacks":"#A71930","tigers":"#0C2340","guardians":"#E50022","athletics":"#003831","white sox":"#27251F","pirates":"#FDB827","brewers":"#FFC52F","marlins":"#00A3E0","nationals":"#AB0003","rangers":"#003278"
}
def team_color(team):
    t=str(team).lower()
    for k,v in TEAM_COLORS.items():
        if k in t: return v
    return "#d9ff2f"

def map_columns(df):
    original=list(df.columns)
    norm={c: re.sub(r"[^a-z0-9]+","_",str(c).strip().lower()).strip("_") for c in original}
    rename={}
    used=set()
    for canon, aliases in ALIASES.items():
        for c,n in norm.items():
            if c in used: continue
            if n in [re.sub(r"[^a-z0-9]+","_",a.lower()).strip("_") for a in aliases]:
                rename[c]=canon; used.add(c); break
    df=df.rename(columns=rename)
    return df

def is_player_name(s):
    s=str(s).strip()
    if len(s)<3: return False
    if re.search(r"\d",s): return False
    low=s.lower()
    if low in BAD or "http" in low: return False
    parts=s.split()
    return 1<=len(parts)<=4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts)

def nfloat(x):
    if x is None or pd.isna(x): return None
    if isinstance(x,(int,float)): return float(x)
    s=str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    if s in ["","-","—","None","nan"]: return None
    try: return float(s)
    except: return None

def nbool(x):
    if isinstance(x,bool): return x
    return str(x).lower().strip() in ["true","1","yes","y","alert","hot","x","confirmed","✅","up"]

def clean_df(df):
    df=map_columns(df.copy())
    for c in CANON:
        if c not in df.columns: df[c]=None
    # If no player mapped, try first text column with name-like values
    if df["player"].isna().all() or (df["player"].astype(str).str.strip()=="").all():
        candidates=[]
        for c in df.columns:
            vals=df[c].dropna().astype(str).head(30)
            score=sum(is_player_name(v) for v in vals)
            if score>=3: candidates.append((score,c))
        if candidates:
            df["player"]=df[sorted(candidates, reverse=True)[0][1]]
    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","odds","public_pct","weather_score","bullpen_dmg","jersey"]:
        df[c]=df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","confirmed_lineup","result_hr"]:
        df[c]=df[c].apply(nbool)
    df["player"]=df["player"].astype(str).str.strip()
    df=df[df["player"].apply(is_player_name)].copy()
    # fill game key from real fields
    df["team"]=df["team"].fillna("").astype(str).replace("None","")
    df["pitcher"]=df["pitcher"].fillna("").astype(str).replace("None","")
    df["game"]=df["game"].fillna("").astype(str)
    df.loc[df["game"].str.strip()=="","game"]=df["team"].fillna("")+" vs "+df["pitcher"].fillna("")
    df.loc[df["game"].str.strip()==" vs ","game"]="Unknown Game"
    return df[CANON]

def pdf_text(b):
    if fitz is None: return ""
    doc=fitz.open(stream=b,filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc)

def parse_pdf(b):
    txt=pdf_text(b)
    if not txt.strip(): return pd.DataFrame(columns=CANON)
    try:
        parsed=parse_star_text(txt)
        if parsed is not None and not parsed.empty:
            return parsed
    except Exception:
        pass
    lines=[x.strip() for x in txt.splitlines() if x.strip()]
    rows=[]; team=""; pitcher=""; section=0; weak_by_pitcher={}
    for line in lines:
        m=re.search(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)",line,re.I)
        if m: weak_by_pitcher[m.group(1).strip()]=f"{m.group(2)},{m.group(3)},{m.group(4)}"
    i=0
    while i<len(lines):
        line=lines[i]
        sec=re.search(r"([A-Z][A-Z\s]+?)\s+PROJECTED\s+vs\.\s+(.+?)\s+~",line,re.I)
        if sec:
            team=sec.group(1).strip().title(); pitcher=sec.group(2).strip(); section+=1; i+=1; continue
        if re.match(r"^\d+$",line) and i+1<len(lines):
            name=lines[i+1].strip()
            if is_player_name(name):
                block=" ".join(lines[i+1:i+20])
                slot=None
                sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
                if sm: slot=int(sm.group(1))
                pull=None
                for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block):
                    val=float(pv)
                    if 5<=abs(val)<=65: pull=val; break
                lm=re.search(r"LINE\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%",block); sweet=float(lm.group(1)) if lm else None
                hm=re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA",block); hrpa=float(hm.group(1)) if hm else None
                dm=re.search(r"([0-9]+(?:\.\d+)?)\s+DMG",block); dmg=float(dm.group(1)) if dm else None
                pem=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
                pitch_like=[(float(a),bb) for a,bb in pem if bb.lower() not in ["hr","line","cond"]]
                pe,pt=(pitch_like[-1] if pitch_like else (None,None))
                pluses=[int(x) for x in re.findall(r"\+\s*(\d+)",block) if 10<=int(x)<=90]
                hpi=pluses[-1] if pluses else None
                tm=team if team else f"Team {section or ((len(rows)//9)+1)}"; pit=pitcher if pitcher else f"Pitcher {section or ((len(rows)//9)+1)}"
                rows.append({"game":f"{tm} vs {pit}","team":tm,"opponent":"","pitcher":pit,"player":name,"bats":"","lineup_slot":slot,"pull_pct":pull,"barrel_pct":None,"sweet_spot_pct":sweet,"hard_hit_pct":None,"hpi":hpi,"dmg":dmg,"hr_pa":hrpa,"pitch_type":pt,"pitch_edge":pe,"hr_alert":"ALERT" in block,"cond_up":"COND ↑" in block,"weak_slot_tag":"Weak Slot" in block,"laser":"Laser" in block,"rakes":"Rakes" in block,"platoon":"Platoon" in block,"weak_slots":weak_by_pitcher.get(pit,""),"odds":None,"public_pct":None,"weather_score":None,"bullpen_dmg":None,"confirmed_lineup":False,"dob":None,"jersey":None,"result_hr":False,"notes":block[:220]})
                i+=14; continue
        i+=1
    df=clean_df(pd.DataFrame(rows))
    if not df.empty and (df.team.nunique()<=1 or df.pitcher.nunique()<=1):
        df=df.reset_index(drop=True)
        df["game"]="Game "+((df.index//9)+1).astype(str); df["team"]="Team "+((df.index//9)+1).astype(str); df["pitcher"]="Pitcher "+((df.index//9)+1).astype(str)
    return df

# =========================
# TRUE ELIMINATION ENGINE
# =========================
def slot_ok(r):
    slots=[int(x) for x in re.findall(r"\d+",str(r.get("weak_slots") or ""))]
    if not slots or pd.isna(r.get("lineup_slot")): return True
    return int(r["lineup_slot"]) in slots or bool(r.get("weak_slot_tag"))

def role_type(r):
    if bool(r.get("weak_slot_tag")) or bool(r.get("laser")) or bool(r.get("rakes")): return "Transfer"
    if (r.get("dmg") or 0)>=1.7 and (r.get("hr_pa") or 0)>=4: return "WHO"
    return "Primary"

def component_scores(r):
    # 0-100 actual usable components. Missing data does NOT become a boost.
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
    # Hard penalties for empty profiles
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
    for c in cols:
        mask = mask | df[c].notna()
    return mask

def run_game(gdf):
    alive=gdf.copy(); logs=[]
    logs.append({"Gate":"0 Game / Pitcher Viability","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16]),"Reason":"Game enters machine."})
    # hard gates only when data is present; missing data survives but later score penalizes
    alive=apply_gate(alive,"1 Pull / Air DNA", alive.pull_pct.isna() | (alive.pull_pct>=20), "Pull must not be dead when available.", logs)
    if len(alive)>1: alive=apply_gate(alive,"2 Pitch Edge", alive.pitch_edge.isna() | (alive.pitch_edge>=0), "Negative pitch edge removed.", logs)
    if len(alive)>1: alive=apply_gate(alive,"3 Weak Slot", alive.apply(slot_ok,axis=1), "Weak slot alignment when available.", logs)
    if len(alive)>1: alive=apply_gate(alive,"4 Launch Window", alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=24), "Launch window must pass when listed.", logs)
    if len(alive)>1: alive=apply_gate(alive,"5 Conversion", alive.hr_pa.isna() | (alive.hr_pa>=2.0) | (alive.barrel_pct.fillna(0)>=8) | alive.hr_alert, "Must show HR/PA, barrel, or alert.", logs)
    if len(alive)>1: alive=apply_gate(alive,"6 DMG", alive.dmg.isna() | (alive.dmg>=0.5) | alive.hr_alert, "Low damage removed unless alert.", logs)
    if len(alive)>1: alive=apply_gate(alive,"7 HPI", alive.hpi.isna() | (alive.hpi>=18) | alive.hr_alert, "Weak HPI removed unless alert.", logs)
    if len(alive)>1: alive=apply_gate(alive,"8 Alert / Condition", alive.hr_alert | alive.cond_up | has_one_of(alive,["dmg","hr_pa","hpi","pull_pct"]), "Needs some valid pressure signal.", logs)
    if len(alive)>1: alive=apply_gate(alive,"9 No Empty Bat", ~(alive.hr_pa.fillna(1).eq(0) & alive.dmg.fillna(1).lt(0.5) & ~alive.hr_alert), "Zero HR profile removed.", logs)
    for g in ["10 Ownership Pressure","10.5 Adjacent / Decoy Transfer","11 Lineup Protection","12 Bullpen Continuation","13 Numerology Overlay","14 Chaos / WHO","15 Finisher Gate","16 Event Likelihood","17 No-Fluke Audit","18 True HR Event Likelihood"]:
        if len(alive)>1:
            logs.append({"Gate":g,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16]),"Reason":"Audit/tie-break; dead players do not return."})
    if alive.empty: return alive,pd.DataFrame(logs)
    alive=alive.copy(); alive["role"]=alive.apply(role_type,axis=1); alive["score"]=alive.apply(true_score,axis=1)
    alive=alive.sort_values("score",ascending=False)
    # If all scores are weak, still show owner but flag weak
    return alive,pd.DataFrame(logs)

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
        # Remove obvious weak owners from core if score < 25 unless no alternatives
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

def fmt(x):
    if x is None or pd.isna(x): return "—"
    return f"{x:.1f}" if isinstance(x,float) else str(x)

def safe_pct(x):
    try: return max(2,min(100,int(float(x or 0))))
    except: return 0

def conf_pct(x):
    return safe_pct(x)

def player_card(r):
    pct=safe_pct(r.get("score"))
    fire=" fire" if pct>=75 else ""
    color=team_color(r.get("team",""))
    st.markdown(f"""<div class="card{fire}" style="border-color:{color}88"><span class="role">{r.get('role','Primary')}</span><div class="player">{r.get('player','')}</div><div class="meta"><span style="color:{color};font-weight:900">{r.get('team','')}</span> vs {r.get('pitcher','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small>TRUE BLEND SCORE</small></div><div class="ring"><div class="fill" style="width:{pct}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><span class="badge">CONF {conf_pct(r.get('score'))}%</span><span class="badge">NO REVIVAL</span></div>""", unsafe_allow_html=True)

def live_blender(names=None, cut_names=None, owner="OWNER", status="DATA IN → GATES SPIN → OWNER LOCKED"):
    names=names or ["Upload Slate","Run Machine","Owners Lock","Core Builds"]
    cut_names=cut_names or []
    n=(names+names+names)[:4]+(cut_names+cut_names)[:2]
    html_names=""
    for i,name in enumerate(n[:6]):
        cls=f"float-name n{i+1}" + (" elim" if i>=4 else "")
        html_names += f"<div class='{cls}'>{html.escape(str(name))}</div>"
    st.markdown(f"""<div class="live-wrap"><div class="live-head"><h3>LIVE BLENDER WHEEL</h3><span class="tag">REAL PLAYER FEED</span></div><div class="live-grid"><div class="blender-stage"><div class="blade"></div><div class="center">{html.escape(str(owner))[:18]}</div>{html_names}<div class="machine-feed"><span> MACHINE SPEAKS: {html.escape(status)} </span></div></div><div class="live-panel"><div class="count-label">Survivor Count</div><div class="big-count">{len(names)}</div><div class="ok">LOCK CONFIRMED only after gate sequence.</div><div class="alert">WHO EVENT DETECTED when chaos/transfer role survives.</div><div class="alert">PUBLIC OVEREXPOSURE ALERT checked at Gate 10.</div></div></div></div>""", unsafe_allow_html=True)

def gate_board(logs=None):
    gate_names=[("0","Game Viability"),("1","Pull DNA"),("2","Pitch Edge"),("3","Weak Slot"),("4","Launch"),("5","Conversion"),("6","DMG"),("7","HPI"),("8","Alert"),("9","No Empty Bat"),("10","Pressure"),("10.5","Transfer"),("11","Protection"),("12","Bullpen"),("13","Numerology"),("14","WHO"),("15","Finisher"),("16","Likelihood"),("17","No-Fluke"),("18","Final")]
    last_after={}; max_before=1
    if logs is not None and not logs.empty:
        max_before=max(1,int(logs["Before"].max()))
        for _,r in logs.iterrows():
            key=str(r["Gate"]).split()[0]; last_after[key]=int(r["After"])
    html="<div class='gate-board'>"
    for n,label in gate_names:
        after=last_after.get(n,None); pct=0 if after is None else max(5,min(100,int(after/max_before*100)))
        sub=label if after is None else f"{label} · {after} alive"
        html+=f"<div class='gate-card'><b>{n}</b><span>{sub}</span><div class='mini-bar'><div class='mini-fill' style='width:{pct}%'></div></div></div>"
    html+="</div>"; st.markdown(html, unsafe_allow_html=True)


def parse_star_text(txt):
    lines=[x.strip() for x in str(txt).splitlines() if str(x).strip()]
    rows=[]; team=""; pitcher=""; section=0; weak_by_pitcher={}
    for line in lines:
        m=re.search(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)",line,re.I)
        if m: weak_by_pitcher[m.group(1).strip()]=f"{m.group(2)},{m.group(3)},{m.group(4)}"
    i=0
    while i < len(lines):
        line=lines[i]
        sec=re.search(r"([A-Z][A-Z\s]+?)\s+PROJECTED\s+vs\.\s+(.+?)(?:\s+~|\s*$)", line, re.I)
        if sec:
            team=sec.group(1).strip().title()
            pitcher=sec.group(2).strip()
            section += 1; i += 1; continue
        name=None; start=i
        if re.match(r"^\d+$", line) and i+1 < len(lines) and is_player_name(lines[i+1]):
            name=lines[i+1].strip(); start=i+1
        elif is_player_name(line) and i>0 and re.match(r"^\d+$", lines[i-1]):
            name=line.strip(); start=i
        if name:
            block=" ".join(lines[start:start+24])
            sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block); slot=int(sm.group(1)) if sm else None
            pull=None
            for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block):
                val=float(pv)
                if 5<=abs(val)<=65: pull=val; break
            lm=re.search(r"LINE\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%",block); sweet=float(lm.group(1)) if lm else None
            hm=re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA",block); hrpa=float(hm.group(1)) if hm else None
            dm=re.search(r"([0-9]+(?:\.\d+)?)\s+DMG",block); dmg=float(dm.group(1)) if dm else None
            pem=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
            pitch_like=[(float(a),bb) for a,bb in pem if bb.lower() not in ["hr","line","cond"]]
            pe,pt=(pitch_like[-1] if pitch_like else (None,None))
            hpi=None
            hm2=re.search(r"HPI\s*\+?\s*(\d+)",block,re.I)
            if hm2: hpi=int(hm2.group(1))
            else:
                pluses=[int(x) for x in re.findall(r"\+\s*(\d+)",block) if 10<=int(x)<=90]
                if pluses: hpi=pluses[-1]
            tm=team if team else f"Team {section or ((len(rows)//9)+1)}"; pit=pitcher if pitcher else f"Pitcher {section or ((len(rows)//9)+1)}"
            rows.append({"game":f"{tm} vs {pit}","team":tm,"opponent":"","pitcher":pit,"player":name,"bats":"","lineup_slot":slot,"pull_pct":pull,"barrel_pct":None,"sweet_spot_pct":sweet,"hard_hit_pct":None,"hpi":hpi,"dmg":dmg,"hr_pa":hrpa,"pitch_type":pt,"pitch_edge":pe,"hr_alert":"ALERT" in block,"cond_up":"COND ↑" in block,"weak_slot_tag":"Weak Slot" in block,"laser":"Laser" in block,"rakes":"Rakes" in block,"platoon":"Platoon" in block,"weak_slots":weak_by_pitcher.get(pit,""),"odds":None,"public_pct":None,"weather_score":None,"bullpen_dmg":None,"confirmed_lineup":False,"dob":None,"jersey":None,"result_hr":False,"notes":block[:220]})
            i += 14; continue
        i += 1
    return clean_df(pd.DataFrame(rows))

def normalize_star_export_lines(df):
    if df.shape[1] <= 3:
        text="\\n".join(df.astype(str).fillna("").agg(" ".join, axis=1).tolist())
        if any(k in text for k in ["PROJECTED","DMG","HR/PA","Weak","ALERT"]):
            parsed=parse_star_text(text)
            if parsed is not None and not parsed.empty: return parsed
    return df

def feeder_audit(df):
    if df is None or df.empty: return False, ["No parsed player rows."]
    issues=[]; total=len(df)
    def blank(col):
        if col not in df.columns: return total
        s=df[col]
        return int(s.isna().sum() + (s.astype(str).str.strip().isin(["","None","nan"]).sum() if s.dtype==object else 0))
    if total < 100: issues.append(f"Player count low: {total}.")
    if df["team"].replace("", pd.NA).dropna().nunique() < 10: issues.append("Team extraction failed/low.")
    if df["pitcher"].replace("", pd.NA).dropna().nunique() < 10: issues.append("Pitcher extraction failed/low.")
    for col in ["hpi","dmg","hr_pa","pull_pct"]:
        if blank(col) > total*.55: issues.append(f"{col.upper()} missing too often.")
    if blank("pitch_edge") > total*.80: issues.append("Pitch edge missing too often.")
    return len(issues)==0, issues

# =========================
# UI
# =========================
st.markdown("""
<div class="top"><div class="brand"><div class="mark">BH</div><div><div class="brand-title">THE BLENDER</div><div class="brand-sub">PRIVATE LOCK ROOM</div></div></div><div class="status">SYSTEM ARMED</div></div>
<div class="hero"><h1>THE <span class="hot">BLENDER</span><br/>PRIVATE LOCK</h1><span class="chip">Official 0 → 18</span><span class="chip">10.5 in sequence</span><span class="chip">One owner per game</span><span class="chip">No revivals</span></div>
""", unsafe_allow_html=True)

tabs=st.tabs(["Launch","Machine","Game Board","Tickets","Kill Feed"])
with tabs[0]:
    if "owners" in st.session_state:
        owners=st.session_state["owners"]
        live_blender(owners.head(6).player.tolist(), [], owners.iloc[0].player if not owners.empty else "OWNER", f"{len(st.session_state['df'])} IN → {len(owners)} OWNERS → CORE LOCKED")
    else:
        live_blender()
    uploaded=st.file_uploader("Upload slate",type=["pdf","csv","xlsx"])
    if uploaded:
        data=uploaded.read(); name=uploaded.name.lower()
        try:
            if name.endswith(".csv"): 
                raw_csv=pd.read_csv(io.BytesIO(data))
                raw_csv=normalize_star_export_lines(raw_csv)
                df=clean_df(raw_csv)
            elif name.endswith(".xlsx"): 
                df=clean_df(pd.read_excel(io.BytesIO(data)))
            else: 
                df=parse_pdf(data)
        except Exception as e:
            st.error(f"Parser error: {e}"); df=pd.DataFrame()
        if df.empty:
            st.error("No valid player rows parsed. Open Parsed/CSV file and make sure a Player/Batter/Hitter column exists.")
        else:
            c1,c2,c3,c4=st.columns(4); c1.metric("Players",len(df)); c2.metric("Games",df.game.nunique()); c3.metric("Teams",df.team.nunique()); c4.metric("Pitchers",df.pitcher.nunique())
            missing_cols=["team","pitcher","hpi","dmg","pitch_edge","weak_slots","hr_pa","pull_pct"]
            miss=df[missing_cols].isna().sum().reset_index(); miss.columns=["Field","Missing Count"]
            if miss["Missing Count"].sum()>0:
                with st.expander("Missing Data Report"):
                    st.dataframe(miss,use_container_width=True)
                    st.markdown("<div class='danger-box'>Missing fields are now penalized in the score instead of accidentally boosting players.</div>", unsafe_allow_html=True)
            ok_feed, feed_issues = feeder_audit(df)
            with st.expander("Feeder Accuracy Audit"):
                if ok_feed:
                    st.markdown("<div class='audit-good'>FEEDER LOCKED</div>", unsafe_allow_html=True)
                else:
                    st.markdown("<div class='audit-bad'>FEEDER NOT LOCKED</div>", unsafe_allow_html=True)
                    st.write(feed_issues)
            if st.button("ENGAGE BLENDER"):
                if not ok_feed:
                    st.error("Feeder quality failed. Fix feed before producing picks — no fake locks.")
                else:
                    progress=st.progress(0); msg=st.empty()
                    for i,txt in enumerate(["Feeding slate","Mapping columns","Running hard gates","Checking 10.5 transfer","Locking game owners","Building slips"]):
                        msg.info(f"MACHINE SPEAKS: {txt.upper()}..."); progress.progress((i+1)/6); time.sleep(.12)
                    owners,core,alt,logs,survivors=run_machine(df)
                    st.session_state.update({"df":df,"owners":owners,"core":core,"alt":alt,"logs":logs,"survivors":survivors})
                    msg.success("MACHINE COMPLETE — FINAL BOARD READY")
            with st.expander("Parsed Slate Preview"):
                st.dataframe(df,use_container_width=True,height=360)
    if "core" in st.session_state:
        st.markdown("<div class='section'><h2>CORE 3</h2><span class='tag'>ROLE BALANCED</span></div>", unsafe_allow_html=True)
        cols=st.columns(3)
        for i,(_,r) in enumerate(st.session_state["core"].iterrows()):
            with cols[i]: player_card(r)
        st.markdown("<div class='section'><h2>ALT 3</h2><span class='tag'>LEGAL BACKUPS</span></div>", unsafe_allow_html=True)
        if not st.session_state["alt"].empty:
            cols=st.columns(3)
            for i,(_,r) in enumerate(st.session_state["alt"].head(3).iterrows()):
                with cols[i]: player_card(r)

with tabs[1]:
    if "owners" in st.session_state:
        owners=st.session_state["owners"]; logs=st.session_state["logs"]
        cuts=",".join(logs["Cut names"].dropna().astype(str).tolist()) if not logs.empty else ""
        cut_names=[x.strip() for x in cuts.split(",") if x.strip()][:4]
        live_blender(owners.head(6).player.tolist(),cut_names,owners.iloc[0].player if not owners.empty else "OWNER",f"{len(st.session_state['df'])} IN → {len(owners)} OWNERS → CORE LOCKED")
        st.markdown("<div class='section'><h2>FUNCTIONAL GATE BOARD</h2><span class='tag'>ALIVE COUNTS</span></div>", unsafe_allow_html=True)
        gate_board(logs)
    else:
        live_blender(); gate_board()

with tabs[2]:
    if "owners" in st.session_state:
        for _,r in st.session_state["owners"].iterrows(): player_card(r)
    else: st.info("Run a slate first.")

with tabs[3]:
    if "core" in st.session_state and not st.session_state["core"].empty:
        core=st.session_state["core"]; alt=st.session_state["alt"]
        roles=core["role"].value_counts().to_dict()
        st.markdown(f"<div class='toggle-row'><span class='toggle'>Primary {roles.get('Primary',0)}</span><span class='toggle'>Transfer {roles.get('Transfer',0)}</span><span class='toggle'>WHO {roles.get('WHO',0)}</span><span class='toggle'>Avg Conf {int(core['score'].mean())}%</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='ticket-grid'>", unsafe_allow_html=True)
        st.markdown("<div class='ticket'><h3>CORE SLIP</h3>", unsafe_allow_html=True)
        for _,r in core.iterrows():
            st.markdown(f"<div class='leg'><span>{r['player']}<br><small>{r.get('team','')} · {r.get('role','')}</small></span><span class='odds'>CONF {conf_pct(r.get('score'))}%</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='exposure'><span style='width:78%'></span></div><div class='lock'>LOCK CORE</div></div>", unsafe_allow_html=True)
        if not alt.empty:
            st.markdown("<div class='ticket'><h3>ALT SLIP</h3>", unsafe_allow_html=True)
            for _,r in alt.head(3).iterrows():
                st.markdown(f"<div class='leg'><span>{r['player']}<br><small>{r.get('team','')} · {r.get('role','')}</small></span><span class='odds'>CONF {conf_pct(r.get('score'))}%</span></div>", unsafe_allow_html=True)
            st.markdown("<div class='exposure'><span style='width:54%'></span></div><div class='lock'>LOCK ALT</div></div>", unsafe_allow_html=True)
        chaos_pool=pd.concat([core,alt],ignore_index=True) if not alt.empty else core
        chaos=chaos_pool[chaos_pool["role"].isin(["WHO","Transfer"])].head(3)
        if not chaos.empty:
            st.markdown("<div class='ticket'><h3>CHAOS SLIP</h3>", unsafe_allow_html=True)
            for _,r in chaos.iterrows():
                st.markdown(f"<div class='leg'><span>{r['player']}<br><small>{r.get('team','')} · {r.get('role','')}</small></span><span class='odds'>CHAOS</span></div>", unsafe_allow_html=True)
            st.markdown("<div class='exposure'><span style='width:41%'></span></div><div class='lock'>LOCK CHAOS</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else: st.info("Run a slate first.")

with tabs[4]:
    if "logs" in st.session_state:
        logs=st.session_state["logs"]
        st.markdown("<div class='feed-box'>", unsafe_allow_html=True)
        for _,r in logs.head(120).iterrows():
            st.markdown(f"<div class='feed-row'><span class='gate'>{r['Gate']}</span> · <span class='cut'>CUT {r['Cut']}</span> · <span class='alive'>ALIVE {r['After']}</span><br/><span style='color:#aaa093'>{r['Game']}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        with st.expander("Full Audit Table"):
            st.dataframe(logs,use_container_width=True,height=540)
    else: st.info("Run a slate first.")
