import re, pandas as pd
from core.config import CANON
from feeder.normalizer import clean_df, is_player_name
from resources.team_data import TEAM_NAMES, TEAM_ABBR
try:
    import fitz
except Exception: fitz=None
def pdf_text(b):
    if fitz is None: return ""
    doc=fitz.open(stream=b,filetype="pdf"); return "\n".join(p.get_text("text") for p in doc)
def team_name(line):
    u=str(line).upper().strip()
    for ab,full in TEAM_ABBR.items():
        if re.fullmatch(ab,u): return full
    for t in TEAM_NAMES:
        if t.upper() in u: return t
    if u.isupper() and 1<=len(u.split())<=4 and not re.search(r"\d",u):
        if not any(x in u for x in ["PROJECTED","DMG","HPI","ALERT","LINEUP","WEAK","HR/PA","PULL"]): return u.title()
    return ""
def sections(lines):
    out=[]; team=""; pitcher=""; start=0
    for i,line in enumerate(lines):
        m=re.search(r"([A-Z][A-Z .'-]{2,}?)\s+PROJECTED\s+v(?:s|s\.)\.?\s+([A-Z][A-Za-z .'-]+?)(?:\s+~|\s+\||\s*$)",line,re.I)
        if m:
            if team or pitcher: out.append((team,pitcher,start,i))
            team=team_name(m.group(1)) or m.group(1).strip().title(); pitcher=m.group(2).strip(); start=i; continue
        if "PROJECTED" in line.upper():
            t=""
            for b in range(1,10):
                if i-b>=0:
                    t=team_name(lines[i-b])
                    if t: break
            joined=" ".join(lines[i:i+10])
            m2=re.search(r"v(?:s|s\.)\.?\s+([A-Z][A-Za-z .'-]+?)(?:\s+~|\s+\||\s*$)",joined,re.I)
            if t and m2:
                if team or pitcher: out.append((team,pitcher,start,i))
                team=t; pitcher=m2.group(1).strip(); start=i; continue
    if team or pitcher: out.append((team,pitcher,start,len(lines)))
    return out
def metrics(block):
    sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block); slot=int(sm.group(1)) if sm else None
    pull=None; pm=re.search(r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?",block,re.I)
    if pm: pull=float(pm.group(1))
    else:
        for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block):
            val=float(pv)
            if 5<=abs(val)<=65: pull=val; break
    sweet=None; lm=re.search(r"(?:LINE|Sweet|Sweet Spot)\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?",block,re.I)
    if lm: sweet=float(lm.group(1))
    hrpa=None; hm=re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA",block,re.I)
    if hm: hrpa=float(hm.group(1))
    dmg=None; dm=re.search(r"([0-9]+(?:\.\d+)?)\s+DMG",block,re.I)
    if dm: dmg=float(dm.group(1))
    pe=None; pt=None; pairs=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
    pairs=[(float(a),b) for a,b in pairs if b.lower() not in ["hr","line","cond","pull"]]
    if pairs: pe,pt=pairs[-1]
    hpi=None; hm2=re.search(r"HPI\s*\+?\s*(\d+)",block,re.I)
    if hm2: hpi=int(hm2.group(1))
    else:
        pluses=[int(x) for x in re.findall(r"\+\s*(\d+)",block) if 10<=int(x)<=90]
        if pluses: hpi=pluses[-1]
    return slot,pull,sweet,hrpa,dmg,pe,pt,hpi
def parse_rows(lines,team,pitcher):
    rows=[]; i=0
    while i<len(lines):
        line=lines[i].strip(); name=None; start=i
        if re.fullmatch(r"\d+",line) and i+1<len(lines) and is_player_name(lines[i+1]):
            name=lines[i+1].strip(); start=i+1
        else:
            m=re.match(r"^(\d+)\s+([A-Z][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ.'’\-]+){0,3})",line)
            if m and is_player_name(m.group(2)): name=m.group(2).strip(); start=i
            elif is_player_name(line) and i>0 and re.fullmatch(r"\d+",lines[i-1].strip()): name=line; start=i
        if name:
            block=" ".join(lines[start:start+34]); slot,pull,sweet,hrpa,dmg,pe,pt,hpi=metrics(block)
            rows.append({"game":f"{team} vs {pitcher}" if team and pitcher else "Unknown Game","team":team,"opponent":"","pitcher":pitcher,"player":name,"bats":"","lineup_slot":slot,"pull_pct":pull,"barrel_pct":None,"sweet_spot_pct":sweet,"hard_hit_pct":None,"hpi":hpi,"dmg":dmg,"hr_pa":hrpa,"pitch_type":pt,"pitch_edge":pe,"hr_alert":"ALERT" in block,"cond_up":"COND ↑" in block,"weak_slot_tag":"Weak Slot" in block,"laser":"Laser" in block,"rakes":"Rakes" in block,"platoon":"Platoon" in block,"weak_slots":"","odds":None,"public_pct":None,"weather_score":None,"bullpen_dmg":None,"confirmed_lineup":False,"dob":None,"jersey":None,"result_hr":False,"notes":block[:260]})
            i+=12; continue
        i+=1
    return rows
def parse_star_text(txt):
    lines=[x.strip() for x in str(txt).splitlines() if str(x).strip()]
    sec=sections(lines); rows=[]
    if sec:
        for team,pitcher,start,end in sec: rows.extend(parse_rows(lines[start:end],team,pitcher))
    else: rows.extend(parse_rows(lines,"",""))
    return clean_df(pd.DataFrame(rows))
def parse_pdf(b):
    txt=pdf_text(b)
    if not txt.strip(): return pd.DataFrame(columns=CANON), txt
    return parse_star_text(txt), txt
