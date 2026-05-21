
import io
import re
from typing import Any, Dict, Tuple

import numpy as np
import pandas as pd
import streamlit as st

APP_VERSION = "V57 BLENDER-FIRST STABLE"

STANDARD_COLUMNS = [
    "game_id", "team", "opponent", "player", "bat_side", "pitcher", "pitcher_hand",
    "slot", "odds", "pull_pct", "hard_hit_pct", "barrel_pct", "launch_angle",
    "pitch_edge", "hr9_split", "recent_hr_allowed", "notes", "source"
]

OUTPUT_COLUMNS = [
    "bucket", "rank", "game_id", "team", "opponent", "player", "pitcher",
    "archetype", "status", "score", "fire", "alert", "survivor_reason", "gate_log"
]

BAD_WORDS = {
    "advanced", "performance", "projected", "athletics", "page", "pitcher", "pitchers",
    "batter", "batters", "lineup", "lineups", "team", "teams", "opponent", "game", "games",
    "home", "away", "runs", "run", "mlb", "baseball", "leaderboard", "dashboard",
    "template", "sample", "score", "rank", "date", "time", "updated", "matchup",
    "stat", "stats", "statistics", "core", "alt", "chaos", "board", "share", "github",
    "streamlit", "download", "upload", "file", "rows", "recovered"
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


def safe_player_name(name: Any, raw_line: Any = "") -> bool:
    n = clean_text(name)
    low = n.lower()
    if not n or len(n) < 5 or len(n) > 42:
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
    return all(re.match(r"^[A-Z][a-zA-Z'.-]{1,}$", p) for p in parts)


looks_like_player_name = safe_player_name


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


def standardize_df(df: pd.DataFrame, source: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=STANDARD_COLUMNS)

    df = df.copy()
    df.columns = [norm_col(c) for c in df.columns]

    if "player" not in df.columns:
        best, hits = None, 0
        for c in df.columns:
            h = df[c].astype(str).map(lambda x: safe_player_name(x)).sum()
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

    df = df[df["player"].map(lambda x: safe_player_name(x, x))].copy()

    for c in ["slot", "odds", "pull_pct", "hard_hit_pct", "barrel_pct", "launch_angle", "hr9_split", "recent_hr_allowed"]:
        df[c] = df[c].map(to_num)

    if not df.empty:
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
        agg["notes"] = lambda s: " | ".join(dict.fromkeys([clean_text(x) for x in s if clean_text(x)]))[:2600]
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
            for page in pdf.pages:
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
    return "\n".join(chunks), warnings


def recover_rows_from_text(text: str, source: str) -> pd.DataFrame:
    lines = [clean_text(x) for x in text.splitlines() if clean_text(x)]
    records = []
    current_game = "Unknown Game"
    game_pat = re.compile(r"\b([A-Z]{2,3})\s*(?:@|vs\.?|VS|v)\s*([A-Z]{2,3})\b")

    for line in lines:
        low = line.lower()
        if any(bad in low for bad in ["share", "github", "manage app", "download", "streamlit"]):
            continue
        gm = game_pat.search(line)
        if gm:
            current_game = f"{gm.group(1)} vs {gm.group(2)}"

        cells = [clean_text(x) for x in (line.split("|") if "|" in line else re.split(r"\s{2,}", line)) if clean_text(x)]
        candidates = [c for c in cells[:6] if safe_player_name(c, line)]

        if not candidates and re.search(r"\d|%|\+|HR|ISO|Barrel|Pull|Hard|Ult|Dmg|HPI|Adj|Odds|Slot", line, re.I):
            for nm in re.findall(r"\b([A-Z][a-zA-Z'.-]+(?:\s+[A-Z][a-zA-Z'.-]+){1,2})\b", line):
                if safe_player_name(nm, line):
                    candidates.append(nm)

        for player in dict.fromkeys(candidates):
            rec = {"game_id": current_game, "player": player, "notes": line, "source": source}
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
            status["mode"] = "table"
        elif name.endswith(".pdf"):
            text, warnings = extract_pdf_text(uploaded_file)
            df = recover_rows_from_text(text, uploaded_file.name)
            status["mode"] = "PDF"
            status["warnings"].extend(warnings)
        else:
            df = pd.DataFrame(columns=STANDARD_COLUMNS)
            status["mode"] = "unsupported"
    except Exception as e:
        df = pd.DataFrame(columns=STANDARD_COLUMNS)
        status["mode"] = "safe fallback"
        status["warnings"].append(str(e))
    status["recovered_rows"] = int(len(df))
    return df, status


def feed_many_uploads(uploaded_files) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    frames, statuses, raw_rows = [], [], 0
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
        agg["notes"] = lambda s: " | ".join(dict.fromkeys([clean_text(x) for x in s if clean_text(x)]))[:2600]
        df = df.groupby(["game_id", "player"], dropna=False, as_index=False).agg(agg)
        df = df[STANDARD_COLUMNS].reset_index(drop=True)
    else:
        df = pd.DataFrame(columns=STANDARD_COLUMNS)

    return df, {
        "mode": "multi-file merge",
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
    if status == "CORE-ELIGIBLE" and score >= 90:
        return "🚨 HE’S HITTING A HOME RUN TODAY 🚨"
    if status == "CORE-ELIGIBLE":
        return "🔥 CORE HR LOCK CANDIDATE"
    if status == "ALT-TRANSFER":
        return "⚡ NEXT-MAN / DECOY TRANSFER ALERT"
    if status == "CHAOS-ELIGIBLE":
        return "🌪️ WHO / CHAOS HR ALERT"
    return "⚠️ SURVIVED, NOT CLEAN"


def gate18(row):
    player = clean_text(row.get("player", ""))
    if not safe_player_name(player):
        return None

    notes = (clean_text(row.get("notes", "")) + " " + clean_text(row.get("pitch_edge", ""))).lower()
    pull, hh, barrel, la = fnum(row,"pull_pct"), fnum(row,"hard_hit_pct"), fnum(row,"barrel_pct"), fnum(row,"launch_angle")
    hr9, recent, slot, odds = fnum(row,"hr9_split"), fnum(row,"recent_hr_allowed"), fnum(row,"slot"), fnum(row,"odds")
    score = 0
    logs = []

    def add(val, msg):
        nonlocal score
        score += val
        logs.append(msg)

    add(4, "G1 No Empty Bat: PASS")
    game_id = clean_text(row.get("game_id","")) or "Unknown Game"
    add(5 if game_id != "Unknown Game" else -4, "G2 Game Context")
    add(7, "G3 Archetype classified")

    if not pd.isna(pull):
        add(14 if pull >= 45 else 11 if pull >= 42 else 4 if pull >= 35 else -12, f"G4 Pull-Air {pull}")
    else:
        add(-7, "G4 Pull-Air missing")

    if not pd.isna(hh):
        add(14 if hh >= 50 else 11 if hh >= 45 else 3 if hh >= 38 else -11, f"G5 Hard-Hit {hh}")
    else:
        add(-6, "G5 Hard-Hit missing")

    launch_pass = False
    if not pd.isna(la) and 12 <= la <= 32:
        add(11, f"G6 Launch Window {la}")
        launch_pass = True
    elif not pd.isna(barrel) and barrel >= 10:
        add(12, f"G6 Barrel Conversion {barrel}")
        launch_pass = True
    elif not pd.isna(barrel):
        add(4, f"G6 Barrel support {barrel}")
    else:
        add(-4, "G6 Barrel/Launch missing")

    pitch_words = ["4-seam","fastball","slider","sinker","curve","change","cutter","splitter","edge","+","mistake"]
    pitch_pass = any(w in notes for w in pitch_words)
    add(14 if pitch_pass else -7, "G7 Pitch-Type Kill Switch")

    if not pd.isna(hr9) and hr9 > 0: add(min(hr9*8,14), "G8 Pitcher HR/9")
    else: logs.append("G8 Pitcher HR/9 missing")

    if not pd.isna(recent) and recent > 0: add(min(recent*6,12), "G9 Recent HR Allowed")
    else: logs.append("G9 Recent HR missing")

    if not pd.isna(slot): add(9 if 1 <= slot <= 5 else 4, f"G10 Lineup Slot {slot}")
    else: logs.append("G10 Slot missing")

    adjacent = any(w in notes for w in ["adjacent","decoy","secondary","behind","after","protection","next man"])
    add(10 if adjacent else 0, "G10.5 Adjacent/Decoy" if adjacent else "G10.5 No adjacent trigger")

    if any(w in notes for w in ["protection","pitch around","walk risk"]): add(5, "G11 Protection/Pitch-around")
    else: logs.append("G11 Protection neutral")

    if any(w in notes for w in ["bullpen","reliever","pen"]): add(5, "G12 Bullpen Continuation")
    else: logs.append("G12 Bullpen unknown")

    chaos = any(w in notes for w in ["chaos","who","value","green","blowout","wind","weather","bullpen"]) or (not pd.isna(slot) and slot >= 6)
    add(8 if chaos else 0, "G13 WHO/Chaos" if chaos else "G13 No chaos trigger")

    if (not pd.isna(barrel) and barrel >= 10) or (not pd.isna(hh) and hh >= 50): add(7, "G14 True HR Conversion")
    else: logs.append("G14 Conversion not confirmed")

    clean_power = (not pd.isna(pull) and pull >= 42) and (not pd.isna(hh) and hh >= 45)
    if clean_power and (launch_pass or pitch_pass): add(8, "G15 Event Ownership PASS")
    elif adjacent or chaos: add(4, "G15 ALT/Chaos path")
    else: add(-3, "G15 weak ownership")

    if not pd.isna(odds): add(3 if abs(odds) <= 700 else 1, "G16 Market/Odds")
    else: logs.append("G16 Odds missing")

    finisher = clean_power and (launch_pass or pitch_pass)
    if finisher: add(10, "G17 Finisher Gate PASS")
    elif adjacent: add(5, "G17 Adjacent pass")
    elif chaos: add(4, "G17 Chaos pass")
    else: add(-5, "G17 Finisher fail")

    if finisher and pitch_pass: add(8, "G18 Final Lock CLEAN")
    elif adjacent: add(4, "G18 ALT lock")
    elif chaos: add(3, "G18 CHAOS lock")
    else: logs.append("G18 incomplete")

    score = max(0, min(100, round(score, 1)))
    if finisher and score >= 78: status = "CORE-ELIGIBLE"
    elif adjacent and score >= 55: status = "ALT-TRANSFER"
    elif chaos and score >= 45: status = "CHAOS-ELIGIBLE"
    else: status = "SURVIVED BUT NOT CLEAN"

    if status == "CHAOS-ELIGIBLE": archetype = "WHO / CHAOS"
    elif status == "ALT-TRANSFER": archetype = "ADJACENT / DECOY TRANSFER"
    elif finisher: archetype = "LANE MATCH FINISHER"
    elif clean_power: archetype = "CLEAN POWER OWNER"
    else: archetype = "RECOVERED / NEEDS DATA"

    reasons = []
    if not pd.isna(pull) and pull >= 42: reasons.append("PULL-AIR")
    if not pd.isna(hh) and hh >= 45: reasons.append("HARD-HIT")
    if not pd.isna(barrel) and barrel >= 10: reasons.append("BARREL")
    if launch_pass: reasons.append("LAUNCH")
    if pitch_pass: reasons.append("PITCH-KILL")
    if adjacent: reasons.append("ADJACENT")
    if chaos: reasons.append("CHAOS")
    if not reasons: reasons = ["18-gate data gap"]

    return {
        "game_id": game_id, "team": clean_text(row.get("team","")), "opponent": clean_text(row.get("opponent","")),
        "player": player, "pitcher": clean_text(row.get("pitcher","")), "archetype": archetype, "status": status,
        "score": score, "fire": score_fire(score), "alert": alert_text(score, status),
        "survivor_reason": " + ".join(reasons), "gate_log": " | ".join(logs),
    }


def choose_game_owner(group):
    priority = {"CORE-ELIGIBLE": 4, "ALT-TRANSFER": 3, "CHAOS-ELIGIBLE": 2, "SURVIVED BUT NOT CLEAN": 1}
    g = group.copy()
    g["priority"] = g["status"].map(priority).fillna(0)
    return g.sort_values(["priority","score"], ascending=[False,False]).head(1).drop(columns=["priority"])


def run_blender(df):
    empty = pd.DataFrame(columns=OUTPUT_COLUMNS)
    if df is None or df.empty:
        return {"tickets": empty, "core3": empty, "alt3": empty, "chaos3": empty, "game_board": empty}

    rows = []
    for _, r in df.iterrows():
        out = gate18(r)
        if out:
            rows.append(out)

    pool = pd.DataFrame(rows)
    if pool.empty:
        return {"tickets": empty, "core3": empty, "alt3": empty, "chaos3": empty, "game_board": empty}

    game_board = pool.groupby("game_id", group_keys=False).apply(choose_game_owner).reset_index(drop=True)
    game_board.insert(0, "rank", range(1, len(game_board)+1))
    game_board.insert(0, "bucket", "GAME SURVIVOR")

    core3 = game_board.sort_values("score", ascending=False).head(3).copy()
    core3["bucket"] = "CORE 3"
    core3["rank"] = range(1, len(core3)+1)

    used = set(core3["player"].tolist())
    remaining = pool[~pool["player"].isin(used)].copy()

    alt = remaining[remaining["status"].isin(["ALT-TRANSFER","CORE-ELIGIBLE"])].sort_values("score", ascending=False).head(3)
    if len(alt) < 3:
        alt = pd.concat([alt, remaining[~remaining.index.isin(alt.index)].sort_values("score", ascending=False).head(3-len(alt))])
    alt = alt.copy()
    alt.insert(0, "rank", range(1, len(alt)+1))
    alt.insert(0, "bucket", "ALT 3")

    used |= set(alt["player"].tolist())
    chaos_pool = pool[~pool["player"].isin(used)].copy()
    chaos = chaos_pool[chaos_pool["status"].eq("CHAOS-ELIGIBLE")].sort_values("score", ascending=False).head(3)
    if len(chaos) < 3:
        chaos = pd.concat([chaos, chaos_pool[~chaos_pool.index.isin(chaos.index)].sort_values("score", ascending=True).head(3-len(chaos))])
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


def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8")


def inject_css():
    st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at 20% 10%, rgba(160,255,0,.15), transparent 25%),
                    radial-gradient(circle at 80% 80%, rgba(0,140,255,.12), transparent 25%),
                    #030503;
        color:#f5fff3;
    }
    [data-testid="stHeader"] {background: rgba(0,0,0,0);}
    .block-container {padding-top: .75rem; max-width: 920px;}
    .shell {border:1px solid rgba(93,255,122,.35);border-radius:28px;padding:18px;background:rgba(0,0,0,.55);}
    .title {font-size:clamp(1.7rem,5vw,2.7rem);font-weight:1000;color:#caff5a;text-align:center;}
    .jar {height:250px;border-radius:40px 40px 90px 90px;border:3px solid rgba(176,255,70,.5);
          background:radial-gradient(circle at 50% 35%,rgba(210,255,60,.25),transparent 30%),rgba(0,255,120,.08);
          display:flex;justify-content:center;align-items:center;position:relative;overflow:hidden;margin:14px 0;}
    .jar:before{content:"";width:170px;height:170px;border-radius:50%;border:16px solid rgba(202,255,90,.3);border-left-color:#18f5a8;border-right-color:#ff9f12;position:absolute;animation:spin 1s linear infinite;}
    .jar:after{content:"⚾ ⚾ ⚾";position:absolute;font-size:2rem;animation:orbit 2.2s linear infinite;}
    @keyframes spin{to{transform:rotate(360deg)}}@keyframes orbit{0%{transform:rotate(0deg) translateX(70px) rotate(0deg)}100%{transform:rotate(360deg) translateX(70px) rotate(-360deg)}}
    .blade{font-size:4rem;z-index:2}
    .ready{border:1px solid rgba(112,255,146,.36);background:rgba(0,255,90,.085);color:#92ffa8;border-radius:18px;padding:13px 16px;font-weight:900;margin-top:10px;}
    .card{border-radius:18px;padding:14px 16px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);margin-bottom:10px;}
    .scorebar{height:13px;background:rgba(255,255,255,.12);border-radius:999px;overflow:hidden;margin:8px 0;}
    </style>
    """, unsafe_allow_html=True)


def score_bar(score):
    try: s = max(0, min(100, float(score)))
    except Exception: s = 0
    return f'<div class="scorebar"><div style="height:100%;width:{s}%;background:linear-gradient(90deg,#5dff7b,#caff32,#ff8a00);"></div></div>'


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
        <small>{clean_text(r.get('game_id',''))} — {clean_text(r.get('archetype',''))} — Score {r.get('score',0)}</small>
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
st.markdown(f'<div class="title">MASTER MLB BLENDER</div><div style="text-align:center">{APP_VERSION}</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "Feed the blender files",
    type=["csv", "xlsx", "xls", "pdf"],
    accept_multiple_files=True,
)

if uploaded_files:
    df, status = feed_many_uploads(uploaded_files)
    st.session_state.feed_df = df
    st.session_state.feed_status = status
    st.session_state.file_count = len(uploaded_files)

st.markdown('<div class="jar"><div class="blade">⚙️</div></div>', unsafe_allow_html=True)

if st.button("ENGAGE BLENDER", type="primary", use_container_width=True):
    st.session_state.results = run_blender(st.session_state.feed_df)
    st.success("MACHINE COMPLETE — tickets built")

rows = len(st.session_state.feed_df)
st.markdown(
    f'<div class="ready">FILES: {st.session_state.file_count} | BLENDER POOL ROWS: {rows}</div>',
    unsafe_allow_html=True
)
st.markdown("</div>", unsafe_allow_html=True)

res = st.session_state.results
card_section(res.get("core3"), "🔥 Core 3")
card_section(res.get("alt3"), "🧯 Alt 3")
card_section(res.get("chaos3"), "🌪️ Chaos 3")

with st.expander("Game Board — one survivor per game", expanded=False):
    st.dataframe(res.get("game_board"), use_container_width=True, hide_index=True)

with st.expander("Tickets / CSV downloads", expanded=False):
    st.download_button("Download tickets.csv", csv_bytes(res.get("tickets", pd.DataFrame())), "tickets.csv", "text/csv")
    st.download_button("Download core.csv", csv_bytes(res.get("core3", pd.DataFrame())), "core.csv", "text/csv")
    st.download_button("Download alt.csv", csv_bytes(res.get("alt3", pd.DataFrame())), "alt.csv", "text/csv")
    st.download_button("Download chaos.csv", csv_bytes(res.get("chaos3", pd.DataFrame())), "chaos.csv", "text/csv")
    st.dataframe(res.get("tickets"), use_container_width=True, hide_index=True)

with st.expander("Recovered feeder table", expanded=False):
    st.dataframe(st.session_state.feed_df, use_container_width=True, hide_index=True)
