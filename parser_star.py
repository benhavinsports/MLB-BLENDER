
import re, io
import pandas as pd
from config import CANON

try:
    import fitz
except Exception:
    fitz = None

ALIASES = {
"player":["player","name","batter","hitter","player_name","batter_name"],
"team":["team","tm","bat_team","batter_team"],
"opponent":["opponent","opp","vs","against"],
"pitcher":["pitcher","opp_pitcher","opposing_pitcher","starter","sp"],
"game":["game","matchup","game_key"],
"lineup_slot":["lineup_slot","slot","batting_order","order","lineup","bo"],
"pull_pct":["pull_pct","pull%","pull","pull_percent"],
"barrel_pct":["barrel_pct","barrel%","barrel","barrel_percent"],
"sweet_spot_pct":["sweet_spot_pct","sweet%","sweet_spot","line","launch","launch_pct"],
"hard_hit_pct":["hard_hit_pct","hardhit%","hard_hit","hh","hh%"],
"hpi":["hpi","hr_power_index","power","ult","adj"],
"dmg":["dmg","damage","dmg_score"],
"hr_pa":["hr_pa","hr/pa","hr_pa_pct","hr%","hr_rate"],
"pitch_edge":["pitch_edge","edge","pitch_matchup","pitch_type_edge"],
"pitch_type":["pitch_type","pitch","primary_pitch"],
"weak_slots":["weak_slots","weak_slot","pitcher_weak_slots"],
"odds":["odds","hr_odds","anytime_odds"],
"public_pct":["public_pct","public","ownership","owned"],
"weather_score":["weather_score","weather","park","env"],
"bullpen_dmg":["bullpen_dmg","bullpen","bp_dmg"],
"hr_alert":["hr_alert","alert"],
"cond_up":["cond_up","condition_up","cond"],
"weak_slot_tag":["weak_slot_tag","weakslot"],
"laser":["laser"],"rakes":["rakes"],"platoon":["platoon"],
"confirmed_lineup":["confirmed_lineup","confirmed","starting"],"notes":["notes","note","raw"]
}

BAD = {
    "dmg","hpi","line","cond","alert","hot","cold","warm","moderate","elevated","low","high",
    "fresh","effort","page","https","star","tool","projected","weak","slot","home","away",
    "none","upload","slate","summary","details","hand","bats"
}

def is_player_name(s):
    s = str(s).strip()
    if len(s) < 3 or re.search(r"\d", s):
        return False
    low = s.lower()
    if low in BAD or "http" in low:
        return False
    parts = s.split()
    return 1 <= len(parts) <= 4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\\-]+$", p) for p in parts)

def nfloat(x):
    if x is None or pd.isna(x):
        return None
    if isinstance(x, (int,float)):
        return float(x)
    s = str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    if s in ["","-","—","None","nan"]:
        return None
    try:
        return float(s)
    except Exception:
        return None

def nbool(x):
    if isinstance(x,bool):
        return x
    return str(x).lower().strip() in ["true","1","yes","y","alert","hot","x","confirmed","✅","up"]

def map_columns(df):
    original = list(df.columns)
    norm = {c: re.sub(r"[^a-z0-9]+","_",str(c).strip().lower()).strip("_") for c in original}
    rename = {}
    used = set()
    for canon, aliases in ALIASES.items():
        aliases_norm = [re.sub(r"[^a-z0-9]+","_",a.lower()).strip("_") for a in aliases]
        for c,n in norm.items():
            if c in used:
                continue
            if n in aliases_norm:
                rename[c] = canon
                used.add(c)
                break
    return df.rename(columns=rename)

def clean_df(df):
    df = map_columns(df.copy())
    for c in CANON:
        if c not in df.columns:
            df[c] = None
    if df["player"].isna().all() or (df["player"].astype(str).str.strip()=="").all():
        candidates=[]
        for c in df.columns:
            vals=df[c].dropna().astype(str).head(60)
            score=sum(is_player_name(v) for v in vals)
            if score >= 5:
                candidates.append((score,c))
        if candidates:
            df["player"] = df[sorted(candidates, reverse=True)[0][1]]
    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","odds","public_pct","weather_score","bullpen_dmg","jersey"]:
        df[c] = df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","confirmed_lineup","result_hr"]:
        df[c] = df[c].apply(nbool)
    df["player"] = df["player"].astype(str).str.strip()
    df = df[df["player"].apply(is_player_name)].copy()
    df["team"] = df["team"].fillna("").astype(str).replace("None","")
    df["pitcher"] = df["pitcher"].fillna("").astype(str).replace("None","")
    df["game"] = df["game"].fillna("").astype(str)
    df.loc[df["game"].str.strip()=="","game"] = df["team"].fillna("") + " vs " + df["pitcher"].fillna("")
    df.loc[df["game"].str.strip()==" vs ","game"] = "Unknown Game"
    return df[CANON]

def pdf_text(file_bytes):
    if fitz is None:
        return ""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    return "\n".join(page.get_text("text") for page in doc)

def parse_player_block(name, block, team, pitcher, weak_by_pitcher, idx):
    sm = re.search(r"\b(\d+)(?:st|nd|rd|th)\b", block)
    slot = int(sm.group(1)) if sm else None

    pull = None
    for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%", block):
        val = float(pv)
        if 5 <= abs(val) <= 65:
            pull = val
            break

    sweet = None
    lm = re.search(r"(?:LINE|Sweet|Sweet Spot)\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?", block, re.I)
    if lm:
        sweet = float(lm.group(1))

    hrpa = None
    hm = re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA", block, re.I)
    if hm:
        hrpa = float(hm.group(1))

    dmg = None
    dm = re.search(r"([0-9]+(?:\.\d+)?)\s+DMG", block, re.I)
    if dm:
        dmg = float(dm.group(1))

    pitch_edge = None
    pitch_type = None
    pem = re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)", block)
    pitch_like = [(float(a),bb) for a,bb in pem if bb.lower() not in ["hr","line","cond"]]
    if pitch_like:
        pitch_edge, pitch_type = pitch_like[-1]

    hpi = None
    hm2 = re.search(r"HPI\s*\+?\s*(\d+)", block, re.I)
    if hm2:
        hpi = int(hm2.group(1))
    else:
        pluses = [int(x) for x in re.findall(r"\+\s*(\d+)", block) if 10 <= int(x) <= 90]
        if pluses:
            hpi = pluses[-1]

    tm = team if team else ""
    pit = pitcher if pitcher else ""
    return {
        "game": (f"{tm} vs {pit}" if tm and pit else "Unknown Game"), "team": tm, "opponent": "", "pitcher": pit,
        "player": name, "bats": "", "lineup_slot": slot, "pull_pct": pull,
        "barrel_pct": None, "sweet_spot_pct": sweet, "hard_hit_pct": None, "hpi": hpi,
        "dmg": dmg, "hr_pa": hrpa, "pitch_type": pitch_type, "pitch_edge": pitch_edge,
        "hr_alert": "ALERT" in block, "cond_up": "COND ↑" in block, "weak_slot_tag": "Weak Slot" in block,
        "laser": "Laser" in block, "rakes": "Rakes" in block, "platoon": "Platoon" in block,
        "weak_slots": weak_by_pitcher.get(pit,""), "odds": None, "public_pct": None,
        "weather_score": None, "bullpen_dmg": None, "confirmed_lineup": False,
        "dob": None, "jersey": None, "result_hr": False, "notes": block[:220]
    }

def parse_star_text(txt):
    lines = [x.strip() for x in str(txt).splitlines() if str(x).strip()]
    rows=[]; team=""; pitcher=""; section=0; weak_by_pitcher={}
    for line in lines:
        m = re.search(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)", line, re.I)
        if m:
            weak_by_pitcher[m.group(1).strip()] = f"{m.group(2)},{m.group(3)},{m.group(4)}"

    i=0
    while i < len(lines):
        line=lines[i]
        sec = re.search(r"([A-Z][A-Z .'-]+?)\s+PROJECTED\s+v(?:s|s\.)\.?\s+(.+?)(?:\s+~|\s+\||\s*$)", line, re.I)
        if sec:
            team = sec.group(1).strip().title()
            pitcher = sec.group(2).strip()
            section += 1
            i += 1
            continue
        # multi-line section fallback: TEAM / PROJECTED / vs. / PITCHER
        if "PROJECTED" in line.upper() and i > 0:
            prior = lines[i-1].strip()
            after = " ".join(lines[i:i+4])
            m2 = re.search(r"vs\.?\s+([A-Z][A-Za-z .'-]+?)(?:\s+~|\s+\||$)", after, re.I)
            if is_player_name(prior) is False and re.search(r"[A-Z]{2,}", prior):
                team = prior.title()
                if m2:
                    pitcher = m2.group(1).strip()
                section += 1
                i += 1
                continue

        name=None; start=i
        if re.match(r"^\d+$", line) and i+1 < len(lines) and is_player_name(lines[i+1]):
            name=lines[i+1].strip(); start=i+1
        elif is_player_name(line) and i>0 and re.match(r"^\d+$", lines[i-1]):
            name=line.strip(); start=i

        if name:
            block = " ".join(lines[start:start+26])
            rows.append(parse_player_block(name, block, team, pitcher, weak_by_pitcher, section or ((len(rows)//9)+1)))
            i += 14
            continue
        i += 1
    return clean_df(pd.DataFrame(rows))

def parse_pdf(file_bytes):
    txt = pdf_text(file_bytes)
    if not txt.strip():
        return pd.DataFrame(columns=CANON)
    return parse_star_text(txt)

def parse_csv(file_bytes):
    raw = pd.read_csv(io.BytesIO(file_bytes))
    if raw.shape[1] <= 3:
        text = "\n".join(raw.astype(str).fillna("").agg(" ".join, axis=1).tolist())
        if any(k in text for k in ["PROJECTED","DMG","HR/PA","Weak","ALERT"]):
            parsed = parse_star_text(text)
            if parsed is not None and not parsed.empty:
                return parsed
    return clean_df(raw)

def parse_xlsx(file_bytes):
    raw = pd.read_excel(io.BytesIO(file_bytes))
    return clean_df(raw)

def feeder_audit(df):
    if df is None or df.empty:
        return False, ["No parsed player rows."]
    issues=[]; total=len(df)
    def blank(col):
        if col not in df.columns: return total
        s=df[col]
        return int(s.isna().sum() + (s.astype(str).str.strip().isin(["","None","nan"]).sum() if s.dtype==object else 0))
    if total < 100: issues.append(f"Player count low: {total}.")
    fake_team = df["team"].astype(str).str.match(r"^Team\s+\d+$", na=False).any()
    fake_pitcher = df["pitcher"].astype(str).str.match(r"^Pitcher\s+\d+$", na=False).any()
    unknown_game = df["game"].astype(str).str.contains("Unknown Game", na=False).any()
    if fake_team or fake_pitcher or unknown_game:
        issues.append("Fake/unknown team-pitcher labels detected.")
    if df["team"].replace("", pd.NA).dropna().nunique() < 10: issues.append("Team extraction failed/low.")
    if df["pitcher"].replace("", pd.NA).dropna().nunique() < 10: issues.append("Pitcher extraction failed/low.")
    for col in ["hpi","dmg","hr_pa","pull_pct"]:
        if blank(col) > total*.55: issues.append(f"{col.upper()} missing too often.")
    if blank("pitch_edge") > total*.80: issues.append("Pitch edge missing too often.")
    return len(issues)==0, issues
