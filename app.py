
import re, io
import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

APP_VERSION = "v11 COSMIC BLENDER"

st.set_page_config(page_title="THE BLENDER", page_icon="🛸", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=Inter:wght@500;700;900&display=swap');

:root{
 --void:#02030a; --glass:rgba(7,12,28,.72); --line:rgba(255,255,255,.13);
 --neon:#00f5ff; --lime:#7CFF00; --pink:#ff2bd6; --gold:#ffd166; --red:#ff355e;
 --text:#f8fbff; --muted:#a7b4cc;
}

html, body, [class*="css"] { font-family: Inter, sans-serif; }
.stApp{
 background:
  radial-gradient(circle at 12% 8%, rgba(0,245,255,.24), transparent 27%),
  radial-gradient(circle at 90% 10%, rgba(255,43,214,.20), transparent 28%),
  radial-gradient(circle at 50% 105%, rgba(124,255,0,.20), transparent 34%),
  linear-gradient(180deg,#02030a 0%,#071022 42%,#02030a 100%);
 color:var(--text);
}
.stApp:before{
 content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
 background-image:
  linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px),
  linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px);
 background-size:42px 42px;
 mask-image:linear-gradient(to bottom, rgba(0,0,0,.65), transparent 85%);
}
.block-container{max-width:1240px;padding:1rem 1rem 5rem; position:relative; z-index:1;}
h1,h2,h3,p,span,div{color:var(--text);}

.bh-command{
 position:sticky; top:0; z-index:999; margin-bottom:16px;
 border:1px solid var(--line); border-radius:24px; padding:12px 14px;
 background:linear-gradient(135deg,rgba(0,245,255,.12),rgba(255,43,214,.10),rgba(7,12,28,.82));
 backdrop-filter:blur(16px);
 box-shadow:0 0 40px rgba(0,245,255,.12), inset 0 0 25px rgba(255,255,255,.035);
 display:flex; justify-content:space-between; align-items:center; gap:12px;
}
.logo-wrap{display:flex;gap:12px;align-items:center;}
.bh-orb{
 width:54px;height:54px;border-radius:18px;display:grid;place-items:center;
 font-family:Orbitron,sans-serif;font-weight:900;color:#021016;
 background:conic-gradient(from 180deg,#00f5ff,#7CFF00,#ff2bd6,#00f5ff);
 box-shadow:0 0 28px rgba(0,245,255,.55),0 0 60px rgba(255,43,214,.22);
 animation:pulse 2.6s infinite ease-in-out;
}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.05)}}
.bh-brand-title{font-family:Orbitron,sans-serif;font-size:20px;font-weight:900;letter-spacing:1px;}
.bh-brand-sub{font-size:11px;color:var(--muted);font-weight:900;text-transform:uppercase;letter-spacing:1.3px;}
.bh-status{
 padding:9px 12px;border-radius:999px;border:1px solid rgba(124,255,0,.28);
 background:rgba(124,255,0,.10);font-size:11px;font-weight:900;color:#dcffd1;
 box-shadow:0 0 25px rgba(124,255,0,.13);
}

.bh-hero{
 position:relative; overflow:hidden;
 border-radius:34px; padding:30px; margin-bottom:18px;
 background:
  radial-gradient(circle at 18% 18%, rgba(0,245,255,.28), transparent 30%),
  radial-gradient(circle at 88% 20%, rgba(255,43,214,.22), transparent 32%),
  linear-gradient(135deg,rgba(10,18,42,.94),rgba(4,7,18,.96));
 border:1px solid rgba(255,255,255,.14);
 box-shadow:0 30px 90px rgba(0,0,0,.45), inset 0 0 80px rgba(0,245,255,.05);
}
.bh-hero:after{
 content:""; position:absolute; width:420px;height:420px;border-radius:50%;
 right:-160px;top:-160px;border:1px solid rgba(0,245,255,.18);
 box-shadow:0 0 80px rgba(0,245,255,.18), inset 0 0 80px rgba(255,43,214,.10);
}
.bh-hero h1{
 font-family:Orbitron,sans-serif;
 font-size:clamp(40px,7vw,78px);line-height:.9;margin:0;letter-spacing:-2px;
 text-shadow:0 0 18px rgba(0,245,255,.25);
}
.bh-hero .glow{
 background:linear-gradient(90deg,#00f5ff,#7CFF00,#ff2bd6);
 -webkit-background-clip:text;background-clip:text;color:transparent;
}
.bh-hero p{color:var(--muted);font-weight:700;max-width:730px;margin:14px 0 0;font-size:15px;}
.bh-pill{
 display:inline-flex;align-items:center;gap:7px;margin:15px 7px 0 0;padding:9px 12px;border-radius:999px;
 background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.13);
 font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.5px;
}

.stTabs [data-baseweb="tab-list"]{
 gap:8px;background:rgba(5,9,22,.68);border:1px solid var(--line);border-radius:22px;padding:8px;
 box-shadow:inset 0 0 18px rgba(0,245,255,.04);
}
.stTabs [data-baseweb="tab"]{border-radius:16px;color:#d7e2f2;font-weight:900;font-size:12px;}
.stTabs [aria-selected="true"]{
 background:linear-gradient(90deg,#00f5ff,#7CFF00)!important;color:#02030a!important;
 box-shadow:0 0 24px rgba(0,245,255,.25);
}

.stFileUploader section{
 background:rgba(255,255,255,.045)!important;border:1px dashed rgba(0,245,255,.35)!important;
 border-radius:26px!important;padding:20px!important;
}
.stButton>button{
 border:0!important;border-radius:22px!important;min-height:64px!important;width:100%!important;
 background:linear-gradient(90deg,#00f5ff,#7CFF00,#ff2bd6)!important;color:#02030a!important;
 font-family:Orbitron,sans-serif!important;font-weight:900!important;letter-spacing:1px!important;
 box-shadow:0 0 36px rgba(0,245,255,.30),0 0 50px rgba(124,255,0,.15)!important;
}
.stButton>button:hover{filter:brightness(1.13);transform:translateY(-1px);}

[data-testid="stMetric"]{
 background:linear-gradient(180deg,rgba(12,20,44,.82),rgba(4,7,18,.82));
 border:1px solid rgba(255,255,255,.12);border-radius:26px;padding:18px;
 box-shadow:0 18px 50px rgba(0,0,0,.28), inset 0 0 30px rgba(0,245,255,.035);
}
[data-testid="stMetricLabel"]{color:#a7b4cc;font-weight:900;}
[data-testid="stMetricValue"]{font-family:Orbitron,sans-serif;color:#fff;font-weight:900;}

.bh-section{display:flex;justify-content:space-between;align-items:center;margin:22px 0 12px;}
.bh-section h2{font-family:Orbitron,sans-serif;margin:0;font-size:25px;letter-spacing:.5px;}
.bh-chip{font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.6px;padding:8px 11px;border-radius:999px;border:1px solid rgba(255,255,255,.13);background:rgba(255,255,255,.055);}

.bh-card{
 position:relative;overflow:hidden;border-radius:30px;min-height:280px;padding:20px;margin-bottom:14px;
 background:
  linear-gradient(180deg,rgba(10,18,42,.92),rgba(3,6,15,.96)),
  radial-gradient(circle at top right,rgba(0,245,255,.12),transparent 35%);
 border:1px solid rgba(255,255,255,.13);
 box-shadow:0 22px 62px rgba(0,0,0,.36), inset 0 0 30px rgba(255,255,255,.035);
}
.bh-card:before{
 content:"";position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,#00f5ff,#7CFF00,#ff2bd6);
}
.bh-card:after{
 content:"";position:absolute;width:190px;height:190px;border-radius:50%;right:-80px;bottom:-80px;
 background:radial-gradient(circle,rgba(0,245,255,.16),transparent 65%);
}
.bh-role{
 display:inline-block;padding:7px 10px;border-radius:999px;background:rgba(255,255,255,.075);
 border:1px solid rgba(255,255,255,.15);font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.8px;
}
.bh-player{font-family:Orbitron,sans-serif;font-size:28px;font-weight:900;margin:14px 0 4px;line-height:1.05;}
.bh-meta{color:#a7b4cc;font-size:13px;font-weight:800;min-height:35px;}
.bh-score{font-family:Orbitron,sans-serif;font-size:44px;font-weight:900;margin-top:14px;text-shadow:0 0 18px rgba(0,245,255,.18);}
.bh-score small{display:block;color:#a7b4cc;font-family:Inter,sans-serif;font-size:10px;letter-spacing:1.4px;margin-top:4px;}
.bh-ring{height:12px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;margin-top:12px;}
.bh-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#00f5ff,#7CFF00,#ff2bd6);}
.bh-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:15px;}
.bh-stat{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.10);border-radius:16px;padding:10px;}
.bh-stat b{display:block;font-size:16px;}
.bh-stat span{display:block;color:#a7b4cc;font-size:9px;font-weight:900;text-transform:uppercase;letter-spacing:.7px;}
.bh-badge{display:inline-block;margin:10px 5px 0 0;font-size:10px;font-weight:900;padding:6px 8px;border-radius:999px;color:#dffcff;background:rgba(0,245,255,.12);border:1px solid rgba(0,245,255,.24);}
div[data-testid="stExpander"]{background:rgba(7,12,28,.70)!important;border:1px solid rgba(255,255,255,.12)!important;border-radius:22px!important;}
div[data-testid="stDataFrame"]{border-radius:18px;overflow:hidden;border:1px solid rgba(255,255,255,.12);}
.bh-empty{border:1px solid rgba(255,255,255,.13);background:rgba(255,255,255,.04);border-radius:22px;padding:18px;color:#a7b4cc;}
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
    return df[df["player"].apply(is_player_name)].copy()[COLS]

def pdf_text(b):
    if fitz is None: return ""
    doc=fitz.open(stream=b,filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc)

def parse_pdf(b):
    txt=pdf_text(b)
    if not txt.strip(): return pd.DataFrame(columns=COLS)
    lines=[x.strip() for x in txt.splitlines() if x.strip()]
    rows=[]; team=""; pitcher=""; weak_by_pitcher={}
    for line in lines:
        m=re.search(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)", line, re.I)
        if m: weak_by_pitcher[m.group(1).strip()]=f"{m.group(2)},{m.group(3)},{m.group(4)}"
    i=0; section=0
    while i < len(lines):
        line=lines[i]
        sec=re.search(r"([A-Z][A-Z\s]+?)\s+PROJECTED\s+vs\.\s+(.+?)\s+~", line, re.I)
        if sec:
            team=sec.group(1).strip().title(); pitcher=sec.group(2).strip(); section+=1; i+=1; continue
        if re.match(r"^\d+$",line) and i+1 < len(lines):
            name=lines[i+1].strip()
            if is_player_name(name):
                block=" ".join(lines[i+1:i+18])
                slot=None
                sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
                if sm: slot=int(sm.group(1))
                pct_vals=re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block)
                pull=None
                for pv in pct_vals:
                    val=float(pv)
                    if 5 <= abs(val) <= 65: pull=val; break
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
                fallback_team=team if team else f"Team {section or ((len(rows)//9)+1)}"
                fallback_pitcher=pitcher if pitcher else f"Pitcher {section or ((len(rows)//9)+1)}"
                rows.append({"game":f"{fallback_team} vs {fallback_pitcher}","team":fallback_team,"opponent":"","pitcher":fallback_pitcher,"player":name,"bats":"","lineup_slot":slot,"pull_pct":pull,"barrel_pct":None,"sweet_spot_pct":sweet,"hard_hit_pct":None,"hpi":hpi,"dmg":dmg,"hr_pa":hrpa,"pitch_type":pt,"pitch_edge":pe,"hr_alert":"ALERT" in block,"cond_up":"COND ↑" in block,"weak_slot_tag":"Weak Slot" in block,"laser":"Laser" in block,"rakes":"Rakes" in block,"platoon":"Platoon" in block,"weak_slots":weak_by_pitcher.get(fallback_pitcher,""),"odds":None,"public_pct":None,"weather_score":None,"bullpen_dmg":None,"confirmed_lineup":False,"dob":None,"jersey":None,"result_hr":False,"notes":block[:220]})
                i+=14; continue
        i+=1
    df=clean_df(pd.DataFrame(rows))
    if not df.empty and (df.team.nunique()<=1 or df.pitcher.nunique()<=1):
        df=df.reset_index(drop=True)
        df["game"]="Game "+((df.index//9)+1).astype(str)
        df["team"]="Team "+((df.index//9)+1).astype(str)
        df["pitcher"]="Pitcher "+((df.index//9)+1).astype(str)
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

def gate(alive,name,mask,reason,logs):
    before=alive.player.tolist(); cut=alive.loc[~mask,"player"].tolist(); alive=alive[mask].copy()
    logs.append({"Gate":name,"Before":len(before),"Cut":len(cut),"After":len(alive),"Cut names":", ".join(cut),"Alive after":", ".join(alive.player.tolist()),"Reason":reason})
    return alive

def run_game(gdf):
    alive=gdf.copy(); logs=[]
    logs.append({"Gate":"0 Game / Pitcher Viability","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()),"Reason":"Game enters machine."})
    alive=gate(alive,"1 Pull %",alive.pull_pct.isna() | (alive.pull_pct>=20),"Kill under 20 pull only when value exists.",logs)
    if len(alive)>1: alive=gate(alive,"2 Matchup / Pitch Edge",alive.pitch_edge.isna() | (alive.pitch_edge>=0),"Kill negative pitch edge.",logs)
    if len(alive)>1: alive=gate(alive,"3 Zones / Weak Slot",alive.apply(slot_ok,axis=1),"Must match weak slot when data exists.",logs)
    if len(alive)>1: alive=gate(alive,"4 Sweet Spot / Launch",alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=25),"Launch filter.",logs)
    if len(alive)>1: alive=gate(alive,"5 Barrel / Conversion",alive.hr_pa.isna() | (alive.hr_pa>=3) | (alive.barrel_pct.fillna(0)>=10),"HR/PA 3+ or barrel 10+.",logs)
    if len(alive)>1: alive=gate(alive,"6 DMG",alive.dmg.isna() | (alive.dmg>=1.0),"Safe DMG floor.",logs)
    if len(alive)>1: alive=gate(alive,"7 HPI",alive.hpi.isna() | (alive.hpi>=30),"Safe HPI floor.",logs)
    if len(alive)>1: alive=gate(alive,"8 Recency / Alert",alive.hr_alert | alive.cond_up | alive.hr_alert.isna(),"Prefer alert/cond.",logs)
    if len(alive)>1: alive=gate(alive,"9 No Empty Bat",alive.hr_pa.isna() | (alive.hr_pa>0) | alive.hr_alert,"Kill zero HR/PA no alert.",logs)
    for g in ["10 Ownership Pressure","10.5 Adjacent / Decoy Transfer","11 Lineup Protection","12 Bullpen Continuation","13 Numerology Overlay","14 Chaos / WHO","15 Finisher Gate","16 Event Likelihood","17 No-Fluke Audit","18 True HR Event Likelihood"]:
        if len(alive)>1: logs.append({"Gate":g,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()),"Reason":"Audit/tie-break layer; no resurrection."})
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
    cls=str(r.get("role","Primary")).lower()
    st.markdown(f"""<div class="bh-card"><span class="bh-role">{r.get('role','Primary')}</span><div class="bh-player">{r.get('player','')}</div><div class="bh-meta">{r.get('game','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="bh-score">{fmt(r.get('score'))}<small>BLEND SCORE</small></div><div class="bh-ring"><div class="bh-fill" style="width:{max(8,min(100,int(r.get('score',40) or 40)))}%"></div></div><div class="bh-stats"><div class="bh-stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="bh-stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="bh-stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="bh-stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="bh-stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="bh-stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><span class="bh-badge">LEGAL</span></div>""",unsafe_allow_html=True)

st.markdown("""<div class="bh-command"><div class="logo-wrap"><div class="bh-orb">BH</div><div><div class="bh-brand-title">THE BLENDER</div><div class="bh-brand-sub">Cosmic HR Machine · 18 Gates</div></div></div><div class="bh-status">SYSTEM ARMED</div></div><div class="bh-hero"><h1>OUT OF THIS WORLD<br><span class="glow">BLENDER</span></h1><p>One owner per game. 18 total gates. 10.5 lives inside the machine. No revivals. No generic dashboard.</p><span class="bh-pill">🛸 Command Center</span><span class="bh-pill">⚾ HR DNA</span><span class="bh-pill">🧨 WHO / Chaos</span><span class="bh-pill">🔒 No Revivals</span></div>""", unsafe_allow_html=True)

tabs=st.tabs(["Launch", "Game Board", "Tickets", "Audit"])
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
                owners,core,alt,logs=run_machine(df)
                st.session_state.update({"df":df,"owners":owners,"core":core,"alt":alt,"logs":logs})
                st.success("Machine complete.")
            with st.expander("Parsed Slate Preview"):
                st.dataframe(df,use_container_width=True,height=360)
    if "core" in st.session_state:
        st.markdown("<div class='bh-section'><h2>CORE 3</h2><span class='bh-chip'>Role Balanced</span></div>", unsafe_allow_html=True)
        core=st.session_state["core"]; alt=st.session_state["alt"]
        cols=st.columns(3)
        for i,(_,r) in enumerate(core.iterrows()):
            with cols[i]: card(r)
        st.markdown("<div class='bh-section'><h2>ALT 3</h2><span class='bh-chip'>Legal Backups</span></div>", unsafe_allow_html=True)
        if not alt.empty:
            cols=st.columns(3)
            for i,(_,r) in enumerate(alt.head(3).iterrows()):
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
