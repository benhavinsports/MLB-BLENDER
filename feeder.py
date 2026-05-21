import io
import re
import pandas as pd
from schema import CANON, normalize_df, is_player_name, normalize_team, nfloat

try:
    import fitz
except Exception:
    fitz = None

def pdf_pages(file_bytes):
    if fitz is None:
        return []
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    out = []
    for idx, page in enumerate(doc, start=1):
        text = page.get_text("text")
        lines = [x.strip() for x in text.splitlines() if x.strip()]
        out.append({"page": idx, "text": text, "lines": lines})
    return out

def clean_pitcher(text):
    s = str(text).strip()
    s = re.sub(r"^[vV][sS]\.?\s+", "", s)
    s = re.sub(r"\s+[~|].*$", "", s)
    s = re.sub(r"\s+\d+-\d+K.*$", "", s)
    s = re.sub(r"\s+[LR]$", "", s)
    return re.sub(r"\s{2,}", " ", s).strip()

def maybe_pitcher(text):
    s = clean_pitcher(text)
    if not s or len(s) > 55:
        return ""
    bad = ["PROJECTED","DMG","HPI","HR/PA","LINEUP SLOT","WEAK","ALERT","PULL","COND","BATS"]
    if any(x in s.upper() for x in bad):
        return ""
    parts = s.split()
    if 1 <= len(parts) <= 4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$", p) for p in parts):
        return s
    return ""

def detect_page_header(lines):
    for i, line in enumerate(lines[:45]):
        joined = " ".join(lines[max(0, i-8): min(len(lines), i+14)])
        if "PROJECTED" not in joined.upper():
            continue
        team = ""
        pitcher = ""
        for b in range(0, 12):
            j = i - b
            if j >= 0:
                team = normalize_team(lines[j])
                if team:
                    break
        m = re.search(r"\bv(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)", joined, re.I)
        if m:
            pitcher = clean_pitcher(m.group(1))
        if not pitcher:
            for f in range(1, 16):
                j = i + f
                if j < len(lines):
                    cand = maybe_pitcher(lines[j])
                    if cand and not normalize_team(cand):
                        pitcher = cand
                        break
        if team and pitcher:
            return team, pitcher
    return "", ""

def metric_block(block):
    def grab(patterns):
        for pat in patterns:
            m = re.search(pat, block, re.I)
            if m:
                return nfloat(m.group(1))
        return None

    slot = None
    sm = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", block)
    if sm:
        slot = int(sm.group(1))

    pull = grab([r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?"])
    if pull is None:
        vals = []
        for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%", block):
            v = nfloat(pv)
            if v is not None and 5 <= abs(v) <= 75:
                vals.append(v)
        if vals:
            pull = vals[0]

    sweet = grab([r"(?:LINE|Sweet|Sweet Spot)\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?"])
    hrpa = grab([r"([0-9]+(?:\.\d+)?)%\s+HR/PA"])
    dmg = grab([r"([0-9]+(?:\.\d+)?)\s+DMG"])
    hpi = grab([r"HPI\s*\+?\s*(\d+)"])

    if hpi is None:
        pluses = [int(x) for x in re.findall(r"\+\s*(\d+)", block) if 10 <= int(x) <= 90]
        if pluses:
            hpi = float(pluses[-1])

    pitch_edge = None
    pitch_type = None
    pairs = re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)", block)
    pairs = [(nfloat(a), b) for a, b in pairs if b.lower() not in {"hr","line","cond","pull","park"}]
    pairs = [p for p in pairs if p[0] is not None]
    if pairs:
        pitch_edge, pitch_type = pairs[-1]

    return {
        "lineup_slot": slot, "pull_pct": pull, "sweet_spot_pct": sweet,
        "hr_pa": hrpa, "dmg": dmg, "hpi": hpi,
        "pitch_edge": pitch_edge, "pitch_type": pitch_type,
        "hr_alert": "ALERT" in block or "HR ALERT" in block,
        "cond_up": "COND ↑" in block or "COND UP" in block.upper(),
        "weak_slot_tag": "Weak Slot" in block,
        "laser": "Laser" in block,
        "rakes": "Rakes" in block,
        "platoon": "Platoon" in block,
    }

def player_blocks(lines):
    out = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        player = ""
        start = i

        if re.fullmatch(r"\d+", line) and i+1 < len(lines) and is_player_name(lines[i+1]):
            player = lines[i+1].strip()
            start = i + 1

        if not player:
            m = re.match(r"^(\d+)\s+([A-Z][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?", line)
            if m and is_player_name(m.group(2)):
                player = m.group(2).strip()
                start = i

        if not player and is_player_name(line):
            nxt = " ".join(lines[i:i+12])
            prev = lines[i-1].strip() if i > 0 else ""
            if re.fullmatch(r"\d+", prev) or ("HR/PA" in nxt and ("DMG" in nxt or "ALERT" in nxt or "★★★★★" in nxt)):
                player = line
                start = i

        if player:
            block = " ".join(lines[start:start+42])
            out.append({"player": player, "raw_block": block})
            i += 8
            continue
        i += 1
    return out

def parse_pdf(file_bytes):
    pages = pdf_pages(file_bytes)
    rows = []
    raw_text = "\n".join(p["text"] for p in pages)
    debug = []

    active_team = ""
    active_pitcher = ""

    for page in pages:
        pno = page["page"]
        lines = page["lines"]
        team, pitcher = detect_page_header(lines)

        if team and pitcher:
            active_team, active_pitcher = team, pitcher

        debug.append({
            "page": pno,
            "team": active_team,
            "pitcher": active_pitcher,
            "line_count": len(lines)
        })

        for blk in player_blocks(lines):
            metrics = metric_block(blk["raw_block"])
            row = {c: None for c in CANON}
            row.update({
                "source": "pdf",
                "page": pno,
                "game": f"{active_team} vs {active_pitcher}" if active_team and active_pitcher else "Unknown Game",
                "team": active_team,
                "opponent": "",
                "pitcher": active_pitcher,
                "player": blk["player"],
                "raw_block": blk["raw_block"],
                "notes": f"page={pno}"
            })
            row.update(metrics)
            rows.append(row)

    df = pd.DataFrame(rows)
    df = normalize_df(df, source="pdf")
    return df, raw_text, debug

def read_csv(file_bytes):
    raw = pd.read_csv(io.BytesIO(file_bytes))
    return normalize_df(raw, source="csv"), "", []

def read_xlsx(file_bytes):
    raw = pd.read_excel(io.BytesIO(file_bytes))
    return normalize_df(raw, source="xlsx"), "", []

def read_file(name, file_bytes):
    n = name.lower()
    if n.endswith(".pdf"):
        return parse_pdf(file_bytes)
    if n.endswith(".csv"):
        return read_csv(file_bytes)
    return read_xlsx(file_bytes)
