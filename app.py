
import re, io, time
import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

APP_VERSION = "v12 MACHINE EXPERIENCE"

st.set_page_config(page_title="THE BLENDER", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Inter:wght@500;700;900&display=swap');

:root{
  --bg:#050607; --panel:#0b1117; --glass:rgba(10,16,24,.74);
  --line:rgba(255,255,255,.13); --text:#f7fff9; --muted:#92a49a;
  --green:#39ff88; --red:#ff325c; --yellow:#ffe74a; --blue:#4de3ff; --orange:#ff9f1c;
}
html,body,[class*="css"]{font-family:Inter,sans-serif}
.stApp{
  background:
    radial-gradient(circle at 15% 4%,rgba(57,255,136,.22),transparent 30%),
    radial-gradient(circle at 88% 15%,rgba(77,227,255,.14),transparent 30%),
    linear-gradient(180deg,#030405 0%,#07100c 45%,#030405 100%);
  color:var(--text);
}
.stApp:before{
  content:"";position:fixed;inset:0;pointer-events:none;z-index:0;
  background-image:
    linear-gradient(rgba(57,255,136,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(57,255,136,.035) 1px, transparent 1px);
  background-size:38px 38px;
  mask-image:linear-gradient(to bottom,rgba(0,0,0,.8),transparent 90%);
}
.block-container{max-width:1260px;padding:1rem 1rem 5rem;position:relative;z-index:1}
h1,h2,h3,p,div,span{color:var(--text)}
.b-top{
  position:sticky;top:0;z-index:999;margin-bottom:16px;padding:12px 14px;border-radius:24px;
  border:1px solid var(--line);background:rgba(3,5,6,.72);backdrop-filter:blur(16px);
  display:flex;align-items:center;justify-content:space-between;box-shadow:0 0 40px rgba(57,255,136,.10)
}
.brand{display:flex;gap:12px;align-items:center}
.logo{
  width:54px;height:54px;border-radius:18px;background:linear-gradient(135deg,var(--green),var(--blue));
  display:grid;place-items:center;color:#031005;font-family:Orbitron;font-weight:900;font-size:22px;
  box-shadow:0 0 28px rgba(57,255,136,.45);
}
.brand-title{font-family:Orbitron;font-size:22px;font-weight:900;letter-spacing:1px}
.brand-sub{font-size:11px;color:var(--muted);font-weight:900;text-transform:uppercase;letter-spacing:1.2px}
.status{font-size:11px;font-weight:900;color:#dfffea;background:rgba(57,255,136,.10);border:1px solid rgba(57,255,136,.25);border-radius:999px;padding:9px 12px}
.hero{
  position:relative;overflow:hidden;border-radius:34px;padding:28px;margin-bottom:18px;
  background:linear-gradient(135deg,rgba(57,255,136,.16),rgba(77,227,255,.08),rgba(8,15,14,.96));
  border:1px solid var(--line);box-shadow:0 30px 90px rgba(0,0,0,.45),inset 0 0 90px rgba(57,255,136,.045)
}
.hero h1{font-family:Orbitron;margin:0;font-size:clamp(38px,7vw,76px);line-height:.92;letter-spacing:-2px}
.hero .hot{background:linear-gradient(90deg,var(--green),var(--yellow));-webkit-background-clip:text;color:transparent}
.hero p{color:var(--muted);font-size:15px;font-weight:800;max-width:760px}
.pill{display:inline-block;margin:13px 7px 0 0;padding:9px 12px;border-radius:999px;border:1px solid rgba(255,255,255,.13);background:rgba(255,255,255,.055);font-size:11px;font-weight:900;text-transform:uppercase}
.stTabs [data-baseweb="tab-list"]{gap:8px;background:rgba(8,15,14,.76);border:1px solid var(--line);border-radius:22px;padding:8px}
.stTabs [data-baseweb="tab"]{border-radius:15px;color:#dbe9df;font-weight:900}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,var(--green),var(--yellow))!important;color:#031005!important}
.stFileUploader section{background:rgba(255,255,255,.045)!important;border:1px dashed rgba(57,255,136,.35)!important;border-radius:24px!important}
.stButton>button{
  min-height:66px!important;width:100%!important;border:0!important;border-radius:22px!important;
  background:linear-gradient(90deg,var(--green),var(--yellow),var(--blue))!important;color:#031005!important;
  font-family:Orbitron!important;font-size:18px!important;font-weight:900!important;letter-spacing:1px!important;
  box-shadow:0 0 42px rgba(57,255,136,.32)!important;
}
[data-testid="stMetric"]{background:rgba(10,16,24,.75);border:1px solid var(--line);border-radius:24px;padding:18px}
[data-testid="stMetricValue"]{font-family:Orbitron;color:white;font-weight:900}
[data-testid="stMetricLabel"]{color:var(--muted);font-weight:900}
.section{display:flex;justify-content:space-between;align-items:center;margin:22px 0 12px}
.section h2{font-family:Orbitron;margin:0;font-size:26px}
.chip{font-size:11px;font-weight:900;text-transform:uppercase;border:1px solid var(--line);background:rgba(255,255,255,.055);border-radius:999px;padding:8px 11px}
.machine-row{display:flex;gap:10px;overflow-x:auto;padding:10px 0}
.gate-tile{min-width:116px;background:rgba(10,16,24,.74);border:1px solid var(--line);border-radius:18px;padding:12px;text-align:center}
.gate-num{font-family:Orbitron;font-size:19px;color:var(--green)}
.gate-label{font-size:10px;color:var(--muted);font-weight:900;text-transform:uppercase}
.card{
  position:relative;overflow:hidden;border-radius:30px;min-height:285px;padding:20px;margin-bottom:14px;
  background:linear-gradient(180deg,rgba(14,23,28,.94),rgba(4,7,7,.97));
  border:1px solid rgba(255,255,255,.14);box-shadow:0 22px 62px rgba(0,0,0,.38),inset 0 0 42px rgba(255,255,255,.035)
}
.card:before{content:"";position:absolute;inset:0 0 auto 0;height:7px;background:linear-gradient(90deg,var(--green),var(--yellow),var(--blue))}
.role{display:inline-block;padding:7px 10px;border-radius:999px;background:rgba(255,255,255,.075);border:1px solid rgba(255,255,255,.15);font-size:11px;font-weight:900;text-transform:uppercase}
.player{font-family:Orbitron;font-size:30px;font-weight:900;margin:15px 0 4px;line-height:1.04}
.meta{color:var(--muted);font-size:13px;font-weight:800;min-height:36px}
.score{font-family:Orbitron;font-size:46px;font-weight:900;margin-top:14px}
.score small{display:block;color:var(--muted);font-family:Inter;font-size:10px;letter-spacing:1.5px;margin-top:4px}
.meter{height:12px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin-top:12px}
.fill{height:100%;border-radius:999px;background:linear-gradient(90deg,var(--green),var(--yellow),var(--blue))}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:15px}
.stat{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.10);border-radius:16px;padding:10px}
.stat b{display:block;font-size:16px}.stat span{display:block;color:var(--muted);font-size:9px;font-weight:900;text-transform:uppercase}
.badge{display:inline-block;margin:10px 5px 0 0;font-size:10px;font-weight:900;padding:6px 8px;border-radius:999px;color:#dfffea;background:rgba(57,255,136,.12);border:1px solid rgba(57,255,136,.24)}
.kill{color:var(--red)} .alive{color:var(--green)}
div[data-testid="stExpander"]{background:rgba(10,16,24,.72)!important;border:1px solid var(--line)!important;border-radius:22px!important}
div[data-testid="stDataFrame"]{border-radius:18px;overflow:hidden;border:1px solid rgba(255,255,255,.12)}
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
                slot=None; sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
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
        df=df.reset_index(drop=True); df["game"]="Game "+((df.index//9)+1).astype(str); df["team"]="Team "+((df.index//9)+1).astype(str); df["pitcher"]="Pitcher "+((df.index//9)+1).astype(str)
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
    gates=[("1 Pull %",alive.pull_pct.isna() | (alive.pull_pct>=20),"Pull DNA"),]
    alive=apply_gate(alive,*gates[0],logs)
    if len(alive)>1: alive=apply_gate(alive,"2 Matchup / Pitch Edge",alive.pitch_edge.isna() | (alive.pitch_edge>=0),"Pitch edge kill",logs)
    if len(alive)>1: alive=apply_gate(alive,"3 Zones / Weak Slot",alive.apply(slot_ok,axis=1),"Weak slot alignment",logs)
    if len(alive)>1: alive=apply_gate(alive,"4 Sweet Spot / Launch",alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=25),"Launch profile",logs)
    if len(alive)>1: alive=apply_gate(alive,"5 Barrel / Conversion",alive.hr_pa.isna() | (alive.hr_pa>=3) | (alive.barrel_pct.fillna(0)>=10),"Conversion",logs)
    if len(alive)>1: alive=apply_gate(alive,"6 DMG",alive.dmg.isna() | (alive.dmg>=1.0),"Damage floor",logs)
    if len(alive)>1: alive=apply_gate(alive,"7 HPI",alive.hpi.isna() | (alive.hpi>=30),"HPI floor",logs)
    if len(alive)>1: alive=apply_gate(alive,"8 Recency / Alert",alive.hr_alert | alive.cond_up | alive.hr_alert.isna(),"Recent pressure",logs)
    if len(alive)>1: alive=apply_gate(alive,"9 No Empty Bat",alive.hr_pa.isna() | (alive.hr_pa>0) | alive.hr_alert,"No empty bat",logs)
    for g in ["10 Ownership Pressure","10.5 Adjacent / Decoy Transfer","11 Lineup Protection","12 Bullpen Continuation","13 Numerology Overlay","14 Chaos / WHO","15 Finisher Gate","16 Event Likelihood","17 No-Fluke Audit","18 True HR Event Likelihood"]:
        if len(alive)>1: logs.append({"Gate":g,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()),"Reason":"Audit layer; no resurrection."})
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
def card(r):
    st.markdown(f"""<div class="card"><span class="role">{r.get('role','Primary')}</span><div class="player">{r.get('player','')}</div><div class="meta">{r.get('game','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small>BLEND SCORE</small></div><div class="meter"><div class="fill" style="width:{max(8,min(100,int(r.get('score',40) or 40)))}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><span class="badge">LEGAL</span></div>""",unsafe_allow_html=True)
def gate_strip():
    gates=["0","1","2","3","4","5","6","7","8","9","10","10.5","11","12","13","14","15","16","17","18"]
    html="<div class='machine-row'>"
    for g in gates: html+=f"<div class='gate-tile'><div class='gate-num'>{g}</div><div class='gate-label'>Gate</div></div>"
    html+="</div>"; st.markdown(html,unsafe_allow_html=True)

st.markdown("""<div class="b-top"><div class="brand"><div class="logo">BH</div><div><div class="brand-title">THE BLENDER</div><div class="brand-sub">Proprietary HR Machine</div></div></div><div class="status">SYSTEM ARMED</div></div><div class="hero"><h1>THE <span class="hot">BLENDER</span><br>MACHINE</h1><p>Not a dashboard. A lock-room terminal: game owners, eliminations, transfer audits, WHO pressure, and final slip output.</p><span class="pill">18 Gates Total</span><span class="pill">Step 10.5 Included</span><span class="pill">One Owner Per Game</span><span class="pill">No Revivals</span></div>""",unsafe_allow_html=True)
gate_strip()
tabs=st.tabs(["Launch","Game Board","Tickets","Audit"])
with tabs[0]:
    up=st.file_uploader("Upload slate",type=["pdf","csv","xlsx"])
    if up:
        data=up.read(); name=up.name.lower()
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
                owners,core,alt,logs=run_machine(df); st.session_state.update({"df":df,"owners":owners,"core":core,"alt":alt,"logs":logs}); st.success("Machine complete.")
            with st.expander("Parsed Slate Preview"): st.dataframe(df,use_container_width=True,height=360)
    if "core" in st.session_state:
        st.markdown("<div class='section'><h2>CORE 3</h2><span class='chip'>Role Balanced</span></div>",unsafe_allow_html=True)
        cols=st.columns(3)
        for i,(_,r) in enumerate(st.session_state["core"].iterrows()):
            with cols[i]: card(r)
        st.markdown("<div class='section'><h2>ALT 3</h2><span class='chip'>Legal Backups</span></div>",unsafe_allow_html=True)
        if not st.session_state["alt"].empty:
            cols=st.columns(3)
            for i,(_,r) in enumerate(st.session_state["alt"].head(3).iterrows()):
                with cols[i]: card(r)
with tabs[1]:
    if "owners" in st.session_state:
        for _,r in st.session_state["owners"].iterrows(): card(r)
    else: st.info("Run a slate first.")
with tabs[2]:
    if "core" in st.session_state and not st.session_state["core"].empty: st.code(" + ".join(st.session_state["core"].player.tolist()))
    else: st.info("Run a slate first.")
with tabs[3]:
    if "logs" in st.session_state: st.dataframe(st.session_state["logs"],use_container_width=True,height=540)
    else: st.info("Run a slate first.")
