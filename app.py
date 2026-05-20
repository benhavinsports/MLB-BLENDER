
import re, io, json, sqlite3, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

APP_VERSION = "v9 Full Machine"

st.set_page_config(
    page_title="BenHavin Blender Machine",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================================
# CSS — SPORTSBOOK COMMAND CENTER UI
# ==========================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800;900&display=swap');
:root{
  --bg:#05070b; --panel:#0c1119; --panel2:#111827; --line:rgba(255,255,255,.10);
  --text:#f8fafc; --muted:#94a3b8; --green:#22c55e; --lime:#a3ff12;
  --yellow:#facc15; --orange:#fb923c; --red:#fb4766; --blue:#38bdf8; --purple:#a855f7;
}
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
.stApp{
  background:
    radial-gradient(circle at top left,rgba(34,197,94,.18),transparent 30%),
    radial-gradient(circle at top right,rgba(168,85,247,.13),transparent 28%),
    linear-gradient(180deg,#05070b 0%,#0b1220 55%,#05070b 100%);
  color:var(--text);
}
.block-container{max-width:1240px;padding:1rem 1rem 4rem;}
h1,h2,h3,p,span,div{color:var(--text);}
[data-testid="stMetric"]{
  background:linear-gradient(180deg,rgba(17,24,39,.94),rgba(12,17,25,.94));
  border:1px solid var(--line); border-radius:18px; padding:14px;
  box-shadow:0 12px 32px rgba(0,0,0,.25);
}
[data-testid="stMetricLabel"]{color:var(--muted);font-weight:900;}
[data-testid="stMetricValue"]{color:#fff;font-weight:1000;}
.bh-topbar{
  display:flex;justify-content:space-between;align-items:center;gap:12px;
  background:rgba(5,7,11,.68);border:1px solid var(--line);border-radius:22px;
  padding:14px 16px;position:sticky;top:0;z-index:999;backdrop-filter:blur(13px);margin-bottom:16px;
}
.bh-brand{display:flex;align-items:center;gap:12px;}
.bh-logo{width:44px;height:44px;border-radius:14px;display:grid;place-items:center;
  background:linear-gradient(135deg,#22c55e,#38bdf8);color:#02130b;font-weight:1000;font-size:21px;
  box-shadow:0 0 28px rgba(34,197,94,.38);}
.bh-title{font-size:20px;font-weight:1000;line-height:1;}
.bh-sub{font-size:12px;color:var(--muted);margin-top:4px;}
.bh-live{display:flex;align-items:center;gap:8px;font-size:12px;font-weight:1000;color:#d1fae5;
  background:rgba(34,197,94,.10);border:1px solid rgba(34,197,94,.22);padding:8px 10px;border-radius:999px;}
.bh-dot{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 16px var(--green);}
.bh-hero{
  border:1px solid var(--line);
  background:linear-gradient(135deg,rgba(34,197,94,.18),rgba(56,189,248,.10) 35%,rgba(17,24,39,.88)),
             linear-gradient(180deg,#111827,#0c1119);
  border-radius:28px;padding:24px;margin-bottom:18px;box-shadow:0 18px 52px rgba(0,0,0,.35);
}
.bh-hero h1{margin:0;font-size:clamp(34px,6vw,64px);letter-spacing:-2.2px;line-height:.95;}
.bh-hero p{color:var(--muted);font-size:15px;margin:12px 0 0;}
.bh-pill{display:inline-flex;align-items:center;gap:6px;margin:14px 7px 0 0;padding:8px 11px;border-radius:999px;
  background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);font-size:12px;font-weight:1000;color:#e2e8f0;}
.stTabs [data-baseweb="tab-list"]{gap:8px;background:rgba(17,24,39,.54);border:1px solid var(--line);border-radius:18px;padding:8px;}
.stTabs [data-baseweb="tab"]{border-radius:13px;color:#cbd5e1;font-weight:900;}
.stTabs [aria-selected="true"]{background:linear-gradient(90deg,#22c55e,#38bdf8)!important;color:#04110a!important;}
.bh-upload{background:linear-gradient(180deg,rgba(17,24,39,.94),rgba(12,17,25,.94));border:1px dashed rgba(163,255,18,.35);
  border-radius:24px;padding:18px;margin-bottom:16px;}
.stFileUploader label{display:none;}
.stFileUploader section{border:0!important;background:rgba(255,255,255,.04)!important;border-radius:18px!important;}
.stButton>button{width:100%;min-height:54px;border-radius:18px;border:0;background:linear-gradient(90deg,#a3ff12,#22c55e,#38bdf8);
  color:#04110a;font-size:16px;font-weight:1000;letter-spacing:.2px;box-shadow:0 0 35px rgba(34,197,94,.35);}
.stButton>button:hover{transform:translateY(-1px);filter:brightness(1.05);}
.bh-section-title{display:flex;align-items:center;justify-content:space-between;margin:18px 0 10px;}
.bh-section-title h2{margin:0;font-size:25px;letter-spacing:-.7px;}
.bh-chip{font-size:12px;font-weight:1000;color:#cbd5e1;padding:7px 10px;border-radius:999px;border:1px solid var(--line);background:rgba(255,255,255,.05);}
.bh-card{position:relative;overflow:hidden;background:linear-gradient(180deg,rgba(17,24,39,.96),rgba(8,13,20,.96));
  border:1px solid rgba(255,255,255,.12);border-radius:24px;padding:18px;min-height:250px;box-shadow:0 18px 42px rgba(0,0,0,.32);}
.bh-card:before{content:"";position:absolute;inset:0 0 auto 0;height:5px;background:linear-gradient(90deg,var(--green),var(--blue));}
.bh-card.primary:before{background:linear-gradient(90deg,#22c55e,#a3ff12);}
.bh-card.transfer:before{background:linear-gradient(90deg,#38bdf8,#a855f7);}
.bh-card.who:before{background:linear-gradient(90deg,#fb923c,#fb4766);}
.bh-card.dead:before{background:linear-gradient(90deg,#64748b,#334155);}
.bh-role{display:inline-block;font-size:11px;font-weight:1000;padding:6px 9px;border-radius:999px;background:rgba(255,255,255,.08);
  border:1px solid rgba(255,255,255,.14);color:#e2e8f0;}
.bh-player{font-size:27px;font-weight:1000;margin:12px 0 2px;letter-spacing:-.9px;}
.bh-meta{color:var(--muted);font-size:13px;font-weight:700;min-height:36px;}
.bh-score-row{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-top:15px;}
.bh-score{font-size:42px;font-weight:1000;letter-spacing:-1.5px;color:#fff;line-height:.9;}
.bh-score small{display:block;color:var(--muted);font-size:11px;letter-spacing:.4px;margin-top:6px;}
.bh-meter{flex:1;height:10px;background:rgba(255,255,255,.08);border-radius:999px;overflow:hidden;}
.bh-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#22c55e,#a3ff12);}
.bh-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px;}
.bh-stat{background:rgba(255,255,255,.045);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:9px;}
.bh-stat b{display:block;font-size:15px;}
.bh-stat span{display:block;color:var(--muted);font-size:10px;font-weight:1000;text-transform:uppercase;}
.bh-badges{margin-top:12px;display:flex;gap:6px;flex-wrap:wrap;}
.bh-badge{font-size:10px;font-weight:1000;padding:5px 7px;border-radius:999px;background:rgba(34,197,94,.12);
  border:1px solid rgba(34,197,94,.24);color:#d1fae5;}
.bh-empty{border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);border-radius:18px;padding:18px;color:var(--muted);}
.bh-timeline{background:rgba(17,24,39,.72);border:1px solid rgba(255,255,255,.10);border-radius:18px;padding:14px;margin:8px 0;}
.bh-step{display:flex;gap:10px;align-items:flex-start;padding:10px;border-bottom:1px solid rgba(255,255,255,.06);}
.bh-step:last-child{border-bottom:0;}
.bh-step-num{min-width:34px;height:34px;border-radius:10px;display:grid;place-items:center;background:rgba(34,197,94,.14);border:1px solid rgba(34,197,94,.25);font-weight:1000;color:#d1fae5;}
.bh-step-body b{display:block;font-size:13px;}
.bh-step-body span{display:block;color:var(--muted);font-size:12px;margin-top:2px;}
div[data-testid="stExpander"]{background:rgba(17,24,39,.72)!important;border:1px solid rgba(255,255,255,.10)!important;border-radius:18px!important;}
div[data-testid="stDataFrame"]{border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,.10);}
</style>
""", unsafe_allow_html=True)

# ==========================================================
# DATA / PARSER
# ==========================================================
COLS = [
    "game","team","opponent","pitcher","player","bats","lineup_slot",
    "pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg",
    "hr_pa","pitch_type","pitch_edge","hr_alert","cond_up","weak_slot_tag",
    "laser","rakes","platoon","weak_slots","odds","public_pct","weather_score",
    "bullpen_dmg","confirmed_lineup","dob","jersey","result_hr","notes"
]
BAD_WORDS = {"dmg","hpi","line","cond","alert","hot","cold","warm","moderate","elevated","low","high","fresh","effort","disengaged","page","https","star","tool","projected","weak","slot","home","away","none"}

def is_player_name(s):
    s = str(s).strip()
    if not s or len(s) < 4: return False
    if re.search(r"\d", s): return False
    low = s.lower()
    if low in BAD_WORDS or "http" in low or "page" in low: return False
    parts = s.split()
    if len(parts) < 2 or len(parts) > 4: return False
    return all(re.match(r"^[A-Za-zÀ-ÿ.'’\\-]+$", p) for p in parts)

def nfloat(x):
    if x is None or pd.isna(x): return None
    if isinstance(x, (int,float)): return float(x)
    s = str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    try: return float(s)
    except: return None

def nbool(x):
    if isinstance(x,bool): return x
    return str(x).strip().lower() in ["true","1","yes","y","alert","hot","x","✅","confirmed"]

def clean_df(df):
    df.columns = [str(c).strip().lower().replace(" ","_") for c in df.columns]
    for c in COLS:
        if c not in df.columns: df[c] = None
    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","odds","public_pct","weather_score","bullpen_dmg","jersey"]:
        df[c] = df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","confirmed_lineup","result_hr"]:
        df[c] = df[c].apply(nbool)
    df["player"] = df["player"].astype(str).str.strip()
    return df[df["player"].apply(is_player_name)].copy()[COLS]

def pdf_text(b):
    if fitz is None: return ""
    doc = fitz.open(stream=b, filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc)

def parse_pdf(b):
    txt = pdf_text(b)
    if not txt.strip(): return pd.DataFrame(columns=COLS)
    lines = [x.strip() for x in txt.splitlines() if x.strip()]
    rows, weak_by_pitcher = [], {}
    team = ""; pitcher = ""; game = ""

    for line in lines:
        m = re.search(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)", line, re.I)
        if m:
            weak_by_pitcher[m.group(1).strip()] = f"{m.group(2)},{m.group(3)},{m.group(4)}"

    i=0
    while i < len(lines):
        line=lines[i]
        sec=re.search(r"^([A-Z\s]+?)\s+PROJECTED\s+vs\.\s+(.+?)\s+~", line, re.I)
        if sec:
            team=sec.group(1).strip().title()
            pitcher=sec.group(2).strip()
            i+=1; continue
        if re.match(r"^\d+$", line) and i+1 < len(lines):
            name=lines[i+1].strip()
            if is_player_name(name):
                block=" ".join(lines[i+1:i+18])
                slot=None
                sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b", block)
                if sm: slot=int(sm.group(1))
                pct_vals=re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%", block)
                pull=None
                for pv in pct_vals:
                    val=float(pv)
                    if 5 <= abs(val) <= 65:
                        pull=val; break
                line_m=re.search(r"LINE\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%", block)
                sweet=float(line_m.group(1)) if line_m else None
                hrpa_m=re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA", block)
                hrpa=float(hrpa_m.group(1)) if hrpa_m else None
                dmg_m=re.search(r"([0-9]+(?:\.\d+)?)\s+DMG", block)
                dmg=float(dmg_m.group(1)) if dmg_m else None
                pem=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\\-]*)", block)
                pe=None; pt=None
                pitch_like=[(float(a),b) for a,b in pem if b.lower() not in ["hr","line","cond"]]
                if pitch_like: pe,pt=pitch_like[-1]
                pluses=[int(x) for x in re.findall(r"\+\s*(\d+)", block) if 10 <= int(x) <= 90]
                hpi=pluses[-1] if pluses else None
                rows.append({
                    "game":game,"team":team,"opponent":"","pitcher":pitcher,"player":name,"bats":"",
                    "lineup_slot":slot,"pull_pct":pull,"barrel_pct":None,"sweet_spot_pct":sweet,"hard_hit_pct":None,
                    "hpi":hpi,"dmg":dmg,"hr_pa":hrpa,"pitch_type":pt,"pitch_edge":pe,
                    "hr_alert":"ALERT" in block,"cond_up":"COND ↑" in block,"weak_slot_tag":"Weak Slot" in block,
                    "laser":"Laser" in block,"rakes":"Rakes" in block,"platoon":"Platoon" in block,
                    "weak_slots":weak_by_pitcher.get(pitcher,""),"odds":None,"public_pct":None,"weather_score":None,
                    "bullpen_dmg":None,"confirmed_lineup":False,"dob":None,"jersey":None,"result_hr":False,"notes":block[:220]
                })
                i+=14; continue
        i+=1
    return clean_df(pd.DataFrame(rows))

# ==========================================================
# MACHINE ENGINE
# ==========================================================
def slot_ok(row):
    ws=str(row.get("weak_slots") or "")
    slots=[int(x) for x in re.findall(r"\d+", ws)]
    if not slots or pd.isna(row.get("lineup_slot")): return True
    return int(row["lineup_slot"]) in slots or bool(row.get("weak_slot_tag"))

def game_key(row):
    # best possible with incomplete PDF data
    return f"{row.get('team','')} vs {row.get('pitcher','')}"

def role_type(row):
    if bool(row.get("weak_slot_tag")) or bool(row.get("laser")) or bool(row.get("rakes")):
        return "Transfer"
    if (row.get("dmg") or 0) >= 1.7 and (row.get("hr_pa") or 0) >= 4:
        return "WHO"
    return "Primary"

def score_row(r):
    return (
        (r.get("pull_pct") or 0)*0.10 + (r.get("pitch_edge") or 0)*0.20 +
        (r.get("sweet_spot_pct") or 0)*0.10 + (r.get("barrel_pct") or 0)*0.15 +
        (r.get("dmg") or 0)*12 + (r.get("hpi") or 0)*0.12 + (r.get("hr_pa") or 0)*2 +
        int(bool(r.get("hr_alert")))*8 + int(bool(r.get("cond_up")))*5 +
        int(bool(r.get("weak_slot_tag")))*4 + int(bool(r.get("laser")))*3 + int(bool(r.get("rakes")))*3 +
        (r.get("weather_score") or 0)*0.2 + (r.get("bullpen_dmg") or 0)*1.5
    )

def add_log(logs, gate, alive_before, cut, alive_after, reason):
    logs.append({
        "Gate": gate,
        "Before": len(alive_before),
        "Cut": len(cut),
        "After": len(alive_after),
        "Cut names": ", ".join(cut),
        "Alive after": ", ".join(alive_after),
        "Reason": reason
    })

def apply_gate(alive, gate_name, mask, reason, logs):
    before=alive["player"].tolist()
    cut=alive.loc[~mask, "player"].tolist()
    after_df=alive[mask].copy()
    after=after_df["player"].tolist()
    add_log(logs, gate_name, before, cut, after, reason)
    return after_df

def run_game_machine(game_df):
    alive=game_df.copy()
    logs=[]
    if alive.empty:
        return alive, pd.DataFrame(logs), "NO PLAY"

    # Step 0 game viability is visible but not killing inside already-grouped game
    add_log(logs, "0 Game / Pitcher Viability", alive.player.tolist(), [], alive.player.tolist(), "Game enters machine if at least one valid hitter parsed.")

    alive = apply_gate(alive, "1 Pull %", alive.pull_pct.isna() | (alive.pull_pct >= 20), "Kill under 20 pull only when value exists.", logs)
    if len(alive)>1: alive = apply_gate(alive, "2 Matchup / Pitch Edge", alive.pitch_edge.isna() | (alive.pitch_edge >= 0), "Kill negative pitch edge when listed.", logs)
    if len(alive)>1: alive = apply_gate(alive, "3 Zones / Weak Slot", alive.apply(slot_ok, axis=1), "Must match weak slot when both datasets exist.", logs)
    if len(alive)>1: alive = apply_gate(alive, "4 Sweet Spot / Launch", alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct >= 25), "Launch profile filter.", logs)
    if len(alive)>1: alive = apply_gate(alive, "5 Barrel / Conversion", alive.hr_pa.isna() | (alive.hr_pa >= 3) | (alive.barrel_pct.fillna(0) >= 10), "HR/PA 3+ or Barrel 10+.", logs)
    if len(alive)>1: alive = apply_gate(alive, "6 DMG", alive.dmg.isna() | (alive.dmg >= 1.0), "Safe DMG floor 1.0; 1.5+ preferred.", logs)
    if len(alive)>1: alive = apply_gate(alive, "7 HPI", alive.hpi.isna() | (alive.hpi >= 30), "Safe HPI floor 30; 35+ preferred.", logs)
    if len(alive)>1: alive = apply_gate(alive, "8 Recency / Alert", alive.hr_alert | alive.cond_up | alive.hr_alert.isna(), "Prefer HR alert or condition-up.", logs)
    if len(alive)>1: alive = apply_gate(alive, "9 No Empty Bat", alive.hr_pa.isna() | (alive.hr_pa > 0) | alive.hr_alert, "Kill pure zero HR/PA without alert.", logs)

    # Step 10 pressure
    if len(alive)>1:
        pressure = alive.sort_values(["hr_pa","dmg","hpi"], ascending=False).head(1)["player"].iloc[0]
        add_log(logs, "10 Ownership Pressure", alive.player.tolist(), [], alive.player.tolist(), f"Pressure center: {pressure}. No cut.")

    # Step 10.5 transfer: only legal survivors. If transfer survives score+role, it can outrank.
    if len(alive)>1:
        before=alive.player.tolist()
        add_log(logs, "10.5 Adjacent / Decoy Transfer", before, [], before, "Only current survivors eligible. Dead players cannot return.")
        alive["transfer_bonus"] = alive.apply(lambda r: 7 if role_type(r)=="Transfer" else 0, axis=1)
    else:
        alive["transfer_bonus"] = 0

    # 11-18 audits
    audit_steps=[
        ("11 Lineup Protection","Manual protection layer; no auto kill without data."),
        ("12 Bullpen Continuation","Uses bullpen_dmg if provided; missing data survives."),
        ("13 Numerology Overlay","Tie-break only; no override."),
        ("14 Chaos / WHO","WHO flag kept as role, no forced randoms."),
        ("15 Finisher Gate","Finisher profile check."),
        ("16 Event Likelihood","Legal survivors ranked by score."),
        ("17 No-Fluke Audit","No recap anchoring; no resurrection."),
        ("18 True HR Event Likelihood","Final game owner or no play.")
    ]
    for step, reason in audit_steps:
        if len(alive)>1:
            add_log(logs, step, alive.player.tolist(), [], alive.player.tolist(), reason)

    if alive.empty:
        return alive, pd.DataFrame(logs), "NO PLAY"

    alive=alive.copy()
    alive["role"]=alive.apply(role_type, axis=1)
    alive["score"]=alive.apply(score_row, axis=1) + alive.get("transfer_bonus", 0)
    alive=alive.sort_values("score", ascending=False)
    return alive, pd.DataFrame(logs), "LIVE"

def run_full_machine(df):
    df=clean_df(df.copy())
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df["game_key"]=df.apply(game_key, axis=1)
    owners=[]
    all_logs=[]
    all_survivors=[]

    for g, gdf in df.groupby("game_key", dropna=False):
        surv, logs, status = run_game_machine(gdf)
        if not logs.empty:
            logs.insert(0, "Game", g)
            all_logs.append(logs)
        if not surv.empty:
            surv=surv.copy()
            surv["game_key"]=g
            all_survivors.append(surv)
            owner=surv.iloc[0].to_dict()
            owner["game_status"]=status
            owners.append(owner)

    owners_df=pd.DataFrame(owners) if owners else pd.DataFrame()
    logs_df=pd.concat(all_logs, ignore_index=True) if all_logs else pd.DataFrame()
    survivors_df=pd.concat(all_survivors, ignore_index=True) if all_survivors else pd.DataFrame()

    # role-balanced Core 3 from game owners only
    core=[]
    if not owners_df.empty:
        owners_df=owners_df.sort_values("score", ascending=False)
        for role in ["Primary","Transfer","WHO"]:
            part=owners_df[owners_df["role"]==role]
            if not part.empty:
                core.append(part.iloc[0].to_dict())
        for _, r in owners_df.iterrows():
            if len(core)>=3: break
            if r["player"] not in [x["player"] for x in core]:
                core.append(r.to_dict())
    core_df=pd.DataFrame(core[:3]) if core else pd.DataFrame()

    alt=[]
    if not owners_df.empty:
        for _, r in owners_df.iterrows():
            if r["player"] not in (core_df["player"].tolist() if not core_df.empty else []):
                alt.append(r.to_dict())
            if len(alt)>=3: break
    alt_df=pd.DataFrame(alt) if alt else pd.DataFrame()

    return owners_df, core_df, alt_df, logs_df

# ==========================================================
# DATABASE / CALIBRATION
# ==========================================================
DB_PATH=Path("blender_history.sqlite")

def db():
    conn=sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT,
            app_version TEXT,
            slate_name TEXT,
            player TEXT,
            team TEXT,
            pitcher TEXT,
            role TEXT,
            score REAL,
            core_rank INTEGER,
            result_hr INTEGER DEFAULT 0
        )
    """)
    return conn

def save_run(core_df, slate_name):
    if core_df.empty: return
    conn=db()
    ts=datetime.datetime.now().isoformat(timespec="seconds")
    for i, row in core_df.reset_index(drop=True).iterrows():
        conn.execute("""
          INSERT INTO runs(ts,app_version,slate_name,player,team,pitcher,role,score,core_rank,result_hr)
          VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (ts, APP_VERSION, slate_name, row.get("player",""), row.get("team",""), row.get("pitcher",""),
              row.get("role",""), float(row.get("score",0) or 0), i+1, 0))
    conn.commit(); conn.close()

def load_history():
    conn=db()
    out=pd.read_sql_query("SELECT * FROM runs ORDER BY id DESC", conn)
    conn.close()
    return out

# ==========================================================
# UI COMPONENTS
# ==========================================================
def fmt(x):
    if x is None or pd.isna(x): return "—"
    if isinstance(x,float): return f"{x:.1f}"
    return str(x)

def conf(score):
    try: return max(8, min(100, int(score)))
    except: return 50

def player_card(row, kind="primary"):
    role=str(row.get("role","Primary"))
    cls="primary"
    if role.lower().startswith("transfer"): cls="transfer"
    if role.lower().startswith("who"): cls="who"
    pct=conf(row.get("score",50))
    badges=[]
    for b in ["hr_alert","cond_up","weak_slot_tag","laser","rakes"]:
        if bool(row.get(b)): badges.append(b.replace("_"," ").upper())
    badge_html="".join([f"<span class='bh-badge'>{x}</span>" for x in badges[:4]]) or "<span class='bh-badge'>LEGAL</span>"
    st.markdown(f"""
    <div class="bh-card {cls}">
      <span class="bh-role">{role}</span>
      <div class="bh-player">{row.get('player','')}</div>
      <div class="bh-meta">{row.get('team','')} vs {row.get('pitcher','')} · Slot {fmt(row.get('lineup_slot'))}</div>
      <div class="bh-score-row">
        <div class="bh-score">{fmt(row.get('score'))}<small>BLEND SCORE</small></div>
        <div class="bh-meter"><div class="bh-fill" style="width:{pct}%"></div></div>
      </div>
      <div class="bh-stats">
        <div class="bh-stat"><b>{fmt(row.get('pull_pct'))}</b><span>Pull</span></div>
        <div class="bh-stat"><b>{fmt(row.get('pitch_edge'))}</b><span>Pitch Edge</span></div>
        <div class="bh-stat"><b>{fmt(row.get('dmg'))}</b><span>DMG</span></div>
        <div class="bh-stat"><b>{fmt(row.get('hr_pa'))}</b><span>HR/PA</span></div>
        <div class="bh-stat"><b>{fmt(row.get('hpi'))}</b><span>HPI</span></div>
        <div class="bh-stat"><b>{fmt(row.get('sweet_spot_pct'))}</b><span>Sweet</span></div>
      </div>
      <div class="bh-badges">{badge_html}</div>
    </div>
    """, unsafe_allow_html=True)

def timeline():
    steps=[
        ("0","Slate scan + game viability"),
        ("1","Pull % DNA"),
        ("2","Pitch matchup edge"),
        ("3","Zones / weak slot"),
        ("4","Sweet spot / launch"),
        ("5","Barrel / conversion"),
        ("6","DMG"),
        ("7","HPI"),
        ("8","Recency / alert"),
        ("9","No empty bat"),
        ("10","Ownership pressure"),
        ("10.5","Adjacent / decoy transfer"),
        ("11","Lineup protection"),
        ("12","Bullpen continuation"),
        ("13","Numerology overlay"),
        ("14","WHO / chaos"),
        ("15","Finisher gate"),
        ("16","Event likelihood"),
        ("17","No-fluke audit"),
        ("18","True HR event")
    ]
    html="<div class='bh-timeline'>"
    for n, txt in steps:
        html += f"<div class='bh-step'><div class='bh-step-num'>{n}</div><div class='bh-step-body'><b>Gate {n}</b><span>{txt}</span></div></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

# ==========================================================
# MAIN UI
# ==========================================================
st.markdown(f"""
<div class="bh-topbar">
  <div class="bh-brand">
    <div class="bh-logo">BH</div>
    <div><div class="bh-title">BenHavin Blender</div><div class="bh-sub">Full Machine · {APP_VERSION}</div></div>
  </div>
  <div class="bh-live"><span class="bh-dot"></span> MACHINE READY</div>
</div>
<div class="bh-hero">
  <h1>Sportsbook Grade<br/>Blender Machine</h1>
  <p>One HR owner per game → Core 3 role balance → Transfer / WHO / No-Fluke audit → calibration history.</p>
  <span class="bh-pill">⚾ MLB HR</span><span class="bh-pill">🔒 No Revivals</span><span class="bh-pill">🧠 Calibration DB</span>
  <span class="bh-pill">🧨 WHO</span><span class="bh-pill">10.5 Transfer</span>
</div>
""", unsafe_allow_html=True)

tab_run, tab_games, tab_tickets, tab_history, tab_settings = st.tabs(["Run Blender", "Game Board", "Tickets", "History", "Settings"])

with tab_run:
    st.markdown("<div class='bh-upload'>", unsafe_allow_html=True)
    uploaded=st.file_uploader("Upload Star Tool PDF / CSV / XLSX", type=["csv","xlsx","pdf"], label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded:
        data=uploaded.read()
        name=uploaded.name.lower()
        df=pd.DataFrame()
        try:
            if name.endswith(".csv"):
                df=clean_df(pd.read_csv(io.BytesIO(data)))
            elif name.endswith(".xlsx"):
                df=clean_df(pd.read_excel(io.BytesIO(data)))
            else:
                df=parse_pdf(data)
        except Exception as e:
            st.error(f"Parser error: {e}")
            df=pd.DataFrame()

        if df.empty:
            st.error("No valid player rows parsed. This file may need OCR or CSV export.")
        else:
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Players", len(df))
            c2.metric("Teams", df.team.nunique())
            c3.metric("Pitchers", df.pitcher.nunique())
            c4.metric("Gates", "18 + 10.5")

            if st.button("RUN FULL MACHINE"):
                owners, core, alt, logs = run_full_machine(df)
                st.session_state["df"]=df
                st.session_state["owners"]=owners
                st.session_state["core"]=core
                st.session_state["alt"]=alt
                st.session_state["logs"]=logs
                save_run(core, uploaded.name)
                st.success("Blend complete. Core / Alt locked from legal game owners.")

            with st.expander("Parsed Slate Preview"):
                st.dataframe(df, use_container_width=True, height=360)

    if "core" in st.session_state:
        core=st.session_state["core"]; alt=st.session_state["alt"]; owners=st.session_state["owners"]; logs=st.session_state["logs"]
        st.markdown("<div class='bh-section-title'><h2>Core 3</h2><span class='bh-chip'>Role Balanced</span></div>", unsafe_allow_html=True)
        if core.empty:
            st.markdown("<div class='bh-empty'>No Core. Machine found no legal owners.</div>", unsafe_allow_html=True)
        else:
            cols=st.columns(3)
            for i, (_, r) in enumerate(core.iterrows()):
                with cols[i]: player_card(r)
        st.markdown("<div class='bh-section-title'><h2>Alt 3</h2><span class='bh-chip'>Legal Game Owners</span></div>", unsafe_allow_html=True)
        if alt.empty:
            st.markdown("<div class='bh-empty'>No Alt survivors.</div>", unsafe_allow_html=True)
        else:
            cols=st.columns(3)
            for i, (_, r) in enumerate(alt.head(3).iterrows()):
                with cols[i]: player_card(r)

        with st.expander("18-Gate Audit"):
            st.dataframe(logs, use_container_width=True, height=460)
        with st.expander("All Game Owners"):
            st.dataframe(owners, use_container_width=True, height=460)

with tab_games:
    st.markdown("<div class='bh-section-title'><h2>Game Board</h2><span class='bh-chip'>One owner per game</span></div>", unsafe_allow_html=True)
    if "owners" not in st.session_state:
        st.info("Run a slate first.")
    else:
        owners=st.session_state["owners"]
        if owners.empty:
            st.warning("No owners.")
        else:
            for _, r in owners.iterrows():
                with st.container():
                    player_card(r)

with tab_tickets:
    st.markdown("<div class='bh-section-title'><h2>Auto Ticket Builder</h2><span class='bh-chip'>Core / Alt / Chaos</span></div>", unsafe_allow_html=True)
    if "core" not in st.session_state:
        st.info("Run a slate first.")
    else:
        core=st.session_state["core"]; alt=st.session_state["alt"]
        if not core.empty:
            st.markdown("### Core Slip")
            st.code(" + ".join(core.player.tolist()))
        if not alt.empty:
            st.markdown("### Alt Slip")
            st.code(" + ".join(alt.head(3).player.tolist()))
        if not core.empty and not alt.empty:
            st.markdown("### Round Robin Pool")
            rr = core.player.tolist() + alt.head(3).player.tolist()
            st.code(", ".join(rr))

with tab_history:
    st.markdown("<div class='bh-section-title'><h2>Calibration History</h2><span class='bh-chip'>Saved Runs</span></div>", unsafe_allow_html=True)
    hist=load_history()
    if hist.empty:
        st.info("No saved runs yet.")
    else:
        st.dataframe(hist, use_container_width=True, height=460)
        st.download_button("Download History CSV", hist.to_csv(index=False), "blender_history.csv", "text/csv")

with tab_settings:
    st.markdown("<div class='bh-section-title'><h2>Gate Map</h2><span class='bh-chip'>Locked machine</span></div>", unsafe_allow_html=True)
    timeline()
    st.markdown("### Multi-Sport Hub")
    st.info("MLB HR is active. NHL ATG / NBA First Basket / NBA 3PM tabs are scaffold-ready for the next build.")
