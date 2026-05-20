
import re, io, time
import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Inter:wght@500;700;800;900&family=Rajdhani:wght@600;700&display=swap');

:root{
  --black:#050505; --panel:#101010; --cream:#f4ead7; --muted:#aaa093;
  --acid:#d7ff2f; --money:#00ff73; --danger:#ff264a; --orange:#ff8a00;
  --line:rgba(244,234,215,.16);
}
html, body, [class*="css"]{font-family:Inter,sans-serif}
.stApp{
  background:
    radial-gradient(circle at 20% 8%,rgba(215,255,47,.14),transparent 26%),
    radial-gradient(circle at 90% 15%,rgba(255,138,0,.12),transparent 30%),
    linear-gradient(180deg,#050505 0%,#0c0c0c 48%,#050505 100%);
  color:var(--cream);
}
.stApp:before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background:linear-gradient(rgba(244,234,215,.035) 1px,transparent 1px),
             linear-gradient(90deg,rgba(244,234,215,.035) 1px,transparent 1px);
  background-size:34px 34px;
}
.block-container{max-width:1280px;padding:1rem 1rem 5rem;position:relative;z-index:1}
h1,h2,h3,p,span,div{color:var(--cream)}

.top{
  position:sticky;top:0;z-index:999;display:flex;justify-content:space-between;align-items:center;
  background:rgba(5,5,5,.82);border:1px solid var(--line);border-radius:22px;padding:12px 14px;margin-bottom:14px;
  backdrop-filter:blur(15px);box-shadow:0 12px 40px rgba(0,0,0,.35)
}
.brand{display:flex;gap:12px;align-items:center}
.logo{
  width:58px;height:58px;border-radius:50%;display:grid;place-items:center;
  font-family:'Black Ops One';font-size:22px;color:#050505;
  background:radial-gradient(circle at 35% 35%,#fff,#d7ff2f 34%,#00ff73 72%,#141414 73%);
  box-shadow:0 0 24px rgba(215,255,47,.35),inset 0 0 8px rgba(0,0,0,.35);
  animation:spin 3.5s linear infinite;
}
@keyframes spin{to{transform:rotate(360deg)}}
.brand-title{font-family:'Black Ops One';font-size:24px;letter-spacing:.6px;line-height:1}
.brand-sub{font-family:Rajdhani;color:var(--muted);font-size:13px;font-weight:700;letter-spacing:1.3px;text-transform:uppercase}
.status{font-family:Rajdhani;font-weight:700;letter-spacing:1px;font-size:13px;padding:9px 12px;border-radius:999px;background:rgba(215,255,47,.10);border:1px solid rgba(215,255,47,.28);color:#efffc0}

.hero{
  min-height:430px;position:relative;overflow:hidden;border-radius:34px;padding:26px;margin-bottom:16px;
  border:1px solid var(--line);
  background:linear-gradient(145deg,rgba(26,26,26,.96),rgba(5,5,5,.98));
  box-shadow:0 32px 90px rgba(0,0,0,.48),inset 0 0 60px rgba(255,255,255,.025)
}
.hero-grid{display:grid;grid-template-columns:1.12fr .88fr;gap:18px;align-items:stretch}
.hero h1{font-family:'Black Ops One';font-size:clamp(48px,7vw,92px);line-height:.82;margin:0;letter-spacing:-1px}
.hero .hot{color:var(--acid);text-shadow:0 0 22px rgba(215,255,47,.28)}
.hero p{max-width:740px;color:var(--muted);font-size:15px;font-weight:800}
.chip{display:inline-block;margin:6px 6px 0 0;padding:9px 12px;border-radius:999px;background:rgba(244,234,215,.055);border:1px solid var(--line);font-family:Rajdhani;font-weight:700;letter-spacing:.8px;font-size:13px;text-transform:uppercase}
.blender-visual{
  min-height:330px;border-radius:30px;border:1px solid rgba(244,234,215,.13);
  background:radial-gradient(circle at center,rgba(215,255,47,.18),transparent 28%),
             linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.015));
  position:relative;overflow:hidden
}
.blender-visual:before{
  content:"";position:absolute;inset:50% auto auto 50%;width:240px;height:240px;margin:-120px 0 0 -120px;border-radius:50%;
  background:conic-gradient(from 0deg,transparent 0deg,rgba(215,255,47,.95) 35deg,transparent 75deg,rgba(0,255,115,.9) 135deg,transparent 180deg,rgba(255,138,0,.9) 245deg,transparent 300deg);
  animation:blade 1.05s linear infinite;
}
.blender-visual:after{
  content:"";position:absolute;inset:50% auto auto 50%;width:104px;height:104px;margin:-52px 0 0 -52px;border-radius:50%;background:#050505;border:2px solid rgba(244,234,215,.25)
}
@keyframes blade{to{transform:rotate(360deg)}}
.ticker{position:absolute;left:0;right:0;bottom:0;background:rgba(5,5,5,.82);border-top:1px solid var(--line);overflow:hidden;white-space:nowrap}
.ticker span{display:inline-block;padding:13px 0;font-family:Rajdhani;font-weight:700;letter-spacing:1.2px;color:#efffc0;animation:ticker 18s linear infinite}
@keyframes ticker{from{transform:translateX(100%)}to{transform:translateX(-100%)}}

.stTabs [data-baseweb="tab-list"]{gap:8px;background:rgba(16,16,16,.82);border:1px solid var(--line);border-radius:18px;padding:8px}
.stTabs [data-baseweb="tab"]{border-radius:13px;color:var(--cream);font-family:Rajdhani;font-size:15px;font-weight:700}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,var(--acid),var(--money))!important;color:#050505!important}
.stButton>button{min-height:66px!important;width:100%!important;border:0!important;border-radius:22px!important;font-family:'Black Ops One'!important;font-size:22px!important;color:#050505!important;background:linear-gradient(90deg,var(--acid),var(--money),var(--orange))!important}
.stFileUploader section{background:rgba(244,234,215,.045)!important;border:1px dashed rgba(215,255,47,.38)!important;border-radius:22px!important}
[data-testid="stMetric"]{background:rgba(16,16,16,.84);border:1px solid var(--line);border-radius:22px;padding:16px}
[data-testid="stMetricLabel"]{color:var(--muted);font-family:Rajdhani;font-size:15px;font-weight:700}
[data-testid="stMetricValue"]{font-family:'Black Ops One';color:var(--cream)}
.section{display:flex;justify-content:space-between;align-items:center;margin:22px 0 12px}
.section h2{font-family:'Black Ops One';margin:0;font-size:34px}
.tag{padding:9px 12px;border-radius:999px;border:1px solid var(--line);background:rgba(244,234,215,.055);font-family:Rajdhani;font-weight:700}
.gate-strip{display:flex;gap:8px;overflow-x:auto;padding:10px 0 14px}
.gate-tile{min-width:104px;height:86px;background:linear-gradient(180deg,rgba(26,26,26,.92),rgba(10,10,10,.92));border:1px solid var(--line);border-radius:18px;display:grid;place-items:center}
.gate-tile b{font-family:'Black Ops One';font-size:22px;color:var(--acid)}
.gate-tile span{font-family:Rajdhani;font-weight:700;font-size:12px;color:var(--muted);text-transform:uppercase}
.card{position:relative;overflow:hidden;min-height:292px;border-radius:28px;border:1px solid var(--line);padding:18px;background:radial-gradient(circle at 85% 10%,rgba(215,255,47,.13),transparent 34%),linear-gradient(180deg,rgba(26,26,26,.96),rgba(6,6,6,.98));box-shadow:0 22px 60px rgba(0,0,0,.43)}
.card:before{content:"";position:absolute;inset:0 0 auto 0;height:7px;background:linear-gradient(90deg,var(--acid),var(--money),var(--orange))}
.role{display:inline-block;padding:7px 10px;border-radius:999px;border:1px solid var(--line);background:rgba(244,234,215,.06);font-family:Rajdhani;font-size:14px;font-weight:700;text-transform:uppercase}
.player{font-family:'Black Ops One';font-size:31px;line-height:1.02;margin:15px 0 5px}
.meta{color:var(--muted);font-family:Rajdhani;font-size:15px;font-weight:700;min-height:38px}
.score{font-family:'Black Ops One';font-size:44px;min-width:120px}
.score small{display:block;font-family:Rajdhani;color:var(--muted);font-size:12px}
.ring{height:13px;border-radius:999px;overflow:hidden;background:rgba(244,234,215,.09);margin-top:10px}
.fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--acid),var(--money),var(--orange))}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px}
.stat{border:1px solid rgba(244,234,215,.10);background:rgba(244,234,215,.045);border-radius:15px;padding:9px}
.stat b{display:block;font-size:16px}.stat span{display:block;font-family:Rajdhani;color:var(--muted);font-weight:700;font-size:11px;text-transform:uppercase}
.badge{display:inline-block;margin:10px 5px 0 0;padding:6px 8px;border-radius:999px;background:rgba(215,255,47,.10);border:1px solid rgba(215,255,47,.24);color:#efffc0;font-family:Rajdhani;font-weight:700;font-size:12px}
.feed{background:rgba(16,16,16,.88);border:1px solid var(--line);border-radius:22px;padding:14px}
.feed-row{padding:10px;border-bottom:1px solid rgba(244,234,215,.08);font-family:Rajdhani}
.feed-row:last-child{border-bottom:0}.feed-gate{color:var(--acid);font-weight:700}.feed-cut{color:var(--danger);font-weight:700}.feed-alive{color:var(--money);font-weight:700}
div[data-testid="stExpander"]{background:rgba(16,16,16,.82)!important;border:1px solid var(--line)!important;border-radius:20px!important}
div[data-testid="stDataFrame"]{border-radius:18px;overflow:hidden;border:1px solid var(--line)}
@media(max-width:850px){.hero-grid{grid-template-columns:1fr}.blender-visual{min-height:250px}}
</style>
""", unsafe_allow_html=True)

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
def card(r):
    st.markdown(f"""<div class="card"><span class="role">{r.get('role','Primary')}</span><div class="player">{r.get('player','')}</div><div class="meta">{r.get('game','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small>BLEND SCORE</small></div><div class="ring"><div class="fill" style="width:{safe_pct(r.get('score'))}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><span class="badge">LEGAL</span><span class="badge">NO REVIVAL</span></div>""", unsafe_allow_html=True)
def gate_strip():
    gates=["0","1","2","3","4","5","6","7","8","9","10","10.5","11","12","13","14","15","16","17","18"]
    html="<div class='gate-strip'>"
    for g in gates: html+=f"<div class='gate-tile'><b>{g}</b><span>gate</span></div>"
    html+="</div>"; st.markdown(html, unsafe_allow_html=True)

st.markdown("""<div class="top"><div class="brand"><div class="logo">BH</div><div><div class="brand-title">THE BLENDER</div><div class="brand-sub">Proprietary HR Machine</div></div></div><div class="status">SYSTEM ARMED</div></div><div class="hero"><div class="hero-grid"><div><h1>THE <span class="hot">BLENDER</span><br/>LOCK ROOM</h1><p>This is the machine view: upload slate, engage Blender, watch legal game owners become Core / Alt through the 18-gate system.</p><div><span class="chip">18 gates total</span><span class="chip">10.5 included</span><span class="chip">one owner per game</span><span class="chip">no revivals</span></div></div><div class="blender-visual"><div class="ticker"><span> MACHINE SPEAKS: DATA IN → GATES SPIN → DEAD IS DEAD → OWNER LOCKED → CORE BUILT </span></div></div></div></div>""", unsafe_allow_html=True)
gate_strip()
tabs=st.tabs(["Launch","Game Board","Tickets","Kill Feed"])
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
        if df.empty: st.error("No valid player rows parsed.")
        else:
            c1,c2,c3=st.columns(3); c1.metric("Players",len(df)); c2.metric("Games",df.game.nunique()); c3.metric("Gates","18")
            if st.button("ENGAGE BLENDER"):
                progress=st.progress(0); msg=st.empty()
                for i,txt in enumerate(["Feeding slate","Spinning gates","Killing dead bats","Checking 10.5","Locking owners","Building Core"]):
                    msg.info(f"MACHINE SPEAKS: {txt.upper()}..."); progress.progress((i+1)/6); time.sleep(.12)
                owners,core,alt,logs=run_machine(df)
                st.session_state.update({"df":df,"owners":owners,"core":core,"alt":alt,"logs":logs})
                msg.success("MACHINE COMPLETE — FINAL BOARD READY")
            with st.expander("Parsed Slate Preview"):
                st.dataframe(df,use_container_width=True,height=360)
    if "core" in st.session_state:
        st.markdown("<div class='section'><h2>CORE 3</h2><span class='tag'>ROLE BALANCED</span></div>",unsafe_allow_html=True)
        cols=st.columns(3)
        for i,(_,r) in enumerate(st.session_state["core"].iterrows()):
            with cols[i]: card(r)
        st.markdown("<div class='section'><h2>ALT 3</h2><span class='tag'>LEGAL BACKUPS</span></div>",unsafe_allow_html=True)
        if not st.session_state["alt"].empty:
            cols=st.columns(3)
            for i,(_,r) in enumerate(st.session_state["alt"].head(3).iterrows()):
                with cols[i]: card(r)
with tabs[1]:
    if "owners" in st.session_state:
        for _,r in st.session_state["owners"].iterrows(): card(r)
    else: st.info("Run a slate first.")
with tabs[2]:
    if "core" in st.session_state and not st.session_state["core"].empty:
        st.code(" + ".join(st.session_state["core"].player.tolist()))
        if "alt" in st.session_state and not st.session_state["alt"].empty:
            st.code("ALT: " + " + ".join(st.session_state["alt"].head(3).player.tolist()))
    else: st.info("Run a slate first.")
with tabs[3]:
    if "logs" in st.session_state:
        logs=st.session_state["logs"]
        st.markdown("<div class='feed'>",unsafe_allow_html=True)
        for _,r in logs.head(60).iterrows():
            st.markdown(f"<div class='feed-row'><span class='feed-gate'>{r['Gate']}</span> · <span class='feed-cut'>CUT {r['Cut']}</span> · <span class='feed-alive'>ALIVE {r['After']}</span><br/><span style='color:#aaa093'>{r['Game']}</span></div>",unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)
        with st.expander("Full Audit Table"):
            st.dataframe(logs,use_container_width=True,height=540)
    else: st.info("Run a slate first.")
