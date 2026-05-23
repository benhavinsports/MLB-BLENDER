
import io
import re
import pandas as pd

TEAM_NAMES = [
    "Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox",
    "Cincinnati Reds","Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals",
    "Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets",
    "New York Yankees","Athletics","Oakland Athletics","Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres",
    "San Francisco Giants","Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers","Toronto Blue Jays",
    "Washington Nationals"
]
TEAM_ABBR = {
    "ari":"Arizona Diamondbacks","atl":"Atlanta Braves","bal":"Baltimore Orioles","bos":"Boston Red Sox","chc":"Chicago Cubs","chw":"Chicago White Sox",
    "cin":"Cincinnati Reds","cle":"Cleveland Guardians","col":"Colorado Rockies","det":"Detroit Tigers","hou":"Houston Astros","kc":"Kansas City Royals",
    "laa":"Los Angeles Angels","lad":"Los Angeles Dodgers","mia":"Miami Marlins","mil":"Milwaukee Brewers","min":"Minnesota Twins","nym":"New York Mets",
    "nyy":"New York Yankees","ath":"Athletics","oak":"Athletics","phi":"Philadelphia Phillies","pit":"Pittsburgh Pirates","sd":"San Diego Padres",
    "sf":"San Francisco Giants","sea":"Seattle Mariners","stl":"St. Louis Cardinals","tb":"Tampa Bay Rays","tex":"Texas Rangers","tor":"Toronto Blue Jays",
    "wsh":"Washington Nationals","was":"Washington Nationals"
}
ALIASES = {
    "player": ["player","name","batter","hitter"],
    "team": ["team","tm","club"],
    "opponent": ["opponent","opp"],
    "pitcher": ["pitcher","opp pitcher","opposing pitcher","probable pitcher","sp"],
    "game": ["game","matchup"],
    "lineup_slot": ["slot","lineup","batting order","order","bo"],
    "pull_pct": ["pull","pull%","pull pct","pull_pct","pull percent"],
    "sweet_spot_pct": ["sweet","sweet%","sweet spot","sweet spot%","sweet_spot_pct","sweet spot pct"],
    "barrel_pct": ["barrel","barrel%","barrel pct","barrel_pct"],
    "hard_hit_pct": ["hardhit","hard hit","hard-hit","hh%","hard hit%","hard_hit_pct","hardhit%"],
    "dmg": ["dmg","damage"],
    "hr_pa": ["hr/pa","hr pa","hr_pa","hr rate","hrpa"],
    "hpi": ["hpi"],
    "pitch_edge": ["pitch edge","pitch_edge","edge","pitch"],
    "weak_slots": ["weak slots","weak slot","slot weakness"],
    "hr_alert": ["hr alert","alert"],
}
METRICS = ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi","pitch_edge"]

def _clean_col(c):
    return re.sub(r"[^a-z0-9]+"," ",str(c).strip().lower()).strip()

def _canon_cols(df):
    if df is None or df.empty:
        return pd.DataFrame()
    rename = {}
    for c in df.columns:
        cc = _clean_col(c)
        for canon, aliases in ALIASES.items():
            if cc in [_clean_col(a) for a in aliases]:
                rename[c] = canon
                break
    return df.rename(columns=rename)

def _to_num(x):
    if x is None or pd.isna(x):
        return None
    s = str(x).replace("%","").replace(",","").strip()
    if s == "" or s.lower() in {"nan","none","-","—"}:
        return None
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None

def _likely_player(s):
    s = str(s or "").strip()
    if len(s) < 3: return False
    bad = {"low effort","medium effort","high effort","effort","player","team","pitcher","pull","hpi","dmg","hr pa","page"}
    if s.lower() in bad: return False
    if len(s.split()) > 5: return False
    if re.search(r"\d", s): return False
    return bool(re.match(r"^[A-Za-zÀ-ÿ\.\'\-\s]+$", s))

def _find_team(text):
    low = str(text).lower()
    for t in TEAM_NAMES:
        if t.lower() in low:
            return t
    for abbr, team in TEAM_ABBR.items():
        if re.search(rf"\b{re.escape(abbr)}\b", low):
            return team
    return ""

def _normalize(df):
    df = _canon_cols(df)
    if df is None or df.empty:
        return pd.DataFrame()
    if "player" not in df.columns:
        best_col = None
        best_rate = 0
        for c in df.columns:
            vals = df[c].dropna().astype(str).head(80)
            rate = vals.map(_likely_player).mean() if len(vals) else 0
            if rate > best_rate:
                best_rate = rate; best_col = c
        if best_col is not None:
            df = df.rename(columns={best_col:"player"})
    if "player" not in df.columns:
        return pd.DataFrame()
    for c in ["team","opponent","pitcher","game","weak_slots"]:
        if c not in df.columns: df[c] = ""
    for c in METRICS + ["lineup_slot"]:
        if c not in df.columns: df[c] = None
        df[c] = df[c].apply(_to_num)
    if "hr_alert" not in df.columns:
        df["hr_alert"] = False
    df["player"] = df["player"].astype(str).str.strip()
    df = df[df["player"].apply(_likely_player)].copy()
    for c in ["team","opponent","pitcher","game","weak_slots"]:
        df[c] = df[c].fillna("").astype(str).replace("nan","")
    df["_metric_count"] = df[METRICS].notna().sum(axis=1)
    # keep player rows even with weak metric counts, but engine labels recovery; need not blank the whole file
    df = df[df["_metric_count"] >= 1].copy()
    if "page" not in df.columns: df["page"] = ""
    return df.reset_index(drop=True)

def _read_table(filename, data):
    name = filename.lower()
    if name.endswith(".csv"):
        return pd.read_csv(io.BytesIO(data))
    if name.endswith((".xlsx",".xls")):
        return pd.read_excel(io.BytesIO(data))
    return pd.DataFrame()

def _pdf_text(data):
    text = ""
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        for i,p in enumerate(reader.pages):
            text += f"\n__PAGE__ {i+1}\n" + (p.extract_text() or "")
    except Exception:
        pass
    return text

def _parse_lines(text):
    rows = []
    current_team = ""
    current_pitcher = ""
    current_game = ""
    current_page = ""
    for raw in str(text).splitlines():
        line = re.sub(r"\s+"," ", raw).strip()
        if not line: continue
        if line.startswith("__PAGE__"):
            current_page = line.replace("__PAGE__","").strip()
            continue
        team = _find_team(line)
        if team:
            current_team = team
            if " vs " in line.lower() or "@" in line:
                current_game = line
        # pitcher line hints: "vs X" after team/player rows
        pm = re.search(r"(?:vs|versus)\s+([A-Z][A-Za-z\.\'\-]+(?:\s+[A-Z][A-Za-z\.\'\-]+){0,2})", line)
        if pm and len(line.split()) < 12:
            current_pitcher = pm.group(1).strip()
        nums = re.findall(r"-?\d+(?:\.\d+)?%?", line)
        if not nums:
            continue
        before = line.split(nums[0])[0].strip(" -|•\t:")
        before = re.sub(r"^\d+\s+", "", before).strip()
        for t in TEAM_NAMES:
            before = before.replace(t, "").strip()
        # common star tool rows may have tags before player; keep last 2-3 capitalized words
        words = before.split()
        if len(words) > 3:
            cand = " ".join(words[-3:])
            if not _likely_player(cand):
                cand = " ".join(words[-2:])
        else:
            cand = before
        if not _likely_player(cand):
            continue
        vals = [_to_num(x) for x in nums]
        # best effort mapping: choose columns by order; real table/CSV will map exact columns
        rows.append({
            "page": current_page,
            "player": cand,
            "team": current_team,
            "pitcher": current_pitcher,
            "game": current_game,
            "pull_pct": vals[0] if len(vals)>0 else None,
            "sweet_spot_pct": vals[1] if len(vals)>1 else None,
            "barrel_pct": vals[2] if len(vals)>2 else None,
            "hard_hit_pct": vals[3] if len(vals)>3 else None,
            "dmg": vals[4] if len(vals)>4 else None,
            "hr_pa": vals[5] if len(vals)>5 else None,
            "hpi": vals[6] if len(vals)>6 else None,
            "pitch_edge": vals[7] if len(vals)>7 else None,
        })
    return pd.DataFrame(rows)

def read_feed(filename, data):
    audit = {"filename":filename, "bytes":len(data) if data else 0, "parser":"", "raw_rows":0, "rows":0}
    try:
        name = filename.lower()
        if name.endswith((".csv",".xlsx",".xls")):
            raw = _read_table(filename, data); audit["parser"]="table"
        elif name.endswith(".pdf"):
            text = _pdf_text(data); audit["parser"]="pdf_text"
            raw = _parse_lines(text)
        else:
            text = data.decode("utf-8", errors="ignore") if isinstance(data, (bytes, bytearray)) else str(data)
            raw = _parse_lines(text); audit["parser"]="text"
        audit["raw_rows"] = len(raw) if raw is not None else 0
        df = _normalize(raw)
        audit["rows"] = len(df)
        audit["columns"] = list(df.columns)
        return df, audit
    except Exception as e:
        audit["error"] = str(e)
        return pd.DataFrame(), audit
