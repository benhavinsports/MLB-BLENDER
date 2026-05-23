import urllib.request
import json
import re

import io, re
import pandas as pd

try:
    import fitz
except Exception:
    fitz = None

try:
    from PIL import Image
    import pytesseract
except Exception:
    Image = None
    pytesseract = None

TEAM_ABBR = {
"ARI":"Arizona Diamondbacks","ATL":"Atlanta Braves","BAL":"Baltimore Orioles","BOS":"Boston Red Sox","CHC":"Chicago Cubs","CHW":"Chicago White Sox","CIN":"Cincinnati Reds","CLE":"Cleveland Guardians","COL":"Colorado Rockies","DET":"Detroit Tigers","HOU":"Houston Astros","KC":"Kansas City Royals","KCR":"Kansas City Royals","LAA":"Los Angeles Angels","LAD":"Los Angeles Dodgers","MIA":"Miami Marlins","MIL":"Milwaukee Brewers","MIN":"Minnesota Twins","NYM":"New York Mets","NYY":"New York Yankees","OAK":"Athletics","ATH":"Athletics","PHI":"Philadelphia Phillies","PIT":"Pittsburgh Pirates","SD":"San Diego Padres","SF":"San Francisco Giants","SEA":"Seattle Mariners","STL":"St. Louis Cardinals","TB":"Tampa Bay Rays","TBR":"Tampa Bay Rays","TEX":"Texas Rangers","TOR":"Toronto Blue Jays","WSH":"Washington Nationals","WAS":"Washington Nationals"
}
TEAM_NAMES = list(set(TEAM_ABBR.values()))

BAD_PLAYER_WORDS = set("""
LOW EFFORT MEDIUM EFFORT HIGH EFFORT EFFORT EATS LHP EATS RHP VS LHP VS RHP LEFTY RIGHTY SPLIT SPLITS

LOW EFFORT MEDIUM EFFORT HIGH EFFORT EFFORT BELOW ABOVE CONSISTENT INCONSISTENT

DISENGAGED ENGAGED READY LOCKED COMPLETE OWNER OWNERS OUTPUT INPUT STATUS LOW EFFORT MEDIUM EFFORT HIGH EFFORT EFFORT
FRESH MODERATE ELEVATED HOT COLD WARM PLATOON LASER RAKES TODAY
PROJECTED PITCHER TEAM LINEUP SLOT BATS HAND ALERT DMG HPI PULL SWEET
HOME AWAY CORE ALT CHAOS MACHINE RESULT RESULTS FEED BLEND
""".split())

CANON = [
"page","game","team","opponent","pitcher","player","lineup_slot","pull_pct","barrel_pct","sweet_spot_pct",
"hard_hit_pct","hpi","dmg","hr_pa","pitch_type","pitch_edge","hr_alert","cond_up",
"weak_slot_tag","laser","rakes","platoon","weak_slots","raw_block","notes"
]

ALIASES = {
"player":["player","name","batter","hitter","player_name","batter_name"],
"team":["team","tm","bat_team","batter_team"],
"pitcher":["pitcher","opp_pitcher","opposing_pitcher","starter","sp"],
"game":["game","matchup","game_key"],
"lineup_slot":["lineup_slot","slot","batting_order","order","lineup","bo"],
"pull_pct":["pull_pct","pull%","pull","pull_percent"],
"barrel_pct":["barrel_pct","barrel%","barrel"],
"sweet_spot_pct":["sweet_spot_pct","sweet%","sweet_spot","line","launch","launch_pct"],
"hard_hit_pct":["hard_hit_pct","hardhit%","hard_hit","hh","hh%","cond"],
"hpi":["hpi","hr_power_index","power","ult","adj"],
"dmg":["dmg","damage","dmg_score"],
"hr_pa":["hr_pa","hr/pa","hr_pa_pct","hr%","hr_rate"],
"pitch_edge":["pitch_edge","edge","pitch_matchup","pitch_type_edge"],
"pitch_type":["pitch_type","pitch","primary_pitch"],
"weak_slots":["weak_slots","weak_slot","pitcher_weak_slots"],
"hr_alert":["hr_alert","alert"],
"cond_up":["cond_up","condition_up"],
"weak_slot_tag":["weak_slot_tag","weakslot"],
"laser":["laser"],
"rakes":["rakes"],
"platoon":["platoon"],
}

def normalize_team(x):
    s = str(x).strip()
    u = re.sub(r"[^A-Z .'-]", "", s.upper()).strip()
    if u in TEAM_ABBR:
        return TEAM_ABBR[u]
    if u in {"ATHLETICS","A'S","AS"}:
        return "Athletics"
    for name in TEAM_NAMES:
        if name.upper() == u or name.upper() in u:
            return name
    return ""

def is_player_name(x):
    s = str(x).strip()
    u = s.upper()
    descriptor_re = r"^(Low Effort|Medium Effort|High Effort|Effort|Eats LHP|Eats RHP|Vs LHP|Vs RHP|Fresh|Moderate|Elevated|Hot|Cold|Home|Away|Platoon|Weak Slot|Laser|Rakes)$"
    if re.match(descriptor_re, s, re.I):
        return False
    if any(tok in u.split() for tok in ["EFFORT","EATS","LHP","RHP"]) and len(s.split()) <= 3:
        return False
    if len(s) < 3 or re.search(r"\d", s):
        return False
    if u in BAD_PLAYER_WORDS:
        return False
    if normalize_team(s):
        return False
    parts = s.split()
    if not (1 <= len(parts) <= 4):
        return False
    if any(p.upper() in BAD_PLAYER_WORDS for p in parts):
        return False
    return all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$", p) for p in parts)

def nfloat(x):
    if x is None or pd.isna(x):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    if s in {"","-","—","nan","None"}:
        return None
    try:
        return float(s)
    except Exception:
        return None

def nbool(x):
    if isinstance(x, bool):
        return x
    return str(x).strip().lower() in {"true","1","yes","y","alert","hot","x","confirmed","up","✅"}

def clean_pitcher(s):
    s = re.sub(r"^[vV][sS]\.?\s+", "", str(s).strip())
    s = re.sub(r"\s+[~|].*$", "", s)
    s = re.sub(r"\s+\d+-\d+K.*$", "", s)
    s = re.sub(r"\s+[LR]$", "", s)
    return re.sub(r"\s{2,}", " ", s).strip()

def maybe_pitcher(s):
    s = clean_pitcher(s)
    if not s or len(s) > 55:
        return ""
    if any(x in s.upper() for x in ["PROJECTED","DMG","HPI","HR/PA","LINEUP","WEAK","ALERT","PULL","COND"]):
        return ""
    parts = s.split()
    if 1 <= len(parts) <= 4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts):
        return s
    return ""

def page_text(page):
    txt = page.get_text("text") or ""
    if txt.strip():
        return txt, "text"
    if Image is None or pytesseract is None or fitz is None:
        return "", "image_no_ocr"
    try:
        pix = page.get_pixmap(matrix=fitz.Matrix(2,2), alpha=False)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img), "ocr"
    except Exception:
        return "", "ocr_failed"

def find_page_sections(lines, carry_team="", carry_pitcher=""):
    headers = []
    n = len(lines)
    for idx, ln in enumerate(lines):
        raw = str(ln).strip()
        joined = " ".join(lines[max(0, idx-8):min(n, idx+14)])

        same = re.search(r"([A-Z][A-Z .'\-]{2,}?)\s+PROJECTED\s+v(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)", raw, re.I)
        if same:
            team = normalize_team(same.group(1)) or same.group(1).title().strip()
            pitcher = clean_pitcher(same.group(2))
            headers.append((idx, team, pitcher))
            continue

        if "PROJECTED" in raw.upper() or "PROJECTED" in joined.upper():
            team = ""
            pitcher = ""
            for b in range(18):
                j = idx - b
                if j >= 0:
                    team = normalize_team(lines[j])
                    if team:
                        break
            m = re.search(r"\bv(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)", joined, re.I)
            if m:
                pitcher = clean_pitcher(m.group(1))
            if not pitcher:
                for f in range(1,18):
                    j = idx + f
                    if j < n:
                        cand = maybe_pitcher(lines[j])
                        if cand and not normalize_team(cand):
                            pitcher = cand
                            break
            if team or pitcher:
                headers.append((idx, team, pitcher))

    cleaned = []
    for idx, team, pitcher in headers:
        if cleaned and abs(idx-cleaned[-1][0]) <= 3:
            old = cleaned[-1]
            cleaned[-1] = (old[0], team or old[1], pitcher or old[2])
        else:
            cleaned.append((idx, team, pitcher))

    spans = []
    if cleaned:
        if (carry_team or carry_pitcher) and cleaned[0][0] > 0:
            spans.append((0, cleaned[0][0], carry_team, carry_pitcher))
        for i, (idx, team, pitcher) in enumerate(cleaned):
            end = cleaned[i+1][0] if i+1 < len(cleaned) else n
            spans.append((idx, end, team or carry_team, pitcher or carry_pitcher))
    else:
        spans.append((0, n, carry_team, carry_pitcher))
    return spans

def metric_block(block):
    def grab(pats):
        for p in pats:
            m = re.search(p, block, re.I)
            if m:
                return nfloat(m.group(1))
        return None

    slot = None
    sm = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", block)
    if sm:
        slot = int(sm.group(1))

    cond = grab([r"COND\s*[↑↓]?\s*([0-9]+(?:\.\d+)?)%"])
    line = grab([r"LINE\s*[↑↓]?\s*([0-9]+(?:\.\d+)?)%?", r"Sweet\s*[↑↓]?\s*([0-9]+(?:\.\d+)?)%?"])
    hrpa = grab([r"([0-9]+(?:\.\d+)?)%\s+HR/PA", r"HR/PA\s*[:=]?\s*([0-9]+(?:\.\d+)?)%?"])
    dmg = grab([r"([0-9]+(?:\.\d+)?)\s+DMG", r"DMG\s*[:=]?\s*([0-9]+(?:\.\d+)?)"])
    hpi = grab([r"ULT\s*★\s*(\d+)", r"HPI\s*\+?\s*(\d+)", r"ULT\s*\+?\s*(\d+)", r"ADJ\s*\+?\s*(\d+)"])

    if hpi is None:
        plus = [int(x) for x in re.findall(r"\+\s*(\d{2})\b", block) if 10 <= int(x) <= 90]
        if plus:
            hpi = float(plus[-1])

    pitch_edge = None
    pitch_type = None
    pairs = re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)", block)
    pairs = [(nfloat(a), b) for a,b in pairs if b.lower() not in {"hr","line","cond","pull","park","edge"}]
    pairs = [p for p in pairs if p[0] is not None]
    if pairs:
        pitch_edge, pitch_type = pairs[-1]

    pull = grab([r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?", r"Pull%?\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)"])
    if pull is None:
        star = re.search(r"★★★★★.*?([0-9]+(?:\.\d+)?)%✦?", block)
        if star:
            pull = nfloat(star.group(1))

    return {
        "lineup_slot": slot,
        "pull_pct": pull,
        "sweet_spot_pct": line,
        "hard_hit_pct": cond,
        "hr_pa": hrpa,
        "dmg": dmg,
        "hpi": hpi,
        "pitch_edge": pitch_edge,
        "pitch_type": pitch_type,
        "hr_alert": "ALERT" in block.upper() or "HR ALERT" in block.upper(),
        "cond_up": "COND ↑" in block or (cond is not None and cond >= 20),
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

        if re.fullmatch(r"\d+", line) and i+1 < len(lines):
            cand = lines[i+1].strip()
            m = re.match(r"^([A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?(?:\s+(?:Platoon|Weak Slot|Laser|Rakes|Eats|RHP|LHP|COND|\d+d|\d+d\+|↑|↓).*)?$", cand)
            if m and is_player_name(m.group(1)):
                player = m.group(1).strip()
                start = i+1

        if not player:
            m = re.match(r"^(\d+)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?", line)
            if m and is_player_name(m.group(2)):
                player = m.group(2).strip()
                start = i

        if not player and is_player_name(line):
            nxt = " ".join(lines[i:i+16])
            prev = lines[i-1].strip() if i > 0 else ""
            if re.fullmatch(r"\d+", prev) or ("★★★★★" in nxt and any(k in nxt for k in ["DMG","HR/PA","ULT","ALERT"])):
                player = line
                start = i

        if player:
            end = min(len(lines), start+70)
            for j in range(start+4, min(len(lines), start+75)):
                if "PROJECTED" in lines[j].upper():
                    end = j
                    break
                if re.fullmatch(r"\d+", lines[j].strip()) and j+1 < len(lines):
                    nxt = lines[j+1].strip()
                    mm = re.match(r"^([A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?", nxt)
                    if mm and is_player_name(mm.group(1)):
                        end = j
                        break
            block = " ".join(lines[start:end])
            if any(k in block for k in ["★★★★★","DMG","HR/PA","ULT","ALERT"]):
                out.append({"player": player, "raw_block": block})
            i = max(i+1, end)
            continue
        i += 1
    return out

def normalize_structured(df, source):
    df = df.copy()
    rename = {}
    norm = {c: re.sub(r"[^a-z0-9]+","_",str(c).lower()).strip("_") for c in df.columns}
    for canon, aliases in ALIASES.items():
        opts = [re.sub(r"[^a-z0-9]+","_",a.lower()).strip("_") for a in aliases]
        for c, n in norm.items():
            if n in opts:
                rename[c] = canon
    df = df.rename(columns=rename)
    for c in CANON:
        if c not in df.columns:
            df[c] = None
    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]:
        df[c] = df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon"]:
        df[c] = df[c].apply(nbool)
    for c in ["game","team","opponent","pitcher","player"]:
        df[c] = df[c].fillna("").astype(str).str.strip()
    df["team"] = df["team"].apply(lambda x: normalize_team(x) or x)
    df = df[df["player"].apply(is_player_name)].copy()
    fake_player_re = r"^(Low Effort|Medium Effort|High Effort|Effort|Eats LHP|Eats RHP|Vs LHP|Vs RHP|Fresh|Moderate|Elevated|Hot|Cold|Today|Home|Away|Platoon|Weak Slot|Laser|Rakes)$"
    df = df[~df["player"].astype(str).str.strip().str.match(fake_player_re, case=False, na=False)].copy()
    metric_cols = ["pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]
    df = df[df[metric_cols].notna().any(axis=1)].copy()
    df.loc[df["game"].str.strip()=="","game"] = df["team"] + " vs " + df["pitcher"]
    df["source"] = source
    return df[CANON]

def parse_pdf(data):
    if fitz is None:
        return pd.DataFrame(columns=CANON), {"error":"PyMuPDF not installed"}
    doc = fitz.open(stream=data, filetype="pdf")
    rows = []
    carry_team = ""
    carry_pitcher = ""
    audit = []

    for pno, page in enumerate(doc, start=1):
        txt, mode = page_text(page)
        lines = [x.strip() for x in txt.splitlines() if x.strip()]
        spans = find_page_sections(lines, carry_team, carry_pitcher)
        audit.append({"page":pno,"mode":mode,"sections":len(spans)})

        for s,e,team,pitcher in spans:
            if team:
                carry_team = team
            if pitcher:
                carry_pitcher = pitcher
            team = team or carry_team
            pitcher = pitcher or carry_pitcher
            subset = lines[s:e]

            weak_slots = ""
            for ln in subset:
                wm = re.search(r"VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)", ln, re.I)
                if wm:
                    weak_slots = f"{wm.group(1)},{wm.group(2)},{wm.group(3)}"

            for block in player_blocks(subset):
                row = {c:None for c in CANON}
                row.update({
                    "page": pno,
                    "game": f"{team} vs {pitcher}" if team and pitcher else f"Unknown Game · page {pno}",
                    "team": team,
                    "pitcher": pitcher,
                    "player": block["player"],
                    "raw_block": block["raw_block"],
                    "weak_slots": weak_slots,
                    "notes": f"page={pno}; mode={mode}; section={team} vs {pitcher}"
                })
                row.update(metric_block(block["raw_block"]))
                rows.append(row)

    out = normalize_structured(pd.DataFrame(rows), "pdf")
    if not out.empty:
        out = out.drop_duplicates(subset=["player","game","raw_block"], keep="first")
    return out, audit


def extract_text_from_image(data):
    if Image is None or pytesseract is None:
        return ""
    try:
        img = Image.open(io.BytesIO(data))
        return pytesseract.image_to_string(img)
    except Exception:
        return ""

def guess_players_from_text(text):
    """
    Universal slip/screenshot parser.
    Finds likely player names from copied text / Twitter slip / screenshot OCR.
    Then the engine can enrich/match from public data when exact metrics are not in the slip.
    """
    rows = []
    lines = [x.strip() for x in str(text).splitlines() if x.strip()]
    seen = set()

    for i, line in enumerate(lines):
        clean = re.sub(r"[@#].*", "", line).strip()
        clean = re.sub(r"\b(HR|Home Run|Homer|Anytime|ATG|Parlay|Odds|Pick|Slip|Bet|Leg)\b", "", clean, flags=re.I).strip()
        # common slip format: "Aaron Judge +350" or "Aaron Judge HR"
        m = re.match(r"^([A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+){1,3})\b", clean)
        if m:
            name = m.group(1).strip()
            if is_player_name(name) and name.lower() not in seen:
                seen.add(name.lower())
                rows.append({
                    "page": 0,
                    "game": "Needs Enrichment",
                    "team": "",
                    "pitcher": "",
                    "player": name,
                    "raw_block": line,
                    "notes": "universal_feed_text_or_screenshot"
                })

    return pd.DataFrame(rows)

def parse_image(data):
    text = extract_text_from_image(data)
    df = guess_players_from_text(text)
    if df.empty:
        return pd.DataFrame(columns=CANON), {"mode":"image_ocr", "error":"No player names detected or OCR unavailable"}
    return normalize_structured(df, "image"), {"mode":"image_ocr", "lines":len(text.splitlines()), "players":len(df)}

def parse_text_file(data):
    try:
        text = data.decode("utf-8", errors="ignore")
    except Exception:
        text = str(data)
    df = guess_players_from_text(text)
    if df.empty:
        return pd.DataFrame(columns=CANON), {"mode":"text_slip", "error":"No player names detected"}
    return normalize_structured(df, "text"), {"mode":"text_slip", "players":len(df)}

def read_feed(name, data):
    name_l = name.lower()

    # Universal Feed Brain:
    # PDF / CSV / XLSX / screenshots / copied text all enter the same feeder.
    if name_l.endswith(".pdf"):
        return parse_pdf(data)
    if name_l.endswith(".csv"):
        return normalize_structured(pd.read_csv(io.BytesIO(data)), "csv"), []
    if name_l.endswith(".xlsx") or name_l.endswith(".xls"):
        return normalize_structured(pd.read_excel(io.BytesIO(data)), "xlsx"), []
    if name_l.endswith((".png",".jpg",".jpeg",".webp")):
        return parse_image(data)
    if name_l.endswith((".txt",".md")):
        return parse_text_file(data)

    # Last-resort text slip attempt.
    return parse_text_file(data)



def add_game_key_feeder(df):
    if df is None or getattr(df, "empty", True):
        return df
    out = df.copy()
    if "opponent" not in out.columns:
        out["opponent"] = ""
    def abbr(x):
        x = str(x or "").strip()
        mp = {
            "Arizona Diamondbacks":"ARI","Atlanta Braves":"ATL","Baltimore Orioles":"BAL","Boston Red Sox":"BOS",
            "Chicago Cubs":"CHC","Chicago White Sox":"CHW","Cincinnati Reds":"CIN","Cleveland Guardians":"CLE",
            "Colorado Rockies":"COL","Detroit Tigers":"DET","Houston Astros":"HOU","Kansas City Royals":"KC",
            "Los Angeles Angels":"LAA","Los Angeles Dodgers":"LAD","Miami Marlins":"MIA","Milwaukee Brewers":"MIL",
            "Minnesota Twins":"MIN","New York Mets":"NYM","New York Yankees":"NYY","Athletics":"ATH",
            "Philadelphia Phillies":"PHI","Pittsburgh Pirates":"PIT","San Diego Padres":"SD","San Francisco Giants":"SF",
            "Seattle Mariners":"SEA","St. Louis Cardinals":"STL","Tampa Bay Rays":"TB","Texas Rangers":"TEX",
            "Toronto Blue Jays":"TOR","Washington Nationals":"WSH"
        }
        return mp.get(x, "".join([c for c in x.upper() if c.isalpha()])[:3] or "UNK")
    def pclean(x):
        return "".join([c for c in str(x or "").upper() if c.isalpha()])[:10] or "UNK"
    out["game_key"] = out.apply(
        lambda r: "_".join(sorted([abbr(r.get("team")), abbr(r.get("opponent"))])) if str(r.get("opponent","")).strip() else f"{abbr(r.get('team'))}_VS_{pclean(r.get('pitcher'))}",
        axis=1
    )
    return out.drop_duplicates(subset=["game_key","team","pitcher","player"], keep="first").reset_index(drop=True)



# ============================================================
# STAR TOOL PDF SMART PARSER V8
# Purpose: read MLB Star Tool PDFs like the May 22 file.
# It extracts actual hitter blocks instead of name-only rows.
# ============================================================

import re as _re
import io as _io
import tempfile as _tempfile
import pandas as _pd
import numpy as _np

_TEAM_CODES_V8 = set("ARI ATL BAL BOS CHC CWS CIN CLE COL DET HOU KC LAA LAD MIA MIL MIN NYM NYY ATH PHI PIT SD SF SEA STL TB TEX TOR WSH".split())

def _v8_txt(x):
    try:
        if x is None or _pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()

def _v8_num(x):
    try:
        if x is None or _pd.isna(x):
            return _np.nan
        s=str(x).replace('%','').replace('+','').replace(',','').strip()
        if s.lower() in {"","nan","none","null","-","—"}:
            return _np.nan
        return float(s)
    except Exception:
        return _np.nan

def _v8_clean_name(s):
    s=_v8_txt(s)
    # remove obvious icons and trailing handedness fragments
    s=_re.sub(r'\s+', ' ', s)
    return s.strip()

def _v8_is_name_line(s):
    s=_v8_txt(s)
    if not s or len(s)>45 or len(s)<3:
        return False
    bad = ["PROJECTED","AWAY","HOME","HPI","DMG","LINE","COND","Best","Page","http","Star Roll","Weak:","lineup slot","FILTER","Today","Tomorrow"]
    if any(b.lower() in s.lower() for b in bad):
        return False
    if s.lower().startswith("vs.") or "~" in s or _re.search(r'~?\d+-\d+K', s):
        return False
    if _re.fullmatch(r'[0-9]+', s):
        return False
    if _re.fullmatch(r'[RL]|⇄[RL]', s):
        return False
    if not _re.search(r'[A-Za-zÁÉÍÓÚÑáéíóúñ]', s):
        return False
    # usually names are 1-4 words, may include Jr., II
    words=s.split()
    return 1 <= len(words) <= 5

def _v8_page_text_from_pdf(raw):
    import fitz
    with _tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(raw); path=tmp.name
    doc=fitz.open(path)
    return [page.get_text("text") for page in doc]

def _v8_parse_star_tool_text(page_texts):
    rows=[]
    current_game=""
    current_team=""
    current_opp=""
    current_pitcher=""
    current_team_name=""
    current_proj_hr=_np.nan
    current_weather=""
    weak_slots_by_pitcher={}

    # combine but keep pages
    for page_idx, text in enumerate(page_texts, start=1):
        lines=[_v8_txt(x) for x in text.splitlines() if _v8_txt(x)]
        i=0
        while i < len(lines):
            line=lines[i]

            # game header team codes
            if line in _TEAM_CODES_V8 and i+4 < len(lines):
                # pattern TEAM AWAY @ TIME OPP HOME
                if lines[i+1] in {"AWAY","HOME"}:
                    current_team=line
                    # find opponent in next few lines
                    for j in range(i+2, min(i+8, len(lines))):
                        if lines[j] in _TEAM_CODES_V8 and lines[j] != current_team:
                            current_opp=lines[j]
                            current_game=f"{current_team} vs {current_opp}"
                            break

            # projected HR / weather
            if "Star Roll" in line:
                chunk=" ".join(lines[i:i+8])
                m=_re.search(r'~([0-9.]+)\s*proj\.?\s*HR', chunk, _re.I)
                if m: current_proj_hr=_v8_num(m.group(1))
                current_weather=chunk

            # team projected vs pitcher
            if "PROJECTED" in line:
                # previous/current line may be team name, next lines contain vs.
                current_team_name=line.replace("PROJECTED","").strip() or (lines[i-1] if i>0 else "")
                chunk=" ".join(lines[i:i+8])
                m=_re.search(r'vs\.\s*([A-Za-zÁÉÍÓÚÑáéíóúñ.\' \-]+?)\s*~', chunk)
                if m:
                    current_pitcher=_v8_clean_name(m.group(1))
                else:
                    # sometimes next line is vs. Pitcher
                    for j in range(i, min(i+10, len(lines))):
                        if lines[j].lower().startswith("vs."):
                            current_pitcher=_v8_clean_name(lines[j][3:].split("~")[0])
                            break

            # weak slot pitcher rows
            if "· VS. LINEUP SLOT" in line and "Weak:" in " ".join(lines[i:i+3]):
                pit=line.split("·")[0].strip()
                chunk=" ".join(lines[i:i+4])
                m=_re.search(r'Weak:\s*#?([0-9,\s#]+)', chunk)
                if m:
                    weak_slots_by_pitcher[pit.title()] = [int(x) for x in _re.findall(r'\d+', m.group(1))]

            # Detect player block: rank line then name line, or standalone name with next line hand/days
            start=False
            rank=None
            name=None
            hand=""
            if _re.fullmatch(r'[1-9]', line) and i+1 < len(lines) and _v8_is_name_line(lines[i+1]):
                rank=int(line); name=_v8_clean_name(lines[i+1]); start=True
                if i+2 < len(lines) and _re.search(r'[RL]', lines[i+2]):
                    hand=lines[i+2]
                block_start=i
            elif _v8_is_name_line(line) and i+1 < len(lines) and _re.fullmatch(r'(⇄)?[RL]', lines[i+1]):
                # continuing player with rank missing from page break
                name=_v8_clean_name(line); hand=lines[i+1]; start=True; block_start=i

            if start and name:
                # Collect until next rank+name or next PROJECTED/game footer, max 45 lines
                j=i+1
                while j < len(lines) and j < i+55:
                    nxt=lines[j]
                    if j > i+3 and _re.fullmatch(r'[1-9]', nxt) and j+1 < len(lines) and _v8_is_name_line(lines[j+1]):
                        break
                    if j > i+3 and ("PROJECTED" in nxt or "· VS. LINEUP SLOT" in nxt or (nxt in _TEAM_CODES_V8 and j+1 < len(lines) and lines[j+1] in {"AWAY","HOME"})):
                        break
                    j+=1
                block_lines=lines[block_start:j]
                block="\n".join(block_lines)
                flat=" ".join(block_lines)

                # Basic fields
                slot=_np.nan
                m=_re.search(r'\b([1-9])(st|nd|rd|th)\b', flat)
                if m: slot=int(m.group(1))

                days=_np.nan
                m=_re.search(r'\b(\d+)d\b', flat)
                if m: days=int(m.group(1))

                rating_pct=_np.nan
                m=_re.search(r'(\d+)%✦?', flat)
                if m: rating_pct=_v8_num(m.group(1))

                cond=_np.nan
                m=_re.search(r'COND\s*[↑↓]?\s*([0-9.]+)%', flat, _re.I)
                if m: cond=_v8_num(m.group(1))

                line_pct=_np.nan
                m=_re.search(r'LINE\s*[↑↓]?\s*([0-9.]+)%', flat, _re.I)
                if m: line_pct=_v8_num(m.group(1))

                hr_edge=_np.nan
                # Park Edge +40% HR OR +2% HR
                matches=_re.findall(r'([+-]?\d+(?:\.\d+)?)%\s*HR', flat, _re.I)
                if matches:
                    # use largest absolute/last park edge-ish value
                    vals=[_v8_num(x) for x in matches]
                    hr_edge=max(vals, key=lambda x: abs(x) if not _pd.isna(x) else -1)

                pitch_edge=_np.nan
                m=_re.search(r'([+-]?\d+(?:\.\d+)?)%\s*(4-Seam|Sinker|Curve|Slider|Cutter|Changeup|Splitter|Sweeper)', flat, _re.I)
                if m: pitch_edge=_v8_num(m.group(1))

                hrpa=_np.nan
                m=_re.search(r'([0-9.]+)%\s*HR/PA', flat, _re.I)
                if m: hrpa=_v8_num(m.group(1))

                best_hr=_np.nan
                m=_re.search(r'Best:\s*#?(\d+)\s*\((\d+)\s*HR\)', flat, _re.I)
                best_rank=_np.nan
                if m:
                    best_rank=int(m.group(1)); best_hr=int(m.group(2))

                status=""
                for st in ["ALERT","HOT","WARM","COLD"]:
                    if _re.search(r'\b'+st+r'\b', flat):
                        status=st; break

                # Effort and lower bar metrics
                effort_label=""
                effort_score=_np.nan
                m=_re.search(r'(Low Effort|Disengaged|Moderate|High|Fresh|Elevated)\s+(\d+)', flat, _re.I)
                if m:
                    effort_label=m.group(1); effort_score=_v8_num(m.group(2))

                # HPI often appears as a number just before DMG, with plus sign marker before it.
                dmg=_np.nan; hpi=_np.nan
                m=_re.search(r'([0-9]+\.[0-9]+)\s*DMG', flat, _re.I)
                if m:
                    dmg=_v8_num(m.group(1))
                    before=flat[:m.start()]
                    nums=[_v8_num(x) for x in _re.findall(r'(?:\+|\b)(\d{1,3})(?=\s|$)', before)]
                    nums=[x for x in nums if not _pd.isna(x) and 0 <= x <= 100]
                    if nums:
                        hpi=nums[-1]
                # if explicit HPI number exists
                m2=_re.search(r'HPI\s*([0-9]{1,3})', flat, _re.I)
                if m2: hpi=_v8_num(m2.group(1))

                tags=[]
                for tag in ["Platoon","Weak Slot","Laser","Rakes RHP","Eats LHP","Park Edge","HR Alert"]:
                    if tag.lower() in flat.lower(): tags.append(tag)
                if status: tags.append(status)
                if effort_label: tags.append(effort_label)

                weak_slot_match=False
                # use player's lineup slot vs current pitcher weak slots from any map
                for pit, slots in weak_slots_by_pitcher.items():
                    if current_pitcher and (current_pitcher.lower() in pit.lower() or pit.lower() in current_pitcher.lower()):
                        if not _pd.isna(slot) and int(slot) in slots:
                            weak_slot_match=True
                            tags.append("Pitcher Weak Slot Match")

                rows.append({
                    "game": current_game,
                    "team": current_team_name or current_team,
                    "opponent": current_opp,
                    "pitcher": current_pitcher,
                    "player": name,
                    "hand": hand,
                    "lineup_slot": slot,
                    "pull_pct": rating_pct,          # Star Tool visible % near stars; used as pressure/ownership proxy if Pull not separately recoverable
                    "hard_hit_pct": cond,            # condition trend proxy
                    "barrel_pct": line_pct,          # line/launch quality proxy
                    "sweet_spot_pct": line_pct,
                    "dmg": dmg,
                    "hpi": hpi,
                    "hr_lane": hrpa,
                    "pitch_edge": pitch_edge if not _pd.isna(pitch_edge) else hr_edge,
                    "hr_edge": hr_edge,
                    "best_hr": best_hr,
                    "best_rank": best_rank,
                    "days": days,
                    "effort_score": effort_score,
                    "projected_game_hr": current_proj_hr,
                    "weather": current_weather,
                    "notes": " ".join(tags),
                    "parser_status": "STAR_TOOL_BLOCK",
                    "source_page": page_idx,
                    "raw_block": block[:1500]
                })
                i=j
                continue
            i+=1

    df=_pd.DataFrame(rows)
    if df.empty:
        return df
    # Add game_key and metric count
    df["game_key"]=df["game"].fillna("").astype(str)
    weak=df["game_key"].str.strip().isin([""," vs ","TEAM vs OPP"])
    df.loc[weak, "game_key"] = df.loc[weak, "team"].fillna("").astype(str) + " vs " + df.loc[weak, "pitcher"].fillna("").astype(str)
    metric_cols=["lineup_slot","pull_pct","hard_hit_pct","barrel_pct","sweet_spot_pct","dmg","hpi","hr_lane","pitch_edge","hr_edge","effort_score","projected_game_hr"]
    df["metric_count"]=df[metric_cols].notna().sum(axis=1)
    df["parser_confidence"]=df["metric_count"].apply(lambda x: "HIGH" if x>=6 else ("MEDIUM" if x>=4 else "LOW"))
    # Drop obvious false positives from interface text
    df=df[~df["player"].str.contains("Star Tool|Today|Tomorrow|PROJECTED|Page|https|FILTER", case=False, na=False)]
    df=df[~df["player"].str.contains(r"^vs\.|~|\d+-\d+K", case=False, na=False, regex=True)]
    df=df[df["player"].astype(str).str.replace(" ","").str.len() >= 3]
    return df.reset_index(drop=True)

def read_feed(name, raw):
    lname=str(name).lower()
    import io as _io
    if lname.endswith(".pdf"):
        pages=_v8_page_text_from_pdf(raw)
        full="\n".join(pages[:3])
        if "Star Tool Analytics" in full or "HR/PA" in full:
            return _v8_parse_star_tool_text(pages), {"source":"star_tool_pdf_v8"}
        # fallback old pdf parser if not star tool
        try:
            import pdfplumber
            with _tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(raw); path=tmp.name
            tables=[]
            with pdfplumber.open(path) as pdf:
                for page in pdf.pages:
                    tables += page.extract_tables() or []
            rows=[]
            for table in tables:
                if table and len(table)>1:
                    header=[_v8_txt(x) for x in table[0]]
                    for row in table[1:]:
                        rows.append({h:v for h,v in zip(header,row) if h})
            return _pd.DataFrame(rows), {"source":"pdf_table_fallback"}
        except Exception as e:
            raise ValueError(f"PDF read failed: {e}")
    if lname.endswith(".csv"):
        return _pd.read_csv(_io.BytesIO(raw)), {"source":"csv"}
    if lname.endswith((".xlsx",".xls")):
        return _pd.read_excel(_io.BytesIO(raw)), {"source":"excel"}
    if lname.endswith((".txt",".md")):
        txt=raw.decode("utf-8", errors="ignore")
        return _v8_parse_star_tool_text([txt]), {"source":"text_star_tool_v8"}
    raise ValueError("Unsupported file type.")
