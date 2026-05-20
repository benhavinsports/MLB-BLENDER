import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO

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

GATE_ORDER = [
    "Step 0 - Slate / Pitcher Weakness",
    "Step 1 - Clean Game Survivor",
    "Step 2 - Archetype",
    "Step 3 - Attack Side Lock",
    "Step 4 - Pull-Air DNA",
    "Step 5 - Pitch-Type Kill",
    "Step 6 - Zone / Weak Slot",
    "Step 7 - Sweet Spot",
    "Step 8 - Barrel / Conversion",
    "Step 9 - Damage / HPI",
    "Step 10 - Ownership Pressure",
    "Step 10.5 - Adjacent / Decoy Transfer",
    "Step 11 - Protection",
    "Step 12 - Bullpen Continuation",
    "Step 13 - WHO / Chaos",
    "Step 14 - No Empty Bat",
    "Step 15 - Finisher",
    "Step 16 - Event Likelihood",
    "Step 17 - No-Fluke Audit",
    "Step 18 - Lock",
]

def boolify(x):
    if pd.isna(x):
        return False
    if isinstance(x, bool):
        return x
    return str(x).strip().lower() in ["1", "true", "yes", "y", "alert", "hot", "pass"]

def parse_weak_slots(x):
    if pd.isna(x):
        return []
    out = []
    for part in str(x).replace("#", "").replace("/", ",").replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out

def load_df(file):
    if file is None:
        return None
    if file.name.lower().endswith(".csv"):
        return pd.read_csv(file)
    if file.name.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(file)
    st.error("Upload CSV or Excel. Export the Star Tool table into rows first.")
    return None

def normalize(df):
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    for c in missing:
        df[c] = np.nan
    numeric_cols = ["lineup_slot", "pitch_edge", "pull_pct", "sweet_spot_pct", "barrel_pct", "hard_hit_pct", "hr_pa", "dmg", "hpi", "cond_up"]
    for c in numeric_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["hr_alert", "weak_slot_tag", "platoon_tag", "laser_tag", "rakes_tag"]:
        df[c] = df[c].map(boolify)
    df["weak_slot_list"] = df["weak_slots"].map(parse_weak_slots)
    df["slot_match"] = df.apply(lambda r: int(r["lineup_slot"]) in r["weak_slot_list"] if pd.notna(r["lineup_slot"]) else False, axis=1)
    return df

def gate_cut(df, condition, gate_name, reason_pass, reason_fail):
    before = df.copy()
    passed = before[condition(before)].copy()
    cut = before[~condition(before)].copy()
    passed["last_reason"] = reason_pass
    cut["cut_gate"] = gate_name
    cut["cut_reason"] = reason_fail
    return passed, cut

def derive_archetype(g):
    top = g.sort_values(["slot_match", "pitch_edge", "hr_pa", "dmg"], ascending=False).head(4)
    primary_count = ((top["hr_alert"] == True) & (top["pull_pct"].fillna(0) >= 20)).sum()
    slot_count = top["slot_match"].sum()
    if slot_count >= 2 and primary_count >= 2:
        return "Transfer / Adjacent Pressure"
    if slot_count >= 2 and top["dmg"].fillna(0).max() >= 1.8:
        return "Clean Power / Slot Stability"
    if primary_count <= 1 and slot_count >= 1:
        return "Underdog / Hidden Lane"
    return "Chaos / WHO Risk"

def process_game(g, thresholds, force_game_alive=True):
    logs = []
    dead = []
    alive = g.copy()
    game_name = alive["game"].iloc[0]

    def log(gate, before, cut, after, reason):
        logs.append({
            "gate": gate,
            "alive_before": ", ".join(before["batter"].astype(str).tolist()),
            "cut": ", ".join(cut["batter"].astype(str).tolist()) if len(cut) else "—",
            "alive_after": ", ".join(after["batter"].astype(str).tolist()) if len(after) else "NO PLAY",
            "reason": reason
        })

    # Step 0
    before = alive.copy(); cut = alive.iloc[0:0].copy()
    log("Step 0 - Pitcher Weakness", before, cut, alive, "Weak-slot map loaded; no hitter cuts.")

    # Step 1 clean game survivor: in-app version does not kill automatically unless no weak slots/pitcher info.
    before = alive.copy()
    if force_game_alive:
        cut = alive.iloc[0:0].copy()
        after = alive
        reason = "Game kept for full processing."
    else:
        cond = before["weak_slot_list"].map(len) > 0
        after = before[cond].copy(); cut = before[~cond].copy()
        reason = "Remove only if no pitcher weak-slot data."
    alive = after
    log("Step 1 - Clean Game Survivor", before, cut, alive, reason)
    if alive.empty: return logs, None, pd.DataFrame()

    # Step 2 archetype
    archetype = derive_archetype(alive)
    before = alive.copy(); cut = alive.iloc[0:0].copy()
    alive["archetype"] = archetype
    log("Step 2 - Archetype", before, cut, alive, archetype)

    # Step 3 attack side lock
    before = alive.copy(); cut = alive.iloc[0:0].copy()
    log("Step 3 - Attack Side Lock", before, cut, alive, "Team side already isolated by game/team rows.")

    # Step 4 pull-air
    alive, cut = gate_cut(alive, lambda d: d["pull_pct"].fillna(0) >= thresholds["pull_min"], "Step 4 - Pull-Air DNA", "Pull threshold passed", "Pull below threshold")
    dead.append(cut); log("Step 4 - Pull-Air DNA", before, cut, alive, f"Pull >= {thresholds['pull_min']}")
    if alive.empty: return logs, None, pd.concat(dead)

    # Step 5 pitch kill
    before = alive.copy()
    alive, cut = gate_cut(alive, lambda d: d["pitch_edge"].fillna(-999) >= thresholds["pitch_edge_min"], "Step 5 - Pitch-Type Kill", "Pitch edge passed", "Negative pitch edge")
    dead.append(cut); log("Step 5 - Pitch-Type Kill", before, cut, alive, f"Pitch edge >= {thresholds['pitch_edge_min']}")
    if alive.empty: return logs, None, pd.concat(dead)

    # Step 6 weak slot; allow nuclear pitch edge (+40) to survive to 10.5 but flag as slot_miss_survivor
    before = alive.copy()
    cond = lambda d: (d["slot_match"] == True) | (d["pitch_edge"].fillna(0) >= 40)
    alive, cut = gate_cut(alive, cond, "Step 6 - Zone / Weak Slot", "Slot match or nuclear pitch edge", "No slot match and no nuclear edge")
    alive["slot_miss_survivor"] = (alive["slot_match"] == False) & (alive["pitch_edge"].fillna(0) >= 40)
    dead.append(cut); log("Step 6 - Zone / Weak Slot", before, cut, alive, "Direct weak-slot match; nuclear pitch edge may survive as chaos flag")
    if alive.empty: return logs, None, pd.concat(dead)

    # Step 7 sweet spot
    before = alive.copy()
    alive, cut = gate_cut(alive, lambda d: d["sweet_spot_pct"].fillna(0) >= thresholds["sweet_spot_min"], "Step 7 - Sweet Spot", "Launch profile passed", "Sweet spot below threshold")
    dead.append(cut); log("Step 7 - Sweet Spot", before, cut, alive, f"Sweet spot >= {thresholds['sweet_spot_min']}")
    if alive.empty: return logs, None, pd.concat(dead)

    # Step 8 barrel/conversion: pass if barrel or HR/PA
    before = alive.copy()
    cond = lambda d: (d["barrel_pct"].fillna(0) >= thresholds["barrel_min"]) | (d["hr_pa"].fillna(0) >= thresholds["hr_pa_min"])
    alive, cut = gate_cut(alive, cond, "Step 8 - Barrel / Conversion", "Barrel or HR/PA passed", "No barrel/conversion")
    dead.append(cut); log("Step 8 - Barrel / Conversion", before, cut, alive, f"Barrel >= {thresholds['barrel_min']} OR HR/PA >= {thresholds['hr_pa_min']}")
    if alive.empty: return logs, None, pd.concat(dead)

    # Step 9 dmg/hpi
    before = alive.copy()
    cond = lambda d: (d["dmg"].fillna(0) >= thresholds["dmg_min"]) & (d["hpi"].fillna(0) >= thresholds["hpi_min"])
    alive, cut = gate_cut(alive, cond, "Step 9 - Damage / HPI", "DMG/HPI passed", "DMG/HPI below threshold")
    dead.append(cut); log("Step 9 - Damage / HPI", before, cut, alive, f"DMG >= {thresholds['dmg_min']} AND HPI >= {thresholds['hpi_min']}")
    if alive.empty: return logs, None, pd.concat(dead)

    # Step 10 ownership pressure: choose current leader only for pressure, no cuts
    before = alive.copy(); cut = alive.iloc[0:0].copy()
    alive["pressure_score"] = alive["hr_pa"].fillna(0)*2 + alive["dmg"].fillna(0) + alive["slot_match"].astype(int)*2 + alive["pitch_edge"].fillna(0)/20
    leader = alive.sort_values("pressure_score", ascending=False).iloc[0]["batter"]
    log("Step 10 - Ownership Pressure", before, cut, alive, f"Pressure center: {leader}; no cuts.")

    # Step 10.5 transfer: only alive are eligible. Cut transfer candidates if worse than pressure leader by event score.
    before = alive.copy()
    alive["event_score"] = (
        alive["pull_pct"].fillna(0)/10 + alive["pitch_edge"].fillna(0)/10 + alive["sweet_spot_pct"].fillna(0)/10 +
        alive["hr_pa"].fillna(0) + alive["dmg"].fillna(0) + alive["hpi"].fillna(0)/20 + alive["slot_match"].astype(int)*2
    )
    # keep top event lane and any within 10% for final gates
    max_score = alive["event_score"].max()
    after = alive[alive["event_score"] >= max_score * 0.90].copy()
    cut = alive[alive["event_score"] < max_score * 0.90].copy()
    dead.append(cut); alive = after
    log("Step 10.5 - Adjacent / Decoy Transfer", before, cut, alive, "Only alive hitters eligible; keep top event lane(s) within 10%.")
    if alive.empty: return logs, None, pd.concat(dead)

    # Steps 11-17 no external data kills; maintain deterministic unless empty bat indicators
    for gate in ["Step 11 - Protection", "Step 12 - Bullpen Continuation", "Step 13 - WHO / Chaos", "Step 14 - No Empty Bat", "Step 15 - Finisher", "Step 16 - Event Likelihood", "Step 17 - No-Fluke Audit"]:
        before = alive.copy(); cut = alive.iloc[0:0].copy()
        log(gate, before, cut, alive, "No manual kill supplied; survivor state preserved.")

    # Step 18 lock single owner by event_score
    before = alive.copy()
    owner_row = alive.sort_values("event_score", ascending=False).head(1).copy()
    cut = alive.drop(owner_row.index).copy()
    log("Step 18 - Lock", before, cut, owner_row, "Highest legal event score after all gates.")
    return logs, owner_row.iloc[0].to_dict(), pd.concat(dead) if dead else pd.DataFrame()

st.title("MLB Home Run Blender — Gate Machine")
st.caption("Deterministic gate engine: no revived players, Step 10.5 only audits alive hitters, no Core 3 until games are processed.")

with st.sidebar:
    st.header("Gate thresholds")
    thresholds = {}
    thresholds["pull_min"] = st.number_input("Pull % minimum", value=DEFAULT_THRESHOLDS["pull_min"], step=1.0)
    thresholds["sweet_spot_min"] = st.number_input("Sweet Spot % minimum", value=DEFAULT_THRESHOLDS["sweet_spot_min"], step=1.0)
    thresholds["barrel_min"] = st.number_input("Barrel % minimum", value=DEFAULT_THRESHOLDS["barrel_min"], step=1.0)
    thresholds["pitch_edge_min"] = st.number_input("Pitch edge minimum", value=DEFAULT_THRESHOLDS["pitch_edge_min"], step=1.0)
    thresholds["hr_pa_min"] = st.number_input("HR/PA minimum", value=DEFAULT_THRESHOLDS["hr_pa_min"], step=0.1)
    thresholds["dmg_min"] = st.number_input("DMG minimum", value=DEFAULT_THRESHOLDS["dmg_min"], step=0.1)
    thresholds["hpi_min"] = st.number_input("HPI minimum", value=DEFAULT_THRESHOLDS["hpi_min"], step=1.0)

uploaded = st.file_uploader("Upload Star Tool CSV/XLSX", type=["csv", "xlsx", "xls"])

if uploaded is None:
    st.info("Upload a CSV/XLSX using the schema in sample_template.csv.")
    st.code(",".join(REQUIRED_COLS), language="text")
    st.stop()

df = load_df(uploaded)
if df is None:
    st.stop()

df = normalize(df)

st.subheader("Loaded slate")
st.dataframe(df[["game", "team", "pitcher", "batter", "lineup_slot", "weak_slots", "pitch_type", "pitch_edge", "pull_pct", "sweet_spot_pct", "barrel_pct", "hr_pa", "dmg", "hpi", "slot_match"]], use_container_width=True)

games = list(df["game"].dropna().unique())
selected_games = st.multiselect("Games to process", games, default=games)

owners = []
all_logs = []
for game in selected_games:
    with st.expander(f"{game} gate run", expanded=False):
        g = df[df["game"] == game].copy()
        logs, owner, dead = process_game(g, thresholds)
        log_df = pd.DataFrame(logs)
        st.dataframe(log_df, use_container_width=True, hide_index=True)
        if owner:
            owners.append(owner)
            st.success(f"Owner: {owner['batter']} ({owner['team']})")
        else:
            st.warning("NO PLAY")
        all_logs.extend(logs)

st.subheader("Survivor board")
if owners:
    owners_df = pd.DataFrame(owners)
    role_map = []
    for _, r in owners_df.iterrows():
        if "Chaos" in str(r.get("archetype", "")) or bool(r.get("slot_miss_survivor", False)):
            role_map.append("Chaos/WHO")
        elif "Transfer" in str(r.get("archetype", "")):
            role_map.append("Transfer/Adjacent")
        else:
            role_map.append("Primary/Clean")
    owners_df["core_role"] = role_map
    st.dataframe(owners_df[["game", "team", "batter", "archetype", "core_role", "event_score", "pitch_edge", "pull_pct", "sweet_spot_pct", "hr_pa", "dmg", "hpi", "slot_match"]], use_container_width=True)

    st.subheader("Role-balanced Core Builder")
    primary = owners_df[owners_df["core_role"] == "Primary/Clean"].sort_values("event_score", ascending=False)
    transfer = owners_df[owners_df["core_role"] == "Transfer/Adjacent"].sort_values("event_score", ascending=False)
    chaos = owners_df[owners_df["core_role"] == "Chaos/WHO"].sort_values("event_score", ascending=False)
    picks = []
    if not primary.empty: picks.append(primary.iloc[0])
    if not transfer.empty: picks.append(transfer.iloc[0])
    if not chaos.empty: picks.append(chaos.iloc[0])
    if len(picks) < 3:
        remaining = owners_df.drop([p.name for p in picks], errors="ignore").sort_values("event_score", ascending=False)
        for _, row in remaining.iterrows():
            if len(picks) >= 3: break
            picks.append(row)
    if picks:
        core = pd.DataFrame(picks)
        st.dataframe(core[["core_role", "game", "team", "batter", "event_score"]], use_container_width=True, hide_index=True)
else:
    st.warning("No owners produced.")
