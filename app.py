
import re
import io
import pandas as pd
import streamlit as st
import requests
from bs4 import BeautifulSoup

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None

st.set_page_config(page_title="MLB HR Blender — Auto Gate Machine", layout="wide")
st.title("MLB Home Run Blender — Auto Gate Machine")
st.caption("Auto-pull from Star Tool URL when available. PDF/CSV/XLSX fallback included.")

REQUIRED_COLS = [
    "game","team","opponent","pitcher","player","bats","lineup_slot",
    "pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg",
    "hr_pa","pitch_type","pitch_edge","hr_alert","cond_up","weak_slot_tag",
    "laser","rakes","platoon","weak_slots"
]

def normalize_pct(x):
    if pd.isna(x): return None
    if isinstance(x, (int, float)): return float(x)
    s = str(x).replace("%","").replace("+","").strip()
    try: return float(s)
    except: return None

def normalize_bool(x):
    if isinstance(x, bool): return x
    s = str(x).strip().lower()
    return s in ["1","true","yes","y","alert","hot","x"]

def clean_df(df):
    df.columns = [str(c).strip().lower().replace(" ","_") for c in df.columns]
    for c in REQUIRED_COLS:
        if c not in df.columns:
            df[c] = None
    for c in ["pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","lineup_slot"]:
        df[c] = df[c].apply(normalize_pct)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon"]:
        df[c] = df[c].apply(normalize_bool)
    df["player"] = df["player"].astype(str).str.strip()
    return df[df["player"].notna() & (df["player"].str.len() > 1)]

def parse_pdf_text(file_bytes):
    if fitz is None:
        return ""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc)

def parse_star_tool_lines(lines):
    rows = []
    current_team = ""
    current_pitcher = ""
    weak_slots_by_pitcher = {}

    for l in lines:
        m = re.search(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s+#?(\d+),\s*#?(\d+),\s*#?(\d+)", l, re.I)
        if m:
            weak_slots_by_pitcher[m.group(1).strip()] = f"{m.group(2)},{m.group(3)},{m.group(4)}"

    i = 0
    while i < len(lines):
        line = lines[i]
        tm = re.search(r"^([A-Z\s]+?)\s+PROJECTED\s+vs\.\s+(.+?)\s+~", line, re.I)
        if tm:
            current_team = tm.group(1).strip().title()
            current_pitcher = tm.group(2).strip()
            i += 1
            continue

        if re.match(r"^\d+$", line) and i+1 < len(lines):
            name = lines[i+1].strip()
            block = " ".join(lines[i+1:i+14])
            if len(name.split()) >= 2 and not any(tok in name.lower() for tok in ["projected", "weak:", "lineup"]):
                slot = None
                sm = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", block)
                if sm: slot = int(sm.group(1))

                pcts = re.findall(r"([+-]?\d+(?:\.\d+)?)%", block)
                pull = float(pcts[0]) if pcts else None

                line_m = re.search(r"LINE\s+[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%", block)
                sweet = float(line_m.group(1)) if line_m else None

                hrpa_m = re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA", block)
                hrpa = float(hrpa_m.group(1)) if hrpa_m else None

                dmg_m = re.search(r"([0-9]+(?:\.\d+)?)\s+DMG", block)
                dmg = float(dmg_m.group(1)) if dmg_m else None

                pe = None; pt = None
                pem = re.search(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z0-9\-]+)", block)
                if pem:
                    pe = float(pem.group(1))
                    pt = pem.group(2)

                hpi = None
                hpi_candidates = re.findall(r"\+\s*(\d+)", block)
                if hpi_candidates:
                    vals = [int(x) for x in hpi_candidates if 10 <= int(x) <= 90]
                    hpi = vals[-1] if vals else None

                rows.append({
                    "game": "",
                    "team": current_team,
                    "opponent": "",
                    "pitcher": current_pitcher,
                    "player": name,
                    "bats": "",
                    "lineup_slot": slot,
                    "pull_pct": pull,
                    "barrel_pct": None,
                    "sweet_spot_pct": sweet,
                    "hard_hit_pct": None,
                    "hpi": hpi,
                    "dmg": dmg,
                    "hr_pa": hrpa,
                    "pitch_type": pt,
                    "pitch_edge": pe,
                    "hr_alert": "ALERT" in block,
                    "cond_up": "COND ↑" in block,
                    "weak_slot_tag": "Weak Slot" in block,
                    "laser": "Laser" in block,
                    "rakes": "Rakes" in block,
                    "platoon": "Platoon" in block,
                    "weak_slots": weak_slots_by_pitcher.get(current_pitcher, ""),
                })
                i += 12
                continue
        i += 1
    return clean_df(pd.DataFrame(rows)) if rows else pd.DataFrame()

def crude_star_tool_pdf_parse(file_bytes):
    text = parse_pdf_text(file_bytes)
    if not text or len(text.strip()) < 100:
        return pd.DataFrame()
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return parse_star_tool_lines(lines)

def fetch_star_tool_url(url):
    headers = {"User-Agent": "Mozilla/5.0 AppleWebKit/537.36 Chrome/124 Safari/537.36"}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n", strip=True)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return parse_star_tool_lines(lines)

def run_gates(df):
    d = clean_df(df.copy())
    logs = []
    alive = d.copy()

    def add_log(name, before, cut, after, reason):
        logs.append({
            "gate": name,
            "alive_before": ", ".join(before),
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
        add_log(name, before, cut, after, reason)

    if alive.empty:
        return alive, pd.DataFrame(logs)

    gate("Step 1 — Pull %", alive["pull_pct"].fillna(0) >= 20, "20% minimum. 40%+ elite when available.")
    if len(alive) > 1:
        gate("Step 2 — Matchup / Pitch Edge", alive["pitch_edge"].fillna(-999) >= 0, "Must not lose vs listed pitch type.")
    if len(alive) > 1:
        def slot_ok(row):
            ws = str(row.get("weak_slots") or "")
            slots = [int(x) for x in re.findall(r"\d+", ws)]
            slot = row.get("lineup_slot")
            if not slots or pd.isna(slot): return True
            return int(slot) in slots or bool(row.get("weak_slot_tag"))
        gate("Step 3 — Zones / Weak Slot", alive.apply(slot_ok, axis=1), "Lineup slot must align if weak-slot data exists.")
    if len(alive) > 1:
        gate("Step 4 — Sweet Spot / Launch", alive["sweet_spot_pct"].fillna(0) >= 25, "Separates fake pressure from real HR launch.")
    if len(alive) > 1:
        gate("Step 5 — Barrel / Conversion", (alive["hr_pa"].fillna(0) >= 3) | (alive["barrel_pct"].fillna(0) >= 10), "Need HR conversion or 10%+ barrel.")
    if len(alive) > 1:
        gate("Step 6 — DMG", alive["dmg"].fillna(0) >= 1.5, "1.5+ solid, 2.0+ elite.")
    if len(alive) > 1:
        gate("Step 7 — HPI", alive["hpi"].fillna(0) >= 35, "HPI 35+ support layer.")
    if len(alive) > 1:
        gate("Step 8 — Alert / Recency", alive["hr_alert"] | alive["cond_up"], "Need HR alert or condition up.")
    if len(alive) > 1:
        before = alive["player"].tolist()
        add_log("Step 9 — Chalk Trap Audit", before, [], before, "Manual review: avoid obvious chalk trap unless all gates support.")
    if len(alive) > 1:
        before = alive["player"].tolist()
        add_log("Step 10.5 — Transfer Audit", before, [], before, "Only current survivors eligible. Dead players cannot return.")

    alive["score"] = (
        alive["pull_pct"].fillna(0)*0.15 +
        alive["pitch_edge"].fillna(0)*0.20 +
        alive["sweet_spot_pct"].fillna(0)*0.15 +
        alive["barrel_pct"].fillna(0)*0.15 +
        alive["dmg"].fillna(0)*12 +
        alive["hpi"].fillna(0)*0.15 +
        alive["hr_pa"].fillna(0)*2 +
        alive["hr_alert"].astype(int)*8 +
        alive["cond_up"].astype(int)*5
    )
    return alive.sort_values("score", ascending=False), pd.DataFrame(logs)

st.sidebar.header("Data source")
source = st.sidebar.radio("Choose source", ["Auto-pull URL", "Upload PDF/CSV/XLSX"])

df = pd.DataFrame()

if source == "Auto-pull URL":
    url = st.sidebar.text_input("Star Tool URL", value="https://mlbstartool.com/")
    if st.sidebar.button("Pull data"):
        try:
            with st.spinner("Pulling page..."):
                df = fetch_star_tool_url(url)
            if df.empty:
                st.error("No rows found from URL. Site may require login or JavaScript. Use PDF upload fallback.")
            else:
                st.success(f"Pulled {len(df)} rows.")
        except Exception as e:
            st.error(f"Auto-pull failed: {e}")

else:
    up = st.file_uploader("Upload Star Tool CSV/XLSX/PDF", type=["csv","xlsx","pdf"])
    if up is not None:
        name = up.name.lower()
        data = up.read()
        try:
            if name.endswith(".csv"):
                df = clean_df(pd.read_csv(io.BytesIO(data)))
            elif name.endswith(".xlsx"):
                df = clean_df(pd.read_excel(io.BytesIO(data)))
            elif name.endswith(".pdf"):
                df = crude_star_tool_pdf_parse(data)
            if df.empty:
                st.error("No rows found. This PDF may be image-only/OCR-required.")
            else:
                st.success(f"Loaded {len(df)} rows.")
        except Exception as e:
            st.error(f"Load failed: {e}")

if not df.empty:
    st.subheader("Parsed Preview")
    st.dataframe(df.head(100), use_container_width=True)

    if st.button("RUN BLENDER"):
        survivors, log = run_gates(df)
        st.subheader("Gate Log")
        st.dataframe(log, use_container_width=True)

        st.subheader("Final Survivors")
        if survivors.empty:
            st.warning("NO PLAY — no legal survivors.")
        else:
            st.dataframe(survivors, use_container_width=True)

st.divider()
st.caption("Auto-pull only works when source exposes data without login/JS blocking. Otherwise upload PDF.")
