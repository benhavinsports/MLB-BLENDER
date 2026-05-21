import io
import re
import math
from typing import Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import streamlit as st


# ============================================================
# MASTER MLB BLENDER MACHINE — V48 FINAL
# One-file Streamlit app.
# Tabs only: Blender Machine, Tickets, Core 3, Alt 3, Chaos 3, Game Board
# Feeder accepts ONE file: CSV / Excel / PDF / image.
# Feeder never blocks the machine. It recovers, normalizes, and keeps rows alive.
# ============================================================

STANDARD_COLUMNS = [
    "game_id", "team", "opponent", "player", "bat_side", "pitcher", "pitcher_hand",
    "slot", "odds", "pull_pct", "hard_hit_pct", "barrel_pct", "launch_angle",
    "pitch_edge", "hr9_split", "recent_hr_allowed", "notes", "source"
]

TEAM_CODES = {
    "ARI","ATL","BAL","BOS","CHC","CWS","CHW","CIN","CLE","COL","DET","HOU","KC","KCR",
    "LAA","LAD","MIA","MIL","MIN","NYM","NYY","ATH","OAK","PHI","PIT","SD","SDP","SEA",
    "SF","SFG","STL","TB","TBR","TEX","TOR","WSH","WAS"
}


# -----------------------------
# Utilities
# -----------------------------
def clean_text(x: Any) -> str:
    if x is None:
        return ""
    s = str(x).replace("\u00a0", " ").replace("\t", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def to_num(x: Any):
    s = clean_text(x)
    if not s:
        return np.nan
    s = s.replace("%", "").replace("+", "")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    if not m:
        return np.nan
    try:
        return float(m.group(0))
    except Exception:
        return np.nan


def norm_col(c: Any) -> str:
    c = clean_text(c).lower()
    c = re.sub(r"[^a-z0-9]+", "_", c).strip("_")
    aliases = {
        "name": "player", "batter": "player", "hitter": "player", "player_name": "player",
        "tm": "team", "team_abbrev": "team", "opp": "opponent", "vs": "opponent",
        "starter": "pitcher", "sp": "pitcher", "probable_pitcher": "pitcher",
        "throws": "pitcher_hand", "p_hand": "pitcher_hand", "pitcher_throws": "pitcher_hand",
        "lineup_spot": "slot", "batting_order": "slot", "order": "slot", "bo": "slot",
        "pull": "pull_pct", "pull_percent": "pull_pct", "pull_percentage": "pull_pct",
        "hardhit": "hard_hit_pct", "hard_hit": "hard_hit_pct", "hard_hit_percent": "hard_hit_pct",
        "hardhit_percent": "hard_hit_pct", "hh": "hard_hit_pct", "hh_pct": "hard_hit_pct",
        "barrel": "barrel_pct", "barrel_percent": "barrel_pct", "barrel_percentage": "barrel_pct",
        "la": "launch_angle", "launch": "launch_angle",
        "pitch_type_edge": "pitch_edge", "edge": "pitch_edge", "pitch_match": "pitch_edge",
        "hr_9": "hr9_split", "hr9": "hr9_split", "l_r_hr_9_hr": "hr9_split",
        "recent_hr": "recent_hr_allowed", "hr_allowed_home_or_away": "recent_hr_allowed",
        "recent_hr_allowed_trend": "recent_hr_allowed", "notes_raw": "notes"
    }
    return aliases.get(c, c)


def standardize_df(df: pd.DataFrame, source: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=STANDARD_COLUMNS)

    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]

    if "player" not in df.columns:
        # Find the text column most likely to contain names
        best = None
        best_hits = 0
        for c in df.columns:
            hits = df[c].astype(str).str.contains(r"[A-Z][a-zA-Z'.-]+\s+[A-Z][a-zA-Z'.-]+", regex=True, na=False).sum()
            if hits > best_hits:
                best_hits = hits
                best = c
        if best:
            df = df.rename(columns={best: "player"})

    for c in STANDARD_COLUMNS:
        if c not in df.columns:
            df[c] = ""

    df["source"] = source

    for c in ["game_id", "team", "opponent", "player", "bat_side", "pitcher", "pitcher_hand", "pitch_edge", "notes", "source"]:
        df[c] = df[c].map(clean_text)

    for c in ["slot", "odds", "pull_pct", "hard_hit_pct", "barrel_pct", "launch_angle", "hr9_split", "recent_hr_allowed"]:
        df[c] = df[c].map(to_num)

    # Rebuild missing game id
    missing = df["game_id"].eq("")
    combo = (df["team"].astype(str) + " vs " + df["opponent"].astype(str)).str.strip()
    df.loc[missing, "game_id"] = combo[missing].replace(" vs ", "")

    # Keep all recoverable rows. Only remove complete blank junk.
    key = df[["game_id", "team", "opponent", "player", "pitcher", "notes"]].astype(str).agg(" ".join, axis=1).str.strip()
    df = df[key.ne("")].copy()

    # Merge duplicate player/game fragments by keeping first real values and combining notes.
    if not df.empty and "player" in df:
        group_cols = ["game_id", "player"]
        for c in group_cols:
            df[c] = df[c].replace("", np.nan)
        df["player"] = df["player"].fillna("")
        df["game_id"] = df["game_id"].fillna("Unknown Game")

        def first_real(s):
            for v in s:
                if clean_text(v) and clean_text(v).lower() != "nan":
                    return v
            return ""

        agg = {c: first_real for c in STANDARD_COLUMNS if c not in ["notes"]}
        agg["notes"] = lambda s: " | ".join(dict.fromkeys([clean_text(x) for x in s if clean_text(x)]))[:1200]
        df = df.groupby(group_cols, dropna=False, as_index=False).agg(agg)

    return df[STANDARD_COLUMNS].reset_index(drop=True)


# -----------------------------
# Feeder: CSV / Excel
# -----------------------------
def read_csv_or_excel(uploaded_file) -> pd.DataFrame:
    raw = uploaded_file.getvalue()
    name = uploaded_file.name.lower()

    if name.endswith(".csv"):
        for enc in ["utf-8", "utf-8-sig", "latin-1"]:
            try:
                return pd.read_csv(io.BytesIO(raw), encoding=enc)
            except Exception:
                pass
        return pd.read_csv(io.StringIO(raw.decode("utf-8", errors="ignore")), engine="python")

    if name.endswith((".xlsx", ".xls")):
        frames = []
        xls = pd.ExcelFile(io.BytesIO(raw))
        for sheet in xls.sheet_names:
            try:
                t = pd.read_excel(xls, sheet_name=sheet)
                t["source_sheet"] = sheet
                frames.append(t)
            except Exception:
                pass
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    return pd.DataFrame()


# -----------------------------
# Feeder: OCR/Text
# -----------------------------
def extract_pdf_text(uploaded_file) -> Tuple[str, List[str]]:
    raw = uploaded_file.getvalue()
    chunks = []
    warnings = []

    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                if text.strip():
                    chunks.append(f"\n--- PAGE {i+1} TEXT ---\n{text}")
                try:
                    tables = page.extract_tables() or []
                    for table in tables:
                        for row in table:
                            chunks.append(" | ".join(clean_text(x) for x in row))
                except Exception:
                    pass
    except Exception as e:
        warnings.append(f"pdfplumber skipped: {e}")

    try:
        import fitz
        doc = fitz.open(stream=raw, filetype="pdf")
        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            if text.strip():
                chunks.append(f"\n--- PAGE {i+1} FITZ ---\n{text}")
    except Exception as e:
        warnings.append(f"PyMuPDF text skipped: {e}")

    # OCR fallback. If tesseract is unavailable, app still works.
    try:
        import fitz
        import pytesseract
        from PIL import Image
        doc = fitz.open(stream=raw, filetype="pdf")
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, config="--psm 6")
            if text.strip():
                chunks.append(f"\n--- PAGE {i+1} OCR ---\n{text}")
    except Exception as e:
        warnings.append(f"OCR skipped: {e}")

    return "\n".join(chunks), warnings


def extract_image_text(uploaded_file) -> Tuple[str, List[str]]:
    warnings = []
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageEnhance
        img = Image.open(io.BytesIO(uploaded_file.getvalue())).convert("RGB")
        # Enhance screenshot readability
        gray = ImageOps.grayscale(img)
        gray = ImageEnhance.Contrast(gray).enhance(1.8)
        text = pytesseract.image_to_string(gray, config="--psm 6")
        return text, warnings
    except Exception as e:
        warnings.append(f"Image OCR skipped: {e}")
        return "", warnings


def recover_rows_from_text(text: str, source: str) -> pd.DataFrame:
    lines = [clean_text(x) for x in text.splitlines()]
    lines = [x for x in lines if x]

    name_pat = re.compile(r"\b([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){1,2})\b")
    game_pat = re.compile(r"\b([A-Z]{2,3})\s*(?:@|vs\.?|VS|v)\s*([A-Z]{2,3})\b")

    bad_names = {
        "Home Run", "Hard Hit", "Barrel Rate", "Launch Angle", "Pitcher Hand", "Game Board",
        "Core Three", "Alt Three", "Chaos Three", "Major League", "Player Pool",
        "Pitch Type", "Recent Form", "Pull Percent", "Bat Side"
    }

    current_game = ""
    current_team = ""
    current_opp = ""
    current_pitcher = ""
    records = []

    for line in lines:
        gm = game_pat.search(line)
        if gm and gm.group(1) in TEAM_CODES and gm.group(2) in TEAM_CODES:
            current_team, current_opp = gm.group(1), gm.group(2)
            current_game = f"{current_team} vs {current_opp}"

        # Pitcher/context lines
        if any(k in line.lower() for k in ["pitcher", "starter", "probable", "sp "]):
            nm = name_pat.search(line)
            if nm and nm.group(1) not in bad_names:
                current_pitcher = nm.group(1)

        names = name_pat.findall(line)
        for nm in names:
            if nm in bad_names:
                continue
            # Skip if it looks like a stat label instead of player
            if any(word in nm.lower() for word in ["hard hit", "home run", "pitch type", "game board"]):
                continue

            rec = {
                "game_id": current_game,
                "team": current_team,
                "opponent": current_opp,
                "player": nm,
                "pitcher": current_pitcher,
                "notes": line,
                "source": source,
            }

            # Pull/HH/Barrel/LA from same raw line if present
            low = line.lower()
            nums = re.findall(r"-?\d+(?:\.\d+)?%?", line)
            if "pull" in low and nums:
                rec["pull_pct"] = nums[-1]
            if ("hard" in low or "hh" in low) and nums:
                rec["hard_hit_pct"] = nums[-1]
            if "barrel" in low and nums:
                rec["barrel_pct"] = nums[-1]
            if "launch" in low and nums:
                rec["launch_angle"] = nums[-1]
            if any(p in low for p in ["4-seam", "fastball", "slider", "sinker", "curve", "change", "cutter", "splitter"]):
                rec["pitch_edge"] = line
            if "hr/9" in low or "hr9" in low:
                rec["hr9_split"] = nums[-1] if nums else ""
            if "recent" in low and "hr" in low:
                rec["recent_hr_allowed"] = nums[-1] if nums else ""

            records.append(rec)

    return standardize_df(pd.DataFrame(records), source)


def feed_upload(uploaded_file) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    status = {
        "file": uploaded_file.name,
        "mode": "",
        "recovered_rows": 0,
        "warnings": [],
    }
    name = uploaded_file.name.lower()

    try:
        if name.endswith((".csv", ".xlsx", ".xls")):
            raw_df = read_csv_or_excel(uploaded_file)
            df = standardize_df(raw_df, uploaded_file.name)
            status["mode"] = "table recovery"

        elif name.endswith(".pdf"):
            text, warnings = extract_pdf_text(uploaded_file)
            df = recover_rows_from_text(text, uploaded_file.name)
            status["mode"] = "PDF text + OCR recovery"
            status["warnings"].extend(warnings)
            if not text.strip():
                status["warnings"].append("No readable PDF text recovered. Add Tesseract OCR support in deployment for image-only PDFs.")

        elif name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            text, warnings = extract_image_text(uploaded_file)
            df = recover_rows_from_text(text, uploaded_file.name)
            status["mode"] = "image OCR recovery"
            status["warnings"].extend(warnings)
            if not text.strip():
                status["warnings"].append("No image text recovered. Add Tesseract OCR support in deployment.")

        else:
            df = pd.DataFrame(columns=STANDARD_COLUMNS)
            status["mode"] = "unsupported file fallback"
            status["warnings"].append("Unsupported file type.")
    except Exception as e:
        df = pd.DataFrame(columns=STANDARD_COLUMNS)
        status["mode"] = "safe fallback"
        status["warnings"].append(f"Feeder recovered without crashing after error: {e}")

    status["recovered_rows"] = int(len(df))
    return df, status


# -----------------------------
# Blender Gates
# -----------------------------


OUTPUT_COLUMNS = [
    "bucket", "rank", "game_id", "team", "opponent", "player", "pitcher",
    "archetype", "status", "score", "fire", "alert", "survivor_reason", "gate_log"
]


def fnum(row, col):
    try:
        v = row.get(col, np.nan)
        return np.nan if pd.isna(v) else float(v)
    except Exception:
        return np.nan


def has_any(text, words):
    t = clean_text(text).lower()
    return any(w.lower() in t for w in words)


def score_fire(score):
    if score >= 90:
        return "🔥🔥🔥 ELITE"
    if score >= 78:
        return "🔥🔥 STRONG"
    if score >= 65:
        return "🔥 LIVE"
    if score >= 50:
        return "⚠️ LEAN"
    return "🧊 COLD / DATA GAP"


def alert_text(score, status):
    if status == "CORE-ELIGIBLE" and score >= 90:
        return "🚨 HE’S HITTING A HOME RUN TODAY 🚨"
    if status == "CORE-ELIGIBLE":
        return "🔥 CORE HR LOCK CANDIDATE"
    if status == "ALT-TRANSFER":
        return "⚡ NEXT-MAN / DECOY TRANSFER ALERT"
    if status == "CHAOS-ELIGIBLE":
        return "🌪️ WHO / CHAOS HR ALERT"
    return "⚠️ SURVIVED, BUT NOT A CLEAN LOCK"


def classify_archetype(row):
    notes = (clean_text(row.get("notes", "")) + " " + clean_text(row.get("pitch_edge", ""))).lower()
    pull = fnum(row, "pull_pct")
    hh = fnum(row, "hard_hit_pct")
    barrel = fnum(row, "barrel_pct")
    la = fnum(row, "launch_angle")
    slot = fnum(row, "slot")

    flags = []
    if not pd.isna(pull) and pull >= 42: flags.append("PULL-AIR")
    if not pd.isna(hh) and hh >= 45: flags.append("HARD-HIT")
    if not pd.isna(barrel) and barrel >= 10: flags.append("BARREL")
    if not pd.isna(la) and 12 <= la <= 32: flags.append("LAUNCH")
    if has_any(notes, ["4-seam", "fastball", "slider", "sinker", "curve", "change", "cutter", "splitter", "edge", "mistake"]): flags.append("PITCH-KILL")
    if has_any(notes, ["adjacent", "decoy", "secondary", "behind", "after", "protection", "next man"]): flags.append("ADJACENT")
    if has_any(notes, ["chaos", "who", "value", "green", "recent hr", "blowout", "bullpen", "weather", "wind"]): flags.append("CHAOS")
    if not pd.isna(slot) and slot >= 6: flags.append("LOWER-SLOT")

    if "CHAOS" in flags or "LOWER-SLOT" in flags:
        archetype = "WHO / CHAOS"
    elif "ADJACENT" in flags:
        archetype = "ADJACENT / DECOY TRANSFER"
    elif "PITCH-KILL" in flags and ("PULL-AIR" in flags or "BARREL" in flags):
        archetype = "LANE MATCH FINISHER"
    elif "PULL-AIR" in flags and "HARD-HIT" in flags:
        archetype = "CLEAN POWER OWNER"
    elif "BARREL" in flags:
        archetype = "CONVERSION BAT"
    else:
        archetype = "RECOVERED / NEEDS DATA"

    return archetype, flags


def gate18_engine_row(row):
    player = clean_text(row.get("player", ""))
    if not looks_like_player_name(player, row.get("notes", "")):
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

    archetype, flags = classify_archetype(row)
    score = 0.0
    logs = []

    # 18-GATE BLENDER FLOW
    # Gate 1 — No Empty Bat / player recovered
    score += 4
    logs.append("G1 No Empty Bat: PASS")

    # Gate 2 — Game owner context / game attached
    game_id = clean_text(row.get("game_id","")) or "Unknown Game"
    if game_id != "Unknown Game":
        score += 5; logs.append("G2 Game Context: PASS")
    else:
        score -= 4; logs.append("G2 Game Context: UNKNOWN")

    # Gate 3 — Archetype classification
    if archetype != "RECOVERED / NEEDS DATA":
        score += 7; logs.append(f"G3 Archetype: {archetype}")
    else:
        score -= 5; logs.append("G3 Archetype: data gap")

    # Gate 4 — Pull-air / launch direction
    if not pd.isna(pull):
        if pull >= 45:
            score += 14; logs.append(f"G4 Pull-Air: ELITE {pull}")
        elif pull >= 42:
            score += 11; logs.append(f"G4 Pull-Air: PASS {pull}")
        elif pull >= 35:
            score += 4; logs.append(f"G4 Pull-Air: BORDERLINE {pull}")
        else:
            score -= 12; logs.append(f"G4 Pull-Air: FAIL {pull}")
    else:
        score -= 7; logs.append("G4 Pull-Air: MISSING")

    # Gate 5 — Hard-hit validation
    if not pd.isna(hh):
        if hh >= 50:
            score += 14; logs.append(f"G5 Hard-Hit: ELITE {hh}")
        elif hh >= 45:
            score += 11; logs.append(f"G5 Hard-Hit: PASS {hh}")
        elif hh >= 38:
            score += 3; logs.append(f"G5 Hard-Hit: BORDERLINE {hh}")
        else:
            score -= 11; logs.append(f"G5 Hard-Hit: FAIL {hh}")
    else:
        score -= 6; logs.append("G5 Hard-Hit: MISSING")

    # Gate 6 — Barrel / Launch window
    launch_pass = False
    if not pd.isna(la) and 12 <= la <= 32:
        score += 11; launch_pass = True; logs.append(f"G6 Launch Window: PASS {la}")
    elif not pd.isna(barrel) and barrel >= 10:
        score += 12; launch_pass = True; logs.append(f"G6 Barrel Conversion: PASS {barrel}")
    elif not pd.isna(barrel):
        score += 4; logs.append(f"G6 Barrel: support {barrel}")
    else:
        score -= 4; logs.append("G6 Barrel/Launch: MISSING")

    # Gate 7 — Pitch-type kill switch
    pitch_words = ["4-seam","fastball","slider","sinker","curve","change","cutter","splitter","edge","+","mistake"]
    pitch_pass = any(w in notes for w in pitch_words)
    if pitch_pass:
        score += 14; logs.append("G7 Pitch-Type Kill Switch: PASS")
    else:
        score -= 7; logs.append("G7 Pitch-Type Kill Switch: NOT CONFIRMED")

    # Gate 8 — Pitcher HR weakness
    if not pd.isna(hr9) and hr9 > 0:
        add = min(hr9 * 8, 14); score += add; logs.append(f"G8 Pitcher HR/9: +{add:.1f}")
    else:
        logs.append("G8 Pitcher HR/9: missing")

    # Gate 9 — Recent HR allowed / green trend
    if not pd.isna(recent) and recent > 0:
        add = min(recent * 6, 12); score += add; logs.append(f"G9 Recent HR Allowed: GREEN +{add:.1f}")
    else:
        logs.append("G9 Recent HR Allowed: not confirmed")

    # Gate 10 — Lineup opportunity
    if not pd.isna(slot):
        if 1 <= slot <= 5:
            score += 9; logs.append(f"G10 Lineup Opportunity: TOP HALF {slot}")
        else:
            score += 4; logs.append(f"G10 Lineup Opportunity: LOWER WHO SLOT {slot}")
    else:
        logs.append("G10 Lineup Opportunity: missing")

    # Gate 10.5 — Book decoy / adjacent shadow
    adjacent = any(w in notes for w in ["adjacent","decoy","secondary","behind","after","protection","next man"])
    if adjacent:
        score += 10; logs.append("G10.5 Adjacent / Decoy Transfer: TRIGGERED")
    else:
        logs.append("G10.5 Adjacent / Decoy Transfer: no trigger")

    # Gate 11 — Pitch-around / protection
    if any(w in notes for w in ["protection", "pitch around", "walk risk", "pitched around"]):
        score += 5; logs.append("G11 Protection/Pitch-Around: context found")
    else:
        logs.append("G11 Protection/Pitch-Around: neutral")

    # Gate 12 — Bullpen continuation
    if any(w in notes for w in ["bullpen", "reliever", "pen", "continues lane"]):
        score += 5; logs.append("G12 Bullpen Continuation: support")
    else:
        logs.append("G12 Bullpen Continuation: unknown")

    # Gate 13 — Chaos / WHO environment
    chaos = any(w in notes for w in ["chaos","who","value","green","blowout","wind","weather","bullpen"]) or (not pd.isna(slot) and slot >= 6)
    if chaos:
        score += 8; logs.append("G13 WHO / Chaos Flag: TRIGGERED")
    else:
        logs.append("G13 WHO / Chaos Flag: no trigger")

    # Gate 14 — True HR conversion profile
    if (not pd.isna(barrel) and barrel >= 10) or (not pd.isna(hh) and hh >= 50):
        score += 7; logs.append("G14 True HR Conversion Profile: PASS")
    else:
        logs.append("G14 True HR Conversion Profile: not fully confirmed")

    # Gate 15 — Event ownership isolation
    clean_power = (not pd.isna(pull) and pull >= 42) and (not pd.isna(hh) and hh >= 45)
    if clean_power and (launch_pass or pitch_pass):
        score += 8; logs.append("G15 Event Ownership Isolation: PASS")
    elif adjacent or chaos:
        score += 4; logs.append("G15 Event Ownership Isolation: ALT/CHAOS path")
    else:
        score -= 3; logs.append("G15 Event Ownership Isolation: weak")

    # Gate 16 — Odds / market pressure and decoy read
    if not pd.isna(odds):
        if abs(odds) <= 700:
            score += 3; logs.append(f"G16 Market/Odds: usable {odds}")
        else:
            score += 1; logs.append(f"G16 Market/Odds: longshot/volatile {odds}")
    else:
        logs.append("G16 Market/Odds: missing")

    # Gate 17 — Finisher gate
    finisher = clean_power and (launch_pass or pitch_pass)
    if finisher:
        score += 10; logs.append("G17 Finisher Gate: PASS")
    elif adjacent:
        score += 5; logs.append("G17 Finisher Gate: adjacent shadow pass")
    elif chaos:
        score += 4; logs.append("G17 Finisher Gate: chaos pass")
    else:
        score -= 5; logs.append("G17 Finisher Gate: FAIL")

    # Gate 18 — Final lock audit
    if finisher and pitch_pass:
        score += 8; logs.append("G18 Final Lock Audit: CLEAN LOCK")
    elif adjacent:
        score += 4; logs.append("G18 Final Lock Audit: ALT LOCK")
    elif chaos:
        score += 3; logs.append("G18 Final Lock Audit: CHAOS LOCK")
    else:
        logs.append("G18 Final Lock Audit: incomplete lock")

    score = max(0, min(100, round(score, 1)))

    if finisher and score >= 78:
        status = "CORE-ELIGIBLE"
    elif adjacent and score >= 55:
        status = "ALT-TRANSFER"
    elif chaos and score >= 45:
        status = "CHAOS-ELIGIBLE"
    else:
        status = "SURVIVED BUT NOT CLEAN"

    fire = score_fire(score)
    alert = alert_text(score, status)

    reason_parts = [x for x in ["PULL-AIR","HARD-HIT","BARREL","LAUNCH","PITCH-KILL","ADJACENT","CHAOS","LOWER-SLOT"] if x in flags]
    if not reason_parts:
        reason_parts = ["18-gate recovered data gap"]

    return {
        "game_id": game_id,
        "team": clean_text(row.get("team","")),
        "opponent": clean_text(row.get("opponent","")),
        "player": player,
        "pitcher": clean_text(row.get("pitcher","")),
        "archetype": archetype,
        "status": status,
        "score": score,
        "fire": fire,
        "alert": alert,
        "survivor_reason": " + ".join(reason_parts),
        "gate_log": " | ".join(logs),
    }


def choose_game_owner(group):
    g = group.copy()
    priority = {"CORE-ELIGIBLE": 4, "ALT-TRANSFER": 3, "CHAOS-ELIGIBLE": 2, "SURVIVED BUT NOT CLEAN": 1}
    g["priority"] = g["status"].map(priority).fillna(0)
    return g.sort_values(["priority", "score"], ascending=[False, False]).head(1).drop(columns=["priority"])


def run_blender(df):
    empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
    if df is None or df.empty:
        return {"tickets": empty, "core3": empty, "alt3": empty, "chaos3": empty, "game_board": empty}

    pool = pd.DataFrame([x for _, r in df.iterrows() for x in [gate18_engine_row(r)] if x])
    if pool.empty:
        return {"tickets": empty, "core3": empty, "alt3": empty, "chaos3": empty, "game_board": empty}

    game_board = pool.groupby("game_id", group_keys=False).apply(choose_game_owner).reset_index(drop=True)
    priority = {"CORE-ELIGIBLE": 4, "ALT-TRANSFER": 3, "CHAOS-ELIGIBLE": 2, "SURVIVED BUT NOT CLEAN": 1}
    game_board["_p"] = game_board["status"].map(priority).fillna(0)
    game_board = game_board.sort_values(["_p", "score"], ascending=[False, False]).drop(columns=["_p"]).reset_index(drop=True)
    game_board.insert(0, "rank", range(1, len(game_board)+1))
    game_board.insert(0, "bucket", "GAME SURVIVOR")

    core_source = game_board[game_board["status"].eq("CORE-ELIGIBLE")]
    if len(core_source) < 3:
        core_source = pd.concat([core_source, game_board[~game_board.index.isin(core_source.index)]], ignore_index=False)
    core3 = core_source.head(3).copy()
    core3["bucket"] = "CORE 3"
    core3["rank"] = range(1, len(core3)+1)

    used = set(core3["player"].tolist())
    remaining = pool[~pool["player"].isin(used)].copy()

    alt_pref = remaining[remaining["status"].isin(["ALT-TRANSFER", "CORE-ELIGIBLE"])]
    alt = alt_pref.sort_values("score", ascending=False).head(3)
    if len(alt) < 3:
        fill = remaining[~remaining.index.isin(alt.index)].sort_values("score", ascending=False).head(3-len(alt))
        alt = pd.concat([alt, fill])
    alt = alt.copy()
    alt.insert(0, "rank", range(1, len(alt)+1))
    alt.insert(0, "bucket", "ALT 3")

    used |= set(alt["player"].tolist())
    chaos_pool = pool[~pool["player"].isin(used)].copy()
    chaos_pref = chaos_pool[
        chaos_pool["status"].eq("CHAOS-ELIGIBLE")
        | chaos_pool["archetype"].str.contains("CHAOS|ADJACENT", case=False, regex=True)
        | chaos_pool["survivor_reason"].str.contains("CHAOS|LOWER-SLOT|ADJACENT", case=False, regex=True)
    ]
    chaos = chaos_pref.sort_values("score", ascending=False).head(3)
    if len(chaos) < 3:
        fill = chaos_pool[~chaos_pool.index.isin(chaos.index)].sort_values("score", ascending=True).head(3-len(chaos))
        chaos = pd.concat([chaos, fill])
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
    }


def csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


# -----------------------------
# UI
# -----------------------------
def inject_css():
    st.markdown("""
    <style>
    .stApp {
        background:
            linear-gradient(rgba(70,255,80,.045) 1px, transparent 1px),
            linear-gradient(90deg, rgba(70,255,80,.045) 1px, transparent 1px),
            radial-gradient(circle at 12% 10%, rgba(181,255,0,.20), transparent 26%),
            radial-gradient(circle at 80% 85%, rgba(0,145,255,.14), transparent 30%),
            linear-gradient(135deg, #030503 0%, #071007 52%, #020202 100%);
        background-size: 48px 48px, 48px 48px, auto, auto, auto;
        color: #f5fff3;
    }
    [data-testid="stHeader"] {background: rgba(0,0,0,0);}
    .block-container {padding-top: 1rem; max-width: 1120px;}
    div[data-testid="stTabs"] button {
        font-weight: 900 !important;
        letter-spacing: .02em;
    }
    .shell {
        border: 1px solid rgba(93,255,122,.35);
        border-radius: 30px;
        padding: 22px;
        background: rgba(0,0,0,.48);
        box-shadow: 0 0 35px rgba(82,255,105,.12), inset 0 0 35px rgba(255,255,255,.035);
    }
    .title {
        font-size: clamp(1.5rem, 4vw, 2.55rem);
        font-weight: 1000;
        color: #caff5a;
        letter-spacing: .07em;
        text-shadow: 0 0 22px rgba(190,255,60,.38);
        margin-bottom: 4px;
    }
    .sub {
        color: rgba(245,255,245,.74);
        font-size: .98rem;
        margin-bottom: 16px;
    }
    .machine {
        display:grid;
        grid-template-columns: 1fr 1.28fr 1fr;
        gap: 18px;
        align-items: stretch;
        margin: 18px 0;
    }
    .panel {
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 22px;
        padding: 18px;
        background: linear-gradient(180deg, rgba(255,255,255,.065), rgba(255,255,255,.025));
        min-height: 260px;
        overflow:hidden;
    }
    .panel h3 {margin-top:0; color:#7eff98; letter-spacing:.04em;}
    .metric {
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 17px;
        padding: 13px 15px;
        margin-top: 10px;
        background: rgba(0,0,0,.28);
    }
    .metric .big {
        font-size: 2.15rem;
        font-weight: 1000;
        color: #fff;
        line-height: 1;
    }
    .feedstream {
        height: 150px;
        position: relative;
        border-radius: 18px;
        background: radial-gradient(circle at center, rgba(120,255,0,.08), transparent 55%);
        border: 1px dashed rgba(140,255,90,.24);
        margin-top: 12px;
        overflow:hidden;
    }
    .feedstream span {
        position:absolute;
        left:-80px;
        font-weight:900;
        color:#ccff5b;
        text-shadow:0 0 12px rgba(190,255,0,.7);
        animation: feedmove 2.4s linear infinite;
    }
    .feedstream span:nth-child(1){top:22px; animation-delay:0s;}
    .feedstream span:nth-child(2){top:66px; animation-delay:.55s;}
    .feedstream span:nth-child(3){top:110px; animation-delay:1.1s;}
    @keyframes feedmove {
        0% {left:-120px; opacity:0;}
        10% {opacity:1;}
        85% {opacity:1;}
        100% {left:115%; opacity:0;}
    }
    .jar-wrap {position:relative;}
    .lid {
        width: 62%;
        height: 18px;
        margin: 0 auto;
        border-radius: 14px 14px 4px 4px;
        background: linear-gradient(90deg, #b9ff1f, #18f5a8, #ff9f12);
        box-shadow: 0 0 20px rgba(170,255,0,.25);
    }
    .jar {
        min-height: 310px;
        border-radius: 44px 44px 92px 92px;
        border: 3px solid rgba(176,255,70,.46);
        background:
            radial-gradient(circle at 50% 32%, rgba(210,255,60,.30), transparent 28%),
            linear-gradient(180deg, rgba(60,255,90,.16), rgba(0,180,255,.08));
        display:flex;
        justify-content:center;
        align-items:center;
        text-align:center;
        overflow:hidden;
        position:relative;
        box-shadow: inset 0 0 55px rgba(0,255,130,.16), 0 0 40px rgba(120,255,0,.16);
    }
    .jar:before {
        content:"";
        width: 190px;
        height: 190px;
        border-radius: 50%;
        border: 18px solid rgba(202,255,90,.35);
        border-left-color: rgba(0,245,185,.78);
        border-right-color: rgba(255,160,20,.72);
        position:absolute;
        animation: spin 1.05s linear infinite;
        filter: blur(.2px);
    }
    .jar:after {
        content:"⚾ ⚾ ⚾";
        position:absolute;
        font-size:2.1rem;
        animation: orbit 2.2s linear infinite;
        opacity:.95;
    }
    .blade {
        z-index:2;
        font-size:4.4rem;
        filter: drop-shadow(0 0 18px rgba(190,255,30,.65));
    }
    .jar-text {
        z-index:2;
        margin-top:100px;
        color:#f8fff1;
        font-weight: 900;
        text-shadow:0 0 14px rgba(0,0,0,.85);
    }
    @keyframes spin {to {transform:rotate(360deg);}}
    @keyframes orbit {
        0% {transform: rotate(0deg) translateX(72px) rotate(0deg);}
        100% {transform: rotate(360deg) translateX(72px) rotate(-360deg);}
    }
    .eject {
        height: 150px;
        border-radius: 18px;
        border: 1px dashed rgba(80,180,255,.26);
        margin-top: 12px;
        position:relative;
        overflow:hidden;
        background: radial-gradient(circle at center, rgba(0,140,255,.10), transparent 55%);
    }
    .eject span {
        position:absolute;
        right:-150px;
        font-weight:900;
        color:#77bdff;
        text-shadow:0 0 12px rgba(0,145,255,.65);
        animation: ejectmove 2.8s linear infinite;
    }
    .eject span:nth-child(1){top:20px; animation-delay:.2s;}
    .eject span:nth-child(2){top:64px; animation-delay:.75s;}
    .eject span:nth-child(3){top:108px; animation-delay:1.35s;}
    @keyframes ejectmove {
        0% {right:-160px; opacity:0;}
        10% {opacity:1;}
        85% {opacity:1;}
        100% {right:115%; opacity:0;}
    }
    .ready {
        border: 1px solid rgba(112,255,146,.36);
        background: rgba(0,255,90,.085);
        color: #92ffa8;
        border-radius: 18px;
        padding: 13px 16px;
        font-weight: 900;
    }
    .done {
        border: 1px solid rgba(66,162,255,.42);
        background: rgba(0,90,255,.13);
        color: #80c3ff;
        border-radius: 18px;
        padding: 13px 16px;
        font-weight: 900;
    }
    .survivor-card {
        border-radius: 18px;
        padding: 14px 16px;
        background: rgba(255,255,255,.055);
        border: 1px solid rgba(255,255,255,.11);
        margin-bottom: 10px;
    }
    @media (max-width: 820px) {
        .machine {grid-template-columns: 1fr;}
        .panel {min-height: auto;}
    }
    </style>
    """, unsafe_allow_html=True)


def machine_visual(rows: int, games: int, teams: int, pitchers: int):
    st.markdown(f"""
    <div class="shell">
        <div class="title">MASTER MLB BLENDER MACHINE</div>
        <div class="sub">One feeder → full blender gates → Core 3 / Alt 3 / Chaos 3 / Game Board. No extra tabs.</div>
        <div class="machine">
            <div class="panel">
                <h3>DATA FEEDER</h3>
                <p>Feed one PDF, screenshot, CSV, or Excel file.</p>
                <div class="metric"><div class="big">{rows}</div>Recovered player rows</div>
                <div class="feedstream">
                    <span>PLAYER ROWS →</span>
                    <span>PDF DATA →</span>
                    <span>SCREENSHOT OCR →</span>
                </div>
            </div>
            <div class="panel jar-wrap">
                <div class="lid"></div>
                <div class="jar">
                    <div>
                        <div class="blade">⚙️</div>
                        <div class="jar-text">SPINNING BLENDER</div>
                    </div>
                </div>
            </div>
            <div class="panel">
                <h3>RESULT OUTPUT</h3>
                <div class="metric"><div class="big">{games}</div>Games</div>
                <div class="metric"><div class="big">{teams}</div>Teams</div>
                <div class="metric"><div class="big">{pitchers}</div>Pitchers</div>
                <div class="eject">
                    <span>CORE 3 →</span>
                    <span>ALT 3 →</span>
                    <span>CHAOS 3 →</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


def show_table(df: pd.DataFrame, title: str):
    st.subheader(title)
    if df is None or df.empty:
        st.info("No survivors yet. Feed a file on the Blender Machine tab and click ENGAGE BLENDER.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)



def score_bar_html(score):
    try:
        s = float(score)
    except Exception:
        s = 0
    s = max(0, min(100, s))
    return f"""
    <div style="height:13px;background:rgba(255,255,255,.12);border-radius:999px;overflow:hidden;margin:8px 0 4px;">
      <div style="height:100%;width:{s}%;background:linear-gradient(90deg,#5dff7b,#caff32,#ff8a00);border-radius:999px;"></div>
    </div>
    """


def quick_cards(df, title):
    st.markdown(f"### {title}")
    if df is None or df.empty:
        st.caption("Waiting for blender output.")
        return
    for _, r in df.head(3).iterrows():
        score = r.get("score", 0)
        st.markdown(f"""
        <div class="survivor-card">
          <b>#{int(r.get('rank',0))} {clean_text(r.get('player',''))}</b><br/>
          <span style="color:#caff5a;font-weight:900;">{clean_text(r.get('fire',''))}</span><br/>
          {score_bar_html(score)}
          <b>{clean_text(r.get('alert',''))}</b><br/>
          <small>{clean_text(r.get('game_id',''))} — Score: {score} — {clean_text(r.get('archetype',''))}</small><br/>
          <small>{clean_text(r.get('status',''))} | {clean_text(r.get('survivor_reason',''))}</small>
        </div>
        """, unsafe_allow_html=True)



st.set_page_config(page_title="Master MLB Blender", page_icon="⚾", layout="wide")
inject_css()

if "feed_df" not in st.session_state:
    st.session_state.feed_df = pd.DataFrame(columns=STANDARD_COLUMNS)
if "feed_status" not in st.session_state:
    st.session_state.feed_status = {}
if "results" not in st.session_state:
    st.session_state.results = run_blender(st.session_state.feed_df)

tabs = st.tabs(["⚙️ Blender Machine", "🎟️ Tickets", "🔥 Core 3", "🧯 Alt 3", "🌪️ Chaos 3", "🎮 Game Board"])

with tabs[0]:
    uploaded = st.file_uploader(
        "Feed the blender one file",
        type=["csv", "xlsx", "xls", "pdf", "png", "jpg", "jpeg", "webp"],
        accept_multiple_files=False,
    )

    if uploaded is not None:
        df, status = feed_upload(uploaded)
        st.session_state.feed_df = df
        st.session_state.feed_status = status
        st.session_state.results = run_blender(df)

    df = st.session_state.feed_df
    games = int(df["game_id"].replace("", np.nan).dropna().nunique()) if not df.empty else 0
    teams = int(pd.concat([df["team"], df["opponent"]]).replace("", np.nan).dropna().nunique()) if not df.empty else 0
    pitchers = int(df["pitcher"].replace("", np.nan).dropna().nunique()) if not df.empty else 0

    machine_visual(len(df), games, teams, pitchers)

    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("ENGAGE BLENDER", type="primary", use_container_width=True):
            st.session_state.results = run_blender(st.session_state.feed_df)
            st.success("MACHINE COMPLETE — tickets built")
    with col2:
        status = st.session_state.feed_status
        if status:
            st.markdown(
                f'<div class="ready">FEEDER LOCKED — {status.get("mode","")} — {status.get("recovered_rows",0)} ROWS RECOVERED</div>',
                unsafe_allow_html=True
            )
            for w in status.get("warnings", [])[:4]:
                st.warning(w)
        else:
            st.markdown('<div class="ready">WAITING FOR FILE — FEEDER READY</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    res = st.session_state.results
    c1, c2, c3 = st.columns(3)
    with c1:
        quick_cards(res.get("core3"), "Core 3 Preview")
    with c2:
        quick_cards(res.get("alt3"), "Alt 3 Preview")
    with c3:
        quick_cards(res.get("chaos3"), "Chaos 3 Preview")

    with st.expander("Recovered feeder table", expanded=False):
        st.dataframe(st.session_state.feed_df, use_container_width=True, hide_index=True)

results = st.session_state.results

with tabs[1]:
    show_table(results.get("tickets"), "Tickets Built")
    st.download_button("Download tickets.csv", csv_bytes(results.get("tickets", pd.DataFrame())), "tickets.csv", "text/csv", use_container_width=True)

with tabs[2]:
    show_table(results.get("core3"), "Core 3")
    st.download_button("Download core.csv", csv_bytes(results.get("core3", pd.DataFrame())), "core.csv", "text/csv", use_container_width=True)

with tabs[3]:
    show_table(results.get("alt3"), "Alt 3")
    st.download_button("Download alt.csv", csv_bytes(results.get("alt3", pd.DataFrame())), "alt.csv", "text/csv", use_container_width=True)

with tabs[4]:
    show_table(results.get("chaos3"), "Chaos 3")
    st.download_button("Download chaos.csv", csv_bytes(results.get("chaos3", pd.DataFrame())), "chaos.csv", "text/csv", use_container_width=True)

with tabs[5]:
    show_table(results.get("game_board"), "Game Board — One Survivor From Each Game")
    st.download_button("Download game_board.csv", csv_bytes(results.get("game_board", pd.DataFrame())), "game_board.csv", "text/csv", use_container_width=True)
