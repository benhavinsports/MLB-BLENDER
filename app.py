
import io
import re
import hashlib
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st

APP_VERSION = "V62 HARD-GATE BLENDER — GATE SCORE ONLY"

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


def standardize_df(df: pd.DataFrame, source: str):
    report = {"source": source, "raw_rows": 0, "kept_rows": 0, "columns": []}
    if df is None or df.empty:
        return pd.DataFrame(columns=STANDARD_COLUMNS), report

    df = df.copy()
    report["raw_rows"] = int(len(df))
    df.columns = [norm_col(c) for c in df.columns]
    report["columns"] = list(df.columns)

    if "player" not in df.columns:
        best, best_score = None, 0
        for c in df.columns:
            score = df[c].astype(str).head(150).map(lambda v: 0 if is_junk_player(v) else 1).sum()
            if score > best_score:
                best, best_score = c, score
        if best:
            df = df.rename(columns={best: "player"})

    for c in STANDARD_COLUMNS:
        if c not in df.columns:
            df[c] = ""

    df["source"] = source
    for c in ["game_id","team","opponent","player","bat_side","pitcher","pitcher_hand","pitch_edge","notes","source"]:
        df[c] = df[c].map(clean_text)

    df = df[~df["player"].map(is_junk_player)].copy()

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

    for line in lines:
        low = line.lower()
        if any(bad in low for bad in ["share", "github", "manage app", "streamlit"]):
            continue

        gm = re.search(r"\b([A-Z]{2,3})\s*(?:@|vs\.?|VS|v)\s*([A-Z]{2,3})\b", line)
        if gm:
            current_game = f"{gm.group(1)} vs {gm.group(2)}"

        if not has_stat_context(line):
            continue

        cells = [clean_text(x) for x in (line.split("|") if "|" in line else re.split(r"\s{2,}", line)) if clean_text(x)]
        candidates = []
        for c in cells[:6]:
            if not is_junk_player(c) and re.search(r"[A-Za-z]", c):
                candidates.append(c)

        if not candidates:
            for nm in re.findall(r"\b([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){1,2})\b", line):
                if not is_junk_player(nm):
                    candidates.append(nm)

        for player in dict.fromkeys(candidates[:2]):
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

    return standardize_df(pd.DataFrame(records), source)


def ocr_image_bytes(image_bytes: bytes, warnings: list):
    # Fast OCR: ONE clean pass only.
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageEnhance
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        gray = ImageOps.grayscale(img)
        gray = ImageEnhance.Contrast(gray).enhance(1.8)
        return pytesseract.image_to_string(gray, config="--psm 6")
    except Exception as e:
        warnings.append(f"OCR unavailable: {e}")
        return ""


@st.cache_data(show_spinner=False)
def cached_parse_file(name: str, raw: bytes):
    fake = io.BytesIO(raw)
    fake.name = name
    return parse_file_uncached(fake)


def parse_file_uncached(uploaded_file):
    status = {"file": uploaded_file.name, "mode": "", "recovered_rows": 0, "warnings": [], "report": {}}
    name = uploaded_file.name.lower()

    try:
        if name.endswith((".csv",".xlsx",".xls",".txt",".tsv")):
            df, report = standardize_df(read_table_file(uploaded_file), uploaded_file.name)
            status["mode"] = "Fast table/text feeder"
            status["report"] = report

        elif name.endswith(".pdf"):
            df, status = fast_pdf_parse(uploaded_file, status)

        elif name.endswith((".png",".jpg",".jpeg",".webp")):
            warnings = []
            text = ocr_image_bytes(uploaded_file.getvalue(), warnings)
            df, report = text_to_rows(text, uploaded_file.name)
            status["mode"] = "Fast screenshot/JPEG OCR"
            status["warnings"].extend(warnings)
            status["report"] = report

        else:
            df = pd.DataFrame(columns=STANDARD_COLUMNS)
            status["mode"] = "Unsupported file type"
            status["warnings"].append("Use PDF, screenshot, JPG/PNG/WebP, CSV, Excel, TXT.")
    except Exception as e:
        df = pd.DataFrame(columns=STANDARD_COLUMNS)
        status["mode"] = "Safe fallback"
        status["warnings"].append(str(e))

    status["recovered_rows"] = int(len(df))
    return df, status


def fast_pdf_parse(uploaded_file, status):
    raw = uploaded_file.getvalue()
    chunks, warnings = [], []
    ocr_pages = 0
    text_pages = 0

    # Layer 1: fast text/tables first. This handles most data PDFs quickly.
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_chunks = []
                txt = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                if txt.strip():
                    page_chunks.append(txt)

                # Only table extraction if page text exists or the PDF is table-like.
                try:
                    tables = page.extract_tables() or []
                    for table in tables:
                        for row in table:
                            page_chunks.append(" | ".join(clean_text(x) for x in row))
                except Exception:
                    pass

                page_text = "\n".join(page_chunks)
                if page_text.strip():
                    chunks.append(page_text)
                    text_pages += 1
    except Exception as e:
        warnings.append(f"Fast PDF text layer skipped: {e}")

    # Try building rows from text first.
    text = "\n".join(chunks)
    df, report = text_to_rows(text, uploaded_file.name)

    # If enough rows are recovered, STOP. No OCR.
    if len(df) >= 5:
        status["mode"] = "FAST PDF TEXT/TABLE — OCR skipped"
        status["warnings"].extend(warnings)
        status["report"] = {**report, "text_pages": text_pages, "ocr_pages": 0, "speed_mode": "text-first stop"}
        return df, status

    # Layer 2: OCR only if row recovery failed/weak.
    try:
        import fitz
        doc = fitz.open(stream=raw, filetype="pdf")
        ocr_chunks = []
        max_pages = min(len(doc), 12)  # prevents giant PDFs from hanging
        for i in range(max_pages):
            page = doc[i]

            # Skip pages that already have enough extracted text.
            txt = page.get_text("text") or ""
            if len(txt.strip()) > 250 and has_stat_context(txt):
                continue

            pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0), alpha=False)
            img_bytes = pix.tobytes("png")
            ocr = ocr_image_bytes(img_bytes, warnings)
            if ocr.strip():
                ocr_chunks.append(ocr)
                ocr_pages += 1

        if ocr_chunks:
            combined = text + "\n" + "\n".join(ocr_chunks)
            df, report = text_to_rows(combined, uploaded_file.name)

    except Exception as e:
        warnings.append(f"OCR fallback skipped: {e}")

    status["mode"] = "FAST PDF MONSTER — OCR only when needed"
    status["warnings"].extend(warnings)
    status["report"] = {**report, "text_pages": text_pages, "ocr_pages": ocr_pages, "speed_mode": "smart fallback"}
    return df, status


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
    else:
        df = pd.DataFrame(columns=STANDARD_COLUMNS)

    return df, {
        "mode": "Fast monster multi-file merge",
        "recovered_rows": int(len(df)),
        "raw_recovered_rows": int(raw_rows),
        "file_statuses": statuses,
        "warnings": [w for s in statuses for w in s.get("warnings", [])],
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
    if is_junk_player(player):
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


def inject_css():
    st.markdown("""
    <style>
    .stApp {
        background:#030503;
        color:#f5fff3;
    }
    [data-testid="stHeader"] {background: rgba(0,0,0,0);}
    .block-container {padding-top:.75rem; max-width:760px;}
    .shell {
        border:1px solid rgba(93,255,122,.35);
        border-radius:28px;
        padding:18px;
        background:rgba(0,0,0,.62);
    }
    .title {
        font-size:clamp(1.8rem,5vw,2.8rem);
        font-weight:1000;
        color:#caff5a;
        text-align:center;
        margin-bottom:8px;
    }
    .jar {
        height:310px;
        border-radius:42px 42px 95px 95px;
        border:3px solid rgba(176,255,70,.55);
        background:
            radial-gradient(circle at 50% 35%,rgba(210,255,60,.26),transparent 32%),
            rgba(0,255,120,.08);
        display:flex;
        justify-content:center;
        align-items:center;
        position:relative;
        overflow:hidden;
        margin:16px 0;
        box-shadow:inset 0 0 40px rgba(0,255,120,.10);
    }
    .jar:before {
        content:"";
        width:180px;
        height:180px;
        border-radius:50%;
        border:16px solid rgba(202,255,90,.30);
        border-left-color:#18f5a8;
        border-right-color:#ff9f12;
        position:absolute;
        animation:spin 1s linear infinite;
    }
    @keyframes spin {to{transform:rotate(360deg)}}
    .player-chip {
        position:absolute;
        padding:6px 10px;
        border-radius:999px;
        background:rgba(0,0,0,.58);
        border:1px solid rgba(202,255,90,.35);
        color:#eaffbd;
        font-size:.82rem;
        font-weight:900;
        white-space:nowrap;
        text-shadow:0 0 9px rgba(202,255,90,.45);
        animation:blendmove 4s linear infinite;
    }
    .player-chip:nth-child(1){top:38px;left:12px;animation-delay:0s}
    .player-chip:nth-child(2){top:88px;right:18px;animation-delay:.45s}
    .player-chip:nth-child(3){bottom:82px;left:24px;animation-delay:.9s}
    .player-chip:nth-child(4){bottom:38px;right:22px;animation-delay:1.35s}
    .player-chip:nth-child(5){top:145px;left:50%;animation-delay:1.8s}
    @keyframes blendmove {
        0% {transform:rotate(0deg) translateX(0) scale(1); opacity:.55}
        50% {transform:rotate(180deg) translateX(38px) scale(1.08); opacity:1}
        100% {transform:rotate(360deg) translateX(0) scale(1); opacity:.55}
    }
    .blade {
        font-size:4rem;
        z-index:3;
        filter:drop-shadow(0 0 14px rgba(202,255,90,.8));
    }
    .statusline {
        text-align:center;
        color:#92ffa8;
        font-weight:900;
        margin-top:8px;
    }
    .card {
        border-radius:18px;
        padding:14px 16px;
        background:rgba(255,255,255,.06);
        border:1px solid rgba(255,255,255,.12);
        margin-bottom:10px;
    }
    .scorebar {
        height:13px;
        background:rgba(255,255,255,.12);
        border-radius:999px;
        overflow:hidden;
        margin:8px 0;
    }
    </style>
    """, unsafe_allow_html=True)


def score_bar(score):
    try:
        s = max(0, min(100, float(score)))
    except Exception:
        s = 0
    return f'<div class="scorebar"><div style="height:100%;width:{s}%;background:linear-gradient(90deg,#5dff7b,#caff32,#ff8a00);"></div></div>'


def player_chips(df):
    names = []
    if df is not None and not df.empty and "player" in df.columns:
        names = [clean_text(x) for x in df["player"].dropna().astype(str).head(5).tolist()]
    while len(names) < 5:
        names.append("PLAYER FEED")
    return "".join([f'<div class="player-chip">{n}</div>' for n in names[:5]])


def card_section(df, title):
    st.markdown(f"### {title}")
    if df is None or df.empty:
        st.caption("No output yet.")
        return
    for _, r in df.head(3).iterrows():
        st.markdown(f"""
        <div class="card">
        <b>#{int(r.get('rank',0))} {clean_text(r.get('player',''))}</b><br>
        <span style="color:#caff5a;font-weight:900">{clean_text(r.get('fire',''))}</span>
        {score_bar(r.get('score',0))}
        <b>{clean_text(r.get('alert',''))}</b><br>
        <small>{clean_text(r.get('game_id',''))} — {clean_text(r.get('archetype',''))} — Score {r.get('score',0)}</small><br>
        <small>{clean_text(r.get('survivor_reason',''))}</small>
        </div>
        """, unsafe_allow_html=True)


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

st.markdown('<div class="shell">', unsafe_allow_html=True)
st.markdown('<div class="title">MASTER MLB BLENDER</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Feed the monster",
    type=["pdf", "png", "jpg", "jpeg", "webp", "csv", "xlsx", "xls", "txt", "tsv"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

if uploaded_files:
    df, status = feed_many_uploads(uploaded_files)
    st.session_state.feed_df = df
    st.session_state.feed_status = status
    st.session_state.file_count = len(uploaded_files)

st.markdown(
    f'<div class="jar">{player_chips(st.session_state.feed_df)}<div class="blade">⚙️</div></div>',
    unsafe_allow_html=True
)

if st.button("ENGAGE BLENDER", type="primary", use_container_width=True):
    st.session_state.results = run_blender(st.session_state.feed_df)
    st.success("MACHINE COMPLETE")

st.markdown(
    f'<div class="statusline">{st.session_state.file_count} FILES FED • {len(st.session_state.feed_df)} PLAYERS IN BLENDER</div>',
    unsafe_allow_html=True
)
st.markdown("</div>", unsafe_allow_html=True)

res = st.session_state.results
card_section(res.get("core3"), "🔥 Core 3")
card_section(res.get("alt3"), "🧯 Alt 3")
card_section(res.get("chaos3"), "🌪️ Chaos 3")

with st.expander("Game Board", expanded=False):
    st.dataframe(res.get("game_board"), use_container_width=True, hide_index=True)

with st.expander("Downloads / Feed Report", expanded=False):
    st.download_button("Download tickets.csv", csv_bytes(res.get("tickets", pd.DataFrame())), "tickets.csv", "text/csv")
    st.download_button("Download core.csv", csv_bytes(res.get("core3", pd.DataFrame())), "core.csv", "text/csv")
    st.download_button("Download alt.csv", csv_bytes(res.get("alt3", pd.DataFrame())), "alt.csv", "text/csv")
    st.download_button("Download chaos.csv", csv_bytes(res.get("chaos3", pd.DataFrame())), "chaos.csv", "text/csv")
    st.write(st.session_state.feed_status)
    st.dataframe(st.session_state.feed_df, use_container_width=True, hide_index=True)
