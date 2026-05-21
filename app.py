import io
import re
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st


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

BAD_WORDS = {
    "advanced", "performance", "projected", "athletics", "page", "pitcher", "pitchers",
    "batter", "batters", "lineup", "lineups", "team", "teams", "opponent", "game", "games",
    "home", "away", "runs", "run", "mlb", "baseball", "leaderboard", "dashboard",
    "template", "sample", "score", "rank", "date", "time", "updated", "matchup",
    "stat", "stats", "statistics", "core", "alt", "chaos", "board",
    "share", "github", "streamlit", "download", "upload", "file", "rows", "recovered"
}

BAD_PHRASES = {
    "advanced mlb performance", "am page", "athletics projected", "mlb performance",
    "player pool", "projected lineup", "projected lineups", "home run", "hard hit",
    "barrel rate", "launch angle", "pitch edge", "game board", "core 3", "alt 3", "chaos 3"
}


def clean_text(x: Any) -> str:
    if x is None:
        return ""
    return re.sub(r"\s+", " ", str(x).replace("\u00a0", " ").replace("\t", " ")).strip()


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
        "tm": "team", "opp": "opponent", "vs": "opponent",
        "starter": "pitcher", "sp": "pitcher", "probable_pitcher": "pitcher",
        "throws": "pitcher_hand", "p_hand": "pitcher_hand", "pitcher_throws": "pitcher_hand",
        "lineup_spot": "slot", "batting_order": "slot", "order": "slot",
        "pull": "pull_pct", "pull_percent": "pull_pct", "pull_percentage": "pull_pct",
        "hardhit": "hard_hit_pct", "hard_hit": "hard_hit_pct", "hard_hit_percent": "hard_hit_pct",
        "hardhit_percent": "hard_hit_pct", "hh": "hard_hit_pct", "hh_pct": "hard_hit_pct",
        "barrel": "barrel_pct", "barrel_percent": "barrel_pct",
        "la": "launch_angle", "launch": "launch_angle",
        "pitch_type_edge": "pitch_edge", "edge": "pitch_edge", "pitch_match": "pitch_edge",
        "hr_9": "hr9_split", "hr9": "hr9_split", "l_r_hr_9_hr": "hr9_split",
        "recent_hr": "recent_hr_allowed", "hr_allowed_home_or_away": "recent_hr_allowed",
    }
    return aliases.get(c, c)


def looks_like_player_name(name: str, raw_line: str = "") -> bool:
    n = clean_text(name)
    low = n.lower()
    if not n or len(n) < 5 or len(n) > 34:
        return False
    if n.isupper():
        return False
    if low in BAD_PHRASES or any(p in low for p in BAD_PHRASES):
        return False
    if re.search(r"\d", n):
        return False
    parts = n.split()
    if len(parts) < 2 or len(parts) > 3:
        return False
    if any(p.lower() in BAD_WORDS for p in parts):
        return False
    if len(parts) == 2 and parts[0].lower() in {"am", "pm", "vs", "at"}:
        return False
    for p in parts:
        if not re.match(r"^[A-Z][a-zA-Z'.-]{1,}$", p):
            return False
    return True


def standardize_df(df: pd.DataFrame, source: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=STANDARD_COLUMNS)

    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]

    if "player" not in df.columns:
        best, hits = None, 0
        for c in df.columns:
            h = df[c].astype(str).map(lambda x: looks_like_player_name(x)).sum()
            if h > hits:
                best, hits = c, h
        if best:
            df = df.rename(columns={best: "player"})

    for c in STANDARD_COLUMNS:
        if c not in df.columns:
            df[c] = ""

    df["source"] = source
    for c in ["game_id", "team", "opponent", "player", "bat_side", "pitcher", "pitcher_hand", "pitch_edge", "notes", "source"]:
        df[c] = df[c].map(clean_text)

    df = df[df["player"].map(lambda x: looks_like_player_name(x, x))].copy()

    for c in ["slot", "odds", "pull_pct", "hard_hit_pct", "barrel_pct", "launch_angle", "hr9_split", "recent_hr_allowed"]:
        df[c] = df[c].map(to_num)

    missing = df["game_id"].eq("")
    combo = (df["team"].astype(str) + " vs " + df["opponent"].astype(str)).str.strip()
    df.loc[missing, "game_id"] = combo[missing].replace(" vs ", "")
    df["game_id"] = df["game_id"].replace("", "Unknown Game")

    def first_real(s):
        for v in s:
            if clean_text(v) and clean_text(v).lower() != "nan":
                return v
        return ""

    agg = {c: first_real for c in STANDARD_COLUMNS if c != "notes"}
    agg["notes"] = lambda s: " | ".join(dict.fromkeys([clean_text(x) for x in s if clean_text(x)]))[:1800]
    df = df.groupby(["game_id", "player"], dropna=False, as_index=False).agg(agg)

    return df[STANDARD_COLUMNS].reset_index(drop=True)


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


def extract_pdf_text(uploaded_file) -> Tuple[str, list]:
    raw = uploaded_file.getvalue()
    chunks, warnings = [], []
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text(x_tolerance=1, y_tolerance=3) or ""
                if text.strip():
                    chunks.append(text)
                for table in page.extract_tables() or []:
                    for row in table:
                        chunks.append(" | ".join(clean_text(x) for x in row))
    except Exception as e:
        warnings.append(f"pdfplumber skipped: {e}")

    try:
        import fitz
        doc = fitz.open(stream=raw, filetype="pdf")
        for page in doc:
            text = page.get_text("text") or ""
            if text.strip():
                chunks.append(text)
    except Exception as e:
        warnings.append(f"PyMuPDF skipped: {e}")

    try:
        import fitz, pytesseract
        from PIL import Image
        doc = fitz.open(stream=raw, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2.7, 2.7), alpha=False)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img, config="--psm 6")
            if text.strip():
                chunks.append(text)
    except Exception:
        if not chunks:
            warnings.append("OCR unavailable. Add packages.txt with tesseract-ocr on Streamlit Cloud.")

    return "\n".join(chunks), warnings


def extract_image_text(uploaded_file) -> Tuple[str, list]:
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageEnhance
        img = Image.open(io.BytesIO(uploaded_file.getvalue())).convert("RGB")
        gray = ImageOps.grayscale(img)
        gray = ImageEnhance.Contrast(gray).enhance(2.0)
        return pytesseract.image_to_string(gray, config="--psm 6"), []
    except Exception:
        return "", ["OCR unavailable. Add packages.txt with tesseract-ocr on Streamlit Cloud."]


def split_cells(line: str) -> list:
    line = clean_text(line)
    if "|" in line:
        return [clean_text(x) for x in line.split("|") if clean_text(x)]
    return [clean_text(x) for x in re.split(r"\s{2,}", line) if clean_text(x)]


def recover_rows_from_text(text: str, source: str) -> pd.DataFrame:
    lines = [clean_text(x) for x in text.splitlines() if clean_text(x)]
    current_game, current_team, current_opp, current_pitcher = "Unknown Game", "", "", ""
    game_pat = re.compile(r"\b([A-Z]{2,3})\s*(?:@|vs\.?|VS|v)\s*([A-Z]{2,3})\b")
    records = []

    for line in lines:
        low = line.lower()
        if any(bad in low for bad in ["share", "github", "manage app", "download", "streamlit"]):
            continue

        gm = game_pat.search(line)
        if gm and gm.group(1) in TEAM_CODES and gm.group(2) in TEAM_CODES:
            current_team, current_opp = gm.group(1), gm.group(2)
            current_game = f"{current_team} vs {current_opp}"

        cells = split_cells(line)
        candidates = [c for c in cells[:6] if looks_like_player_name(c, line)]

        if not candidates and re.search(r"\d|%|\+|HR|ISO|Barrel|Pull|Hard|Ult|Dmg|HPI|Adj|Odds|Slot", line, re.I):
            for nm in re.findall(r"\b([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){1,2})\b", line):
                if looks_like_player_name(nm, line):
                    candidates.append(nm)

        for player in dict.fromkeys(candidates):
            rec = {
                "game_id": current_game, "team": current_team, "opponent": current_opp,
                "player": player, "pitcher": current_pitcher, "notes": line, "source": source
            }
            nums = re.findall(r"-?\d+(?:\.\d+)?%?", line)
            if "pull" in low and nums: rec["pull_pct"] = nums[-1]
            if ("hard" in low or "hh" in low) and nums: rec["hard_hit_pct"] = nums[-1]
            if "barrel" in low and nums: rec["barrel_pct"] = nums[-1]
            if "launch" in low and nums: rec["launch_angle"] = nums[-1]
            if any(p in low for p in ["4-seam","fastball","slider","sinker","curve","change","cutter","splitter","edge"]):
                rec["pitch_edge"] = line
            if "hr/9" in low or "hr9" in low: rec["hr9_split"] = nums[-1] if nums else ""
            if "recent" in low and "hr" in low: rec["recent_hr_allowed"] = nums[-1] if nums else ""
            records.append(rec)

    return standardize_df(pd.DataFrame(records), source)


def feed_upload(uploaded_file) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    status = {"file": uploaded_file.name, "mode": "", "recovered_rows": 0, "warnings": []}
    name = uploaded_file.name.lower()
    try:
        if name.endswith((".csv", ".xlsx", ".xls")):
            df = standardize_df(read_csv_or_excel(uploaded_file), uploaded_file.name)
            status["mode"] = "table recovery"
        elif name.endswith(".pdf"):
            text, warnings = extract_pdf_text(uploaded_file)
            df = recover_rows_from_text(text, uploaded_file.name)
            status["mode"] = "PDF text/table/OCR recovery"
            status["warnings"].extend(warnings)
        elif name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            text, warnings = extract_image_text(uploaded_file)
            df = recover_rows_from_text(text, uploaded_file.name)
            status["mode"] = "image OCR recovery"
            status["warnings"].extend(warnings)
        else:
            df = pd.DataFrame(columns=STANDARD_COLUMNS)
            status["mode"] = "unsupported"
            status["warnings"].append("Unsupported file type.")
    except Exception as e:
        df = pd.DataFrame(columns=STANDARD_COLUMNS)
        status["mode"] = "safe fallback"
        status["warnings"].append(f"Feeder recovered after error: {e}")

    status["recovered_rows"] = int(len(df))
    return df, status


def feed_many_uploads(uploaded_files) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    frames = []
    statuses = []
    raw_rows = 0

    for f in uploaded_files:
        file_df, file_status = feed_upload(f)
        statuses.append(file_status)
        raw_rows += int(file_status.get("recovered_rows", 0))
        if file_df is not None and not file_df.empty:
            frames.append(file_df)

    if frames:
        df = pd.concat(frames, ignore_index=True)

        def first_real(s):
            for v in s:
                if clean_text(v) and clean_text(v).lower() != "nan":
                    return v
            return ""

        agg = {c: first_real for c in STANDARD_COLUMNS if c != "notes"}
        agg["notes"] = lambda s: " | ".join(dict.fromkeys([clean_text(x) for x in s if clean_text(x)]))[:2200]
        df = df.groupby(["game_id", "player"], dropna=False, as_index=False).agg(agg)
        df = df[STANDARD_COLUMNS].reset_index(drop=True)
    else:
        df = pd.DataFrame(columns=STANDARD_COLUMNS)

    status = {
        "file": f"{len(uploaded_files)} files",
        "mode": "TRUE MULTI-FILE FEEDER MERGE",
        "recovered_rows": int(len(df)),
        "raw_recovered_rows": int(raw_rows),
        "file_statuses": statuses,
        "warnings": [w for s in statuses for w in s.get("warnings", [])],
    }
    return df, status


OUTPUT_COLUMNS = ["bucket", "rank", "game_id", "team", "opponent", "player", "pitcher", "score", "survivor_reason", "gate_log"]


def fnum(row, col):
    try:
        v = row.get(col, np.nan)
        return np.nan if pd.isna(v) else float(v)
    except Exception:
        return np.nan


def score_row(row):
    score, logs, reasons = 10.0, ["G1 player recovered"], []
    pull, hh, barrel, la = fnum(row,"pull_pct"), fnum(row,"hard_hit_pct"), fnum(row,"barrel_pct"), fnum(row,"launch_angle")
    edge = (clean_text(row.get("pitch_edge","")) + " " + clean_text(row.get("notes",""))).lower()
    hr9, recent, slot = fnum(row,"hr9_split"), fnum(row,"recent_hr_allowed"), fnum(row,"slot")

    if not pd.isna(pull):
        score += min(max(pull,0),65)*0.62; reasons.append("pull-air"); logs.append(f"G2 pull {pull}")
    else:
        score += 6; logs.append("G2 pull missing")
    if not pd.isna(la) and 12 <= la <= 32:
        score += 12; reasons.append("launch window"); logs.append(f"G2b launch {la}")
    if not pd.isna(hh):
        score += min(max(hh,0),70)*0.45; reasons.append("hard-hit"); logs.append(f"G3 HH {hh}")
    else:
        score += 5; logs.append("G3 HH missing")
    if not pd.isna(barrel):
        score += min(max(barrel,0),30)*1.35; reasons.append("barrel"); logs.append(f"G4 barrel {barrel}")
    if any(w in edge for w in ["4-seam","fastball","slider","sinker","curve","change","cutter","splitter","edge","+","mistake"]):
        score += 15; reasons.append("pitch edge"); logs.append("G5 pitch edge")
    if not pd.isna(hr9):
        score += min(max(hr9,0)*13,26); reasons.append("pitcher HR/9"); logs.append(f"G6 HR9 {hr9}")
    if not pd.isna(recent):
        score += min(max(recent,0)*9,24); reasons.append("recent HR allowed"); logs.append(f"G7 recent {recent}")
    if not pd.isna(slot):
        score += 10 if 1 <= slot <= 5 else 5
        reasons.append("lineup slot"); logs.append(f"G8 slot {slot}")
    if any(w in edge for w in ["chaos","who","secondary","adjacent","decoy","value","green"]):
        score += 11; reasons.append("chaos/adjacent"); logs.append("G9 chaos/adjacent")

    if not reasons:
        reasons.append("recovered feeder survivor")
    return round(score,2), " + ".join(reasons), " | ".join(logs)


def run_blender(df):
    empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
    if df is None or df.empty:
        return {"tickets": empty, "core3": empty, "alt3": empty, "chaos3": empty, "game_board": empty}

    rows = []
    for _, r in df.iterrows():
        if not looks_like_player_name(r.get("player",""), r.get("notes","")):
            continue
        score, reason, log = score_row(r)
        rows.append({
            "game_id": clean_text(r.get("game_id","")) or "Unknown Game",
            "team": clean_text(r.get("team","")),
            "opponent": clean_text(r.get("opponent","")),
            "player": clean_text(r.get("player","")),
            "pitcher": clean_text(r.get("pitcher","")),
            "score": score,
            "survivor_reason": reason,
            "gate_log": log
        })

    scored = pd.DataFrame(rows)
    if scored.empty:
        return {"tickets": empty, "core3": empty, "alt3": empty, "chaos3": empty, "game_board": empty}

    scored = scored.sort_values(["game_id","score"], ascending=[True,False]).reset_index(drop=True)

    game_board = scored.groupby("game_id", as_index=False).head(1).sort_values("score", ascending=False).reset_index(drop=True)
    game_board.insert(0, "rank", range(1, len(game_board)+1))
    game_board.insert(0, "bucket", "GAME SURVIVOR")

    core3 = game_board.head(3).copy()
    core3["bucket"] = "CORE 3"
    core3["rank"] = range(1, len(core3)+1)

    alt = scored.groupby("game_id").nth(1).reset_index().sort_values("score", ascending=False).head(3).copy()
    alt.insert(0, "rank", range(1, len(alt)+1))
    alt.insert(0, "bucket", "ALT 3")

    used = set(core3["player"].tolist()) | set(alt["player"].tolist())
    chaos = scored[~scored["player"].isin(used)].copy()
    if not chaos.empty:
        chaos["chaos_boost"] = chaos["survivor_reason"].str.contains("chaos|adjacent|lower|recovered|recent", case=False, regex=True).astype(int)*25 + chaos["score"]
        chaos = chaos.sort_values("chaos_boost", ascending=False).head(3).drop(columns=["chaos_boost"])
    chaos.insert(0, "rank", range(1, len(chaos)+1))
    chaos.insert(0, "bucket", "CHAOS 3")

    tickets = pd.concat([core3, alt, chaos], ignore_index=True)
    tickets["ticket_type"] = tickets["bucket"]

    return {
        "tickets": tickets,
        "core3": core3[OUTPUT_COLUMNS],
        "alt3": alt[OUTPUT_COLUMNS],
        "chaos3": chaos[OUTPUT_COLUMNS],
        "game_board": game_board[OUTPUT_COLUMNS]
    }


def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


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
    div[data-testid="stTabs"] button {font-weight: 900 !important;}
    .shell{border:1px solid rgba(93,255,122,.35);border-radius:30px;padding:22px;background:rgba(0,0,0,.48);box-shadow:0 0 35px rgba(82,255,105,.12),inset 0 0 35px rgba(255,255,255,.035);}
    .title{font-size:clamp(1.5rem,4vw,2.55rem);font-weight:1000;color:#caff5a;letter-spacing:.07em;text-shadow:0 0 22px rgba(190,255,60,.38);}
    .machine{display:grid;grid-template-columns:1fr 1.28fr 1fr;gap:18px;align-items:stretch;margin:18px 0;}
    .panel{border:1px solid rgba(255,255,255,.12);border-radius:22px;padding:18px;background:linear-gradient(180deg,rgba(255,255,255,.065),rgba(255,255,255,.025));min-height:260px;overflow:hidden;}
    .panel h3{margin-top:0;color:#7eff98;}
    .metric{border:1px solid rgba(255,255,255,.12);border-radius:17px;padding:13px 15px;margin-top:10px;background:rgba(0,0,0,.28);}
    .metric .big{font-size:2.15rem;font-weight:1000;color:#fff;line-height:1;}
    .feedstream,.eject{height:150px;position:relative;border-radius:18px;border:1px dashed rgba(140,255,90,.24);margin-top:12px;overflow:hidden;background:radial-gradient(circle at center,rgba(120,255,0,.08),transparent 55%);}
    .feedstream span{position:absolute;left:-120px;font-weight:900;color:#ccff5b;text-shadow:0 0 12px rgba(190,255,0,.7);animation:feedmove 2.4s linear infinite;}
    .feedstream span:nth-child(1){top:22px}.feedstream span:nth-child(2){top:66px;animation-delay:.55s}.feedstream span:nth-child(3){top:110px;animation-delay:1.1s}
    @keyframes feedmove{0%{left:-120px;opacity:0}10%{opacity:1}85%{opacity:1}100%{left:115%;opacity:0}}
    .lid{width:62%;height:18px;margin:0 auto;border-radius:14px 14px 4px 4px;background:linear-gradient(90deg,#b9ff1f,#18f5a8,#ff9f12);}
    .jar{min-height:310px;border-radius:44px 44px 92px 92px;border:3px solid rgba(176,255,70,.46);background:radial-gradient(circle at 50% 32%,rgba(210,255,60,.30),transparent 28%),linear-gradient(180deg,rgba(60,255,90,.16),rgba(0,180,255,.08));display:flex;justify-content:center;align-items:center;text-align:center;overflow:hidden;position:relative;box-shadow:inset 0 0 55px rgba(0,255,130,.16),0 0 40px rgba(120,255,0,.16);}
    .jar:before{content:"";width:190px;height:190px;border-radius:50%;border:18px solid rgba(202,255,90,.35);border-left-color:rgba(0,245,185,.78);border-right-color:rgba(255,160,20,.72);position:absolute;animation:spin 1.05s linear infinite;}
    .jar:after{content:"⚾ ⚾ ⚾";position:absolute;font-size:2.1rem;animation:orbit 2.2s linear infinite;}
    .blade{z-index:2;font-size:4.4rem;filter:drop-shadow(0 0 18px rgba(190,255,30,.65));}
    .jar-text{z-index:2;margin-top:100px;color:#f8fff1;font-weight:900;text-shadow:0 0 14px rgba(0,0,0,.85);}
    @keyframes spin{to{transform:rotate(360deg)}}@keyframes orbit{0%{transform:rotate(0deg) translateX(72px) rotate(0deg)}100%{transform:rotate(360deg) translateX(72px) rotate(-360deg)}}
    .eject span{position:absolute;right:-150px;font-weight:900;color:#77bdff;text-shadow:0 0 12px rgba(0,145,255,.65);animation:ejectmove 2.8s linear infinite;}
    .eject span:nth-child(1){top:20px}.eject span:nth-child(2){top:64px;animation-delay:.75s}.eject span:nth-child(3){top:108px;animation-delay:1.35s}
    @keyframes ejectmove{0%{right:-160px;opacity:0}10%{opacity:1}85%{opacity:1}100%{right:115%;opacity:0}}
    .ready{border:1px solid rgba(112,255,146,.36);background:rgba(0,255,90,.085);color:#92ffa8;border-radius:18px;padding:13px 16px;font-weight:900;}
    .survivor-card{border-radius:18px;padding:14px 16px;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.11);margin-bottom:10px;}
    @media(max-width:820px){.machine{grid-template-columns:1fr}.panel{min-height:auto}}
    </style>
    """, unsafe_allow_html=True)


def machine_visual(rows, games, teams, pitchers, file_count):
    st.markdown(f"""
    <div class="shell">
      <div class="title">MASTER MLB BLENDER MACHINE</div>
      <div>True multi-file feeder → blender gates → Core 3 / Alt 3 / Chaos 3 / Game Board.</div>
      <div class="machine">
        <div class="panel"><h3>DATA FEEDER</h3><p>Upload all split CSVs/PDFs/images together.</p><div class="metric"><div class="big">{file_count}</div>Files loaded</div><div class="metric"><div class="big">{rows}</div>Valid player rows</div><div class="feedstream"><span>CSV 1 →</span><span>CSV 2 →</span><span>CSV 3/4 →</span></div></div>
        <div class="panel"><div class="lid"></div><div class="jar"><div><div class="blade">⚙️</div><div class="jar-text">SPINNING BLENDER</div></div></div></div>
        <div class="panel"><h3>RESULT OUTPUT</h3><div class="metric"><div class="big">{games}</div>Games</div><div class="metric"><div class="big">{teams}</div>Teams</div><div class="metric"><div class="big">{pitchers}</div>Pitchers</div><div class="eject"><span>CORE 3 →</span><span>ALT 3 →</span><span>CHAOS 3 →</span></div></div>
      </div>
    """, unsafe_allow_html=True)


def show_table(df, title):
    st.subheader(title)
    if df is None or df.empty:
        st.info("No survivors yet. Feed files and click ENGAGE BLENDER.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def quick_cards(df, title):
    st.markdown(f"### {title}")
    if df is None or df.empty:
        st.caption("Waiting for blender output.")
        return
    for _, r in df.head(3).iterrows():
        st.markdown(f"""
        <div class="survivor-card">
          <b>#{int(r.get('rank',0))} {clean_text(r.get('player',''))}</b><br/>
          {clean_text(r.get('game_id',''))} — Score: {r.get('score','')}<br/>
          <small>{clean_text(r.get('survivor_reason',''))}</small>
        </div>
        """, unsafe_allow_html=True)


st.set_page_config(page_title="Master MLB Blender", page_icon="⚾", layout="wide")
inject_css()

if "feed_df" not in st.session_state:
    st.session_state.feed_df = pd.DataFrame(columns=STANDARD_COLUMNS)
if "feed_status" not in st.session_state:
    st.session_state.feed_status = {}
if "file_count" not in st.session_state:
    st.session_state.file_count = 0
if "results" not in st.session_state:
    st.session_state.results = run_blender(st.session_state.feed_df)

tabs = st.tabs(["⚙️ Blender Machine", "🎟️ Tickets", "🔥 Core 3", "🧯 Alt 3", "🌪️ Chaos 3", "🎮 Game Board"])

with tabs[0]:
    uploaded_files = st.file_uploader(
        "Feed the blender files",
        type=["csv", "xlsx", "xls", "pdf", "png", "jpg", "jpeg", "webp"],
        accept_multiple_files=True,
        help="Select all 4 split CSV files together. On iPhone, tap Browse then Select and choose multiple files."
    )

    if uploaded_files:
        df, status = feed_many_uploads(uploaded_files)
        st.session_state.feed_df = df
        st.session_state.feed_status = status
        st.session_state.file_count = len(uploaded_files)
        st.session_state.results = run_blender(df)

    df = st.session_state.feed_df
    games = int(df["game_id"].replace("", np.nan).dropna().nunique()) if not df.empty else 0
    teams = int(pd.concat([df["team"], df["opponent"]]).replace("", np.nan).dropna().nunique()) if not df.empty else 0
    pitchers = int(df["pitcher"].replace("", np.nan).dropna().nunique()) if not df.empty else 0

    machine_visual(len(df), games, teams, pitchers, st.session_state.file_count)

    col1, col2 = st.columns([1,2])
    with col1:
        if st.button("ENGAGE BLENDER", type="primary", use_container_width=True):
            st.session_state.results = run_blender(st.session_state.feed_df)
            st.success("MACHINE COMPLETE — tickets built")
    with col2:
        status = st.session_state.feed_status
        if status:
            raw_rows = status.get("raw_recovered_rows", status.get("recovered_rows", 0))
            st.markdown(f'<div class="ready">MULTI-FILE FEEDER LOCKED — {status.get("recovered_rows",0)} VALID PLAYER ROWS / {raw_rows} RAW ROWS</div>', unsafe_allow_html=True)
            if status.get("file_statuses"):
                with st.expander("Files loaded", expanded=False):
                    for fs in status["file_statuses"]:
                        st.write(f"{fs.get('file','file')} — {fs.get('mode','')} — {fs.get('recovered_rows',0)} rows")
            if status.get("warnings"):
                with st.expander("Feeder notes", expanded=False):
                    for w in status["warnings"]:
                        st.write(w)
        else:
            st.markdown('<div class="ready">WAITING FOR FILES — MULTI-FILE FEEDER READY</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    res = st.session_state.results
    c1,c2,c3 = st.columns(3)
    with c1: quick_cards(res.get("core3"), "Core 3 Preview")
    with c2: quick_cards(res.get("alt3"), "Alt 3 Preview")
    with c3: quick_cards(res.get("chaos3"), "Chaos 3 Preview")

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
