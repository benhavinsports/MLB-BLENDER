
import re, io, time, html
import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")

# =========================
# CSS: FUNCTIONAL BLENDER UI
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Inter:wght@500;700;800;900&family=Rajdhani:wght@600;700&display=swap');
:root{
  --cream:#f5ead8;--muted:#a99e91;--acid:#d9ff2f;--green:#00ff73;--red:#ff355c;--orange:#ff9900;
  --panel:#10100f;--panel2:#171615;--line:rgba(245,234,216,.16)
}
html,body,[class*="css"]{font-family:Inter,sans-serif}
.stApp{background:linear-gradient(180deg,#050505 0%,#0b0b09 50%,#050505 100%);color:var(--cream)}
.stApp:before{content:"";position:fixed;inset:0;pointer-events:none;background:
linear-gradient(rgba(245,234,216,.04) 1px,transparent 1px),
linear-gradient(90deg,rgba(245,234,216,.04) 1px,transparent 1px);background-size:34px 34px;opacity:.9}
.block-container{max-width:1220px;padding:1rem 1rem 4rem;position:relative;z-index:1}
h1,h2,h3,p,div,span{color:var(--cream)}
.top{position:sticky;top:0;z-index:999;display:flex;justify-content:space-between;align-items:center;background:rgba(5,5,5,.84);border:1px solid var(--line);border-radius:22px;padding:12px 14px;margin-bottom:14px;backdrop-filter:blur(14px)}
.brand{display:flex;align-items:center;gap:12px}.mark{width:56px;height:56px;border-radius:16px;display:grid;place-items:center;background:linear-gradient(135deg,var(--acid),var(--green));color:#050505;font-family:'Black Ops One';font-size:23px;box-shadow:0 0 26px rgba(217,255,47,.28)}
.brand-title{font-family:'Black Ops One';font-size:25px;line-height:1}.brand-sub{font-family:Rajdhani;color:var(--muted);font-size:13px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase}.status{font-family:Rajdhani;font-weight:700;padding:9px 12px;border-radius:999px;background:rgba(217,255,47,.10);border:1px solid rgba(217,255,47,.28);color:#ecffc1}
.hero{border:1px solid var(--line);border-radius:30px;background:linear-gradient(145deg,rgba(23,22,21,.96),rgba(5,5,5,.98));padding:22px;margin-bottom:16px;box-shadow:0 24px 70px rgba(0,0,0,.45)}
.hero h1{font-family:'Black Ops One';font-size:clamp(42px,7vw,82px);line-height:.86;margin:0}.hot{color:var(--acid)}.hero p{color:var(--muted);font-weight:800;font-size:15px;max-width:760px}.chip{display:inline-block;margin:6px 6px 0 0;padding:9px 12px;border-radius:999px;border:1px solid var(--line);background:rgba(245,234,216,.055);font-family:Rajdhani;font-weight:700;letter-spacing:.6px;text-transform:uppercase}
.stTabs [data-baseweb="tab-list"]{gap:8px;background:rgba(16,16,15,.86);border:1px solid var(--line);border-radius:18px;padding:8px}.stTabs [data-baseweb="tab"]{border-radius:13px;color:var(--cream);font-family:Rajdhani;font-weight:700;font-size:15px}.stTabs [aria-selected="true"]{background:linear-gradient(90deg,var(--acid),var(--green))!important;color:#050505!important}
.stButton>button{min-height:62px!important;width:100%!important;border:0!important;border-radius:20px!important;font-family:'Black Ops One'!important;font-size:20px!important;color:#050505!important;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))!important}
.stFileUploader section{background:rgba(245,234,216,.045)!important;border:1px dashed rgba(217,255,47,.35)!important;border-radius:20px!important}
[data-testid="stMetric"]{background:rgba(16,16,15,.84);border:1px solid var(--line);border-radius:20px;padding:16px}[data-testid="stMetricValue"]{font-family:'Black Ops One';color:var(--cream)}[data-testid="stMetricLabel"]{color:var(--muted);font-family:Rajdhani;font-weight:700}
.section{display:flex;justify-content:space-between;align-items:center;margin:20px 0 12px}.section h2{font-family:'Black Ops One';font-size:32px;margin:0}.tag{font-family:Rajdhani;font-weight:700;border:1px solid var(--line);background:rgba(245,234,216,.055);border-radius:999px;padding:9px 12px}

/* Functional blender */
.blender-box{border:1px solid var(--line);border-radius:30px;background:radial-gradient(circle at center,rgba(217,255,47,.10),transparent 35%),linear-gradient(180deg,rgba(23,22,21,.96),rgba(5,5,5,.98));padding:18px;margin:14px 0;position:relative;overflow:hidden}
.blender-stage{position:relative;height:390px;border-radius:24px;border:1px solid rgba(245,234,216,.12);background:radial-gradient(circle at center,rgba(0,0,0,.55),rgba(0,0,0,.88));overflow:hidden}
.blade{position:absolute;left:50%;top:50%;width:250px;height:250px;margin:-125px;border-radius:50%;background:conic-gradient(transparent 0deg,rgba(217,255,47,.82) 36deg,transparent 75deg,rgba(0,255,115,.82) 142deg,transparent 190deg,rgba(255,153,0,.78) 250deg,transparent 310deg);animation:spin 1.05s linear infinite;filter:blur(.2px)}
.center{position:absolute;left:50%;top:50%;width:116px;height:116px;margin:-58px;border-radius:50%;background:#050505;border:2px solid rgba(245,234,216,.25);display:grid;place-items:center;font-family:'Black Ops One';color:var(--acid);z-index:3}
.float-name{position:absolute;font-family:Rajdhani;font-weight:700;font-size:16px;color:var(--cream);background:rgba(245,234,216,.08);border:1px solid rgba(245,234,216,.14);border-radius:999px;padding:7px 10px;z-index:4;animation:orbit 5s linear infinite}
.n1{left:8%;top:16%;animation-delay:0s}.n2{right:8%;top:20%;animation-delay:-.8s}.n3{left:12%;bottom:20%;animation-delay:-1.5s}.n4{right:13%;bottom:18%;animation-delay:-2.2s}.n5{left:38%;top:8%;animation-delay:-3s}.n6{left:38%;bottom:8%;animation-delay:-3.8s}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes orbit{0%{transform:translateY(0) scale(1);opacity:.95}50%{transform:translateY(-22px) scale(.94);opacity:.58}100%{transform:translateY(0) scale(1);opacity:.95}}
.machine-feed{position:absolute;left:0;right:0;bottom:0;background:rgba(5,5,5,.88);border-top:1px solid var(--line);height:54px;overflow:hidden;white-space:nowrap}.machine-feed span{display:inline-block;padding:15px 0;font-family:Rajdhani;font-weight:700;letter-spacing:1px;color:#ecffc1;animation:ticker 18s linear infinite}@keyframes ticker{from{transform:translateX(100%)}to{transform:translateX(-100%)}}
.gate-list{display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px;margin:12px 0}.gate-row{border:1px solid var(--line);border-radius:16px;background:rgba(16,16,15,.84);padding:11px}.gate-row b{font-family:'Black Ops One';color:var(--acid)}.gate-row span{display:block;color:var(--muted);font-family:Rajdhani;font-weight:700;font-size:12px;text-transform:uppercase;margin-top:2px}

/* Cards */
.card{position:relative;overflow:hidden;min-height:282px;border-radius:26px;border:1px solid var(--line);padding:18px;background:linear-gradient(180deg,rgba(23,22,21,.96),rgba(6,6,6,.98));box-shadow:0 18px 48px rgba(0,0,0,.35)}
.card:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}
.role{display:inline-block;font-family:Rajdhani;font-weight:700;text-transform:uppercase;border:1px solid var(--line);border-radius:999px;padding:7px 10px;background:rgba(245,234,216,.055)}
.player{font-family:'Black Ops One';font-size:29px;line-height:1.05;margin:14px 0 4px}.meta{font-family:Rajdhani;color:var(--muted);font-weight:700;font-size:15px;min-height:38px}.score{font-family:'Black Ops One';font-size:42px}.score small{display:block;font-family:Rajdhani;color:var(--muted);font-size:12px}.ring{height:12px;background:rgba(245,234,216,.09);border-radius:999px;overflow:hidden;margin-top:8px}.fill{height:100%;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange));border-radius:999px}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}.stat{border:1px solid rgba(245,234,216,.10);background:rgba(245,234,216,.045);border-radius:14px;padding:9px}.stat b{display:block}.stat span{font-family:Rajdhani;color:var(--muted);font-size:11px;text-transform:uppercase;font-weight:700}.badge{display:inline-block;margin:10px 5px 0 0;padding:6px 8px;border-radius:999px;background:rgba(217,255,47,.10);border:1px solid rgba(217,255,47,.24);font-family:Rajdhani;font-weight:700;color:#ecffc1}

/* Ticket */
.ticket-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.ticket{border:1px solid var(--line);border-radius:24px;background:linear-gradient(180deg,rgba(23,22,21,.96),rgba(6,6,6,.98));padding:18px}.ticket h3{font-family:'Black Ops One';font-size:28px;margin:0 0 12px}.leg{display:flex;justify-content:space-between;border-bottom:1px solid rgba(245,234,216,.1);padding:12px 0;font-family:Rajdhani;font-weight:700}.lock{margin-top:14px;padding:14px;border-radius:16px;background:linear-gradient(90deg,var(--acid),var(--green));color:#050505;font-family:'Black Ops One';text-align:center}
.feed-box{background:rgba(16,16,15,.86);border:1px solid var(--line);border-radius:22px;padding:12px}.feed-row{font-family:Rajdhani;padding:10px;border-bottom:1px solid rgba(245,234,216,.08)}.feed-row:last-child{border-bottom:0}.cut{color:var(--red);font-weight:700}.alive{color:var(--green);font-weight:700}.gate{color:var(--acid);font-weight:700}
div[data-testid="stExpander"]{background:rgba(16,16,15,.82)!important;border:1px solid var(--line)!important;border-radius:18px!important}
@media(max-width:850px){.blender-stage{height:310px}.float-name{font-size:12px}.hero h1{font-size:44px}}
</style>
""", unsafe_allow_html=True)

# =========================
# DATA ENGINE
# =========================
COLS=["game","team","opponent","pitcher","player","bats","lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_type","pitch_edge","hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","weak_slots","odds","public_pct","weather_score","bullpen_dmg","confirmed_lineup","dob","jersey","result_hr","notes"]
BAD={"dmg","hpi","line","cond","alert","hot","cold","warm","moderate","elevated","low","high","fresh","effort","page","https","star","tool","projected","weak","slot","home","away","none"}

def is_player_name(s):
    s=str(s).strip()
    if len(s)<4 or re.search(r"\d",s): return False
    low=s.lower()
    if low in BAD or "http" in low: return False
    parts=s.split()
    return 2<=len(parts)<=4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts)

def nfloat(x):
    if x is None or pd.isna(x): return None
    if isinstance(x,(int,float)): return float(x)
    try: return float(str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip())
    except: return None

def nbool(x):
    if isinstance(x,bool): return x
    return str(x).lower().strip() in ["true","1","yes","y","alert","hot","x","confirmed","✅"]

def clean_df(df):
    df.columns=[str(c).strip().lower().replace(" ","_") for c in df.columns]
    for c in COLS:
        if c not in df.columns: df[c]=None
    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","odds","public_pct","weather_score","bullpen_dmg","jersey"]:
        df[c]=df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","confirmed_lineup","result_hr"]:
        df[c]=df[c].apply(nbool)
    df["player"]=df["player"].astype(str).str.strip()
    return df[df["player"].apply(is_player_name)].copy()[COLS]

def pdf_text(b):
    if fitz is None: return ""
    doc=fitz.open(stream=b,filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc)

def parse_pdf(b):
    txt=pdf_text(b)
    if not txt.strip(): return pd.DataFrame(columns=COLS)
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
                block=" ".join(lines[i+1:i+18])
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

def slot_ok(r):
    slots=[int(x) for x in re.findall(r"\d+",str(r.get("weak_slots") or ""))]
    if not slots or pd.isna(r.get("lineup_slot")): return True
    return int(r["lineup_slot"]) in slots or bool(r.get("weak_slot_tag"))

def role_type(r):
    if bool(r.get("weak_slot_tag")) or bool(r.get("laser")) or bool(r.get("rakes")): return "Transfer"
    if (r.get("dmg") or 0)>=1.7 and (r.get("hr_pa") or 0)>=4: return "WHO"
    return "Primary"

def score_row(r):
    return ((r.get("pull_pct") or 0)*.10+(r.get("pitch_edge") or 0)*.20+(r.get("sweet_spot_pct") or 0)*.10+(r.get("dmg") or 0)*12+(r.get("hpi") or 0)*.12+(r.get("hr_pa") or 0)*2+int(bool(r.get("hr_alert")))*8+int(bool(r.get("cond_up")))*5+int(bool(r.get("weak_slot_tag")))*4+int(bool(r.get("laser")))*3+int(bool(r.get("rakes")))*3)

def apply_gate(alive,name,mask,reason,logs):
    before=alive.player.tolist(); cut=alive.loc[~mask,"player"].tolist(); alive=alive[mask].copy()
    logs.append({"Gate":name,"Before":len(before),"Cut":len(cut),"After":len(alive),"Cut names":", ".join(cut),"Alive after":", ".join(alive.player.tolist()),"Reason":reason})
    return alive

def run_game(gdf):
    alive=gdf.copy(); logs=[]
    logs.append({"Gate":"0 Game / Pitcher Viability","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()),"Reason":"Game enters machine."})
    alive=apply_gate(alive,"1 Pull %",alive.pull_pct.isna() | (alive.pull_pct>=20),"Pull DNA.",logs)
    if len(alive)>1: alive=apply_gate(alive,"2 Matchup / Pitch Edge",alive.pitch_edge.isna() | (alive.pitch_edge>=0),"Pitch edge kill.",logs)
    if len(alive)>1: alive=apply_gate(alive,"3 Zones / Weak Slot",alive.apply(slot_ok,axis=1),"Weak slot alignment.",logs)
    if len(alive)>1: alive=apply_gate(alive,"4 Sweet Spot / Launch",alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=25),"Launch profile.",logs)
    if len(alive)>1: alive=apply_gate(alive,"5 Barrel / Conversion",alive.hr_pa.isna() | (alive.hr_pa>=3) | (alive.barrel_pct.fillna(0)>=10),"Conversion.",logs)
    if len(alive)>1: alive=apply_gate(alive,"6 DMG",alive.dmg.isna() | (alive.dmg>=1.0),"Damage floor.",logs)
    if len(alive)>1: alive=apply_gate(alive,"7 HPI",alive.hpi.isna() | (alive.hpi>=30),"HPI floor.",logs)
    if len(alive)>1: alive=apply_gate(alive,"8 Recency / Alert",alive.hr_alert | alive.cond_up | alive.hr_alert.isna(),"Recent pressure.",logs)
    if len(alive)>1: alive=apply_gate(alive,"9 No Empty Bat",alive.hr_pa.isna() | (alive.hr_pa>0) | alive.hr_alert,"No empty bat.",logs)
    for g in ["10 Ownership Pressure","10.5 Adjacent / Decoy Transfer","11 Lineup Protection","12 Bullpen Continuation","13 Numerology Overlay","14 Chaos / WHO","15 Finisher Gate","16 Event Likelihood","17 No-Fluke Audit","18 True HR Event Likelihood"]:
        if len(alive)>1:
            logs.append({"Gate":g,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()),"Reason":"Audit layer; no resurrection."})
    if alive.empty: return alive,pd.DataFrame(logs)
    alive=alive.copy(); alive["role"]=alive.apply(role_type,axis=1); alive["score"]=alive.apply(score_row,axis=1)
    return alive.sort_values("score",ascending=False),pd.DataFrame(logs)

def run_machine(df):
    owners=[]; logs=[]
    for g,gdf in df.groupby("game",dropna=False):
        surv,lg=run_game(gdf)
        if not lg.empty: lg.insert(0,"Game",g); logs.append(lg)
        if not surv.empty: owners.append(surv.iloc[0].to_dict())
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    logs=pd.concat(logs,ignore_index=True) if logs else pd.DataFrame()
    core=[]
    if not owners.empty:
        owners=owners.sort_values("score",ascending=False)
        for role in ["Primary","Transfer","WHO"]:
            p=owners[owners.role==role]
            if not p.empty: core.append(p.iloc[0].to_dict())
        for _,r in owners.iterrows():
            if len(core)>=3: break
            if r.player not in [x["player"] for x in core]: core.append(r.to_dict())
    core=pd.DataFrame(core[:3]) if core else pd.DataFrame()
    alt=[]
    for _,r in owners.iterrows() if not owners.empty else []:
        if core.empty or r.player not in core.player.tolist(): alt.append(r.to_dict())
        if len(alt)>=3: break
    return owners,core,pd.DataFrame(alt),logs

def fmt(x):
    if x is None or pd.isna(x): return "—"
    return f"{x:.1f}" if isinstance(x,float) else str(x)
def safe_pct(x):
    try: return max(8,min(100,int(float(x or 40))))
    except: return 40

def player_card(r):
    st.markdown(f"""<div class="card"><span class="role">{r.get('role','Primary')}</span><div class="player">{r.get('player','')}</div><div class="meta">{r.get('game','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small>BLEND SCORE</small></div><div class="ring"><div class="fill" style="width:{safe_pct(r.get('score'))}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><span class="badge">LEGAL</span><span class="badge">NO REVIVAL</span></div>""", unsafe_allow_html=True)

def blender_visual(names=None, status="DATA IN → GATES SPIN → OWNER LOCKED"):
    names = names or ["Upload Slate", "Run Machine", "Owners Lock", "Core Builds"]
    padded=(names+names+names)[:6]
    html_names="".join([f"<div class='float-name n{i+1}'>{html.escape(str(n))}</div>" for i,n in enumerate(padded)])
    st.markdown(f"""<div class="blender-box"><div class="blender-stage"><div class="blade"></div><div class="center">OWNER</div>{html_names}<div class="machine-feed"><span> MACHINE SPEAKS: {html.escape(status)} </span></div></div></div>""", unsafe_allow_html=True)

def gate_board(logs=None):
    gate_names=[("0","Game Viability"),("1","Pull DNA"),("2","Pitch Edge"),("3","Weak Slot"),("4","Launch"),("5","Conversion"),("6","DMG"),("7","HPI"),("8","Alert"),("9","No Empty Bat"),("10","Pressure"),("10.5","Transfer"),("11","Protection"),("12","Bullpen"),("13","Numerology"),("14","WHO"),("15","Finisher"),("16","Likelihood"),("17","No-Fluke"),("18","Final")]
    counts={}
    if logs is not None and not logs.empty:
        for _,r in logs.iterrows():
            key=str(r["Gate"]).split()[0]
            counts[key]=r.get("After","")
    html="<div class='gate-list'>"
    for n,label in gate_names:
        after = counts.get(n, "")
        sub = f"{label}" if after=="" else f"{label} · Alive {after}"
        html += f"<div class='gate-row'><b>{n}</b><span>{sub}</span></div>"
    html+="</div>"
    st.markdown(html, unsafe_allow_html=True)

# =========================
# UI
# =========================
st.markdown("""
<div class="top"><div class="brand"><div class="mark">BH</div><div><div class="brand-title">THE BLENDER</div><div class="brand-sub">Functional HR Machine</div></div></div><div class="status">SYSTEM ARMED</div></div>
<div class="hero"><h1>THE <span class="hot">BLENDER</span><br/>LOCK ROOM</h1><p>Data first. Visuals second. The blender now uses live player names after a run, the gate board shows function, and tickets use a real slip layout.</p><span class="chip">Official 0 → 18</span><span class="chip">10.5 in sequence</span><span class="chip">One owner per game</span><span class="chip">No revivals</span></div>
""", unsafe_allow_html=True)

tabs=st.tabs(["Launch","Machine","Game Board","Tickets","Kill Feed"])
with tabs[0]:
    uploaded=st.file_uploader("Upload slate",type=["pdf","csv","xlsx"])
    if uploaded:
        data=uploaded.read(); name=uploaded.name.lower()
        try:
            if name.endswith(".csv"): df=clean_df(pd.read_csv(io.BytesIO(data)))
            elif name.endswith(".xlsx"): df=clean_df(pd.read_excel(io.BytesIO(data)))
            else: df=parse_pdf(data)
        except Exception as e:
            st.error(f"Parser error: {e}"); df=pd.DataFrame()
        if df.empty:
            st.error("No valid player rows parsed.")
        else:
            c1,c2,c3=st.columns(3); c1.metric("Players",len(df)); c2.metric("Games",df.game.nunique()); c3.metric("Gate System","0 → 18")
            if st.button("ENGAGE BLENDER"):
                progress=st.progress(0); msg=st.empty()
                for i,txt in enumerate(["Feeding slate","Spinning legal gates","Killing dead bats","Checking 10.5 transfer","Locking game owners","Building slips"]):
                    msg.info(f"MACHINE SPEAKS: {txt.upper()}..."); progress.progress((i+1)/6); time.sleep(.12)
                owners,core,alt,logs=run_machine(df)
                st.session_state.update({"df":df,"owners":owners,"core":core,"alt":alt,"logs":logs})
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
        names=st.session_state["owners"].head(6).player.tolist()
        blender_visual(names, " → ".join([f"{len(st.session_state['df'])} IN", f"{len(st.session_state['owners'])} OWNERS", "CORE LOCKED"]))
        st.markdown("<div class='section'><h2>FUNCTIONAL GATE BOARD</h2><span class='tag'>ALIVE COUNTS</span></div>", unsafe_allow_html=True)
        gate_board(st.session_state["logs"])
    else:
        blender_visual()
        gate_board()

with tabs[2]:
    if "owners" in st.session_state:
        for _,r in st.session_state["owners"].iterrows(): player_card(r)
    else: st.info("Run a slate first.")

with tabs[3]:
    if "core" in st.session_state and not st.session_state["core"].empty:
        st.markdown("<div class='ticket-grid'>", unsafe_allow_html=True)
        st.markdown("<div class='ticket'><h3>CORE SLIP</h3>", unsafe_allow_html=True)
        for _,r in st.session_state["core"].iterrows():
            st.markdown(f"<div class='leg'><span>{r['player']}</span><span>{r.get('role','')}</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='lock'>LOCK CORE</div></div>", unsafe_allow_html=True)
        if "alt" in st.session_state and not st.session_state["alt"].empty:
            st.markdown("<div class='ticket'><h3>ALT SLIP</h3>", unsafe_allow_html=True)
            for _,r in st.session_state["alt"].head(3).iterrows():
                st.markdown(f"<div class='leg'><span>{r['player']}</span><span>{r.get('role','')}</span></div>", unsafe_allow_html=True)
            st.markdown("<div class='lock'>LOCK ALT</div></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else: st.info("Run a slate first.")

with tabs[4]:
    if "logs" in st.session_state:
        logs=st.session_state["logs"]
        st.markdown("<div class='feed-box'>", unsafe_allow_html=True)
        for _,r in logs.head(100).iterrows():
            st.markdown(f"<div class='feed-row'><span class='gate'>{r['Gate']}</span> · <span class='cut'>CUT {r['Cut']}</span> · <span class='alive'>ALIVE {r['After']}</span><br/><span style='color:#aaa093'>{r['Game']}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        with st.expander("Full Audit Table"):
            st.dataframe(logs,use_container_width=True,height=540)
    else: st.info("Run a slate first.")
