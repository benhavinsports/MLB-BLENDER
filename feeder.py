from __future__ import annotations

import io
import re
import tempfile
from pathlib import Path
import pandas as pd
import numpy as np

TEAM_NAMES = [
"Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox",
"Cincinnati Reds","Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals",
"Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets",
"New York Yankees","Athletics","Oakland Athletics","Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres",
"San Francisco Giants","Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers","Toronto Blue Jays",
"Washington Nationals"
]
TEAM_RE = re.compile("|".join([re.escape(t) for t in sorted(TEAM_NAMES, key=len, reverse=True)]), re.I)

TEAM_ABBR = {
    "ARI":"Arizona Diamondbacks","ATL":"Atlanta Braves","BAL":"Baltimore Orioles","BOS":"Boston Red Sox","CHC":"Chicago Cubs",
    "CWS":"Chicago White Sox","CHW":"Chicago White Sox","CIN":"Cincinnati Reds","CLE":"Cleveland Guardians","COL":"Colorado Rockies",
    "DET":"Detroit Tigers","HOU":"Houston Astros","KC":"Kansas City Royals","KCR":"Kansas City Royals","LAA":"Los Angeles Angels",
    "LAD":"Los Angeles Dodgers","MIA":"Miami Marlins","MIL":"Milwaukee Brewers","MIN":"Minnesota Twins","NYM":"New York Mets",
    "NYY":"New York Yankees","ATH":"Athletics","OAK":"Oakland Athletics","PHI":"Philadelphia Phillies","PIT":"Pittsburgh Pirates",
    "SD":"San Diego Padres","SDP":"San Diego Padres","SF":"San Francisco Giants","SFG":"San Francisco Giants","SEA":"Seattle Mariners",
    "STL":"St. Louis Cardinals","TB":"Tampa Bay Rays","TBR":"Tampa Bay Rays","TEX":"Texas Rangers","TOR":"Toronto Blue Jays","WSH":"Washington Nationals","WAS":"Washington Nationals"
}
ABBR_RE = re.compile(r"\b(" + "|".join(map(re.escape, sorted(TEAM_ABBR, key=len, reverse=True))) + r")\b")

METRIC_COLS = ["lineup_slot","pull_pct","hard_hit_pct","barrel_pct","sweet_spot_pct","dmg","hpi","hr_lane","pitch_edge"]


def _txt(x) -> str:
    try:
        if x is None or pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def _num(x, default=np.nan):
    try:
        if x is None or pd.isna(x):
            return default
        s = str(x).replace("%", "").replace("+", "").replace(",", "").strip()
        if s.lower() in {"", "nan", "none", "null", "-", "—"}:
            return default
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group(0)) if m else default
    except Exception:
        return default


def _compact(s) -> str:
    return str(s).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")


def _find_col(df: pd.DataFrame, aliases: list[str]):
    cmap = {_compact(c): c for c in df.columns}
    for a in aliases:
        aa = _compact(a)
        if aa in cmap:
            return cmap[aa]
    for a in aliases:
        aa = _compact(a)
        for k, v in cmap.items():
            if aa in k or k in aa:
                return v
    return None


def extract_pdf_text(raw: bytes) -> str:
    text = ""
    try:
        import fitz
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(raw)
            path = f.name
        doc = fitz.open(path)
        for page in doc:
            text += "\n" + page.get_text("text")
    except Exception:
        pass
    return text


def extract_pdf_tables(raw: bytes) -> pd.DataFrame:
    rows = []
    try:
        import pdfplumber
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(raw)
            path = f.name
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                for table in page.extract_tables() or []:
                    if not table or len(table) < 2:
                        continue
                    headers = [_txt(x) or f"col_{i}" for i, x in enumerate(table[0])]
                    for rr in table[1:]:
                        rows.append({h: v for h, v in zip(headers, rr)})
    except Exception:
        pass
    return pd.DataFrame(rows)


def normalize_table(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    raw = df.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    aliases = {
        "player":["player","hitter","batter","name"],
        "team":["team","club","bat team","batter team"],
        "opponent":["opponent","opp","vs"],
        "pitcher":["pitcher","sp","starter","opposing pitcher","probable"],
        "game":["game","matchup"],
        "lineup_slot":["lineup","slot","order","bo","batting order"],
        "pull_pct":["pull","pull%","pull pct"],
        "hard_hit_pct":["hardhit","hardhit%","hard hit","hard hit%","hh","hh%"],
        "barrel_pct":["barrel","barrel%","brl","brl%"],
        "sweet_spot_pct":["sweet","sweet%","sweet spot","launch","la"],
        "dmg":["dmg","damage","ult","ultimate","adj","adjusted"],
        "hpi":["hpi","model","rating","hr score","score"],
        "hr_lane":["hr lane","hr/pa","hr_pa","hr9","hr/9","pitcher hr9"],
        "pitch_edge":["pitch edge","pitch_edge","edge"],
        "notes":["notes","note","tag","status"]
    }
    out = pd.DataFrame(index=raw.index)
    for target, names in aliases.items():
        col = _find_col(raw, names)
        out[target] = raw[col] if col is not None else ""

    if out["player"].astype(str).str.strip().eq("").all():
        best_col, best_score = None, -1
        for c in raw.columns:
            if any(x in str(c).lower() for x in ["pitch", "team", "game", "date", "time"]):
                continue
            vals = raw[c].fillna("").astype(str).head(200)
            score = sum(1 for v in vals if _looks_like_player_name(v))
            if score > best_score:
                best_col, best_score = c, score
        if best_col is not None and best_score > 0:
            out["player"] = raw[best_col]

    for c in ["player","team","opponent","pitcher","game","notes"]:
        out[c] = out[c].apply(_txt)
    for c in METRIC_COLS:
        out[c] = out[c].apply(_num)
    out["game_key"] = out.apply(lambda r: derive_game_key(r), axis=1)
    return clean_feed(out)


def _looks_like_player_name(s: object) -> bool:
    s = _txt(s)
    if len(s) < 3 or len(s.split()) > 5:
        return False
    low = s.lower()
    bad = ["download","copyright","disclaimer","page ","pull%","barrel","hard hit","pitcher","probable","starter","team total","game total","projected","analytics"]
    if any(x in low for x in bad):
        return False
    return bool(re.search(r"[A-Za-z]", s)) and not bool(re.search(r"\d{2,}", s))


def derive_game_key(row) -> str:
    for key in ["game_key", "game", "matchup"]:
        g = _txt(row.get(key, "")) if hasattr(row, "get") else ""
        if (" vs " in g or "@" in g) and "pitcher" not in g.lower():
            teams = TEAM_RE.findall(g)
            if len(teams) >= 2 and teams[0].lower() != teams[1].lower():
                return f"{teams[0]} vs {teams[1]}"
            parts = re.split(r"\s+(?:vs\.?|@)\s+", g, flags=re.I)
            if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                return f"{parts[0].strip()} vs {parts[1].strip()}"
    team, opp = _txt(row.get("team", "")), _txt(row.get("opponent", ""))
    if team and opp and team.lower() != opp.lower():
        return f"{team} vs {opp}"
    return ""


def _abbr_to_team(abbr: str) -> str:
    return TEAM_ABBR.get(abbr.upper(), abbr)


def parse_star_tool_text(text: str) -> pd.DataFrame:
    lines = [_txt(x) for x in str(text).splitlines()]
    lines = [x for x in lines if x]
    rows = []
    current_game = ""
    current_away = ""
    current_home = ""
    current_time = ""
    current_team = ""
    current_pitcher = ""
    current_side_team_abbr = ""

    # collect name rows with chunk until next name/rank/team
    i = 0
    while i < len(lines):
        line = lines[i]
        # game header pattern around time: ABBR AWAY @ TIME ABBR HOME may be split over lines
        if re.match(r"^\d{1,2}:\d{2}\s*[AP]M\s*ET$", line, re.I):
            current_time = line
            prev_abbr = ""
            next_abbr = ""
            for j in range(max(0, i-5), i):
                if lines[j].upper() in TEAM_ABBR:
                    prev_abbr = lines[j].upper()
            for j in range(i+1, min(len(lines), i+8)):
                if lines[j].upper() in TEAM_ABBR:
                    next_abbr = lines[j].upper(); break
            if prev_abbr and next_abbr:
                current_away = _abbr_to_team(prev_abbr)
                current_home = _abbr_to_team(next_abbr)
                current_game = f"{current_away} vs {current_home}"
        # team full uppercase header
        if line.upper() == line and TEAM_RE.search(line.title()) is None:
            pass
        if line.upper() == line and len(line.split()) >= 2:
            title = line.title().replace("Mlb", "MLB")
            teams = TEAM_RE.findall(title)
            if teams:
                current_team = teams[0]
        # direct team names from Star Tool uppercase
        for t in TEAM_NAMES:
            if line.upper() == t.upper():
                current_team = t
        # pitcher line
        if line.lower().startswith("vs.") or line.lower().startswith("vs "):
            m = re.search(r"vs\.?\s+(.+?)(?:\s+~|$)", line, re.I)
            if m:
                current_pitcher = m.group(1).strip()
        # player pattern: rank number then name then hand
        if re.match(r"^\d{1,2}$", line) and i+2 < len(lines) and _looks_like_player_name(lines[i+1]) and lines[i+2] in {"R","L","S"}:
            rank = int(line)
            player = lines[i+1]
            hand = lines[i+2]
            chunk = []
            j = i+3
            while j < len(lines):
                if re.match(r"^\d{1,2}$", lines[j]) and j+2 < len(lines) and _looks_like_player_name(lines[j+1]) and lines[j+2] in {"R","L","S"}:
                    break
                if lines[j].upper() in [x.upper() for x in TEAM_NAMES] and j > i+8:
                    break
                if "Page " in lines[j] and " of " in lines[j]:
                    # continue, because player can spill pages but avoid huge chunks
                    pass
                chunk.append(lines[j])
                if len(chunk) > 42:
                    break
                j += 1
            row = parse_player_chunk(player, hand, rank, chunk, current_team, current_pitcher, current_game, current_time)
            rows.append(row)
            i = j
            continue
        i += 1
    df = pd.DataFrame(rows)
    return clean_feed(df)


def parse_player_chunk(player, hand, rank, chunk, team, pitcher, game_key, game_time_et) -> dict:
    blob = "\n".join(chunk)
    pct_vals = [float(x) for x in re.findall(r"([+-]?\d+(?:\.\d+)?)%", blob)]
    signed_pitch = []
    for val, pitch in re.findall(r"([+-]?\d+(?:\.\d+)?)%\s+([A-Za-z0-9\- ]+)", blob):
        if "HR" not in pitch.upper():
            try: signed_pitch.append(float(val))
            except Exception: pass
    hr_lane = np.nan
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)%\s+HR/PA", blob, re.I)
    if m: hr_lane = float(m.group(1))
    dmg = np.nan
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s+DMG", blob, re.I)
    if m: dmg = float(m.group(1))
    lineup_slot = np.nan
    m = re.search(r"(\d+)(?:st|nd|rd|th)", blob)
    if m: lineup_slot = float(m.group(1))
    barrel = pct_vals[0] if pct_vals else np.nan
    # Use available text metrics as proxies. Better official/pdf data can override in table parser.
    hard = np.nan
    pull = np.nan
    sweet = np.nan
    if len(pct_vals) >= 2: hard = pct_vals[1]
    if len(pct_vals) >= 3: pull = abs(pct_vals[2])
    if len(pct_vals) >= 4: sweet = abs(pct_vals[3])
    pitch_edge = max(signed_pitch) if signed_pitch else np.nan
    hpi = np.nan
    # Star Tool often has HPI number isolated after DMG; use rank-strength proxy only if no real number.
    if pd.isna(hpi):
        hpi = max(1.0, 100 - rank * 4)
    notes = " ".join([x for x in chunk if any(tag in x.lower() for tag in ["platoon","weak slot","laser","alert","cold","hot","rakes","bullpen","launch"])])
    return {
        "player": player, "hand": hand, "rank": rank, "team": team, "opponent": "", "pitcher": pitcher,
        "game": game_key, "game_key": game_key, "game_time_et": game_time_et, "slate_window": _window_from_time(game_time_et),
        "lineup_slot": lineup_slot, "pull_pct": pull, "hard_hit_pct": hard, "barrel_pct": barrel, "sweet_spot_pct": sweet,
        "dmg": dmg, "hpi": hpi, "hr_lane": hr_lane, "pitch_edge": pitch_edge, "notes": notes,
        "parser_status": "STAR_TOOL_TEXT"
    }


def _window_from_time(t: str) -> str:
    m = re.search(r"(\d{1,2}):(\d{2})\s*([AP]M)", _txt(t), re.I)
    if not m: return "Unknown"
    hour = int(m.group(1)); ampm = m.group(3).upper()
    if ampm == "PM" and hour != 12: hour += 12
    if ampm == "AM" and hour == 12: hour = 0
    return "Early" if hour < 16 else "Late"


def clean_feed(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame(columns=["player","team","opponent","pitcher","game_key",*METRIC_COLS,"metric_count","parser_status"])
    out = df.copy()
    for c in ["player","team","opponent","pitcher","game","game_key","notes","slate_window","game_time_et"]:
        if c not in out.columns: out[c] = ""
        out[c] = out[c].apply(_txt)
    for c in METRIC_COLS:
        if c not in out.columns: out[c] = np.nan
        out[c] = out[c].apply(_num)
    bad = []
    for _, r in out.iterrows():
        p, pit = _txt(r.get("player","")), _txt(r.get("pitcher",""))
        low = p.lower()
        is_bad = not p or (pit and low == pit.lower()) or any(x in low for x in ["download","copyright","disclaimer","page ","pull%","barrel%","hard hit%","team total","game total"])
        bad.append(is_bad)
    out = out[~pd.Series(bad, index=out.index)].copy()
    out["metric_count"] = out[METRIC_COLS].notna().sum(axis=1)
    if "parser_status" not in out.columns: out["parser_status"] = "READY"
    out.loc[out["metric_count"] == 0, "parser_status"] = "NAME_ONLY"
    if "game_key" not in out.columns: out["game_key"] = ""
    return out.reset_index(drop=True)


def read_feed(filename, data):
    name = str(filename).lower()
    audit = {"filename": str(filename), "parser_version": "V148_FULL_FIX"}
    if name.endswith(".csv"):
        df = normalize_table(pd.read_csv(io.BytesIO(data)))
    elif name.endswith((".xlsx", ".xls")):
        df = normalize_table(pd.read_excel(io.BytesIO(data)))
    elif name.endswith(".pdf"):
        # Native Star Tool text parser first. Only use slow table parser if text parser fails.
        text = extract_pdf_text(data)
        df_text = parse_star_tool_text(text)
        audit["text_chars"] = len(text)
        audit["text_rows"] = int(len(df_text))
        if len(df_text) >= 20:
            audit["table_rows"] = "skipped_text_parser_succeeded"
            df = df_text
        else:
            df_table = normalize_table(extract_pdf_tables(data))
            audit["table_rows"] = int(len(df_table))
            df = df_table if len(df_table) > 0 else df_text
    elif name.endswith((".txt", ".md")):
        df = parse_star_tool_text(data.decode("utf-8", errors="ignore"))
    else:
        raise ValueError("Unsupported file type. Use PDF, CSV, XLSX, XLS, TXT, or MD.")
    df = clean_feed(df)
    audit["rows"] = int(len(df))
    audit["metric_rows"] = int((df["metric_count"] > 0).sum()) if not df.empty else 0
    audit["pdf_games"] = int(df["game_key"].replace("", pd.NA).dropna().nunique()) if not df.empty and "game_key" in df.columns else 0
    return df, audit


def actual_game_count(df: pd.DataFrame) -> int:
    if not isinstance(df, pd.DataFrame) or df.empty: return 0
    if "game_pk" in df.columns:
        s = df["game_pk"].dropna().astype(str).str.strip(); s=s[(s!="")&(s!="nan")]
        if len(s): return int(s.nunique())
    if "game_key" in df.columns:
        s = df["game_key"].dropna().astype(str).str.strip(); s=s[(s!="")&(s!="nan")]
        return int(s.nunique())
    return 0


def attack_pool_count(df: pd.DataFrame) -> int:
    return actual_game_count(df)


def slate_game_count_from_public_context(ctx=None, df=None) -> int:
    return actual_game_count(df if df is not None else ctx)
