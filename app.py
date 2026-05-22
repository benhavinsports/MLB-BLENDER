
import io
import re
import hashlib
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st

APP_VERSION = "V65 MACHINE ROOM INTERFACE"

STANDARD_COLUMNS = [
    "game_id", "team", "opponent", "player", "bat_side", "pitcher", "pitcher_hand",
    "slot", "odds", "pull_pct", "hard_hit_pct", "barrel_pct", "launch_angle",
    "pitch_edge", "hr9_split", "recent_hr_allowed", "notes", "source"
]

OUTPUT_COLUMNS = [
    "bucket", "rank", "game_id", "team", "opponent", "player", "pitcher",
    "archetype", "status", "score", "fire", "alert", "survivor_reason", "gate_log"
]

PLAYER_ALIASES = {"player","player_name","name","batter","batter_name","hitter","hitter_name","pick","selection"}
COLUMN_ALIASES = {
    "tm":"team","opp":"opponent","vs":"opponent","starter":"pitcher","sp":"pitcher","probable_pitcher":"pitcher",
    "throws":"pitcher_hand","lineup_spot":"slot","batting_order":"slot","order":"slot",
    "pull":"pull_pct","pull_percent":"pull_pct","pull_percentage":"pull_pct",
    "hardhit":"hard_hit_pct","hard_hit":"hard_hit_pct","hard_hit_percent":"hard_hit_pct","hh":"hard_hit_pct","hh_pct":"hard_hit_pct",
    "barrel":"barrel_pct","barrel_percent":"barrel_pct","brl":"barrel_pct","brl_pct":"barrel_pct",
    "la":"launch_angle","launch":"launch_angle","pitch_type_edge":"pitch_edge","edge":"pitch_edge","pitch_mix":"pitch_edge",
    "hr_9":"hr9_split","hr9":"hr9_split","l_r_hr_9_hr":"hr9_split",
    "recent_hr":"recent_hr_allowed","hr_allowed_home_or_away":"recent_hr_allowed"
}


def clean_text(x: Any) -> str:
    if x is None:
        return ""
    return re.sub(r"\s+", " ", str(x).replace("\u00a0", " ").replace("\t", " ")).strip()


def norm_col(c: Any) -> str:
    c = clean_text(c).lower()
    c = re.sub(r"[^a-z0-9]+", "_", c).strip("_")
    if c in PLAYER_ALIASES:
        return "player"
    return COLUMN_ALIASES.get(c, c)


def to_num(x: Any):
    s = clean_text(x)
    if not s or s.lower() in {"nan","none","null"}:
        return np.nan
    s = s.replace("%","").replace("+","")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return np.nan
    try:
        return float(m.group(0))
    except Exception:
        return np.nan


def is_junk_player(x: Any) -> bool:
    s = clean_text(x)
    low = s.lower()
    if not s or low in {"nan","none","null"}:
        return True
    junk = [
        "advanced mlb performance","am page","athletics projected","projected lineup",
        "player pool","home run","hard hit","barrel rate","launch angle","pitch edge",
        "game board","core 3","alt 3","chaos 3","share","github","streamlit",
        "download","upload","manage app","pitcher","team","opponent"
    ]
    if any(j in low for j in junk):
        return True
    if len(s) < 3 or len(s) > 60:
        return True
    return False



def looks_like_real_player_name(x: Any) -> bool:
    """
    Strict guard for PDF/OCR rows.
    Prevents stat fragments like '0.0% HR/PA' or '+1% HR' from entering as players.
    Allows real names like 'Bo Naylor', 'Jose Ramirez', "Ryan O'Hearn".
    """
    s = clean_text(x)
    if is_junk_player(s):
        return False
    if re.search(r"\d|%|\+|/|:|—|\(|\)|\||,", s):
        return False

    parts = s.split()
    if len(parts) < 2 or len(parts) > 3:
        return False

    bad_tokens = {
        "hr", "pa", "hrpa", "iso", "avg", "ops", "hpi", "adj", "ult", "dmg",
        "pull", "hard", "barrel", "launch", "pitch", "edge", "score", "team",
        "projected", "advanced", "performance", "page", "home", "away"
    }
    if any(p.lower().replace(".", "") in bad_tokens for p in parts):
        return False

    # Require normal person-name shape. Accept initials/suffix-like pieces.
    for p in parts:
        if not re.match(r"^[A-Z][a-zA-Z'.-]{1,}$", p):
            return False

    return True


def choose_player_candidate_from_line(line: str):
    """
    Extract one real player from a PDF/OCR stat line.
    Use table cells first, then name regex. Never use stat fragments.
    """
    cells = [clean_text(x) for x in (line.split("|") if "|" in line else re.split(r"\s{2,}", line)) if clean_text(x)]

    # Prefer first real person-shaped cell.
    for c in cells[:8]:
        if looks_like_real_player_name(c):
            return c

    # Fallback: First Last / First M. Last shaped text from the line.
    for nm in re.findall(r"\b([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){1,2})\b", line):
        if looks_like_real_player_name(nm):
            return nm

    return ""



def strict_real_player_name(x: Any) -> bool:
    """
    Final feeder gate:
    - exactly person-name shape
    - no stat symbols/numbers
    - no heading/metric words
    """
    s = clean_text(x)
    low = s.lower()

    if is_junk_player(s):
        return False
    if re.search(r"[\d%+/|:;=<>@\[\]{}]", s):
        return False
    if any(token in low for token in [
        "hr", "pa", "iso", "avg", "ops", "hpi", "adj", "ult", "dmg", "pull", "hard",
        "barrel", "launch", "pitch", "edge", "score", "projected", "advanced",
        "performance", "page", "team", "opponent", "probable", "starter"
    ]):
        return False

    parts = s.split()
    if len(parts) not in (2, 3):
        return False

    # real player names should not be all caps OCR labels
    if s.isupper():
        return False

    for p in parts:
        if not re.match(r"^[A-Z][a-zA-Z'.-]{1,}$", p):
            return False

    return True


def line_has_blender_data(line: str) -> bool:
    low = clean_text(line).lower()
    signals = 0
    groups = [
        ["pull", "pull-air"],
        ["hard", "hard-hit", "hh"],
        ["barrel", "brl"],
        ["launch", "la"],
        ["hr/9", "hr9", "hr allowed", "home run allowed"],
        ["4-seam", "fastball", "slider", "sinker", "curve", "change", "cutter", "splitter", "edge"],
        ["odds", "+", "-"],
        ["slot", "lineup", "batting"],
        ["green", "recent", "chaos", "who", "adjacent", "decoy"],
    ]
    for g in groups:
        if any(x in low for x in g):
            signals += 1
    if re.search(r"\d+(?:\.\d+)?%", low):
        signals += 1
    return signals >= 2


def extract_player_from_stat_line(line: str) -> str:
    cells = [clean_text(x) for x in (line.split("|") if "|" in line else re.split(r"\s{2,}", line)) if clean_text(x)]

    # Only choose cells that are clean person names.
    for c in cells[:8]:
        if strict_real_player_name(c):
            return c

    # OCR fallback.
    for nm in re.findall(r"\b([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){1,2})\b", line):
        if strict_real_player_name(nm):
            return nm

    return ""


def quarantine_bad_feed_rows(df: pd.DataFrame):
    if df is None or df.empty:
        return pd.DataFrame(columns=STANDARD_COLUMNS), pd.DataFrame()

    good_mask = df["player"].map(strict_real_player_name)
    # Table files with clean player column can pass even if some metrics missing.
    good = df[good_mask].copy()
    bad = df[~good_mask].copy()

    # Extra guard against PDF/OCR fragments: if source looks like PDF/image OCR, require blender data in notes.
    if not good.empty:
        source_text = good["source"].astype(str).str.lower()
        pdfish = source_text.str.contains("pdf|png|jpg|jpeg|webp", regex=True, na=False)
        if pdfish.any():
            has_data = good["notes"].astype(str).map(line_has_blender_data)
            moved_bad = good[pdfish & ~has_data].copy()
            good = good[~(pdfish & ~has_data)].copy()
            bad = pd.concat([bad, moved_bad], ignore_index=True)

    return good.reset_index(drop=True), bad.reset_index(drop=True)


def standardize_df(df: pd.DataFrame, source: str):
    report = {"source": source, "raw_rows": 0, "kept_rows": 0, "columns": []}
    if df is None or df.empty:
        return pd.DataFrame(columns=STANDARD_COLUMNS), report

    df = df.copy()
    report["raw_rows"] = int(len(df))
    df.columns = [norm_col(c) for c in df.columns]
    report["columns"] = list(df.columns)

    if "player" not in df.columns:
        # Only auto-detect a player column for structured table files.
        # OCR/PDF fragments must go through text_to_rows, not random best-column guessing.
        if not str(source).lower().endswith((".pdf", ".png", ".jpg", ".jpeg", ".webp")):
            best, best_score = None, 0
            for c in df.columns:
                score = df[c].astype(str).head(150).map(lambda v: 1 if strict_real_player_name(v) else 0).sum()
                if score > best_score:
                    best, best_score = c, score
            if best and best_score >= 2:
                df = df.rename(columns={best: "player"})

    for c in STANDARD_COLUMNS:
        if c not in df.columns:
            df[c] = ""

    df["source"] = source
    for c in ["game_id","team","opponent","player","bat_side","pitcher","pitcher_hand","pitch_edge","notes","source"]:
        df[c] = df[c].map(clean_text)

    df = df[df["player"].map(strict_real_player_name)].copy()

    for c in ["slot","odds","pull_pct","hard_hit_pct","barrel_pct","launch_angle","hr9_split","recent_hr_allowed"]:
        df[c] = df[c].map(to_num)

    if not df.empty:
        missing = df["game_id"].eq("")
        combo = (df["team"].astype(str) + " vs " + df["opponent"].astype(str)).str.strip()
        df.loc[missing, "game_id"] = combo[missing].replace(" vs ", "")
        df["game_id"] = df["game_id"].replace("", "Unknown Game")

        empty_notes = df["notes"].eq("")
        if empty_notes.any():
            df.loc[empty_notes, "notes"] = df.loc[empty_notes].astype(str).agg(" | ".join, axis=1).str[:2500]

        def first_real(s):
            for v in s:
                if clean_text(v) and clean_text(v).lower() not in {"nan","none","null"}:
                    return v
            return ""

        def max_num(s):
            vals = [to_num(v) for v in s]
            vals = [v for v in vals if not pd.isna(v)]
            return max(vals) if vals else np.nan

        agg = {}
        for c in STANDARD_COLUMNS:
            if c == "notes":
                agg[c] = lambda s: " | ".join(dict.fromkeys([clean_text(x) for x in s if clean_text(x)]))[:3500]
            elif c in ["slot","odds","pull_pct","hard_hit_pct","barrel_pct","launch_angle","hr9_split","recent_hr_allowed"]:
                agg[c] = max_num
            else:
                agg[c] = first_real

        df = df.groupby(["game_id","player"], dropna=False, as_index=False).agg(agg)
        df = df[STANDARD_COLUMNS].reset_index(drop=True)

    report["kept_rows"] = int(len(df))
    return df, report


def read_table_file(uploaded_file):
    raw = uploaded_file.getvalue()
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        for enc in ["utf-8","utf-8-sig","latin-1"]:
            try:
                return pd.read_csv(io.BytesIO(raw), encoding=enc)
            except Exception:
                pass
        return pd.read_csv(io.StringIO(raw.decode("utf-8", errors="ignore")), engine="python")

    if name.endswith((".xlsx",".xls")):
        xls = pd.ExcelFile(io.BytesIO(raw))
        frames = []
        for sheet in xls.sheet_names:
            try:
                t = pd.read_excel(xls, sheet_name=sheet)
                t["source_sheet"] = sheet
                frames.append(t)
            except Exception:
                pass
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if name.endswith((".txt",".tsv")):
        text = raw.decode("utf-8", errors="ignore")
        sep = "\t" if "\t" in text[:1000] else None
        try:
            return pd.read_csv(io.StringIO(text), sep=sep, engine="python")
        except Exception:
            return pd.DataFrame({"raw_text": text.splitlines()})

    return pd.DataFrame()


def has_stat_context(line: str) -> bool:
    return bool(re.search(r"\d|%|\+|HR|ISO|Barrel|Pull|Hard|Ult|Dmg|HPI|Adj|Odds|Slot|4-seam|fastball|slider|sinker|curve|change|cutter", line, re.I))


def text_to_rows(text: str, source: str):
    lines = [clean_text(x) for x in text.splitlines() if clean_text(x)]
    records = []
    current_game = "Unknown Game"
    quarantined = 0

    for line in lines:
        low = line.lower()
        if any(bad in low for bad in ["share", "github", "manage app", "streamlit"]):
            continue

        gm = re.search(r"\b([A-Z]{2,3})\s*(?:@|vs\.?|VS|v)\s*([A-Z]{2,3})\b", line)
        if gm:
            current_game = f"{gm.group(1)} vs {gm.group(2)}"

        if not line_has_blender_data(line):
            continue

        player = extract_player_from_stat_line(line)
        if not player:
            quarantined += 1
            continue

        rec = {"game_id": current_game, "player": player, "notes": line, "source": source}
        nums = re.findall(r"-?\d+(?:\.\d+)?%?", line)

        if "pull" in low and nums: rec["pull_pct"] = nums[-1]
        if ("hard" in low or "hh" in low) and nums: rec["hard_hit_pct"] = nums[-1]
        if "barrel" in low and nums: rec["barrel_pct"] = nums[-1]
        if "launch" in low and nums: rec["launch_angle"] = nums[-1]
        if any(p in low for p in ["4-seam","fastball","slider","sinker","curve","change","cutter","splitter","edge"]):
            rec["pitch_edge"] = line
        if "hr/9" in low or "hr9" in low:
            rec["hr9_split"] = nums[-1] if nums else ""
        if "recent" in low and "hr" in low:
            rec["recent_hr_allowed"] = nums[-1] if nums else ""
        records.append(rec)

    df, report = standardize_df(pd.DataFrame(records), source)
    report["quarantined_text_lines"] = quarantined
    return df, report


def feed_upload(uploaded_file):
    raw = uploaded_file.getvalue()
    # Cache by file bytes + name so re-clicks are instant.
    return cached_parse_file(uploaded_file.name, raw)


def feed_many_uploads(uploaded_files):
    frames, statuses, raw_rows = [], [], 0
    progress = st.progress(0, text="Feeding monster...")
    total = max(len(uploaded_files), 1)

    for idx, f in enumerate(uploaded_files):
        file_df, file_status = feed_upload(f)
        statuses.append(file_status)
        raw_rows += int(file_status.get("recovered_rows", 0))
        if file_df is not None and not file_df.empty:
            frames.append(file_df)
        progress.progress((idx + 1) / total, text=f"Loaded {idx+1}/{total}: {f.name}")

    progress.empty()

    if frames:
        df = pd.concat(frames, ignore_index=True)
        df, _ = standardize_df(df, "merged fast monster feed")
        df, quarantined_df = quarantine_bad_feed_rows(df)
    else:
        df = pd.DataFrame(columns=STANDARD_COLUMNS)

    return df, {
        "mode": "Fast monster multi-file merge",
        "recovered_rows": int(len(df)),
        "raw_recovered_rows": int(raw_rows),
        "file_statuses": statuses,
        "warnings": [w for s in statuses for w in s.get("warnings", [])],
        "quarantined_rows": int(len(quarantined_df)) if "quarantined_df" in locals() else 0,
    }


def fnum(row, col):
    try:
        v = row.get(col, np.nan)
        return np.nan if pd.isna(v) else float(v)
    except Exception:
        return np.nan


def score_fire(score):
    if score >= 90: return "🔥🔥🔥 ELITE"
    if score >= 78: return "🔥🔥 STRONG"
    if score >= 65: return "🔥 LIVE"
    if score >= 50: return "⚠️ LEAN"
    return "🧊 DATA GAP"


def alert_text(score, status):
    if status == "CORE-ELIGIBLE" and score >= 90: return "🚨 HE’S HITTING A HOME RUN TODAY 🚨"
    if status == "CORE-ELIGIBLE": return "🔥 CORE HR LOCK CANDIDATE"
    if status == "ALT-TRANSFER": return "⚡ NEXT-MAN / DECOY TRANSFER ALERT"
    if status == "CHAOS-ELIGIBLE": return "🌪️ WHO / CHAOS HR ALERT"
    return "⚠️ SURVIVED, NOT CLEAN"



def gate_result(name, result, detail="", kill=False):
    return {"gate": name, "result": result, "detail": detail, "kill": kill}


def has_word(text, words):
    t = clean_text(text).lower()
    return any(w.lower() in t for w in words)


def pass_fail_from_number(value, pass_at, warn_at=None, fail_below=None):
    if pd.isna(value):
        return "UNKNOWN"
    if value >= pass_at:
        return "PASS"
    if warn_at is not None and value >= warn_at:
        return "WARN"
    if fail_below is not None and value < fail_below:
        return "FAIL"
    return "WARN"


def summarize_gate_score(gates, path_bonus=0):
    """
    Score comes only from Blender gate results.
    PASS = full credit, WARN/UNKNOWN = partial/neutral, FAIL kill gates crush.
    """
    passed = sum(1 for g in gates if g["result"] == "PASS")
    warned = sum(1 for g in gates if g["result"] == "WARN")
    unknown = sum(1 for g in gates if g["result"] == "UNKNOWN")
    failed = sum(1 for g in gates if g["result"] == "FAIL")
    kill_failed = sum(1 for g in gates if g["result"] == "FAIL" and g.get("kill"))

    raw = (passed * 5.4) + (warned * 2.2) + (unknown * 0.6) + path_bonus - (failed * 7) - (kill_failed * 28)
    score = max(0, min(100, round(raw, 1)))
    return score, passed, warned, unknown, failed, kill_failed


def gate18(row):
    player = clean_text(row.get("player", ""))
    if is_junk_player(player) or not strict_real_player_name(player):
        return None

    notes = (clean_text(row.get("notes", "")) + " " + clean_text(row.get("pitch_edge", ""))).lower()
    pull = fnum(row, "pull_pct")
    hh = fnum(row, "hard_hit_pct")
    barrel = fnum(row, "barrel_pct")
    la = fnum(row, "launch_angle")
    hr9 = fnum(row, "hr9_split")
    recent = fnum(row, "recent_hr_allowed")
    slot = fnum(row, "slot")
    odds = fnum(row, "odds")
    game_id = clean_text(row.get("game_id", "")) or "Unknown Game"

    gates = []

    # G1 No Empty Bat
    gates.append(gate_result("G1 No Empty Bat", "PASS", player))

    # G2 Game Context
    gates.append(gate_result("G2 Game Context", "PASS" if game_id != "Unknown Game" else "WARN", game_id))

    # G3 Role / Lineup / Opportunity
    if not pd.isna(slot):
        if 1 <= slot <= 5:
            gates.append(gate_result("G3 Role / Lineup", "PASS", f"top-half slot {slot}"))
        elif 6 <= slot <= 9:
            gates.append(gate_result("G3 Role / Lineup", "WARN", f"lower slot {slot}, WHO eligible"))
        else:
            gates.append(gate_result("G3 Role / Lineup", "UNKNOWN", f"slot {slot}"))
    elif has_word(notes, ["lineup", "starting", "starter", "batting", "cleanup", "leadoff"]):
        gates.append(gate_result("G3 Role / Lineup", "PASS", "role text found"))
    else:
        gates.append(gate_result("G3 Role / Lineup", "UNKNOWN", "slot/role missing"))

    # G4 Pull-Air Gate — kill only if known and bad, not if missing from PDF.
    if not pd.isna(pull):
        pf = pass_fail_from_number(pull, pass_at=42, warn_at=35, fail_below=35)
        gates.append(gate_result("G4 Pull-Air Gate", pf, f"pull {pull}", kill=(pf == "FAIL")))
    elif has_word(notes, ["pull", "pull-air", "air", "lift", "fly ball"]):
        gates.append(gate_result("G4 Pull-Air Gate", "PASS", "pull/air text found"))
    else:
        gates.append(gate_result("G4 Pull-Air Gate", "UNKNOWN", "pull data missing"))

    # G5 Hard-Hit Gate
    if not pd.isna(hh):
        pf = pass_fail_from_number(hh, pass_at=45, warn_at=38, fail_below=38)
        gates.append(gate_result("G5 Hard-Hit Gate", pf, f"HH {hh}", kill=(pf == "FAIL")))
    elif has_word(notes, ["hard", "hard-hit", "hh", "damage", "dmg", "ult", "hpi"]):
        gates.append(gate_result("G5 Hard-Hit Gate", "PASS", "hard contact text found"))
    else:
        gates.append(gate_result("G5 Hard-Hit Gate", "UNKNOWN", "HH data missing"))

    # G6 Launch / Barrel Gate
    launch_pass = False
    if not pd.isna(la) and 12 <= la <= 32:
        launch_pass = True
        gates.append(gate_result("G6 Launch / Barrel", "PASS", f"launch {la}"))
    elif not pd.isna(barrel) and barrel >= 10:
        launch_pass = True
        gates.append(gate_result("G6 Launch / Barrel", "PASS", f"barrel {barrel}"))
    elif not pd.isna(la) or not pd.isna(barrel):
        gates.append(gate_result("G6 Launch / Barrel", "WARN", f"launch {la}, barrel {barrel}"))
    elif has_word(notes, ["launch", "barrel", "fly", "lift"]):
        launch_pass = True
        gates.append(gate_result("G6 Launch / Barrel", "PASS", "launch/barrel text found"))
    else:
        gates.append(gate_result("G6 Launch / Barrel", "UNKNOWN", "launch/barrel missing"))

    # G7 Pitch-Type Kill Switch
    pitch_words = ["4-seam", "fastball", "slider", "sinker", "curve", "change", "cutter", "splitter", "edge", "mistake"]
    pitch_pass = has_word(notes, pitch_words) or clean_text(row.get("pitch_edge", "")) != ""
    gates.append(gate_result("G7 Pitch-Type Kill Switch", "PASS" if pitch_pass else "UNKNOWN", "pitch lane found" if pitch_pass else "pitch lane missing"))

    # G8 Pitcher HR Weakness
    if not pd.isna(hr9) and hr9 > 0:
        gates.append(gate_result("G8 Pitcher HR Weakness", "PASS" if hr9 >= 1.0 else "WARN", f"HR/9 {hr9}"))
    elif has_word(notes, ["hr/9", "hr9", "weakness", "allows hr", "home run allowed"]):
        gates.append(gate_result("G8 Pitcher HR Weakness", "PASS", "HR weakness text found"))
    else:
        gates.append(gate_result("G8 Pitcher HR Weakness", "UNKNOWN", "HR weakness missing"))

    # G9 Recent HR Allowed / Green Trend
    if not pd.isna(recent) and recent > 0:
        gates.append(gate_result("G9 Recent HR Allowed", "PASS", f"recent {recent}"))
    elif has_word(notes, ["green", "recent", "hot", "allowed hr"]):
        gates.append(gate_result("G9 Recent HR Allowed", "PASS", "green/recent text found"))
    else:
        gates.append(gate_result("G9 Recent HR Allowed", "UNKNOWN", "recent trend missing"))

    # G10 Lineup Opportunity already partially captured, but formalized.
    if not pd.isna(slot) and 1 <= slot <= 5:
        gates.append(gate_result("G10 Opportunity", "PASS", f"slot {slot}"))
    elif not pd.isna(slot):
        gates.append(gate_result("G10 Opportunity", "WARN", f"slot {slot}"))
    else:
        gates.append(gate_result("G10 Opportunity", "UNKNOWN", "slot missing"))

    # G10.5 Book Decoy / Adjacent Shadow
    adjacent = has_word(notes, ["adjacent", "decoy", "secondary", "behind", "after", "protection", "next man", "shadow"])
    gates.append(gate_result("G10.5 Adjacent / Decoy", "PASS" if adjacent else "UNKNOWN", "transfer trigger" if adjacent else "no trigger"))

    # G11 Pitch-Around / Protection
    protection = has_word(notes, ["protection", "pitch around", "walk risk", "pitched around"])
    gates.append(gate_result("G11 Protection", "PASS" if protection else "UNKNOWN", "protection context" if protection else "neutral/unknown"))

    # G12 Bullpen Continuation
    bullpen = has_word(notes, ["bullpen", "reliever", "pen", "continues lane"])
    gates.append(gate_result("G12 Bullpen Continuation", "PASS" if bullpen else "UNKNOWN", "bullpen lane" if bullpen else "unknown"))

    # G13 WHO / Chaos
    chaos = has_word(notes, ["chaos", "who", "value", "green", "blowout", "wind", "weather", "bullpen"]) or (not pd.isna(slot) and slot >= 6)
    gates.append(gate_result("G13 WHO / Chaos", "PASS" if chaos else "UNKNOWN", "chaos path" if chaos else "no chaos trigger"))

    # G14 True HR Conversion
    if (not pd.isna(barrel) and barrel >= 10) or (not pd.isna(hh) and hh >= 50):
        gates.append(gate_result("G14 True HR Conversion", "PASS", "conversion metric pass"))
    elif has_word(notes, ["conversion", "barrel", "home run history", "hr cadence", "multi-hr"]):
        gates.append(gate_result("G14 True HR Conversion", "PASS", "conversion text found"))
    else:
        gates.append(gate_result("G14 True HR Conversion", "UNKNOWN", "conversion not confirmed"))

    # G15 Event Ownership Isolation
    clean_power = (
        ((not pd.isna(pull) and pull >= 42) or has_word(notes, ["pull", "pull-air"]))
        and ((not pd.isna(hh) and hh >= 45) or has_word(notes, ["hard-hit", "damage", "dmg"]))
    )
    event_owner = clean_power and (launch_pass or pitch_pass)
    if event_owner:
        gates.append(gate_result("G15 Event Ownership", "PASS", "clean owner path"))
    elif adjacent or chaos:
        gates.append(gate_result("G15 Event Ownership", "WARN", "ALT/Chaos owner path"))
    else:
        gates.append(gate_result("G15 Event Ownership", "UNKNOWN", "owner not isolated"))

    # G16 Market / Odds
    if not pd.isna(odds):
        gates.append(gate_result("G16 Market / Odds", "PASS" if abs(odds) <= 700 else "WARN", f"odds {odds}"))
    else:
        gates.append(gate_result("G16 Market / Odds", "UNKNOWN", "odds missing"))

    # G17 Finisher Gate
    finisher = event_owner
    if finisher:
        gates.append(gate_result("G17 Finisher Gate", "PASS", "finisher path"))
    elif adjacent:
        gates.append(gate_result("G17 Finisher Gate", "WARN", "adjacent finisher path"))
    elif chaos:
        gates.append(gate_result("G17 Finisher Gate", "WARN", "chaos finisher path"))
    else:
        gates.append(gate_result("G17 Finisher Gate", "UNKNOWN", "not confirmed"))

    # G18 Final Lock Audit
    if finisher and pitch_pass:
        gates.append(gate_result("G18 Final Lock Audit", "PASS", "clean lock"))
    elif adjacent:
        gates.append(gate_result("G18 Final Lock Audit", "WARN", "ALT lock"))
    elif chaos:
        gates.append(gate_result("G18 Final Lock Audit", "WARN", "CHAOS lock"))
    else:
        gates.append(gate_result("G18 Final Lock Audit", "UNKNOWN", "incomplete"))

    path_bonus = 0
    if chaos:
        path_bonus += 8
    if adjacent:
        path_bonus += 8
    if finisher:
        path_bonus += 10

    score, passed, warned, unknown, failed, kill_failed = summarize_gate_score(gates, path_bonus=path_bonus)

    # Hard-gate status. A kill fail eliminates from winners no matter the score.
    if kill_failed:
        status = "ELIMINATED"
    elif finisher and pitch_pass and passed >= 10:
        status = "CORE-ELIGIBLE"
    elif adjacent and passed + warned >= 9:
        status = "ALT-TRANSFER"
    elif chaos and passed + warned >= 8:
        status = "CHAOS-ELIGIBLE"
    elif score >= 60 and failed == 0:
        status = "SURVIVED BUT NOT CLEAN"
    else:
        status = "ELIMINATED"

    if status == "CHAOS-ELIGIBLE":
        archetype = "WHO / CHAOS"
    elif status == "ALT-TRANSFER":
        archetype = "ADJACENT / DECOY TRANSFER"
    elif finisher:
        archetype = "LANE MATCH FINISHER"
    elif clean_power:
        archetype = "CLEAN POWER OWNER"
    else:
        archetype = "GATE SURVIVOR / DATA GAP"

    reasons = []
    if clean_power: reasons.append("CLEAN-POWER")
    if launch_pass: reasons.append("LAUNCH/BARREL")
    if pitch_pass: reasons.append("PITCH-KILL")
    if adjacent: reasons.append("ADJACENT")
    if chaos: reasons.append("CHAOS")
    if not reasons: reasons = ["18-GATE VERDICT"]

    gate_log = " | ".join([f'{g["gate"]}: {g["result"]} ({g["detail"]})' for g in gates])

    return {
        "game_id": game_id,
        "team": clean_text(row.get("team", "")),
        "opponent": clean_text(row.get("opponent", "")),
        "player": player,
        "pitcher": clean_text(row.get("pitcher", "")),
        "archetype": archetype,
        "status": status,
        "score": score,
        "fire": score_fire(score),
        "alert": alert_text(score, status),
        "survivor_reason": " + ".join(reasons) + f" | gates {passed}P/{warned}W/{unknown}U/{failed}F",
        "gate_log": gate_log,
    }


def choose_game_owner(group):
    priority = {
        "CORE-ELIGIBLE": 5,
        "CHAOS-ELIGIBLE": 4,
        "ALT-TRANSFER": 3,
        "SURVIVED BUT NOT CLEAN": 2,
        "ELIMINATED": 0,
    }
    g = group.copy()
    g["priority"] = g["status"].map(priority).fillna(0)
    g = g[g["status"] != "ELIMINATED"]
    if g.empty:
        return group.sort_values("score", ascending=False).head(1)
    return g.sort_values(["priority", "score"], ascending=[False, False]).head(1).drop(columns=["priority"], errors="ignore")


def run_blender(df):
    empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
    if df is None or df.empty:
        return {"tickets": empty, "core3": empty, "alt3": empty, "chaos3": empty, "game_board": empty, "all_gates": empty}

    rows = []
    for _, r in df.iterrows():
        out = gate18(r)
        if out:
            rows.append(out)

    pool = pd.DataFrame(rows)
    if pool.empty:
        return {"tickets": empty, "core3": empty, "alt3": empty, "chaos3": empty, "game_board": empty, "all_gates": empty}

    alive = pool[pool["status"] != "ELIMINATED"].copy()
    if alive.empty:
        alive = pool.sort_values("score", ascending=False).head(3).copy()

    game_board = alive.groupby("game_id", group_keys=False).apply(choose_game_owner).reset_index(drop=True)
    game_board = game_board.sort_values("score", ascending=False).reset_index(drop=True)
    game_board.insert(0, "rank", range(1, len(game_board)+1))
    game_board.insert(0, "bucket", "GAME SURVIVOR")

    core_source = game_board[game_board["status"].eq("CORE-ELIGIBLE")]
    if len(core_source) < 3:
        core_source = pd.concat([core_source, game_board[~game_board.index.isin(core_source.index)]], ignore_index=False)
    core3 = core_source.head(3).copy()
    core3["bucket"] = "CORE 3"
    core3["rank"] = range(1, len(core3)+1)

    used = set(core3["player"].tolist())
    remaining = alive[~alive["player"].isin(used)].copy()

    alt = remaining[remaining["status"].isin(["ALT-TRANSFER","CORE-ELIGIBLE"])].sort_values("score", ascending=False).head(3)
    if len(alt) < 3:
        alt = pd.concat([alt, remaining[~remaining.index.isin(alt.index)].sort_values("score", ascending=False).head(3-len(alt))])
    alt = alt.copy()
    alt.insert(0, "rank", range(1, len(alt)+1))
    alt.insert(0, "bucket", "ALT 3")

    used |= set(alt["player"].tolist())
    chaos_pool = alive[~alive["player"].isin(used)].copy()
    chaos = chaos_pool[chaos_pool["status"].eq("CHAOS-ELIGIBLE")].sort_values("score", ascending=False).head(3)
    if len(chaos) < 3:
        chaos = pd.concat([chaos, chaos_pool[~chaos_pool.index.isin(chaos.index)].sort_values("score", ascending=False).head(3-len(chaos))])
    chaos = chaos.copy()
    chaos.insert(0, "rank", range(1, len(chaos)+1))
    chaos.insert(0, "bucket", "CHAOS 3")

    tickets = pd.concat([core3, alt, chaos], ignore_index=True)
    tickets["ticket_type"] = tickets["bucket"]

    return {
        "tickets": tickets[OUTPUT_COLUMNS + ["ticket_type"]],
        "core3": core3[OUTPUT_COLUMNS],
        "alt3": alt[OUTPUT_COLUMNS],
        "chaos3": chaos[OUTPUT_COLUMNS],
        "game_board": game_board[OUTPUT_COLUMNS],
        "all_gates": pool[OUTPUT_COLUMNS],
    }


def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")



def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")



def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


def inject_css():
    st.markdown("""
    <style>
    .stApp {
        background:
          radial-gradient(circle at 50% 18%, rgba(110,255,40,.12), transparent 28%),
          radial-gradient(circle at 50% 95%, rgba(255,65,30,.10), transparent 24%),
          #020302;
        color:#f4fff1;
    }
    [data-testid="stHeader"] {background: rgba(0,0,0,0);}
    .block-container {padding-top:.7rem; max-width:820px;}
    #MainMenu, footer {visibility:hidden;}
    .machine-shell{
        min-height:92vh;
        border:1px solid rgba(120,255,90,.28);
        border-radius:28px;
        padding:16px;
        background:linear-gradient(180deg, rgba(0,0,0,.78), rgba(0,0,0,.94));
        box-shadow:0 0 40px rgba(110,255,40,.08), inset 0 0 30px rgba(110,255,40,.06);
    }
    .machine-title{
        text-align:center;color:#caff5a;font-weight:1000;
        font-size:clamp(1.7rem,6vw,3.2rem);
        letter-spacing:.05em;text-shadow:0 0 18px rgba(202,255,90,.36);
        margin:6px 0 4px;
    }
    .machine-sub{
        text-align:center;color:#7cff92;font-size:.78rem;font-weight:900;
        letter-spacing:.18em;margin-bottom:14px;opacity:.85;
    }
    .feed-slot{
        border:1px dashed rgba(202,255,90,.42);
        border-radius:999px;background:rgba(0,0,0,.55);
        padding:7px 12px;margin-bottom:10px;
    }
    .feed-slot [data-testid="stFileUploader"] section{
        padding:0 !important;background:transparent !important;border:0 !important;
    }
    .feed-slot button{
        border-radius:999px !important;background:rgba(202,255,90,.10) !important;
        color:#eaffbd !important;border:1px solid rgba(202,255,90,.28) !important;
        font-weight:900 !important;
    }
    .chamber{
        height:360px;border-radius:34px 34px 86px 86px;
        border:3px solid rgba(108,255,90,.55);
        background:
          radial-gradient(circle at 50% 45%, rgba(202,255,90,.28), transparent 22%),
          radial-gradient(circle at 50% 50%, rgba(12,245,170,.14), transparent 38%),
          linear-gradient(180deg, rgba(5,24,7,.92), rgba(1,8,3,.98));
        position:relative;overflow:hidden;margin:14px 0 12px;
        box-shadow:inset 0 0 60px rgba(65,255,80,.12),0 0 30px rgba(0,0,0,.55);
    }
    .blade-ring{
        position:absolute;top:50%;left:50%;width:210px;height:210px;
        margin-left:-105px;margin-top:-105px;border-radius:50%;
        border:18px solid rgba(202,255,90,.22);
        border-left-color:#18f5a8;border-right-color:#ff3d2f;
        animation:spin .72s linear infinite;filter:drop-shadow(0 0 18px rgba(202,255,90,.28));
    }
    .blade-core{
        position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
        font-size:4.3rem;z-index:3;filter:drop-shadow(0 0 18px rgba(202,255,90,.65));
    }
    @keyframes spin {to{transform:rotate(360deg)}}
    .player-feed{
        position:absolute;padding:7px 12px;border-radius:999px;
        background:rgba(0,0,0,.68);border:1px solid rgba(202,255,90,.34);
        color:#eaffbd;font-size:.83rem;font-weight:1000;white-space:nowrap;
        text-shadow:0 0 10px rgba(202,255,90,.52);
        max-width:190px;overflow:hidden;text-overflow:ellipsis;
    }
    .player-feed:nth-child(1){top:28px;left:18px;animation:grind1 3.8s linear infinite}
    .player-feed:nth-child(2){top:58px;right:18px;animation:grind2 4.1s linear infinite}
    .player-feed:nth-child(3){bottom:64px;left:20px;animation:grind3 3.6s linear infinite}
    .player-feed:nth-child(4){bottom:32px;right:18px;animation:grind4 4.0s linear infinite}
    .player-feed:nth-child(5){top:170px;left:50%;animation:grind5 4.4s linear infinite}
    .player-feed:nth-child(6){top:250px;left:38%;animation:grind2 4.7s linear infinite}
    @keyframes grind1{50%{transform:translate(160px,95px) rotate(18deg) scale(.92);opacity:.88}}
    @keyframes grind2{50%{transform:translate(-160px,105px) rotate(-24deg) scale(.9);opacity:.88}}
    @keyframes grind3{50%{transform:translate(160px,-95px) rotate(-20deg) scale(.9);opacity:.88}}
    @keyframes grind4{50%{transform:translate(-160px,-90px) rotate(22deg) scale(.9);opacity:.88}}
    @keyframes grind5{50%{transform:translate(-60px,-95px) rotate(190deg) scale(.86);opacity:.8}}
    .status-line{
        text-align:center;font-weight:1000;color:#96ff9c;
        letter-spacing:.05em;font-size:.9rem;margin:8px 0 10px;
    }
    .stButton>button{
        background:#ff4545 !important;color:white !important;border:0 !important;
        border-radius:14px !important;font-weight:1000 !important;
        letter-spacing:.08em !important;padding:.8rem 1rem !important;
    }
    .eject-title{margin-top:20px;font-size:1.22rem;color:#caff5a;font-weight:1000;letter-spacing:.08em;}
    .survivor{
        border-radius:18px;padding:13px 14px;
        background:linear-gradient(90deg, rgba(35,255,90,.11), rgba(255,255,255,.035));
        border:1px solid rgba(120,255,90,.20);margin-bottom:10px;
    }
    .survivor.elim{
        background:linear-gradient(90deg, rgba(255,60,45,.12), rgba(255,255,255,.03));
        border:1px solid rgba(255,80,65,.22);
    }
    .survivor-name{font-weight:1000;font-size:1.03rem;}
    .machine-alert{color:#fff;font-weight:1000;margin-top:4px;}
    .scorebar{height:12px;background:rgba(255,255,255,.10);border-radius:999px;overflow:hidden;margin:8px 0;}
    .small{font-size:.78rem;color:rgba(255,255,255,.72);}
    </style>
    """, unsafe_allow_html=True)


def score_bar(score):
    try: s = max(0, min(100, float(score)))
    except Exception: s = 0
    return f'<div class="scorebar"><div style="height:100%;width:{s}%;background:linear-gradient(90deg,#5dff7b,#caff32,#ff8a00,#ff3b30);"></div></div>'


def player_feed_html(df):
    names = []
    if df is not None and not df.empty and "player" in df.columns:
        for x in df["player"].dropna().astype(str).tolist():
            try:
                ok = strict_real_player_name(x)
            except Exception:
                ok = bool(clean_text(x))
            if ok:
                names.append(clean_text(x))
            if len(names) >= 6:
                break
    while len(names) < 6:
        names.append("AWAITING PLAYER")
    return "".join([f'<div class="player-feed">{n}</div>' for n in names[:6]])


def survivor_card(row):
    status = clean_text(row.get("status",""))
    cls = "survivor elim" if status == "ELIMINATED" else "survivor"
    return f"""
    <div class="{cls}">
      <div class="survivor-name">#{int(row.get('rank',0))} {clean_text(row.get('player',''))}</div>
      <div style="color:#caff5a;font-weight:1000;">{clean_text(row.get('fire',''))}</div>
      {score_bar(row.get('score',0))}
      <div class="machine-alert">{clean_text(row.get('alert',''))}</div>
      <div class="small">{clean_text(row.get('game_id',''))} • {clean_text(row.get('archetype',''))} • Score {row.get('score',0)}</div>
      <div class="small">{clean_text(row.get('survivor_reason',''))}</div>
    </div>
    """


def section(df, title):
    st.markdown(f'<div class="eject-title">{title}</div>', unsafe_allow_html=True)
    if df is None or df.empty:
        st.caption("No survivors ejected yet.")
        return
    for _, r in df.head(3).iterrows():
        st.markdown(survivor_card(r), unsafe_allow_html=True)


st.set_page_config(page_title="MLB Blender", page_icon="⚾", layout="wide")
inject_css()

if "feed_df" not in st.session_state:
    st.session_state.feed_df = pd.DataFrame(columns=STANDARD_COLUMNS)
if "results" not in st.session_state:
    st.session_state.results = run_blender(st.session_state.feed_df)
if "feed_status" not in st.session_state:
    st.session_state.feed_status = {}
if "file_count" not in st.session_state:
    st.session_state.file_count = 0

st.markdown('<div class="machine-shell">', unsafe_allow_html=True)
st.markdown('<div class="machine-title">MASTER MLB BLENDER</div>', unsafe_allow_html=True)
st.markdown('<div class="machine-sub">FEED • BLEND • SURVIVE</div>', unsafe_allow_html=True)

st.markdown('<div class="feed-slot">', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "FEED",
    type=["pdf","png","jpg","jpeg","webp","csv","xlsx","xls","txt","tsv"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)
st.markdown('</div>', unsafe_allow_html=True)

if uploaded_files:
    df, status = feed_many_uploads(uploaded_files)
    st.session_state.feed_df = df
    st.session_state.feed_status = status
    st.session_state.file_count = len(uploaded_files)

st.markdown(
    f'<div class="chamber">{player_feed_html(st.session_state.feed_df)}<div class="blade-ring"></div><div class="blade-core">⚙️</div></div>',
    unsafe_allow_html=True
)

if st.button("ENGAGE BLENDER", type="primary", use_container_width=True):
    st.session_state.results = run_blender(st.session_state.feed_df)
    st.success("SURVIVORS EJECTED")

st.markdown(
    f'<div class="status-line">{st.session_state.file_count} FILES FED • {len(st.session_state.feed_df)} REAL PLAYERS IN MACHINE</div>',
    unsafe_allow_html=True
)
st.markdown('</div>', unsafe_allow_html=True)

res = st.session_state.results
section(res.get("core3"), "CORE 3")
section(res.get("alt3"), "ALT 3")
section(res.get("chaos3"), "CHAOS 3")

with st.expander("GAME SURVIVORS", expanded=False):
    st.dataframe(res.get("game_board"), use_container_width=True, hide_index=True)

with st.expander("MACHINE OUTPUT / DOWNLOADS", expanded=False):
    st.download_button("tickets.csv", csv_bytes(res.get("tickets", pd.DataFrame())), "tickets.csv", "text/csv", use_container_width=True)
    st.download_button("core.csv", csv_bytes(res.get("core3", pd.DataFrame())), "core.csv", "text/csv", use_container_width=True)
    st.download_button("alt.csv", csv_bytes(res.get("alt3", pd.DataFrame())), "alt.csv", "text/csv", use_container_width=True)
    st.download_button("chaos.csv", csv_bytes(res.get("chaos3", pd.DataFrame())), "chaos.csv", "text/csv", use_container_width=True)
    st.dataframe(res.get("tickets"), use_container_width=True, hide_index=True)

with st.expander("FEED QUARANTINE / DEBUG", expanded=False):
    st.write(st.session_state.feed_status)
    st.dataframe(st.session_state.feed_df, use_container_width=True, hide_index=True)
