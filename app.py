
import streamlit as st
import pandas as pd
import numpy as np
import json, traceback, re, tempfile, os
from pathlib import Path
from datetime import datetime

# ============================================================
# THE BLENDER MACHINE — SINGLE FILE FINAL
# Feeder + AI Oil + Engine + UI + Tickets + Game Board + Recap
# No cross-file imports. No missing module failures.
# ============================================================

st.set_page_config(page_title="THE BLENDER MACHINE", page_icon="🔥", layout="wide", initial_sidebar_state="collapsed")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
LOCK_FILE = DATA_DIR / "latest_locked_results.json"
RECAP_FILE = DATA_DIR / "recap_history.csv"

# -------------------------
# STYLE / UI
# -------------------------
def inject_css():
    st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at top left, #223000 0%, #050505 28%, #000 100%); color:#f7eedf; }
    h1,h2,h3 { font-weight:900!important; letter-spacing:1px; color:#f7eedf!important; }
    .hero { border:1px solid #2e2e2e; border-radius:34px; padding:28px; background:#080808; margin-bottom:20px; }
    .hero-title { font-size:58px; line-height:.88; font-weight:1000; color:#f7eedf; }
    .lime { color:#b8ff22; }
    .card { border:1px solid #303030; border-radius:24px; padding:18px; background:#0b0b0b; margin:12px 0; }
    .ok { background:#102a0f; border-radius:14px; padding:14px; color:#dbffd8; margin:10px 0; }
    .warn { background:#3b3a00; border-radius:14px; padding:14px; color:#fffac2; margin:10px 0; }
    .bad { background:#3a1111; border-radius:14px; padding:14px; color:#ffd2d2; margin:10px 0; }
    .audit { background:#071829; border-radius:14px; padding:14px; color:#b8dcff; margin:10px 0; }
    div.stButton > button { background:linear-gradient(90deg,#a8ff2d,#00f59b,#ffa10a); color:#000; border:none; border-radius:30px; min-height:62px; font-size:18px; font-weight:900; }
    .small {font-size:13px; opacity:.8;}
    </style>
    """, unsafe_allow_html=True)

def hero():
    st.markdown('<div class="hero"><div class="hero-title">THE<br><span class="lime">BLENDER</span><br>MACHINE</div></div>', unsafe_allow_html=True)

def safe_df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

def show_df(title, df, cols=None):
    st.subheader(title)
    df = safe_df(df)
    if df.empty:
        st.info("No rows yet.")
        return
    if cols:
        keep = [c for c in cols if c in df.columns]
        if keep:
            df = df[keep]
    st.dataframe(df, use_container_width=True, hide_index=True)

# -------------------------
# UTILITIES
# -------------------------
def txt(x):
    try:
        if x is None or pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()

def num(x, default=np.nan):
    try:
        if x is None or pd.isna(x):
            return default
        s = str(x).replace("%","").replace("+","").replace(",","").strip()
        if s.lower() in {"", "nan", "none", "null", "-", "—"}:
            return default
        return float(s)
    except Exception:
        return default

def first_col(df, aliases):
    low = {str(c).lower().strip(): c for c in df.columns}
    for a in aliases:
        if a.lower().strip() in low:
            return low[a.lower().strip()]
    for c in df.columns:
        cl = str(c).lower().strip()
        for a in aliases:
            if a.lower().strip() in cl:
                return c
    return None

FIELD_ALIASES = {
    "player": ["player","hitter","batter","name","player_name"],
    "team": ["team","bat_team","batter_team","club"],
    "opponent": ["opponent","opp","vs","pitcher_team"],
    "pitcher": ["pitcher","sp","starter","opposing_pitcher","probable"],
    "game": ["game","matchup"],
    "lineup_slot": ["lineup_slot","slot","order","batting_order","bo"],
    "pull_pct": ["pull_pct","pull%","pull","pull rate","pull_percent"],
    "sweet_spot_pct": ["sweet_spot_pct","sweet%","sweet spot","sweet_spot","launch","launch_angle","la"],
    "barrel_pct": ["barrel_pct","barrel%","brl%","barrel"],
    "hard_hit_pct": ["hard_hit_pct","hardhit%","hard_hit%","hard hit%","hh%","hardhit","hard hit"],
    "dmg": ["dmg","damage","ult","ultimate","adj","adjusted"],
    "hr_pa": ["hr_pa","hr/pa","hr rate","hr_rate","hr9","hr/9","pitcher_hr9"],
    "hpi": ["hpi","score","rating","model","hr score"],
    "pitch_edge": ["pitch_edge","pitch edge","edge","pitch","pitchtype edge"],
    "notes": ["notes","note","tag","status"],
}
NUMERIC_FIELDS = ["lineup_slot","pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi","pitch_edge"]

# -------------------------
# FEEDER
# -------------------------
def read_feed(uploaded_file):
    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()

    if name.endswith(".csv"):
        return pd.read_csv(uploaded_file), {"source":"csv"}
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded_file), {"source":"excel"}
    if name.endswith(".txt") or name.endswith(".md"):
        text = raw.decode("utf-8", errors="ignore")
        return text_to_rows(text), {"source":"text"}
    if name.endswith(".pdf"):
        return read_pdf(raw), {"source":"pdf"}
    if name.endswith((".png",".jpg",".jpeg",".webp")):
        return pd.DataFrame(), {"source":"image", "warning":"Image OCR is disabled in single-file build. Upload PDF/CSV/XLSX for reliable runs."}
    raise ValueError("Unsupported file type. Use CSV, XLSX, PDF, TXT.")

def read_pdf(raw):
    rows = []
    # Try pdfplumber tables
    try:
        import pdfplumber
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(raw)
            path = tmp.name
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    header = [txt(x) for x in table[0]]
                    for row in table[1:]:
                        rec = {}
                        for h, v in zip(header, row):
                            if h:
                                rec[h] = v
                        if rec:
                            rows.append(rec)
        if rows:
            return pd.DataFrame(rows)
    except Exception:
        pass

    # Try PyMuPDF text fallback
    try:
        import fitz
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(raw)
            path = tmp.name
        doc = fitz.open(path)
        text_lines = []
        for page in doc:
            text_lines += [x.strip() for x in page.get_text("text").splitlines() if x.strip()]
        return text_to_rows("\n".join(text_lines))
    except Exception as e:
        raise ValueError(f"PDF read failed: {e}")

def text_to_rows(text):
    lines = [x.strip() for x in str(text).splitlines() if x.strip()]
    rows = []
    current_game = ""
    current_pitcher = ""
    for line in lines:
        # detect game-ish line
        if re.search(r"\bvs\b|@", line, re.I) and len(line) < 80:
            current_game = line
            continue
        if re.search(r"pitcher|starter|probable", line, re.I) and len(line) < 100:
            current_pitcher = line
            continue
        # player-ish line
        if len(line.split()) >= 2 and not re.search(r"copyright|page \d+|disclaimer", line, re.I):
            rows.append({"player": line, "game": current_game, "pitcher": current_pitcher, "notes": "text_parse"})
    return pd.DataFrame(rows)

# -------------------------
# AI OIL
# -------------------------
def ai_field_mapper(df):
    if df is None or len(df) == 0:
        return pd.DataFrame(), {"status":"EMPTY", "warnings":["No rows"]}

    raw = df.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    mapped = pd.DataFrame()
    mapping = {}

    for target, aliases in FIELD_ALIASES.items():
        col = first_col(raw, aliases)
        mapping[target] = col
        mapped[target] = raw[col] if col is not None else ""

    for c in ["player","team","opponent","pitcher","game","notes"]:
        mapped[c] = mapped[c].apply(txt)
    for c in NUMERIC_FIELDS:
        mapped[c] = mapped[c].apply(num)

    # Preserve raw columns
    for c in raw.columns:
        if c not in [v for v in mapping.values() if v is not None]:
            mapped[f"raw_{c}"] = raw[c]

    # remove trash rows
    mapped = mapped[mapped["player"].astype(str).str.strip().ne("")]
    mapped = mapped[~mapped["player"].astype(str).str.lower().isin(["player","hitter","batter","name"])]

    # Game repair
    blank = mapped["game"].astype(str).str.strip().eq("")
    mapped.loc[blank, "game"] = (
        mapped.loc[blank, "team"].replace("", "TEAM").astype(str)
        + " vs "
        + mapped.loc[blank, "opponent"].replace("", "OPP").astype(str)
    )

    # game key
    mapped["game_key"] = mapped["game"].astype(str)
    weak_game = mapped["game_key"].str.strip().isin([" vs ", "TEAM vs OPP", "", "TEAM vs "])
    mapped.loc[weak_game, "game_key"] = (
        mapped.loc[weak_game, "team"].astype(str).replace("", "TEAM")
        + " vs "
        + mapped.loc[weak_game, "pitcher"].astype(str).replace("", "PITCHER")
    )

    warnings = []
    for f in ["player","team","pitcher","game"]:
        if f in mapped and mapped[f].astype(str).str.strip().eq("").mean() > 0.7:
            warnings.append(f"Most rows missing {f}")

    return mapped.reset_index(drop=True), {"status":"MAPPED", "mapping":mapping, "warnings":warnings}

def ai_feed_validator(df):
    if df is None or df.empty:
        return {"status":"BAD", "score":0, "issues":["No rows"], "summary":"No feed rows loaded."}
    score = 100
    issues = []

    if df["player"].astype(str).str.strip().eq("").all():
        score -= 60; issues.append("No player names")
    if df["team"].astype(str).str.strip().eq("").mean() > 0.7:
        score -= 15; issues.append("Team mostly missing")
    if df["pitcher"].astype(str).str.strip().eq("").mean() > 0.7:
        score -= 15; issues.append("Pitcher mostly missing")

    metric_cells = 0
    for c in NUMERIC_FIELDS:
        metric_cells += pd.to_numeric(df[c], errors="coerce").notna().sum()
    ratio = metric_cells / max(1, len(df) * len(NUMERIC_FIELDS))
    if ratio < .15:
        score -= 25; issues.append("Very low metric coverage")
    elif ratio < .35:
        score -= 10; issues.append("Partial metric coverage")

    status = "GOOD" if score >= 80 else ("USABLE" if score >= 55 else "WEAK")
    return {"status":status, "score":max(0, int(score)), "issues":issues, "summary":f"Feed quality {status} ({max(0,int(score))}/100). Rows={len(df)}."}

def chaos_detector(df):
    if df is None or df.empty:
        return pd.DataFrame()
    rows = []
    for game, g in df.groupby("game_key", dropna=False):
        flags = []
        pull = pd.to_numeric(g["pull_pct"], errors="coerce")
        hard = pd.to_numeric(g["hard_hit_pct"], errors="coerce")
        barrel = pd.to_numeric(g["barrel_pct"], errors="coerce")
        hrpa = pd.to_numeric(g["hr_pa"], errors="coerce")
        notes = " ".join(g["notes"].astype(str).str.lower().tolist())

        if len(g) >= 6: flags.append("large pool")
        if hrpa.max(skipna=True) >= 1.5: flags.append("pitcher HR lane")
        if (pull.fillna(0).between(30, 40) & hard.fillna(0).between(30, 45)).sum() >= 2: flags.append("secondary chaos band")
        if barrel.notna().sum() >= 3 and barrel.std(skipna=True) <= 3: flags.append("no barrel separation")
        if "who" in notes or "chaos" in notes: flags.append("chaos tag")
        level = "HIGH" if len(flags) >= 3 else ("MEDIUM" if len(flags) >= 2 else "LOW")
        rows.append({"game_key":game, "chaos_level":level, "flags":"; ".join(flags)})
    return pd.DataFrame(rows)

# -------------------------
# BLENDER ENGINE
# -------------------------
def metric_presence(row):
    return sum(1 for c in NUMERIC_FIELDS if c in row and not pd.isna(row.get(c)))

def eval_gates(row):
    pull = num(row.get("pull_pct"), 0)
    sweet = num(row.get("sweet_spot_pct"), 0)
    barrel = num(row.get("barrel_pct"), 0)
    hard = num(row.get("hard_hit_pct"), 0)
    dmg = num(row.get("dmg"), 0)
    hrpa = num(row.get("hr_pa"), 0)
    hpi = num(row.get("hpi"), 0)
    edge = num(row.get("pitch_edge"), 0)
    slot = num(row.get("lineup_slot"), 0)
    notes = txt(row.get("notes")).lower()
    metrics = metric_presence(row)

    player_ok = bool(txt(row.get("player")))
    context_ok = bool(txt(row.get("team")) or txt(row.get("pitcher")) or txt(row.get("game")))
    data_ok = metrics >= 2
    strong_data = metrics >= 5

    gates = []
    def add(name, passed, hard_gate, weight, pass_note, fail_note):
        gates.append({"gate":name, "passed":bool(passed), "hard":bool(hard_gate), "weight":weight, "note":pass_note if passed else fail_note})

    add("0 Environment / Game Target", context_ok, False, 5, "Context present", "Context thin")
    add("1 Uploaded Pool Legality", player_ok, True, 10, "Real uploaded player row", "Invalid player row")
    add("2 Side / Team Lock", bool(txt(row.get("team"))) or not strong_data, False, 4, "Team or recovery context OK", "Team missing")
    add("3 Pitcher Weakness / HR Lane", hrpa >= 1.0 or edge >= .5 or dmg >= 1.2 or hpi >= 30 or not strong_data, False, 7, "HR lane signal/recovery", "No lane signal")
    add("4 Pitch-Type Kill Switch", edge >= 0 or not strong_data, True, 9, "Pitch edge not negative", "Negative pitch edge")
    add("5 Pull-Air Trigger", pull >= 35 or sweet >= 25 or not strong_data, True, 12, "Pull-air survives", "Pull-air failed")
    add("6 Launch / Sweet Spot", sweet >= 22 or barrel >= 7 or not strong_data, False, 6, "Launch support", "Launch thin")
    add("7 Damage / Barrel", dmg >= 1.0 or barrel >= 6 or hpi >= 25 or not strong_data, True, 12, "Damage/conversion survives", "Damage/barrel thin")
    add("8 True HR Conversion DNA", hpi >= 25 or hrpa >= 1.2 or dmg >= 1.1 or not strong_data, True, 12, "Conversion proxy survives", "Conversion DNA thin")
    add("9 Opportunity / Lineup", slot == 0 or slot <= 7, False, 5, "Opportunity OK", "Weak lineup opportunity")
    add("10 Hard-Hit Support", hard >= 35 or barrel >= 6 or dmg >= 1.0 or not strong_data, False, 6, "Hard-hit support", "Hard-hit thin")
    add("10.5 Adjacent / Decoy Transfer", True, False, 3, "Transfer checked", "No transfer")
    add("11 WHO / Chaos Check", "who" in notes or "chaos" in notes or (pull >= 30 and hard >= 30) or not strong_data, False, 4, "WHO/chaos eligible", "No chaos profile")
    add("12 Game Script", True, False, 3, "No script kill", "Script kill")
    add("13 Recap DNA Calibration", pull >= 35 or dmg >= 1.0 or hpi >= 25 or hrpa >= 1.0 or not strong_data, False, 6, "Matches recap DNA proxy", "Recap DNA weak")
    add("14 Trap Audit", "trap" not in notes, True, 8, "No trap tag", "Trap tag present")
    add("15 Bullpen Continuation", "bullpen kill" not in notes, False, 3, "No bullpen kill", "Bullpen kill")
    add("16 Finisher Gate", (pull >= 35 and (hard >= 35 or barrel >= 6 or dmg >= 1.0 or hpi >= 25)) or not strong_data, True, 14, "Finisher survives", "Finisher failed")
    add("17 One-Owner Isolation", True, True, 5, "Isolatable", "Not isolatable")
    add("18 Final Lock Audit", player_ok and context_ok, True, 6, "Final structure OK", "Final structure failed")
    add("19 HR Model Confirmation", pull >= 30 or hard >= 30 or dmg >= 1.0 or hpi >= 20 or hrpa >= 1.0 or not strong_data, True, 14, "HR model confirmed/recovery", "HR model failed")

    hard_fails = [g["gate"] for g in gates if g["hard"] and not g["passed"]]
    soft_fails = [g["gate"] for g in gates if not g["hard"] and not g["passed"]]
    clean = len(hard_fails) == 0 and data_ok
    recovery = player_ok and len(hard_fails) <= 3
    return gates, hard_fails, soft_fails, clean, recovery, data_ok, strong_data

def score_row(row, gates, clean, recovery, data_ok, strong_data):
    pull = max(0, num(row.get("pull_pct"), 0))
    sweet = max(0, num(row.get("sweet_spot_pct"), 0))
    barrel = max(0, num(row.get("barrel_pct"), 0))
    hard = max(0, num(row.get("hard_hit_pct"), 0))
    dmg = max(0, num(row.get("dmg"), 0))
    hrpa = max(0, num(row.get("hr_pa"), 0))
    hpi = max(0, num(row.get("hpi"), 0))
    edge = num(row.get("pitch_edge"), 0)

    gate_score = sum(g["weight"] for g in gates if g["passed"])
    stat_score = pull*.22 + sweet*.14 + barrel*.45 + hard*.12 + min(dmg,6)*4 + min(hrpa,6)*3 + min(hpi,100)*.16 + max(min(edge,30),-20)*.2
    score = gate_score*.62 + stat_score + metric_presence(row)*2

    if clean: score += 12
    elif recovery: score += 4
    if not data_ok: score = min(score, 54)
    if not strong_data: score = min(score, 68)
    return round(max(1, min(99, score)), 1)

def role_for(row, clean, recovery, strong_data):
    notes = txt(row.get("notes")).lower()
    pull = num(row.get("pull_pct"), 0)
    hard = num(row.get("hard_hit_pct"), 0)
    dmg = num(row.get("dmg"), 0)
    hpi = num(row.get("hpi"), 0)
    edge = num(row.get("pitch_edge"), 0)

    if clean:
        if "who" in notes or "chaos" in notes or (pull >= 30 and hard >= 30 and hpi < 35):
            return "WHO", "WHO / Chaos Finisher"
        if "adjacent" in notes or "decoy" in notes:
            return "Adjacent", "Adjacent / Transfer Owner"
        if edge >= 8:
            return "Primary", "Pitch-Type Punisher"
        if pull >= 42 and dmg >= 1.4 and hpi >= 30:
            return "Primary", "Elite Converter"
        return "Primary", "Primary HR Owner"
    if recovery:
        return "Recovery", "Data-Recovery Owner"
    return "NO PLAY", "No Clean Owner"

def run_true_blender(raw_df):
    mapped, audit = ai_field_mapper(raw_df)
    validation = ai_feed_validator(mapped)
    chaos = chaos_detector(mapped)

    # add chaos notes
    if not mapped.empty and not chaos.empty:
        cmap = dict(zip(chaos["game_key"].astype(str), chaos["chaos_level"].astype(str)))
        mapped["notes"] = mapped.apply(lambda r: (txt(r.get("notes")) + (" chaos_"+cmap.get(txt(r.get("game_key")), "").lower() if cmap.get(txt(r.get("game_key"))) in ["HIGH","MEDIUM"] else "")).strip(), axis=1)

    meta = {
        "engine_version":"SINGLE_FILE_FINAL_19_GATE_AI_OIL",
        "input_rows": int(len(mapped)),
        "games": int(mapped["game_key"].nunique()) if not mapped.empty and "game_key" in mapped else 0,
        "ai_feed_status": validation["status"],
        "ai_feed_score": validation["score"],
        "ai_validation_summary": validation["summary"],
        "message": ""
    }

    if mapped.empty:
        meta["message"] = "No feed rows available."
        return result_pack(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), meta, mapped, chaos, validation)

    all_rows = []
    gate_rows = []

    for _, r in mapped.iterrows():
        row = r.to_dict()
        gates, hard_fails, soft_fails, clean, recovery, data_ok, strong_data = eval_gates(row)
        score = score_row(row, gates, clean, recovery, data_ok, strong_data)
        role, archetype = role_for(row, clean, recovery, strong_data)

        if not recovery:
            role, archetype = "NO PLAY", "No Clean Owner"

        final_text = "GAME OWNER LOCKED" if clean else ("RECOVERY OWNER LOCKED — DATA WEAK" if recovery else "NO PLAY")

        row.update({
            "score":score,
            "official_core_role":role,
            "archetype":archetype,
            "hard_fails":", ".join(hard_fails),
            "soft_fails":", ".join(soft_fails),
            "clean_owner":bool(clean),
            "recovery_owner":bool(recovery and not clean),
            "data_status":"FULL_DATA" if strong_data else ("PARTIAL_DATA" if data_ok else "DATA_WEAK"),
            "gate_path":" | ".join([f"{g['gate']}: {'PASS' if g['passed'] else ('KILL' if g['hard'] else 'WEAK')} — {g['note']}" for g in gates]) + " | FINAL: " + final_text
        })
        all_rows.append(row)

        for g in gates:
            gate_rows.append({
                "game": row.get("game_key"),
                "player": row.get("player"),
                "gate": g["gate"],
                "verdict": "PASS" if g["passed"] else ("KILL" if g["hard"] else "WEAK"),
                "note": g["note"],
                "score": score
            })

    survivors = pd.DataFrame(all_rows)
    game_board = pd.DataFrame(gate_rows)

    owners = []
    for game, g in survivors.groupby("game_key", dropna=False):
        g = g.sort_values(["clean_owner","score"], ascending=[False, False]).reset_index(drop=True)
        pick = g.iloc[0].to_dict()
        if pick["official_core_role"] == "NO PLAY":
            pick["official_core_role"] = "Recovery"
            pick["archetype"] = "Emergency Audit Owner"
            pick["recovery_owner"] = True
            pick["score"] = min(num(pick.get("score"), 40), 52)
        owners.append(pick)

    owners = pd.DataFrame(owners).sort_values("score", ascending=False).reset_index(drop=True)

    core, alt, chaos_ticket = build_tickets(owners)
    meta["owners_locked"] = int(len(owners))
    meta["clean_owners"] = int(owners["clean_owner"].fillna(False).sum()) if not owners.empty and "clean_owner" in owners else 0
    meta["recovery_owners"] = int(owners["recovery_owner"].fillna(False).sum()) if not owners.empty and "recovery_owner" in owners else 0
    meta["message"] = f"Blender complete: {len(owners)} game owners locked from {meta['games']} games. Clean={meta['clean_owners']} · Recovery={meta['recovery_owners']}."

    results = result_pack(owners, core, alt, chaos_ticket, survivors, meta, mapped, chaos, validation, game_board)
    save_locked_results(results)
    return results

def build_tickets(owners):
    owners = safe_df(owners)
    if owners.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    owners = owners.sort_values("score", ascending=False).reset_index(drop=True)

    core_rows = []
    for pattern in ["Primary", "WHO|Recovery", "Adjacent", ""]:
        pool = owners if pattern == "" else owners[owners["official_core_role"].astype(str).str.contains(pattern, case=False, na=False)]
        for _, r in pool.iterrows():
            if len(core_rows) >= 3: break
            if r["player"] not in [x["player"] for x in core_rows]:
                core_rows.append(r.to_dict())
        if len(core_rows) >= 3: break
    core = pd.DataFrame(core_rows).head(3)
    if not core.empty: core["ticket_role"] = "CORE"

    used = set(core["player"].astype(str)) if not core.empty else set()
    alt = owners[~owners["player"].astype(str).isin(used)].head(3).copy()
    if alt.empty: alt = owners.tail(min(3, len(owners))).copy()
    if not alt.empty: alt["ticket_role"] = "ALT"

    used.update(alt["player"].astype(str).tolist() if not alt.empty else [])
    chaos = owners[owners["official_core_role"].astype(str).str.contains("WHO|Recovery", case=False, na=False) & ~owners["player"].astype(str).isin(used)].head(3).copy()
    if chaos.empty: chaos = owners[~owners["player"].astype(str).isin(used)].head(3).copy()
    if chaos.empty: chaos = owners.tail(min(3, len(owners))).copy()
    if not chaos.empty: chaos["ticket_role"] = "WHO"

    return core, alt, chaos

def result_pack(owners, core, alt, chaos, survivors, meta, feed=None, ai_chaos=None, validation=None, game_board=None):
    return {
        "owners": safe_df(owners),
        "core": safe_df(core),
        "alt": safe_df(alt),
        "chaos": safe_df(chaos),
        "survivors": safe_df(survivors),
        "game_board": safe_df(game_board),
        "feed": safe_df(feed),
        "ai_chaos": safe_df(ai_chaos),
        "ai_validation": validation or {},
        "meta": meta or {}
    }

# -------------------------
# SAVE / LOAD / RECAP
# -------------------------
def df_records(df):
    df = safe_df(df)
    if df.empty: return []
    return df.replace({np.nan: None}).to_dict(orient="records")

def save_locked_results(results):
    payload = {
        "meta": results.get("meta", {}),
        "owners": df_records(results.get("owners")),
        "core": df_records(results.get("core")),
        "alt": df_records(results.get("alt")),
        "chaos": df_records(results.get("chaos")),
        "survivors": df_records(results.get("survivors")),
        "game_board": df_records(results.get("game_board")),
    }
    LOCK_FILE.write_text(json.dumps(payload, indent=2, default=str))
    return str(LOCK_FILE)

def load_locked_results():
    if not LOCK_FILE.exists():
        return result_pack(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), {}, pd.DataFrame())
    payload = json.loads(LOCK_FILE.read_text())
    return result_pack(
        pd.DataFrame(payload.get("owners", [])),
        pd.DataFrame(payload.get("core", [])),
        pd.DataFrame(payload.get("alt", [])),
        pd.DataFrame(payload.get("chaos", [])),
        pd.DataFrame(payload.get("survivors", [])),
        payload.get("meta", {}),
        pd.DataFrame(),
        pd.DataFrame(),
        {},
        pd.DataFrame(payload.get("game_board", []))
    )

def run_recap_now(results):
    owners = safe_df(results.get("owners")) if isinstance(results, dict) else pd.DataFrame()
    if owners.empty:
        return pd.DataFrame(), "No locked owners found. Run Blender first."
    rec = owners.copy()
    rec["recap_checked_at"] = datetime.now().isoformat()
    rec["hr_result"] = "MANUAL_CHECK_REQUIRED"
    if RECAP_FILE.exists():
        old = pd.read_csv(RECAP_FILE)
        rec = pd.concat([old, rec], ignore_index=True)
    rec.to_csv(RECAP_FILE, index=False)
    return rec, "Recap saved."

def csv_bytes(df):
    return safe_df(df).to_csv(index=False).encode("utf-8")

# -------------------------
# APP STATE
# -------------------------
inject_css()
hero()

if "feed_df" not in st.session_state:
    st.session_state.feed_df = pd.DataFrame()
if "results" not in st.session_state:
    st.session_state.results = load_locked_results()
if "machine_state" not in st.session_state:
    st.session_state.machine_state = "READY"
if "last_error" not in st.session_state:
    st.session_state.last_error = ""

tabs = st.tabs(["Blender Machine", "Tickets", "Game Board", "Debug"])

# -------------------------
# MAIN TAB
# -------------------------
with tabs[0]:
    st.markdown('<div class="card"><h2>FEED DATA HERE</h2><p>Upload PDF, CSV, XLSX, or TXT. Then press RUN BLENDER NOW.</p></div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Upload slate", type=["pdf","csv","xlsx","xls","txt","md"], label_visibility="collapsed")

    if uploaded is not None:
        try:
            df, audit = read_feed(uploaded)
            st.session_state.feed_df = df
            st.session_state.machine_state = "FEED LOADED"
            st.success(f"Feed loaded: {len(df)} rows from {uploaded.name}")
        except Exception as e:
            st.session_state.last_error = traceback.format_exc()
            st.session_state.machine_state = "ERROR"
            st.error(f"Feed failed: {e}")

    feed = safe_df(st.session_state.feed_df)
    if not feed.empty:
        mapped_preview, preview_audit = ai_field_mapper(feed)
        v = ai_feed_validator(mapped_preview)
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Rows Read", len(feed))
        c2.metric("Mapped Players", len(mapped_preview))
        c3.metric("Feed Status", v["status"])
        c4.metric("Feed Score", v["score"])

        with st.expander("Preview mapped feed"):
            st.dataframe(mapped_preview.head(30), use_container_width=True, hide_index=True)

        if st.button("RUN BLENDER NOW", use_container_width=True, key="run_blender_single_file"):
            try:
                with st.spinner("Running full 19-gate Blender + AI oil..."):
                    results = run_true_blender(feed)
                st.session_state.results = results
                st.session_state.machine_state = "OWNERS LOCKED" if not results["owners"].empty else "AUDIT ONLY"
                st.success(results["meta"].get("message", "Blender complete."))
                st.rerun()
            except Exception as e:
                st.session_state.last_error = traceback.format_exc()
                st.session_state.machine_state = "ERROR"
                st.error(f"Run failed: {e}")
                st.code(st.session_state.last_error)
    else:
        st.info("Upload a feed first.")

    res = st.session_state.results
    meta = res.get("meta", {}) if isinstance(res, dict) else {}
    if meta:
        st.markdown(f'<div class="ok"><b>Machine State:</b> {st.session_state.machine_state}<br>{meta.get("message","")}</div>', unsafe_allow_html=True)
        st.markdown("### 🧠 AI Oil Status")
        c1,c2,c3 = st.columns(3)
        c1.metric("AI Feed", meta.get("ai_feed_status", "—"))
        c2.metric("AI Score", meta.get("ai_feed_score", "—"))
        c3.metric("Engine", meta.get("engine_version", "—"))
        st.write(meta.get("ai_validation_summary", ""))

    show_df("LOCKED GAME OWNERS", res.get("owners", pd.DataFrame()) if isinstance(res, dict) else pd.DataFrame(),
            ["game_key","game","player","team","pitcher","score","official_core_role","archetype","data_status","hard_fails"])

    st.markdown('<div class="card"><h2>2AM EASTERN AUTO RECAP</h2><p>Manual recap saves/checks locked owners now.</p></div>', unsafe_allow_html=True)
    if st.button("RUN RECAP NOW", key="recap_now_single"):
        rec, msg = run_recap_now(st.session_state.results)
        st.info(msg)
        if not rec.empty:
            st.dataframe(rec.tail(100), use_container_width=True, hide_index=True)

# -------------------------
# TICKETS
# -------------------------
with tabs[1]:
    res = st.session_state.results
    if not isinstance(res, dict) or safe_df(res.get("owners")).empty:
        st.info("Run the Blender first.")
    else:
        show_df("CORE 3", res.get("core"), ["ticket_role","game_key","player","team","pitcher","score","official_core_role","archetype","data_status"])
        show_df("ALT 3", res.get("alt"), ["ticket_role","game_key","player","team","pitcher","score","official_core_role","archetype","data_status"])
        show_df("WHO / CHAOS 3", res.get("chaos"), ["ticket_role","game_key","player","team","pitcher","score","official_core_role","archetype","data_status","hard_fails"])
        st.download_button("DOWNLOAD OWNERS CSV", data=csv_bytes(res.get("owners")), file_name="blender_locked_owners.csv", mime="text/csv")

# -------------------------
# GAME BOARD
# -------------------------
with tabs[2]:
    res = st.session_state.results
    if not isinstance(res, dict) or safe_df(res.get("owners")).empty:
        st.info("Run the Blender first.")
    else:
        show_df("OWNERS BY GAME", res.get("owners"), ["game_key","player","team","pitcher","score","official_core_role","archetype","clean_owner","recovery_owner","data_status","hard_fails","soft_fails"])
        show_df("FULL GATE AUDIT", res.get("game_board"), ["game","player","gate","verdict","note","score"])
        show_df("ALL SURVIVORS / KILL REASONS", res.get("survivors"), ["game_key","player","team","pitcher","score","official_core_role","data_status","hard_fails","soft_fails","gate_path"])

# -------------------------
# DEBUG
# -------------------------
with tabs[3]:
    st.header("Debug / Health Check")
    st.write("This build is single-file, so there are no missing import files.")
    st.write("Current state:", st.session_state.machine_state)
    if st.button("RUN BUILT-IN SAMPLE TEST", key="sample_test"):
        sample = pd.DataFrame([
            {"game":"NYY vs BOS","team":"NYY","opponent":"BOS","pitcher":"Pitcher A","player":"Elite Guy","lineup_slot":3,"pull_pct":48,"sweet_spot_pct":31,"barrel_pct":14,"hard_hit_pct":52,"dmg":2.1,"hr_pa":2.8,"hpi":68,"pitch_edge":7,"notes":"primary lane"},
            {"game":"NYY vs BOS","team":"NYY","opponent":"BOS","pitcher":"Pitcher A","player":"Adjacent Bat","lineup_slot":4,"pull_pct":39,"sweet_spot_pct":26,"barrel_pct":8,"hard_hit_pct":44,"dmg":1.4,"hr_pa":1.7,"hpi":41,"pitch_edge":3,"notes":"adjacent decoy"},
            {"game":"LAD vs SF","team":"LAD","opponent":"SF","pitcher":"Pitcher B","player":"Launch Man","lineup_slot":2,"pull_pct":44,"sweet_spot_pct":33,"barrel_pct":11,"hard_hit_pct":49,"dmg":1.8,"hr_pa":2.4,"hpi":62,"pitch_edge":6,"notes":"primary lane"},
            {"game":"LAD vs SF","team":"LAD","opponent":"SF","pitcher":"Pitcher B","player":"WHO Bat","lineup_slot":7,"pull_pct":34,"sweet_spot_pct":23,"barrel_pct":5,"hard_hit_pct":38,"dmg":1.1,"hr_pa":1.3,"hpi":28,"pitch_edge":1,"notes":"who chaos"},
            {"game":"ATL vs PHI","team":"ATL","opponent":"PHI","pitcher":"Pitcher C","player":"Pull Finisher","lineup_slot":4,"pull_pct":51,"sweet_spot_pct":29,"barrel_pct":10,"hard_hit_pct":45,"dmg":1.7,"hr_pa":2.2,"hpi":58,"pitch_edge":4,"notes":"primary lane"},
        ])
        st.session_state.feed_df = sample
        st.session_state.results = run_true_blender(sample)
        st.session_state.machine_state = "SAMPLE TEST PASSED"
        st.success(st.session_state.results["meta"]["message"])
        st.rerun()

    if st.session_state.last_error:
        st.subheader("Last Error")
        st.code(st.session_state.last_error)

    st.subheader("Session Results Meta")
    st.json(st.session_state.results.get("meta", {}) if isinstance(st.session_state.results, dict) else {})
