
import re, io
import pandas as pd
import streamlit as st

try:
    import fitz
except Exception:
    fitz = None

st.set_page_config(page_title="MLB Blender — 18 Gate Machine", layout="wide")
st.title("MLB Home Run Blender — 18 Gate Machine")
st.caption("PDF/CSV/XLSX → 18 gates → survivor board → Core/Alt. Dead players cannot return.")

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
    df = df[df["player"].apply(is_player_name)].copy()
    return df[COLS]

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

        # Team section
        sec = re.search(r"^([A-Z\s]+?)\s+PROJECTED\s+vs\.\s+(.+?)\s+~", line, re.I)
        if sec:
            team = sec.group(1).strip().title()
            pitcher = sec.group(2).strip()
            i += 1
            continue

        # Ranking number followed by likely player name
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

                hpi = None
                pluses = [int(x) for x in re.findall(r"\+\s*(\d+)", block) if 10 <= int(x) <= 90]
                if pluses: hpi = pluses[-1]

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

def run_18_gates(df):
    df = clean_df(df.copy())
    alive = df.copy()
    logs = []

    def log(gate, before, cut, after, reason):
        logs.append({
            "gate": gate,
            "alive_before_count": len(before),
            "cut_count": len(cut),
            "alive_after_count": len(after),
            "cut": ", ".join(cut),
            "alive_after": ", ".join(after),
            "reason": reason
        })

    def gate(name, mask, reason):
        nonlocal alive
        before = alive["player"].tolist()
        cut = alive.loc[~mask, "player"].tolist()
        alive = alive[mask].copy()
        after = alive["player"].tolist()
        log(name, before, cut, after, reason)

    if alive.empty:
        return alive, pd.DataFrame(logs)

    # Missing values survive for manual review. Bad known values die.
    gate("Step 1 — Pull %", alive.pull_pct.isna() | (alive.pull_pct >= 20), "Kill under 20 pull only when value exists.")
    if len(alive)>1: gate("Step 2 — Matchup / Pitch Edge", alive.pitch_edge.isna() | (alive.pitch_edge >= 0), "Kill negative pitch edge when listed.")
    if len(alive)>1: gate("Step 3 — Zones / Weak Slot", alive.apply(slot_ok, axis=1), "Must match pitcher weak slot if both slot datasets exist.")
    if len(alive)>1: gate("Step 4 — Sweet Spot / Launch", alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct >= 25), "Launch profile filter.")
    if len(alive)>1: gate("Step 5 — Barrel / Conversion", alive.hr_pa.isna() | (alive.hr_pa >= 3) | (alive.barrel_pct.fillna(0) >= 10), "HR/PA 3+ or barrel 10+.")
    if len(alive)>1: gate("Step 6 — DMG", alive.dmg.isna() | (alive.dmg >= 1.0), "Safe DMG floor 1.0; 1.5+ preferred.")
    if len(alive)>1: gate("Step 7 — HPI", alive.hpi.isna() | (alive.hpi >= 30), "Safe HPI floor 30; 35+ preferred.")
    if len(alive)>1: gate("Step 8 — Recency / Alert", alive.hr_alert | alive.cond_up | alive.hr_alert.isna(), "Prefer HR alert or condition-up.")
    if len(alive)>1: gate("Step 9 — No Empty Bat", alive.hr_pa.isna() | (alive.hr_pa > 0) | alive.hr_alert, "Kill pure zero HR/PA without alert.")
    if len(alive)>1:
        before = alive.player.tolist()
        log("Step 10 — Ownership Pressure", before, [], before, "No auto cut. Identifies pressure before transfer.")
    if len(alive)>1:
        before = alive.player.tolist()
        log("Step 10.5 — Adjacent / Decoy Transfer", before, [], before, "Only current survivors eligible. Dead players cannot return.")
    if len(alive)>1: gate("Step 11 — Lineup Protection", pd.Series([True]*len(alive), index=alive.index), "Manual protection check placeholder.")
    if len(alive)>1: gate("Step 12 — Bullpen Continuation", pd.Series([True]*len(alive), index=alive.index), "Manual bullpen check placeholder.")
    if len(alive)>1: gate("Step 13 — Numerology Overlay", pd.Series([True]*len(alive), index=alive.index), "Tie-break only, no override.")
    if len(alive)>1: gate("Step 14 — Chaos / WHO", pd.Series([True]*len(alive), index=alive.index), "Manual chaos check; no forced WHO.")
    if len(alive)>1: gate("Step 15 — Finisher Gate", alive.dmg.isna() | (alive.dmg >= 1.2) | (alive.hr_pa.fillna(0) >= 4), "Finisher profile.")
    if len(alive)>1: gate("Step 16 — Event Likelihood", pd.Series([True]*len(alive), index=alive.index), "Keeps legal survivors for ranking.")
    if len(alive)>1: gate("Step 17 — No-Fluke Audit", pd.Series([True]*len(alive), index=alive.index), "No recap anchoring; no resurrection.")
    if len(alive)>1: gate("Step 18 — True HR Event Likelihood", pd.Series([True]*len(alive), index=alive.index), "Final legal survivor set.")

    alive = alive.copy()
    alive["score"] = (
        alive.pull_pct.fillna(0)*0.10 +
        alive.pitch_edge.fillna(0)*0.20 +
        alive.sweet_spot_pct.fillna(0)*0.10 +
        alive.barrel_pct.fillna(0)*0.15 +
        alive.dmg.fillna(0)*12 +
        alive.hpi.fillna(0)*0.12 +
        alive.hr_pa.fillna(0)*2 +
        alive.hr_alert.astype(int)*8 +
        alive.cond_up.astype(int)*5 +
        alive.weak_slot_tag.astype(int)*4 +
        alive.laser.astype(int)*3 +
        alive.rakes.astype(int)*3
    )
    return alive.sort_values("score", ascending=False), pd.DataFrame(logs)

uploaded = st.file_uploader("Upload Star Tool CSV/XLSX/PDF", type=["csv","xlsx","pdf"])

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

if uploaded is not None:
    if df.empty:
        st.error("No valid player rows parsed. This file may need OCR or CSV export.")
    else:
        st.success(f"Parsed {len(df)} player rows.")
        st.subheader("Parsed Preview")
        st.dataframe(df, use_container_width=True)

        if st.button("RUN BLENDER"):
            survivors, logs = run_18_gates(df)
            st.subheader("18-Gate Log")
            st.dataframe(logs, use_container_width=True)

            st.subheader("Final Survivors")
            if survivors.empty:
                st.warning("NO PLAY — no legal survivors.")
            else:
                st.dataframe(survivors, use_container_width=True)

                st.subheader("Core / Alt Helper")
                top = survivors.head(6)
                st.write("Core candidates are the top legal survivors. Manually choose role balance: Primary / Transfer / WHO.")
                st.dataframe(top[["player","team","pitcher","score","pull_pct","pitch_edge","sweet_spot_pct","hpi","dmg","hr_pa","weak_slot_tag","laser","rakes"]], use_container_width=True)

st.divider()
st.caption("This app does not revive cut players. Missing parsed stats survive instead of being auto-killed so you can review the preview.")
