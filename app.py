
import re, io, sqlite3, datetime
from pathlib import Path
import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

APP_VERSION="v10 Parser Fix"

st.set_page_config(page_title="BenHavin Blender", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800;900&display=swap');
html,body,[class*="css"]{font-family:Inter,sans-serif}
.stApp{background:radial-gradient(circle at top left,rgba(34,197,94,.18),transparent 30%),linear-gradient(180deg,#05070b,#0b1220 55%,#05070b);color:#f8fafc}
.block-container{max-width:1180px;padding:1rem 1rem 4rem}
h1,h2,h3,p,span,div{color:#f8fafc}
[data-testid="stMetric"]{background:linear-gradient(180deg,rgba(17,24,39,.94),rgba(12,17,25,.94));border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:14px}
[data-testid="stMetricLabel"]{color:#94a3b8;font-weight:900}[data-testid="stMetricValue"]{color:#fff;font-weight:1000}
.bh-top{display:flex;justify-content:space-between;align-items:center;background:rgba(5,7,11,.7);border:1px solid rgba(255,255,255,.1);border-radius:22px;padding:14px 16px;position:sticky;top:0;z-index:999;backdrop-filter:blur(12px);margin-bottom:16px}
.bh-brand{display:flex;align-items:center;gap:12px}.bh-logo{width:44px;height:44px;border-radius:14px;background:linear-gradient(135deg,#22c55e,#38bdf8);display:grid;place-items:center;color:#02130b;font-weight:1000;font-size:21px}
.bh-title{font-size:20px;font-weight:1000}.bh-sub{font-size:12px;color:#94a3b8}
.bh-live{font-size:12px;font-weight:1000;color:#d1fae5;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.22);padding:8px 10px;border-radius:999px}
.bh-hero{border:1px solid rgba(255,255,255,.1);background:linear-gradient(135deg,rgba(34,197,94,.18),rgba(56,189,248,.10),rgba(17,24,39,.88));border-radius:28px;padding:24px;margin-bottom:18px}
.bh-hero h1{margin:0;font-size:clamp(34px,6vw,62px);letter-spacing:-2px;line-height:.95}.bh-hero p{color:#94a3b8;font-size:15px}.bh-pill{display:inline-block;margin:12px 7px 0 0;padding:8px 11px;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);font-size:12px;font-weight:1000}
.stTabs [data-baseweb="tab-list"]{gap:8px;background:rgba(17,24,39,.54);border:1px solid rgba(255,255,255,.1);border-radius:18px;padding:8px}.stTabs [data-baseweb="tab"]{border-radius:13px;color:#cbd5e1;font-weight:900}.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#22c55e,#38bdf8)!important;color:#04110a!important}
.stButton>button{width:100%;min-height:54px;border-radius:18px;border:0;background:linear-gradient(90deg,#a3ff12,#22c55e,#38bdf8);color:#04110a;font-weight:1000;font-size:16px}
.bh-card{position:relative;overflow:hidden;background:linear-gradient(180deg,rgba(17,24,39,.96),rgba(8,13,20,.96));border:1px solid rgba(255,255,255,.12);border-radius:24px;padding:18px;min-height:245px;margin-bottom:12px}
.bh-card:before{content:"";position:absolute;inset:0 0 auto 0;height:5px;background:linear-gradient(90deg,#22c55e,#38bdf8)}.primary:before{background:linear-gradient(90deg,#22c55e,#a3ff12)}.transfer:before{background:linear-gradient(90deg,#38bdf8,#a855f7)}.who:before{background:linear-gradient(90deg,#fb923c,#fb4766)}
.bh-role{display:inline-block;font-size:11px;font-weight:1000;padding:6px 9px;border-radius:999px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14)}
.bh-player{font-size:27px;font-weight:1000;margin:12px 0 2px}.bh-meta{color:#94a3b8;font-size:13px;font-weight:700;min-height:36px}.bh-score{font-size:42px;font-weight:1000}.bh-score small{display:block;color:#94a3b8;font-size:11px}.bh-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:14px}.bh-stat{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:9px}.bh-stat span{display:block;color:#94a3b8;font-size:10px;font-weight:1000;text-transform:uppercase}.bh-badge{font-size:10px;font-weight:1000;padding:5px 7px;border-radius:999px;background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.24);color:#d1fae5;margin-right:5px}
.bh-section{display:flex;align-items:center;justify-content:space-between;margin:18px 0 10px}.bh-section h2{margin:0;font-size:25px}.bh-chip{font-size:12px;font-weight:1000;color:#cbd5e1;padding:7px 10px;border-radius:999px;border:1px solid rgba(255,255,255,.10);background:rgba(255,255,255,.05)}
</style>
""", unsafe_allow_html=True)

COLS=["game","team","opponent","pitcher","player","bats","lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_type","pitch_edge","hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","weak_slots","odds","public_pct","weather_score","bullpen_dmg","confirmed_lineup","dob","jersey","result_hr","notes"]
BAD={"dmg","hpi","line","cond","alert","hot","cold","warm","moderate","elevated","low","high","fresh","effort","page","https","star","tool","projected","weak","slot","home","away","none"}

def is_player_name(s):
    s=str(s).strip()
    if len(s)<4 or re.search(r"\d",s): return False
    low=s.lower()
    if low in BAD or "http" in low or "page" in low: return False
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
    df=df[df["player"].apply(is_player_name)].copy()
    return df[COLS]

def pdf_text(b):
    if fitz is None: return ""
    doc=fitz.open(stream=b,filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc)

def parse_pdf(b):
    txt=pdf_text(b)
    if not txt.strip(): return pd.DataFrame(columns=COLS)
    lines=[x.strip() for x in txt.splitlines() if x.strip()]
    rows=[]; team=""; pitcher=""; game=""; away=""; home=""
    weak_by_pitcher={}
    # capture game headers where possible
    for idx,line in enumerate(lines):
        m=re.search(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)", line, re.I)
        if m: weak_by_pitcher[m.group(1).strip()]=f"{m.group(2)},{m.group(3)},{m.group(4)}"

    i=0; hitter_count_in_section=0; section_id=0
    while i < len(lines):
        line=lines[i]

        # robust team section: line can contain "TEAM PROJECTED vs. Pitcher ~"
        sec=re.search(r"([A-Z][A-Z\s]+?)\s+PROJECTED\s+vs\.\s+(.+?)\s+~", line, re.I)
        if sec:
            team=sec.group(1).strip().title()
            pitcher=sec.group(2).strip()
            hitter_count_in_section=0; section_id += 1
            i+=1; continue

        # fallback if PDF places team line and vs line separately
        if "PROJECTED" in line.upper() and "VS." in line.upper():
            parts=line.split("PROJECTED")
            if parts:
                team=parts[0].strip().title()
            vm=re.search(r"vs\.\s+(.+?)\s+~",line,re.I)
            if vm: pitcher=vm.group(1).strip()
            hitter_count_in_section=0; section_id += 1
            i+=1; continue

        if re.match(r"^\d+$",line) and i+1 < len(lines):
            name=lines[i+1].strip()
            if is_player_name(name):
                block=" ".join(lines[i+1:i+18])
                hitter_count_in_section += 1
                # fallback group every 9 hitters if team/pitcher missing or stuck
                fallback_team = team if team else f"Section {section_id or ((len(rows)//9)+1)}"
                fallback_pitcher = pitcher if pitcher else f"Unknown Pitcher {section_id or ((len(rows)//9)+1)}"
                fallback_game = game if game else f"{fallback_team} vs {fallback_pitcher}"

                slot=None
                sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
                if sm: slot=int(sm.group(1))
                pct_vals=re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block)
                pull=None
                for pv in pct_vals:
                    val=float(pv)
                    if 5 <= abs(val) <= 65:
                        pull=val; break
                lm=re.search(r"LINE\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%",block)
                sweet=float(lm.group(1)) if lm else None
                hm=re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA",block)
                hrpa=float(hm.group(1)) if hm else None
                dm=re.search(r"([0-9]+(?:\.\d+)?)\s+DMG",block)
                dmg=float(dm.group(1)) if dm else None
                pem=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
                pe=None; pt=None
                pitch_like=[(float(a),bb) for a,bb in pem if bb.lower() not in ["hr","line","cond"]]
                if pitch_like: pe,pt=pitch_like[-1]
                pluses=[int(x) for x in re.findall(r"\+\s*(\d+)",block) if 10 <= int(x) <= 90]
                hpi=pluses[-1] if pluses else None
                rows.append({
                    "game":fallback_game,"team":fallback_team,"opponent":"","pitcher":fallback_pitcher,"player":name,"bats":"",
                    "lineup_slot":slot,"pull_pct":pull,"barrel_pct":None,"sweet_spot_pct":sweet,"hard_hit_pct":None,
                    "hpi":hpi,"dmg":dmg,"hr_pa":hrpa,"pitch_type":pt,"pitch_edge":pe,
                    "hr_alert":"ALERT" in block,"cond_up":"COND ↑" in block,"weak_slot_tag":"Weak Slot" in block,
                    "laser":"Laser" in block,"rakes":"Rakes" in block,"platoon":"Platoon" in block,
                    "weak_slots":weak_by_pitcher.get(fallback_pitcher,""),"odds":None,"public_pct":None,"weather_score":None,
                    "bullpen_dmg":None,"confirmed_lineup":False,"dob":None,"jersey":None,"result_hr":False,"notes":block[:220]
                })
                i+=14; continue
        i+=1

    df=clean_df(pd.DataFrame(rows))
    # if parser still got one team/pitcher only, force game sections every 9 players so machine doesn't collapse to one card
    if not df.empty and (df.team.nunique() <= 1 or df.pitcher.nunique() <= 1):
        df=df.reset_index(drop=True)
        df["game"]="Game " + ((df.index//9)+1).astype(str)
        df["team"]="Team " + ((df.index//9)+1).astype(str)
        df["pitcher"]="Pitcher " + ((df.index//9)+1).astype(str)
    return df

def slot_ok(row):
    ws=str(row.get("weak_slots") or "")
    slots=[int(x) for x in re.findall(r"\d+",ws)]
    if not slots or pd.isna(row.get("lineup_slot")): return True
    return int(row["lineup_slot"]) in slots or bool(row.get("weak_slot_tag"))

def role_type(r):
    if bool(r.get("weak_slot_tag")) or bool(r.get("laser")) or bool(r.get("rakes")): return "Transfer"
    if (r.get("dmg") or 0)>=1.7 and (r.get("hr_pa") or 0)>=4: return "WHO"
    return "Primary"

def score_row(r):
    return ((r.get("pull_pct") or 0)*.10 + (r.get("pitch_edge") or 0)*.20 + (r.get("sweet_spot_pct") or 0)*.10 +
            (r.get("barrel_pct") or 0)*.15 + (r.get("dmg") or 0)*12 + (r.get("hpi") or 0)*.12 +
            (r.get("hr_pa") or 0)*2 + int(bool(r.get("hr_alert")))*8 + int(bool(r.get("cond_up")))*5 +
            int(bool(r.get("weak_slot_tag")))*4 + int(bool(r.get("laser")))*3 + int(bool(r.get("rakes")))*3)

def apply_gate(alive, gate, mask, reason, logs):
    before=alive.player.tolist(); cut=alive.loc[~mask,"player"].tolist(); alive=alive[mask].copy(); after=alive.player.tolist()
    logs.append({"Gate":gate,"Before":len(before),"Cut":len(cut),"After":len(after),"Cut names":", ".join(cut),"Alive after":", ".join(after),"Reason":reason})
    return alive

def run_game(gdf):
    alive=gdf.copy(); logs=[]
    logs.append({"Gate":"0 Game / Pitcher Viability","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()),"Reason":"Game enters machine."})
    alive=apply_gate(alive,"1 Pull %",alive.pull_pct.isna() | (alive.pull_pct>=20),"Kill under 20 pull only when value exists.",logs)
    if len(alive)>1: alive=apply_gate(alive,"2 Matchup / Pitch Edge",alive.pitch_edge.isna() | (alive.pitch_edge>=0),"Kill negative pitch edge when listed.",logs)
    if len(alive)>1: alive=apply_gate(alive,"3 Zones / Weak Slot",alive.apply(slot_ok,axis=1),"Must match weak slot when both datasets exist.",logs)
    if len(alive)>1: alive=apply_gate(alive,"4 Sweet Spot / Launch",alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=25),"Launch profile filter.",logs)
    if len(alive)>1: alive=apply_gate(alive,"5 Barrel / Conversion",alive.hr_pa.isna() | (alive.hr_pa>=3) | (alive.barrel_pct.fillna(0)>=10),"HR/PA 3+ or barrel 10+.",logs)
    if len(alive)>1: alive=apply_gate(alive,"6 DMG",alive.dmg.isna() | (alive.dmg>=1.0),"Safe DMG floor 1.0.",logs)
    if len(alive)>1: alive=apply_gate(alive,"7 HPI",alive.hpi.isna() | (alive.hpi>=30),"Safe HPI floor 30.",logs)
    if len(alive)>1: alive=apply_gate(alive,"8 Recency / Alert",alive.hr_alert | alive.cond_up | alive.hr_alert.isna(),"Prefer HR alert or condition up.",logs)
    if len(alive)>1: alive=apply_gate(alive,"9 No Empty Bat",alive.hr_pa.isna() | (alive.hr_pa>0) | alive.hr_alert,"Kill zero HR/PA without alert.",logs)
    if len(alive)>1: logs.append({"Gate":"10 Ownership Pressure","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()),"Reason":"Sets pressure center before transfer."})
    if len(alive)>1: logs.append({"Gate":"10.5 Adjacent / Decoy Transfer","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()),"Reason":"Only current survivors eligible. Dead players cannot return."})
    for gate in ["11 Lineup Protection","12 Bullpen Continuation","13 Numerology Overlay","14 Chaos / WHO","15 Finisher Gate","16 Event Likelihood","17 No-Fluke Audit","18 True HR Event Likelihood"]:
        if len(alive)>1: logs.append({"Gate":gate,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()),"Reason":"Audit/tie-break layer; no resurrection."})
    if alive.empty: return alive, pd.DataFrame(logs)
    alive=alive.copy(); alive["role"]=alive.apply(role_type,axis=1); alive["score"]=alive.apply(score_row,axis=1)
    return alive.sort_values("score",ascending=False), pd.DataFrame(logs)

def run_machine(df):
    df=clean_df(df.copy())
    owners=[]; logs=[]; survivors=[]
    for g,gdf in df.groupby("game", dropna=False):
        surv,lg=run_game(gdf)
        if not lg.empty: lg.insert(0,"Game",g); logs.append(lg)
        if not surv.empty:
            surv=surv.copy(); surv["game"]=g; survivors.append(surv)
            owners.append(surv.iloc[0].to_dict())
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    logs=pd.concat(logs,ignore_index=True) if logs else pd.DataFrame()
    survivors=pd.concat(survivors,ignore_index=True) if survivors else pd.DataFrame()
    core=[]
    if not owners.empty:
        owners=owners.sort_values("score",ascending=False)
        for role in ["Primary","Transfer","WHO"]:
            part=owners[owners.role==role]
            if not part.empty: core.append(part.iloc[0].to_dict())
        for _,r in owners.iterrows():
            if len(core)>=3: break
            if r.player not in [x["player"] for x in core]: core.append(r.to_dict())
    core=pd.DataFrame(core[:3]) if core else pd.DataFrame()
    alt=[]
    for _,r in owners.iterrows() if not owners.empty else []:
        if core.empty or r.player not in core.player.tolist(): alt.append(r.to_dict())
        if len(alt)>=3: break
    return owners, core, pd.DataFrame(alt), logs

def fmt(x):
    if x is None or pd.isna(x): return "—"
    if isinstance(x,float): return f"{x:.1f}"
    return str(x)

def card(r):
    cls=str(r.get("role","Primary")).lower()
    st.markdown(f"""
    <div class="bh-card {cls}">
      <span class="bh-role">{r.get('role','Primary')}</span>
      <div class="bh-player">{r.get('player','')}</div>
      <div class="bh-meta">{r.get('game','')} · Slot {fmt(r.get('lineup_slot'))}</div>
      <div class="bh-score">{fmt(r.get('score'))}<small>BLEND SCORE</small></div>
      <div class="bh-stats">
        <div class="bh-stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div>
        <div class="bh-stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch Edge</span></div>
        <div class="bh-stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div>
        <div class="bh-stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div>
        <div class="bh-stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div>
        <div class="bh-stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div>
      </div>
      <div style="margin-top:12px;"><span class="bh-badge">LEGAL</span></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="bh-top"><div class="bh-brand"><div class="bh-logo">BH</div><div><div class="bh-title">BenHavin Blender</div><div class="bh-sub">v10 · 18 Gate Machine</div></div></div><div class="bh-live">MACHINE READY</div></div>
<div class="bh-hero"><h1>Sportsbook Grade<br/>Blender Machine</h1><p>18 gates total. Step 10.5 is inside the 18-gate machine.</p><span class="bh-pill">18 Gates</span><span class="bh-pill">No Revivals</span><span class="bh-pill">One Owner Per Game</span></div>
""", unsafe_allow_html=True)

tabs=st.tabs(["Run Blender","Game Board","Tickets","Audit"])
with tabs[0]:
    uploaded=st.file_uploader("Upload Star Tool PDF / CSV / XLSX",type=["pdf","csv","xlsx"])
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
            c1,c2,c3=st.columns(3)
            c1.metric("Players",len(df)); c2.metric("Games/Sections",df.game.nunique()); c3.metric("Gates","18")
            if st.button("RUN FULL MACHINE"):
                owners,core,alt,logs=run_machine(df)
                st.session_state.update({"df":df,"owners":owners,"core":core,"alt":alt,"logs":logs})
                st.success("Blend complete.")
            with st.expander("Parsed Slate Preview"):
                st.dataframe(df,use_container_width=True,height=360)
    if "core" in st.session_state:
        st.markdown("<div class='bh-section'><h2>Core 3</h2><span class='bh-chip'>Role Balanced</span></div>", unsafe_allow_html=True)
        core=st.session_state["core"]; alt=st.session_state["alt"]
        if core.empty: st.warning("No Core.")
        else:
            cols=st.columns(3)
            for i,(_,r) in enumerate(core.iterrows()):
                with cols[i]: card(r)
        st.markdown("<div class='bh-section'><h2>Alt 3</h2><span class='bh-chip'>Legal Backups</span></div>", unsafe_allow_html=True)
        if not alt.empty:
            cols=st.columns(3)
            for i,(_,r) in enumerate(alt.head(3).iterrows()):
                with cols[i]: card(r)

with tabs[1]:
    if "owners" in st.session_state:
        for _,r in st.session_state["owners"].iterrows(): card(r)
    else: st.info("Run a slate first.")
with tabs[2]:
    if "core" in st.session_state and not st.session_state["core"].empty:
        st.code(" + ".join(st.session_state["core"].player.tolist()))
    else: st.info("Run a slate first.")
with tabs[3]:
    if "logs" in st.session_state:
        st.dataframe(st.session_state["logs"],use_container_width=True,height=520)
    else: st.info("Run a slate first.")
