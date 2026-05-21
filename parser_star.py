
import re, pandas as pd
from config import CANON
from normalizer import clean_df, is_player_name
from team_data import TEAM_NAMES, TEAM_ABBR

try:
    import fitz
except Exception:
    fitz=None

BAD_HEADER_WORDS=["PROJECTED","DMG","HPI","ALERT","LINEUP","WEAK","HR/PA","PULL","COND","STAR TOOL","TODAY","BATS","HAND","SLOT"]

def pdf_pages(b):
    if fitz is None:
        return []
    doc=fitz.open(stream=b,filetype="pdf")
    return [p.get_text("text") for p in doc]

def pdf_text(b):
    return "\n".join(pdf_pages(b))

def clean_pitcher(s):
    s=str(s).strip()
    s=re.sub(r"^[vV][sS]\.?\s+","",s).strip()
    s=re.sub(r"\s+[~|].*$","",s).strip()
    s=re.sub(r"\s+\d+-\d+K.*$","",s).strip()
    s=re.sub(r"\s+[LR]$","",s).strip()
    s=re.sub(r"\s{2,}"," ",s).strip()
    return s

def team_name(line):
    u=str(line).upper().strip()
    u=re.sub(r"[^A-Z .'-]","",u).strip()
    for ab,full in TEAM_ABBR.items():
        if re.fullmatch(ab,u):
            return full
    for t in TEAM_NAMES:
        if t.upper() in u:
            return t
    if u == "A'S" or u == "AS":
        return "Athletics"
    if u.isupper() and 1<=len(u.split())<=4 and not re.search(r"\d",u):
        if not any(x in u for x in BAD_HEADER_WORDS):
            return u.title()
    return ""

def maybe_pitcher(line):
    s=str(line).strip()
    if not s or len(s)>55: return ""
    if any(x in s.upper() for x in ["PROJECTED","DMG","HPI","HR/PA","LINEUP SLOT","WEAK","ALERT","PULL","COND"]): return ""
    s=clean_pitcher(s)
    parts=s.split()
    if 1 <= len(parts) <= 4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts):
        if not is_player_name(s):  # if it fails player filter it can still be pitcher; keep.
            return s
        return s
    return ""

def find_headers(lines):
    hits=[]
    n=len(lines)
    for i,line in enumerate(lines):
        raw=str(line).strip()
        up=raw.upper()

        # Pattern A: TEAM PROJECTED vs Pitcher on one line
        m=re.search(r"([A-Z][A-Z .'\-]{2,}?)\s+PROJECTED\s+v(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s*$)",raw,re.I)
        if m:
            tm=team_name(m.group(1)) or m.group(1).strip().title()
            pit=clean_pitcher(m.group(2))
            if tm and pit:
                hits.append((i,tm,pit))
                continue

        # Pattern B: any PROJECTED line with team before and pitcher after
        if "PROJECTED" in up:
            tm=""
            pit=""
            # team usually appears before projected line
            for b in range(0,14):
                j=i-b
                if j>=0:
                    tm=team_name(lines[j])
                    if tm: break
            # pitcher may be on same line after vs, or next lines after a "vs" marker
            joined=" ".join(lines[i:i+12])
            m2=re.search(r"\bv(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)",joined,re.I)
            if m2:
                pit=clean_pitcher(m2.group(1))
            if not pit:
                for f in range(1,14):
                    j=i+f
                    if j<n:
                        cand=maybe_pitcher(lines[j])
                        if cand and not team_name(cand):
                            pit=cand; break
            if tm and pit:
                hits.append((i,tm,pit))
                continue

        # Pattern C: separated lines: TEAM then PROJECTED then vs then Pitcher
        if up in ["PROJECTED","PROJECTED LINEUP","PROJECTED BATTERS"] or up.startswith("PROJECTED"):
            tm=""
            pit=""
            for b in range(1,14):
                if i-b>=0:
                    tm=team_name(lines[i-b])
                    if tm: break
            for f in range(1,14):
                if i+f<n:
                    cand=lines[i+f].strip()
                    if cand.lower().startswith("vs"):
                        cand=clean_pitcher(cand)
                        if cand:
                            pit=cand; break
                    cand2=maybe_pitcher(cand)
                    if cand2 and not team_name(cand2):
                        pit=cand2; break
            if tm and pit:
                hits.append((i,tm,pit))
                continue

    # remove duplicate same-index / same header
    out=[]
    seen=set()
    for h in hits:
        key=(h[0],h[1],h[2])
        if key not in seen:
            out.append(h); seen.add(key)
    return out

def metric_block(block):
    sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
    slot=int(sm.group(1)) if sm else None

    pull=None
    pm=re.search(r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?",block,re.I)
    if pm:
        pull=float(pm.group(1))
    else:
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

        if re.fullmatch(r"\d+",line) and i+1<len(lines) and is_player_name(lines[i+1]):
            name=lines[i+1].strip()
            start=i+1

        if name is None:
            m=re.match(r"^(\d+)\s+([A-Z][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?",line)
            if m and is_player_name(m.group(2)):
                name=m.group(2).strip()
                start=i

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

def parse_pdf(b):
    pages=pdf_pages(b)
    if not pages:
        return pd.DataFrame(columns=CANON), ""

    all_txt="\n".join(pages)

    rows=[]
    active_team=""
    active_pitcher=""
    header_count=0

    for page_txt in pages:
        lines=[x.strip() for x in page_txt.splitlines() if x.strip()]
        if not lines:
            continue
        headers=find_headers(lines)
        header_count += len(headers)

        if headers:
            first_i=headers[0][0]
            if active_team and active_pitcher and first_i>0:
                rows.extend(parse_rows(lines[:first_i],active_team,active_pitcher))

            for h_idx,(start,team,pitcher) in enumerate(headers):
                end=headers[h_idx+1][0] if h_idx+1<len(headers) else len(lines)
                active_team,active_pitcher=team,pitcher
                rows.extend(parse_rows(lines[start:end],team,pitcher))
        else:
            # If no formal header is found, use page-level team/pitcher recovery.
            page_team=""
            page_pitcher=""
            for j,line in enumerate(lines[:35]):
                if not page_team:
                    page_team=team_name(line)
                if not page_pitcher:
                    cand=maybe_pitcher(line)
                    if cand and not team_name(cand):
                        # avoid player rows by requiring nearby projected/vs on page
                        nearby=" ".join(lines[max(0,j-8):min(len(lines),j+8)]).upper()
                        if "PROJECTED" in nearby or " VS " in nearby or "VS." in nearby:
                            page_pitcher=cand
                if page_team and page_pitcher:
                    break

            if page_team and page_pitcher:
                active_team,active_pitcher=page_team,page_pitcher
                rows.extend(parse_rows(lines,active_team,active_pitcher))
            elif active_team and active_pitcher:
                rows.extend(parse_rows(lines,active_team,active_pitcher))
            else:
                rows.extend(parse_rows(lines,"","",""))

    df=clean_df(pd.DataFrame(rows))

    # If header detection still failed but rows exist, put parser status into notes for audit visibility.
    if not df.empty:
        df["notes"]=df["notes"].astype(str) + f" | headers_found={header_count}"

    return df, all_txt

def parse_star_text(txt):
    lines=[x.strip() for x in str(txt).splitlines() if str(x).strip()]
    headers=find_headers(lines)
    rows=[]
    if headers:
        for idx,(start,team,pitcher) in enumerate(headers):
            end=headers[idx+1][0] if idx+1<len(headers) else len(lines)
            rows.extend(parse_rows(lines[start:end],team,pitcher))
    else:
        rows.extend(parse_rows(lines,"","",""))
    return clean_df(pd.DataFrame(rows))
