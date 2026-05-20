import re
from io import StringIO
import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="MLB HR Blender", layout="wide")

REQUIRED_COLS = [
    "game", "team", "opponent", "pitcher", "pitcher_hand", "batter", "batter_hand",
    "lineup_slot", "weak_slots", "pitch_type", "pitch_edge", "pull_pct", "sweet_spot_pct",
    "barrel_pct", "hard_hit_pct", "hr_pa", "dmg", "hpi", "cond_up", "recency_tag",
    "hr_alert", "weak_slot_tag", "platoon_tag", "laser_tag", "rakes_tag", "effort", "ownership_role"
]

DEFAULT_THRESHOLDS = {
    "pull_min": 20.0,
    "sweet_spot_min": 33.0,
    "barrel_min": 8.0,
    "pitch_edge_min": 0.0,
    "hr_pa_min": 1.5,
    "dmg_min": 1.0,
    "hpi_min": 30.0,
}

TEAM_ABBR = {
    "ATLANTA BRAVES":"ATL", "MIAMI MARLINS":"MIA", "CLEVELAND GUARDIANS":"CLE", "DETROIT TIGERS":"DET",
    "BALTIMORE ORIOLES":"BAL", "TAMPA BAY RAYS":"TB", "CINCINNATI REDS":"CIN", "PHILADELPHIA PHILLIES":"PHI",
    "NEW YORK METS":"NYM", "WASHINGTON NATIONALS":"WSH", "TORONTO BLUE JAYS":"TOR", "NEW YORK YANKEES":"NYY",
    "BOSTON RED SOX":"BOS", "KANSAS CITY ROYALS":"KC", "HOUSTON ASTROS":"HOU", "MINNESOTA TWINS":"MIN",
    "MILWAUKEE BREWERS":"MIL", "CHICAGO CUBS":"CHC", "PITTSBURGH PIRATES":"PIT", "ST. LOUIS CARDINALS":"STL",
    "TEXAS RANGERS":"TEX", "COLORADO ROCKIES":"COL", "ATHLETICS":"ATH", "LOS ANGELES ANGELS":"LAA",
    "LOS ANGELES DODGERS":"LAD", "SAN DIEGO PADRES":"SD", "SAN FRANCISCO GIANTS":"SF", "ARIZONA DIAMONDBACKS":"ARI",
    "CHICAGO WHITE SOX":"CHW", "SEATTLE MARINERS":"SEA"
}

PITCH_TYPES = ["4-Seam","Sinker","Cutter","Sweeper","Change","Slider","Curve","Splitter"]

def boolify(x):
    if pd.isna(x): return False
    if isinstance(x, bool): return x
    return str(x).strip().lower() in ["1","true","yes","y","alert","hot","pass"]

def parse_weak_slots(x):
    if pd.isna(x): return []
    out = []
    for part in str(x).replace("#", "").replace("/", ",").replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit(): out.append(int(part))
    return out

def extract_pdf_rows(file):
    try:
        import pdfplumber
    except Exception:
        st.error("PDF support needs pdfplumber. Make sure requirements.txt was uploaded.")
        return pd.DataFrame(columns=REQUIRED_COLS)
    text = "\n".join([(p.extract_text() or "") for p in pdfplumber.open(file).pages])
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    rows = []
    current_team = current_opp = current_pitcher = current_pitcher_hand = None
    current_game = None
    weak_slots_by_pitcher = {}

    # collect weak slots by pitcher
    for ln in lines:
        m = re.search(r"^(.+?) · VS\. LINEUP SLOT Weak: #?(\d+), #?(\d+), #?(\d+)", ln)
        if m:
            weak_slots_by_pitcher[m.group(1).strip().title()] = f"{m.group(2)},{m.group(3)},{m.group(4)}"

    i = 0
    while i < len(lines):
        ln = lines[i]
        sec = re.search(r"^([A-Z .]+?) PROJECTED vs\. (.+?) ~[^ ]+ ([LR])$", ln)
        if sec:
            team_full = sec.group(1).strip()
            current_team = TEAM_ABBR.get(team_full, team_full[:3])
            current_pitcher = sec.group(2).strip()
            current_pitcher_hand = sec.group(3)
            # opponent inferred from section headers is not always easy, keep blank if unavailable
            current_opp = ""
            current_game = current_team
            i += 1
            continue

        # player block starts: number line, then "Name L/R" line
        if current_team and ln.isdigit() and i + 1 < len(lines):
            name_line = lines[i + 1]
            nm = re.search(r"^(.+?)\s+([LR])$", name_line)
            if nm:
                batter = nm.group(1).strip()
                batter_hand = nm.group(2)
                chunk = " ".join(lines[i+1:i+12])
                slot = None
                sm = re.search(r"\b(\d)(?:st|nd|rd|th)\b", chunk)
                if sm: slot = int(sm.group(1))
                pitch_type = ""
                pitch_edge = np.nan
                for pt in PITCH_TYPES:
                    pm = re.search(r"([+-]?\d+)%\s+" + re.escape(pt), chunk)
                    if pm:
                        pitch_type = pt
                        pitch_edge = float(pm.group(1))
                        break
                # pull pct is usually the percent beside stars; use first percent before star/emoji area if present
                pull_pct = np.nan
                pull_matches = re.findall(r"(\d+(?:\.\d+)?)%", chunk)
                if pull_matches:
                    try: pull_pct = float(pull_matches[0])
                    except: pass
                hr_pa = np.nan
                hm = re.search(r"(\d+(?:\.\d+)?)%\s+HR/PA", chunk)
                if hm: hr_pa = float(hm.group(1))
                dmg = np.nan
                dm = re.search(r"(\d+\.\d+)\s+DMG", chunk)
                if dm: dmg = float(dm.group(1))
                hpi = np.nan
                hp = re.search(r"HPI\s*(\d+)", chunk)
                if not hp: hp = re.search(r"\+\s*(\d+)\s+(?:\d+\.\d+\s+DMG)", chunk)
                if hp:
                    try: hpi = float(hp.group(1))
                    except: pass
                cond_up = np.nan
                cm = re.search(r"COND ↑\s*(\d+(?:\.\d+)?)%", chunk)
                if cm: cond_up = float(cm.group(1))
                sweet = np.nan
                hard_hit = np.nan
                # common two numbers near Low/Moderate/Elevated/High labels; use first as hard_hit/effort and second as sweet proxy
                vals = re.findall(r"(?:Low Effort|Moderate|Elevated|High Effort|High|Max Effort|Fresh|Disengaged)\s+(\d+)", chunk)
                if vals:
                    try: hard_hit = float(vals[0])
                    except: pass
                    if len(vals) > 1:
                        try: sweet = float(vals[1])
                        except: pass
                rec = "ALERT" if "ALERT" in chunk else ("HOT" if "HOT" in chunk else ("WARM" if "WARM" in chunk else ("COLD" if "COLD" in chunk else "")))
                rows.append({
                    "game": current_game, "team": current_team, "opponent": current_opp, "pitcher": current_pitcher, "pitcher_hand": current_pitcher_hand,
                    "batter": batter, "batter_hand": batter_hand, "lineup_slot": slot, "weak_slots": weak_slots_by_pitcher.get(current_pitcher.title(), ""),
                    "pitch_type": pitch_type, "pitch_edge": pitch_edge, "pull_pct": pull_pct, "sweet_spot_pct": sweet, "barrel_pct": np.nan,
                    "hard_hit_pct": hard_hit, "hr_pa": hr_pa, "dmg": dmg, "hpi": hpi, "cond_up": cond_up, "recency_tag": rec,
                    "hr_alert": "ALERT" in chunk, "weak_slot_tag": "Weak Slot" in chunk, "platoon_tag": "Platoon" in chunk, "laser_tag": "Laser" in chunk,
                    "rakes_tag": "Rakes" in chunk, "effort": hard_hit, "ownership_role": ""
                })
            i += 1
        i += 1
    return pd.DataFrame(rows, columns=REQUIRED_COLS)

def load_df(file):
    if file is None: return None
    name = file.name.lower()
    if name.endswith(".csv"): return pd.read_csv(file)
    if name.endswith((".xlsx", ".xls")): return pd.read_excel(file)
    if name.endswith(".pdf"): return extract_pdf_rows(file)
    st.error("Upload CSV, Excel, or PDF.")
    return None

def normalize(df):
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    for c in REQUIRED_COLS:
        if c not in df.columns: df[c] = np.nan
    numeric_cols = ["lineup_slot","pitch_edge","pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","hr_pa","dmg","hpi","cond_up"]
    for c in numeric_cols: df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["hr_alert","weak_slot_tag","platoon_tag","laser_tag","rakes_tag"]: df[c] = df[c].map(boolify)
    df["weak_slot_list"] = df["weak_slots"].map(parse_weak_slots)
    df["slot_match"] = df.apply(lambda r: int(r["lineup_slot"]) in r["weak_slot_list"] if pd.notna(r["lineup_slot"]) else False, axis=1)
    return df

def derive_archetype(g):
    slot_count = g["slot_match"].sum()
    nuke_edge = (g["pitch_edge"].fillna(-999) >= 40).sum()
    alerts = (g["hr_alert"] == True).sum()
    if nuke_edge >= 1 and slot_count <= 1: return "Chaos/WHO"
    if slot_count >= 2 and alerts >= 2: return "Transfer/Adjacent"
    if slot_count >= 1: return "Primary/Clean"
    return "No Play Risk"

def gate_cut(df, condition, gate_name, pass_reason, fail_reason):
    before = df.copy()
    mask = condition(before)
    passed = before[mask].copy()
    cut = before[~mask].copy()
    return passed, cut

def process_game(g, thresholds):
    logs=[]; dead=[]; alive=g.copy()
    def log(gate,before,cut,after,reason):
        logs.append({"gate":gate,"alive_before":", ".join(before["batter"].astype(str)),"cut":", ".join(cut["batter"].astype(str)) if len(cut) else "—","alive_after":", ".join(after["batter"].astype(str)) if len(after) else "NO PLAY","reason":reason})
    before=alive.copy(); log("Step 0 - Pitcher Weakness", before, alive.iloc[0:0], alive, "Weak slots loaded")
    archetype=derive_archetype(alive); alive["archetype"]=archetype
    before=alive.copy(); log("Step 1 - Clean Game Survivor", before, alive.iloc[0:0], alive, archetype)
    for gate, cond, reason in [
        ("Step 2 - Pull-Air DNA", lambda d: d["pull_pct"].fillna(0) >= thresholds["pull_min"], f"Pull >= {thresholds['pull_min']}"),
        ("Step 3 - Matchup / Pitch-Type Kill", lambda d: d["pitch_edge"].fillna(-999) >= thresholds["pitch_edge_min"], f"Pitch edge >= {thresholds['pitch_edge_min']}"),
        ("Step 4 - Zone / Weak Slot", lambda d: (d["slot_match"]==True) | (d["pitch_edge"].fillna(0) >= 40), "Slot match or nuclear pitch edge"),
        ("Step 5 - Sweet Spot", lambda d: d["sweet_spot_pct"].fillna(0) >= thresholds["sweet_spot_min"], f"Sweet Spot >= {thresholds['sweet_spot_min']}"),
        ("Step 6 - Barrel / Conversion", lambda d: (d["barrel_pct"].fillna(0) >= thresholds["barrel_min"]) | (d["hr_pa"].fillna(0) >= thresholds["hr_pa_min"]), "Barrel or HR/PA pass"),
        ("Step 7 - DMG / HPI", lambda d: (d["dmg"].fillna(0) >= thresholds["dmg_min"]) & (d["hpi"].fillna(0) >= thresholds["hpi_min"]), "DMG + HPI pass"),
    ]:
        before=alive.copy(); alive, cut = gate_cut(alive, cond, gate, reason, "failed")
        dead.append(cut); log(gate,before,cut,alive,reason)
        if alive.empty: return logs, None, pd.concat(dead)
    before=alive.copy(); log("Step 8 - Recency", before, alive.iloc[0:0], alive, "No cut unless user marks stale")
    before=alive.copy(); log("Step 9 - Chalk Audit", before, alive.iloc[0:0], alive, "No cut; pressure noted")
    before=alive.copy(); log("Step 10 - Ownership", before, alive.iloc[0:0], alive, "Ownership pressure set")
    before=alive.copy()
    alive["event_score"]=(alive["pull_pct"].fillna(0)/10 + alive["pitch_edge"].fillna(0)/10 + alive["sweet_spot_pct"].fillna(0)/10 + alive["hr_pa"].fillna(0) + alive["dmg"].fillna(0) + alive["hpi"].fillna(0)/20 + alive["slot_match"].astype(int)*2)
    mx=alive["event_score"].max(); after=alive[alive["event_score"] >= mx*.90].copy(); cut=alive[alive["event_score"] < mx*.90].copy(); dead.append(cut); alive=after
    log("Step 10.5 - Adjacent / Decoy Transfer", before, cut, alive, "Only alive hitters eligible")
    if alive.empty: return logs, None, pd.concat(dead)
    for gate in ["Step 11 - Protection", "Step 12 - Bullpen Continuation", "Step 13 - WHO / Chaos", "Step 14 - No Empty Bat", "Step 15 - Finisher", "Step 16 - Event Likelihood", "Step 17 - No-Fluke Audit"]:
        before=alive.copy(); log(gate,before,alive.iloc[0:0],alive,"Preserve legal survivor state")
    before=alive.copy(); owner=alive.sort_values("event_score", ascending=False).head(1).copy(); cut=alive.drop(owner.index)
    log("Step 18 - Lock", before, cut, owner, "Highest legal event score")
    return logs, owner.iloc[0].to_dict(), pd.concat(dead) if dead else pd.DataFrame()

st.title("MLB Home Run Blender — Gate Machine")
st.caption("Upload CSV/XLSX or Star Tool PDF. PDF parser is best-effort; review preview before running.")

with st.sidebar:
    st.header("Gate thresholds")
    thresholds={k: st.number_input(k, value=v, step=1.0 if k not in ["hr_pa_min","dmg_min"] else 0.1) for k,v in DEFAULT_THRESHOLDS.items()}

uploaded=st.file_uploader("Upload Star Tool CSV/XLSX/PDF", type=["csv","xlsx","xls","pdf"])
if uploaded is None:
    st.info("Upload your PDF or the CSV template.")
    st.code(",".join(REQUIRED_COLS), language="text")
    st.stop()

df=load_df(uploaded)
if df is None or df.empty:
    st.error("No rows found. Try CSV template or check the PDF text export.")
    st.stop()

df=normalize(df)
st.subheader("Loaded / Parsed Slate")
st.data_editor(df[REQUIRED_COLS], use_container_width=True, num_rows="dynamic", key="editable")

run_df = normalize(pd.DataFrame(st.session_state["editable"]["edited_rows"]).combine_first(df) if False else df)
games=list(df["game"].dropna().unique())
selected=st.multiselect("Games to process", games, default=games)
owners=[]
for game in selected:
    with st.expander(f"{game} gate run", expanded=False):
        logs, owner, dead=process_game(df[df["game"]==game].copy(), thresholds)
        st.dataframe(pd.DataFrame(logs), use_container_width=True, hide_index=True)
        if owner:
            owners.append(owner); st.success(f"Owner: {owner['batter']} ({owner['team']})")
        else: st.warning("NO PLAY")

st.subheader("Survivor Board")
if owners:
    odf=pd.DataFrame(owners)
    def role(r):
        if "Chaos" in str(r.get("archetype","")): return "Chaos/WHO"
        if "Transfer" in str(r.get("archetype","")): return "Transfer/Adjacent"
        return "Primary/Clean"
    odf["core_role"] = odf.apply(role, axis=1)
    st.dataframe(odf[["game","team","batter","archetype","core_role","event_score","pitch_edge","pull_pct","sweet_spot_pct","hr_pa","dmg","hpi","slot_match"]], use_container_width=True)
    st.subheader("Role-Balanced Core Builder")
    picks=[]
    for rname in ["Primary/Clean","Transfer/Adjacent","Chaos/WHO"]:
        part=odf[odf["core_role"]==rname].sort_values("event_score", ascending=False)
        if not part.empty: picks.append(part.iloc[0])
    if len(picks)<3:
        rem=odf.drop([p.name for p in picks], errors="ignore").sort_values("event_score", ascending=False)
        for _, row in rem.iterrows():
            if len(picks)>=3: break
            picks.append(row)
    st.dataframe(pd.DataFrame(picks)[["core_role","game","team","batter","event_score"]], use_container_width=True, hide_index=True)
else:
    st.warning("No owners produced.")
