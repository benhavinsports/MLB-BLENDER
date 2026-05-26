
import io, re
import pandas as pd
import numpy as np

FEEDER_VERSION = "v148_CORRECT_CLEAN_RUNTIME"

def clean(s):
    return re.sub(r"\s+", " ", str(s or "").replace("’","'")).strip()

def normalize_df(df):
    if df is None:
        return pd.DataFrame()
    out = df.copy()
    out.columns = [clean(c).lower().replace(" ","_").replace("%","pct").replace("/","_") for c in out.columns]
    aliases = {
        "opponent_pitcher":"pitcher", "pitcher_matchup":"pitcher",
        "hr_pct_pa":"hr_pa", "hr_pa_pct":"hr_pa",
        "line":"line_drive_pct", "line_pct":"line_drive_pct",
        "cond":"cond_pct", "pitch_edge":"pitch_edge_pct", "hr_edge":"hr_edge_pct",
        "sweet":"sweet_spot_pct", "sweet_spot":"sweet_spot_pct",
        "pull":"pull_pct", "barrel":"barrel_pct"
    }
    for a,b in aliases.items():
        if a in out.columns and b not in out.columns:
            out[b] = out[a]
    for c in ["team","player","pitcher"]:
        if c not in out.columns:
            out[c] = ""
        out[c] = out[c].astype(str).map(clean)
    if "game" not in out.columns:
        out["game"] = out.apply(lambda r: f"{r.get('team','')} vs {r.get('pitcher','')}", axis=1)
    for c in ["hr_pa","dmg","hpi","line_drive_pct","cond_pct","hr_edge_pct","pitch_edge_pct","effort","sweet_spot_pct","pull_pct","barrel_pct","score"]:
        if c not in out.columns:
            out[c] = np.nan
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out[out["player"].str.split().str.len().ge(2)]
    out = out[out["team"].str.len().gt(1) & out["pitcher"].str.len().gt(1)]
    metrics = ["hr_pa","dmg","hpi","line_drive_pct","cond_pct","hr_edge_pct"]
    out = out[out[metrics].notna().any(axis=1)].copy()
    bad = {"weak slot","star roll","low effort","high effort","line drive","parse audit","data recovery"}
    out = out[~out["player"].str.lower().isin(bad)]
    return out.drop_duplicates(subset=["team","pitcher","player"], keep="first").reset_index(drop=True)

def parse_pdf(data):
    import pdfplumber
    TEAM = re.compile(r"^([A-Z][A-Z\s\.\-&]+?) PROJECTED vs\. (.+)$")
    GAME = re.compile(r"^([A-Z]{2,3}) @ ([A-Z]{2,3})$")
    TIME = re.compile(r"AWAY\s+([0-9]{1,2}:[0-9]{2}\s+[AP]M\s+ET)\s+HOME")
    PLAYER = re.compile(r"^([A-ZÀ-ÿ][A-Za-zÀ-ÿ\.'’\-]+(?:\s+[A-ZÀ-ÿ][A-Za-zÀ-ÿ\.'’\-]+){1,3})\s+(R|L|⇄R|⇄L|⇄)?(?:\s+\+\d+)?$")
    ORDER = re.compile(r"^[1-9](st|nd|rd|th)$")
    pats = {
        "hr_pa": re.compile(r"([0-9]+(?:\.[0-9]+)?)%\s*HR/PA"),
        "dmg": re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*DMG"),
        "hpi": re.compile(r"HPI\s*([0-9]+)", re.I),
        "line_drive_pct": re.compile(r"LINE\s*[↑↓]?\s*([0-9]+(?:\.[0-9]+)?)%"),
        "cond_pct": re.compile(r"COND\s*[↑↓]?\s*([0-9]+(?:\.[0-9]+)?)%"),
        "hr_edge_pct": re.compile(r"([+\-][0-9]+)%\s*HR")
    }
    pitch_edge = re.compile(r"([+\-][0-9]+)%\s*(4-Seam|Sinker|Splitter|Slider|Cutter|Curve|Changeup|Sweeper|Fastball)")
    effort = re.compile(r"(Low Effort|Moderate|High Effort|Disengaged|Fresh|Elevated)\s+([0-9]+)")
    bad_starts = ("Star Tool","Today's","Monday","Data refreshes","FILTER","HR#","Barrel","Line Drive","Hide","https","Page","ADVANCED","Recap","Star Roll")
    def player_line(line):
        if any(line.startswith(b) for b in bad_starts):
            return None
        if any(x in line for x in ["PROJECTED","VS. LINEUP SLOT","★","HR/PA","DMG","HPI"]):
            return None
        m = PLAYER.match(line)
        if not m:
            return None
        name = clean(m.group(1)); bats = clean(m.group(2))
        if name.lower() in {"low effort","high effort","star roll","park edge","line drive"}:
            return None
        return name, bats
    def finish(b):
        if not b:
            return None
        txt = " ".join(b["lines"])
        r = {k:v for k,v in b.items() if k != "lines"}
        r["raw_block"] = txt
        r["game"] = f"{r.get('team','')} vs {r.get('pitcher','')}"
        for col, rx in pats.items():
            m = rx.search(txt); r[col] = float(m.group(1)) if m else np.nan
        pe = pitch_edge.findall(txt)
        r["pitch_edge_pct"] = float(pe[-1][0]) if pe else np.nan
        r["pitch_type"] = pe[-1][1] if pe else ""
        ev = effort.findall(txt)
        r["effort"] = float(ev[0][1]) if ev else np.nan
        r["sweet_spot_pct"] = float(ev[-1][1]) if len(ev)>1 else np.nan
        r["pull_pct"] = np.nan
        r["barrel_pct"] = np.nan
        return r
    rows, cur = [], None
    team = pitcher = away = home = gtime = ""
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            for line in [clean(x) for x in (page.extract_text() or "").splitlines() if clean(x)]:
                gm = GAME.match(line)
                if gm: away, home = gm.group(1), gm.group(2)
                tm = TIME.search(line)
                if tm: gtime = tm.group(1)
                th = TEAM.match(line)
                if th:
                    if cur:
                        rows.append(finish(cur)); cur = None
                    team, pitcher = clean(th.group(1)), clean(th.group(2))
                    continue
                pl = player_line(line)
                if pl and team and pitcher:
                    if cur:
                        rows.append(finish(cur))
                    nm,bats = pl
                    cur = {"game_time":gtime,"away":away,"home":home,"team":team,"player":nm,"bats":bats,"lineup_spot":"","pitcher":pitcher,"page":page_no,"tags":"","lines":[line]}
                    continue
                if cur:
                    cur["lines"].append(line)
                    if ORDER.match(line):
                        cur["lineup_spot"] = line
                    if any(t in line for t in ["Platoon","Weak Slot","Laser","Rakes RHP","Eats LHP"]):
                        cur["tags"] = (cur.get("tags","") + " | " + line).strip(" |")
        if cur:
            rows.append(finish(cur))
    return normalize_df(pd.DataFrame([r for r in rows if r]))

def read_feed(filename=None, data=None):
    audit = {"ok":False,"rows":0,"source":filename or "uploaded","mode":"v148_clean","errors":[]}
    try:
        name = str(filename or "").lower()
        if data is not None and name.endswith(".csv"):
            df = normalize_df(pd.read_csv(io.BytesIO(data)))
        elif data is not None and (name.endswith(".xlsx") or name.endswith(".xls")):
            df = normalize_df(pd.read_excel(io.BytesIO(data)))
        elif data is not None and name.endswith(".pdf"):
            df = parse_pdf(data)
            audit["mode"] = "pdf_hitter_rows_only"
        else:
            df = pd.DataFrame()
        audit["ok"] = not df.empty
        audit["rows"] = int(len(df))
        audit["columns"] = list(df.columns)
        return df, audit
    except Exception as e:
        audit["errors"].append(str(e))
        return pd.DataFrame(), audit
