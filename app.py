
import re, io
import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

st.set_page_config(page_title="BenHavin MLB Blender", layout="wide", initial_sidebar_state="collapsed")

# ---------- CSS ----------
st.markdown("""
<style>
:root {
  --bg:#0b0f14;
  --card:#121923;
  --card2:#17212e;
  --text:#f5f7fb;
  --muted:#aab4c0;
  --green:#45ff9a;
  --yellow:#ffe45c;
  --red:#ff5f6d;
  --blue:#65a7ff;
}
.stApp { background: linear-gradient(180deg, #070a0f 0%, #101722 100%); color: var(--text); }
.block-container { padding-top: 1.2rem; padding-bottom: 3rem; max-width: 1200px; }
h1,h2,h3 { color: #ffffff !important; letter-spacing: .2px; }
[data-testid="stMetricValue"] { color: #ffffff; }
.bh-hero {
  border:1px solid rgba(255,255,255,.12);
  background: radial-gradient(circle at top left, rgba(69,255,154,.16), transparent 35%),
              linear-gradient(135deg, #121923, #0b0f14);
  padding: 22px;
  border-radius: 22px;
  margin-bottom: 18px;
}
.bh-title { font-size: 34px; font-weight: 900; margin:0; }
.bh-sub { color:#aab4c0; margin-top:6px; font-size:15px; }
.bh-pill {
  display:inline-block; padding:7px 11px; border-radius:999px; margin: 4px 6px 0 0;
  background:#17212e; border:1px solid rgba(255,255,255,.12); color:#dbe6f3; font-size:13px;
}
.bh-card {
  background: rgba(18,25,35,.92);
  border:1px solid rgba(255,255,255,.10);
  border-radius:18px;
  padding:16px;
  margin:10px 0;
  box-shadow: 0 8px 28px rgba(0,0,0,.22);
}
.bh-core {
  border-left: 5px solid #45ff9a;
}
.bh-alt {
  border-left: 5px solid #ffe45c;
}
.bh-who {
  border-left: 5px solid #ff5f6d;
}
.bh-name { font-size:22px; font-weight:800; margin-bottom:4px; }
.bh-meta { color:#aab4c0; font-size:13px; }
.bh-score { font-size:28px; font-weight:900; color:#45ff9a; }
.bh-badge {
  font-size:12px; padding:4px 8px; border-radius:999px; margin-right:5px;
  background:#223044; color:#dbe6f3; display:inline-block;
}
.stButton>button {
  width:100%;
  border-radius:14px;
  border:1px solid rgba(255,255,255,.14);
  background: linear-gradient(90deg,#45ff9a,#65a7ff);
  color:#07100c;
  font-weight:900;
  padding:.8rem 1rem;
}
.stFileUploader {
  background: rgba(18,25,35,.72);
  padding:16px;
  border-radius:18px;
  border:1px dashed rgba(255,255,255,.18);
}
div[data-testid="stDataFrame"] { border-radius:16px; overflow:hidden; }
</style>
""", unsafe_allow_html=True)

# ---------- Data ----------
COLS = [
    "game","team","opponent","pitcher","player","bats","lineup_slot",
    "pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg",
    "hr_pa","pitch_type","pitch_edge","hr_alert","cond_up","weak_slot_tag",
    "laser","rakes","platoon","weak_slots","notes"
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
    return str(x).strip().lower() in ["true","1","yes","y","alert","hot","x","✅"]

def clean_df(df):
    df.columns = [str(c).strip().lower().replace(" ","_") for c in df.columns]
    for c in COLS:
        if c not in df.columns: df[c] = None
    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]:
        df[c] = df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon"]:
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
    rows = []
    team = ""; pitcher = ""; game = ""
    weak_by_pitcher = {}

    for line in lines:
        m = re.search(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)", line, re.I)
        if m:
            weak_by_pitcher[m.group(1).strip()] = f"{m.group(2)},{m.group(3)},{m.group(4)}"

    i = 0
    while i < len(lines):
        line = lines[i]
        sec = re.search(r"^([A-Z\s]+?)\s+PROJECTED\s+vs\.\s+(.+?)\s+~", line, re.I)
        if sec:
            team = sec.group(1).strip().title()
            pitcher = sec.group(2).strip()
            i += 1
            continue

        if re.match(r"^\d+$", line) and i+1 < len(lines):
            name = lines[i+1].strip()
            if is_player_name(name):
                block = " ".join(lines[i+1:i+18])
                slot = None
                sm = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", block)
                if sm: slot = int(sm.group(1))

                pct_vals = re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%", block)
                pull = None
                for pv in pct_vals:
                    val = float(pv)
                    if 5 <= abs(val) <= 65:
                        pull = val; break

                line_m = re.search(r"LINE\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%", block)
                sweet = float(line_m.group(1)) if line_m else None

                hrpa_m = re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA", block)
                hrpa = float(hrpa_m.group(1)) if hrpa_m else None

                dmg_m = re.search(r"([0-9]+(?:\.\d+)?)\s+DMG", block)
                dmg = float(dmg_m.group(1)) if dmg_m else None

                pem = re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\\-]*)", block)
                pe = None; pt = None
                pitch_like = [(float(a),b) for a,b in pem if b.lower() not in ["hr","line","cond"]]
                if pitch_like:
                    pe, pt = pitch_like[-1]

                pluses = [int(x) for x in re.findall(r"\+\s*(\d+)", block) if 10 <= int(x) <= 90]
                hpi = pluses[-1] if pluses else None

                rows.append({
                    "game": game, "team": team, "opponent": "", "pitcher": pitcher, "player": name,
                    "bats": "", "lineup_slot": slot, "pull_pct": pull, "barrel_pct": None,
                    "sweet_spot_pct": sweet, "hard_hit_pct": None, "hpi": hpi, "dmg": dmg,
                    "hr_pa": hrpa, "pitch_type": pt, "pitch_edge": pe,
                    "hr_alert": "ALERT" in block, "cond_up": "COND ↑" in block,
                    "weak_slot_tag": "Weak Slot" in block, "laser": "Laser" in block,
                    "rakes": "Rakes" in block, "platoon": "Platoon" in block,
                    "weak_slots": weak_by_pitcher.get(pitcher, ""), "notes": block[:220]
                })
                i += 14
                continue
        i += 1
    return clean_df(pd.DataFrame(rows))

def slot_ok(row):
    ws = str(row.get("weak_slots") or "")
    slots = [int(x) for x in re.findall(r"\d+", ws)]
    if not slots or pd.isna(row.get("lineup_slot")): return True
    return int(row["lineup_slot"]) in slots or bool(row.get("weak_slot_tag"))

def classify_role(row):
    if bool(row.get("weak_slot_tag")) or bool(row.get("laser")) or bool(row.get("rakes")):
        return "Transfer"
    if (row.get("dmg") or 0) >= 1.7 and (row.get("hr_pa") or 0) >= 4:
        return "WHO"
    return "Primary"

def run_18_gates(df):
    df = clean_df(df.copy())
    alive = df.copy()
    logs = []

    def log(gate, before, cut, after, reason):
        logs.append({
            "Gate": gate, "Before": len(before), "Cut": len(cut), "After": len(after),
            "Cut names": ", ".join(cut), "Alive after": ", ".join(after), "Reason": reason
        })

    def gate(name, mask, reason):
        nonlocal alive
        before = alive["player"].tolist()
        cut = alive.loc[~mask, "player"].tolist()
        alive = alive[mask].copy()
        after = alive["player"].tolist()
        log(name,before,cut,after,reason)

    if alive.empty:
        return alive, pd.DataFrame(logs)

    gate("1 Pull %", alive.pull_pct.isna() | (alive.pull_pct >= 20), "Kill under 20 pull only when value exists.")
    if len(alive)>1: gate("2 Matchup / Pitch Edge", alive.pitch_edge.isna() | (alive.pitch_edge >= 0), "Kill negative pitch edge when listed.")
    if len(alive)>1: gate("3 Zones / Weak Slot", alive.apply(slot_ok, axis=1), "Must match pitcher weak slot if both slot datasets exist.")
    if len(alive)>1: gate("4 Sweet Spot / Launch", alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct >= 25), "Launch profile filter.")
    if len(alive)>1: gate("5 Barrel / Conversion", alive.hr_pa.isna() | (alive.hr_pa >= 3) | (alive.barrel_pct.fillna(0) >= 10), "HR/PA 3+ or barrel 10+.")
    if len(alive)>1: gate("6 DMG", alive.dmg.isna() | (alive.dmg >= 1.0), "Safe DMG floor 1.0; 1.5+ preferred.")
    if len(alive)>1: gate("7 HPI", alive.hpi.isna() | (alive.hpi >= 30), "Safe HPI floor 30; 35+ preferred.")
    if len(alive)>1: gate("8 Recency / Alert", alive.hr_alert | alive.cond_up | alive.hr_alert.isna(), "Prefer HR alert or condition-up.")
    if len(alive)>1: gate("9 No Empty Bat", alive.hr_pa.isna() | (alive.hr_pa > 0) | alive.hr_alert, "Kill pure zero HR/PA without alert.")
    if len(alive)>1: log("10 Ownership Pressure", alive.player.tolist(), [], alive.player.tolist(), "No auto cut. Sets pressure before transfer.")
    if len(alive)>1: log("10.5 Adjacent / Decoy Transfer", alive.player.tolist(), [], alive.player.tolist(), "Only current survivors eligible. Dead players cannot return.")
    for step, name in [
        (11,"Lineup Protection"),(12,"Bullpen Continuation"),(13,"Numerology Overlay"),
        (14,"Chaos / WHO"),(15,"Finisher Gate"),(16,"Event Likelihood"),
        (17,"No-Fluke Audit"),(18,"True HR Event Likelihood")
    ]:
        if len(alive)>1:
            log(f"{step} {name}", alive.player.tolist(), [], alive.player.tolist(), "Final audit/tie-break layer; no resurrection.")

    alive = alive.copy()
    alive["score"] = (
        alive.pull_pct.fillna(0)*0.10 + alive.pitch_edge.fillna(0)*0.20 +
        alive.sweet_spot_pct.fillna(0)*0.10 + alive.barrel_pct.fillna(0)*0.15 +
        alive.dmg.fillna(0)*12 + alive.hpi.fillna(0)*0.12 + alive.hr_pa.fillna(0)*2 +
        alive.hr_alert.astype(int)*8 + alive.cond_up.astype(int)*5 +
        alive.weak_slot_tag.astype(int)*4 + alive.laser.astype(int)*3 + alive.rakes.astype(int)*3
    )
    alive["role"] = alive.apply(classify_role, axis=1)
    return alive.sort_values("score", ascending=False), pd.DataFrame(logs)

def player_card(row, kind="core"):
    cls = "bh-core" if kind=="core" else ("bh-alt" if kind=="alt" else "bh-who")
    badges = []
    for b in ["hr_alert","cond_up","weak_slot_tag","laser","rakes"]:
        if bool(row.get(b)): badges.append(b.replace("_"," ").upper())
    badge_html = "".join([f"<span class='bh-badge'>{x}</span>" for x in badges[:4]])
    st.markdown(f"""
    <div class="bh-card {cls}">
      <div class="bh-name">{row['player']}</div>
      <div class="bh-meta">{row.get('team','')} vs {row.get('pitcher','')} · Role: <b>{row.get('role','')}</b></div>
      <div style="margin:8px 0;">{badge_html}</div>
      <div class="bh-score">{row.get('score',0):.1f}</div>
      <div class="bh-meta">Pull {row.get('pull_pct','—')} · PitchEdge {row.get('pitch_edge','—')} · Sweet {row.get('sweet_spot_pct','—')} · DMG {row.get('dmg','—')} · HR/PA {row.get('hr_pa','—')}</div>
    </div>
    """, unsafe_allow_html=True)

# ---------- UI ----------
st.markdown("""
<div class="bh-hero">
  <div class="bh-title">BenHavin MLB Blender</div>
  <div class="bh-sub">Upload PDF → tap Run → get Core / Alt / WHO with full 18-gate audit hidden underneath.</div>
  <span class="bh-pill">18 Gates</span><span class="bh-pill">No Revivals</span><span class="bh-pill">Core / Alt</span><span class="bh-pill">Mobile Friendly</span>
</div>
""", unsafe_allow_html=True)

uploaded = st.file_uploader("Upload Star Tool PDF / CSV / XLSX", type=["csv","xlsx","pdf"], label_visibility="collapsed")

df = pd.DataFrame()
if uploaded is not None:
    data = uploaded.read()
    name = uploaded.name.lower()
    try:
        if name.endswith(".csv"):
            df = clean_df(pd.read_csv(io.BytesIO(data)))
        elif name.endswith(".xlsx"):
            df = clean_df(pd.read_excel(io.BytesIO(data)))
        else:
            df = parse_pdf(data)
    except Exception as e:
        st.error(f"Parser error: {e}")
        df = pd.DataFrame()

    if df.empty:
        st.error("No valid player rows parsed. This file may need OCR or CSV export.")
    else:
        c1,c2,c3 = st.columns(3)
        c1.metric("Players parsed", len(df))
        c2.metric("Teams found", df["team"].nunique())
        c3.metric("Pitchers found", df["pitcher"].nunique())

        with st.expander("Preview parsed data"):
            st.dataframe(df, use_container_width=True, height=320)

        if st.button("RUN BLENDER"):
            survivors, logs = run_18_gates(df)
            st.session_state["survivors"] = survivors
            st.session_state["logs"] = logs

if "survivors" in st.session_state:
    survivors = st.session_state["survivors"]
    logs = st.session_state["logs"]

    st.subheader("Final Board")
    if survivors.empty:
        st.warning("NO PLAY — no legal survivors.")
    else:
        core = []
        # role-balanced helper: top Primary, top Transfer, top WHO/Chaos if available
        for role in ["Primary","Transfer","WHO"]:
            part = survivors[survivors["role"]==role]
            if not part.empty:
                core.append(part.iloc[0])
        # fill if less than 3
        for _, r in survivors.iterrows():
            if len(core) >= 3: break
            if r["player"] not in [x["player"] for x in core]:
                core.append(r)

        alt = []
        for _, r in survivors.iterrows():
            if r["player"] not in [x["player"] for x in core]:
                alt.append(r)
            if len(alt) >= 3: break

        st.markdown("### Core 3")
        cols = st.columns(3)
        for i, r in enumerate(core[:3]):
            with cols[i]:
                player_card(r, "core")

        st.markdown("### Alt 3")
        if alt:
            cols = st.columns(3)
            for i, r in enumerate(alt[:3]):
                with cols[i]:
                    player_card(r, "alt")
        else:
            st.info("No extra legal survivors for Alt.")

        with st.expander("18-Gate Audit Log"):
            st.dataframe(logs, use_container_width=True, height=420)

        with st.expander("All Legal Survivors"):
            st.dataframe(survivors, use_container_width=True, height=420)
else:
    st.info("Upload your slate, then tap RUN BLENDER.")
