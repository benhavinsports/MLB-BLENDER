
import re, pandas as pd
from config import CANON
from normalizer import clean_df, is_player_name
from team_data import TEAM_NAMES, TEAM_ABBR

try:
    import fitz
except Exception:
    fitz=None

HEADER_RE = re.compile(
    r"([A-Z][A-Z .'\-]{2,}?)\s+PROJECTED\s+v(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s*$)",
    re.I
)

WEAK_RE = re.compile(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)", re.I)

def pdf_pages(b):
    if fitz is None:
        return []
    doc=fitz.open(stream=b,filetype="pdf")
    return [p.get_text("text") for p in doc]

def pdf_text(b):
    return "\n".join(pdf_pages(b))

def team_name(line):
    u=str(line).upper().strip()
    for ab,full in TEAM_ABBR.items():
        if re.fullmatch(ab,u):
            return full
    for t in TEAM_NAMES:
        if t.upper() in u:
            return t
    # Star Tool headers may show "ATHLETICS" only.
    if u.isupper() and 1<=len(u.split())<=4 and not re.search(r"\d",u):
        bad=["PROJECTED","DMG","HPI","ALERT","LINEUP","WEAK","HR/PA","PULL","COND","STAR TOOL","TODAY"]
        if not any(x in u for x in bad):
            return u.title()
    return ""

def clean_pitcher(s):
    s=str(s).strip()
    s=re.sub(r"\s+[~|].*$","",s).strip()
    s=re.sub(r"\s+\d+-\d+K.*$","",s).strip()
    s=re.sub(r"\s+[LR]$","",s).strip()
    return s

def find_headers(lines):
    hits=[]
    for i,line in enumerate(lines):
        m=HEADER_RE.search(line)
        if m:
            tm=team_name(m.group(1)) or m.group(1).strip().title()
            pit=clean_pitcher(m.group(2))
            if tm and pit:
                hits.append((i,tm,pit))
    return hits

def metric_block(block):
    sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
    slot=int(sm.group(1)) if sm else None

    pull=None
    pm=re.search(r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?",block,re.I)
    if pm:
        pull=float(pm.group(1))
    else:
        # Star Tool card percent near stars is often pull/ownership-ish. Use as fallback only.
        vals=[]
        for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block):
            try:
                val=float(pv)
                if 5<=abs(val)<=65:
                    vals.append(val)
            except Exception:
                pass
        if vals:
            pull=vals[0]

    sweet=None
    lm=re.search(r"(?:LINE|Sweet|Sweet Spot)\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?",block,re.I)
    if lm:
        sweet=float(lm.group(1))

    hrpa=None
    hm=re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA",block,re.I)
    if hm:
        hrpa=float(hm.group(1))

    dmg=None
    dm=re.search(r"([0-9]+(?:\.\d+)?)\s+DMG",block,re.I)
    if dm:
        dmg=float(dm.group(1))

    pe=None; pt=None
    pairs=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
    pairs=[(float(a),b) for a,b in pairs if b.lower() not in ["hr","line","cond","pull","park"]]
    if pairs:
        pe,pt=pairs[-1]

    hpi=None
    hm2=re.search(r"HPI\s*\+?\s*(\d+)",block,re.I)
    if hm2:
        hpi=int(hm2.group(1))
    else:
        pluses=[int(x) for x in re.findall(r"\+\s*(\d+)",block) if 10<=int(x)<=90]
        if pluses:
            hpi=pluses[-1]

    return slot,pull,sweet,hrpa,dmg,pe,pt,hpi

def parse_rows(lines,team,pitcher,weak_slots=""):
    rows=[]
    i=0
    while i<len(lines):
        line=lines[i].strip()
        name=None
        start=i

        # Format:
        # 1
        # TJ Friedl L
        if re.fullmatch(r"\d+",line) and i+1<len(lines) and is_player_name(lines[i+1]):
            name=lines[i+1].strip()
            start=i+1

        # Format:
        # 1 TJ Friedl L
        if name is None:
            m=re.match(r"^(\d+)\s+([A-Z][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?",line)
            if m and is_player_name(m.group(2)):
                name=m.group(2).strip()
                start=i

        # Format:
        # TJ Friedl L, when previous line was rank
        if name is None and is_player_name(line):
            prev=lines[i-1].strip() if i>0 else ""
            nxt=" ".join(lines[i:i+8])
            if re.fullmatch(r"\d+",prev) or ("HR/PA" in nxt and ("★★★★★" in nxt or "DMG" in nxt)):
                name=line
                start=i

        if name:
            block=" ".join(lines[start:start+34])
            slot,pull,sweet,hrpa,dmg,pe,pt,hpi=metric_block(block)
            rows.append({
                "game":f"{team} vs {pitcher}" if team and pitcher else "Unknown Game",
                "team":team,
                "opponent":"",
                "pitcher":pitcher,
                "player":name,
                "bats":"",
                "lineup_slot":slot,
                "pull_pct":pull,
                "barrel_pct":None,
                "sweet_spot_pct":sweet,
                "hard_hit_pct":None,
                "hpi":hpi,
                "dmg":dmg,
                "hr_pa":hrpa,
                "pitch_type":pt,
                "pitch_edge":pe,
                "hr_alert":"ALERT" in block or "HR ALERT" in block,
                "cond_up":"COND ↑" in block,
                "weak_slot_tag":"Weak Slot" in block,
                "laser":"Laser" in block,
                "rakes":"Rakes" in block,
                "platoon":"Platoon" in block,
                "weak_slots":weak_slots,
                "odds":None,
                "public_pct":None,
                "weather_score":None,
                "bullpen_dmg":None,
                "confirmed_lineup":False,
                "dob":None,
                "jersey":None,
                "result_hr":False,
                "notes":block[:260]
            })
            i+=10
            continue
        i+=1
    return rows

def parse_star_text(txt):
    lines=[x.strip() for x in str(txt).splitlines() if str(x).strip()]
    weak_by_pitcher={}
    for line in lines:
        m=WEAK_RE.search(line)
        if m:
            weak_by_pitcher[clean_pitcher(m.group(1))]=f"{m.group(2)},{m.group(3)},{m.group(4)}"

    headers=find_headers(lines)
    rows=[]
    if headers:
        for idx,(start,team,pitcher) in enumerate(headers):
            end=headers[idx+1][0] if idx+1<len(headers) else len(lines)
            weak=weak_by_pitcher.get(pitcher,"")
            rows.extend(parse_rows(lines[start:end],team,pitcher,weak))
    else:
        rows.extend(parse_rows(lines,"","",""))

    return clean_df(pd.DataFrame(rows))

def parse_pdf(b):
    pages=pdf_pages(b)
    if not pages:
        return pd.DataFrame(columns=CANON), ""

    all_txt="\n".join(pages)
    weak_by_pitcher={}
    for line in all_txt.splitlines():
        m=WEAK_RE.search(line.strip())
        if m:
            weak_by_pitcher[clean_pitcher(m.group(1))]=f"{m.group(2)},{m.group(3)},{m.group(4)}"

    rows=[]
    active_team=""
    active_pitcher=""

    # Page-aware parser: each page can contain header continuation and/or new section.
    for page_txt in pages:
        lines=[x.strip() for x in page_txt.splitlines() if x.strip()]
        if not lines:
            continue
        headers=find_headers(lines)

        if headers:
            # parse any top-of-page carryover segment before first new header
            first_i=headers[0][0]
            if active_team and active_pitcher and first_i>0:
                rows.extend(parse_rows(lines[:first_i],active_team,active_pitcher,weak_by_pitcher.get(active_pitcher,"")))

            for h_idx,(start,team,pitcher) in enumerate(headers):
                end=headers[h_idx+1][0] if h_idx+1<len(headers) else len(lines)
                active_team,active_pitcher=team,pitcher
                rows.extend(parse_rows(lines[start:end],team,pitcher,weak_by_pitcher.get(pitcher,"")))
        else:
            # continuation page from previous team/pitcher section
            if active_team and active_pitcher:
                rows.extend(parse_rows(lines,active_team,active_pitcher,weak_by_pitcher.get(active_pitcher,"")))
            else:
                rows.extend(parse_rows(lines,"","",""))

    df=clean_df(pd.DataFrame(rows))
    return df, all_txt
