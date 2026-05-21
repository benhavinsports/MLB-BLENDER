
import re, io
import pandas as pd
from config import CANON
try:
    import fitz
except Exception:
    fitz=None

TEAM_NAMES=[
"Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox","Cincinnati Reds","Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals","Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets","New York Yankees","Athletics","Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres","San Francisco Giants","Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers","Toronto Blue Jays","Washington Nationals"
]
TEAM_ABBR={"ARI":"Arizona Diamondbacks","ATL":"Atlanta Braves","BAL":"Baltimore Orioles","BOS":"Boston Red Sox","CHC":"Chicago Cubs","CHW":"Chicago White Sox","CIN":"Cincinnati Reds","CLE":"Cleveland Guardians","COL":"Colorado Rockies","DET":"Detroit Tigers","HOU":"Houston Astros","KC":"Kansas City Royals","KCR":"Kansas City Royals","LAA":"Los Angeles Angels","LAD":"Los Angeles Dodgers","MIA":"Miami Marlins","MIL":"Milwaukee Brewers","MIN":"Minnesota Twins","NYM":"New York Mets","NYY":"New York Yankees","OAK":"Athletics","ATH":"Athletics","PHI":"Philadelphia Phillies","PIT":"Pittsburgh Pirates","SD":"San Diego Padres","SF":"San Francisco Giants","SEA":"Seattle Mariners","STL":"St. Louis Cardinals","TB":"Tampa Bay Rays","TBR":"Tampa Bay Rays","TEX":"Texas Rangers","TOR":"Toronto Blue Jays","WSH":"Washington Nationals","WAS":"Washington Nationals"}
BAD=set("dmg hpi line cond alert hot cold warm moderate elevated low high fresh effort page https star tool projected weak slot home away none upload slate summary details hand bats team pitcher player vs lineup pull sweet barrel damage ownership public".split())

def is_player_name(s):
    s=str(s).strip()
    if len(s)<3 or re.search(r"\d",s): return False
    if s.lower() in BAD or "http" in s.lower(): return False
    parts=s.split()
    return 1<=len(parts)<=4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts)

def nfloat(x):
    if x is None or pd.isna(x): return None
    if isinstance(x,(int,float)): return float(x)
    s=str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    if s in ["","-","—","None","nan"]: return None
    try: return float(s)
    except: return None

def nbool(x):
    if isinstance(x,bool): return x
    return str(x).strip().lower() in ["true","1","yes","y","alert","hot","x","confirmed","✅","up"]

ALIASES={
"player":["player","name","batter","hitter","player_name","batter_name"],
"team":["team","tm","bat_team","batter_team"],
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
"hr_alert":["hr_alert","alert"],"cond_up":["cond_up","condition_up","cond"],
"weak_slot_tag":["weak_slot_tag","weakslot"],"laser":["laser"],"rakes":["rakes"],"platoon":["platoon"],
"confirmed_lineup":["confirmed_lineup","confirmed","starting"],"notes":["notes","note","raw"]
}

def map_columns(df):
    norm={c:re.sub(r"[^a-z0-9]+","_",str(c).lower()).strip("_") for c in df.columns}
    rename={}
    for canon,als in ALIASES.items():
        opts=[re.sub(r"[^a-z0-9]+","_",a.lower()).strip("_") for a in als]
        for c,n in norm.items():
            if n in opts: rename[c]=canon
    return df.rename(columns=rename)

def clean_df(df):
    df=map_columns(df.copy())
    for c in CANON:
        if c not in df.columns: df[c]=None
    if df["player"].isna().all() or (df["player"].astype(str).str.strip()=="").all():
        candidates=[]
        for c in df.columns:
            vals=df[c].dropna().astype(str).head(120)
            score=sum(is_player_name(v) for v in vals)
            if score>=4: candidates.append((score,c))
        if candidates: df["player"]=df[sorted(candidates,reverse=True)[0][1]]
    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","odds","public_pct","weather_score","bullpen_dmg","jersey"]:
        df[c]=df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","confirmed_lineup","result_hr"]:
        df[c]=df[c].apply(nbool)
    df["player"]=df["player"].astype(str).str.strip()
    df=df[df["player"].apply(is_player_name)].copy()
    for c in ["team","pitcher","game"]:
        df[c]=df[c].fillna("").astype(str).replace("None","")
    df.loc[df["game"].str.strip()=="","game"]=df["team"]+" vs "+df["pitcher"]
    df.loc[df["game"].str.strip()==" vs ","game"]="Unknown Game"
    return df[CANON]

def pdf_text(b):
    if fitz is None: return ""
    doc=fitz.open(stream=b,filetype="pdf")
    return "\n".join(p.get_text("text") for p in doc)

def team_name(line):
    u=str(line).upper().strip()
    for ab,full in TEAM_ABBR.items():
        if re.fullmatch(ab,u): return full
    for t in TEAM_NAMES:
        if t.upper() in u: return t
    if u.isupper() and 1<=len(u.split())<=4 and not re.search(r"\d",u):
        if not any(x in u for x in ["PROJECTED","DMG","HPI","ALERT","LINEUP","WEAK","HR/PA","PULL"]):
            return u.title()
    return ""

def sections(lines):
    out=[]; team=""; pitcher=""; start=0
    for i,line in enumerate(lines):
        m=re.search(r"([A-Z][A-Z .'-]{2,}?)\s+PROJECTED\s+v(?:s|s\.)\.?\s+([A-Z][A-Za-z .'-]+?)(?:\s+~|\s+\||\s*$)",line,re.I)
        if m:
            if team or pitcher: out.append((team,pitcher,start,i))
            team=team_name(m.group(1)) or m.group(1).strip().title()
            pitcher=m.group(2).strip()
            start=i; continue
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
    pull=None
    pm=re.search(r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?",block,re.I)
    if pm: pull=float(pm.group(1))
    else:
        for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block):
            val=float(pv)
            if 5<=abs(val)<=65: pull=val; break
    sweet=None
    lm=re.search(r"(?:LINE|Sweet|Sweet Spot)\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?",block,re.I)
    if lm: sweet=float(lm.group(1))
    hrpa=None
    hm=re.search(r"([0-9]+(?:\.\d+)?)%\s+HR/PA",block,re.I)
    if hm: hrpa=float(hm.group(1))
    dmg=None
    dm=re.search(r"([0-9]+(?:\.\d+)?)\s+DMG",block,re.I)
    if dm: dmg=float(dm.group(1))
    pe=None; pt=None
    pairs=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
    pairs=[(float(a),b) for a,b in pairs if b.lower() not in ["hr","line","cond","pull"]]
    if pairs: pe,pt=pairs[-1]
    hpi=None
    hm2=re.search(r"HPI\s*\+?\s*(\d+)",block,re.I)
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
            if m and is_player_name(m.group(2)):
                name=m.group(2).strip(); start=i
            elif is_player_name(line) and i>0 and re.fullmatch(r"\d+",lines[i-1].strip()):
                name=line; start=i
        if name:
            block=" ".join(lines[start:start+34])
            slot,pull,sweet,hrpa,dmg,pe,pt,hpi=metrics(block)
            rows.append({"game":f"{team} vs {pitcher}" if team and pitcher else "Unknown Game","team":team,"opponent":"","pitcher":pitcher,"player":name,"bats":"","lineup_slot":slot,"pull_pct":pull,"barrel_pct":None,"sweet_spot_pct":sweet,"hard_hit_pct":None,"hpi":hpi,"dmg":dmg,"hr_pa":hrpa,"pitch_type":pt,"pitch_edge":pe,"hr_alert":"ALERT" in block,"cond_up":"COND ↑" in block,"weak_slot_tag":"Weak Slot" in block,"laser":"Laser" in block,"rakes":"Rakes" in block,"platoon":"Platoon" in block,"weak_slots":"","odds":None,"public_pct":None,"weather_score":None,"bullpen_dmg":None,"confirmed_lineup":False,"dob":None,"jersey":None,"result_hr":False,"notes":block[:260]})
            i+=12; continue
        i+=1
    return rows

def parse_star_text(txt):
    lines=[x.strip() for x in str(txt).splitlines() if str(x).strip()]
    sec=sections(lines); rows=[]
    if sec:
        for team,pitcher,start,end in sec:
            rows.extend(parse_rows(lines[start:end],team,pitcher))
    else:
        rows.extend(parse_rows(lines,"",""))
    return clean_df(pd.DataFrame(rows))

def parse_pdf(b):
    txt=pdf_text(b)
    if not txt.strip(): return pd.DataFrame(columns=CANON), txt
    return parse_star_text(txt), txt

def parse_csv(b):
    raw=pd.read_csv(io.BytesIO(b))
    if raw.shape[1]<=3:
        text="\n".join(raw.astype(str).fillna("").agg(" ".join,axis=1).tolist())
        if any(k in text for k in ["PROJECTED","DMG","HR/PA","Weak","ALERT"]):
            parsed=parse_star_text(text)
            if parsed is not None and not parsed.empty: return parsed,text
    return clean_df(raw), ""

def parse_xlsx(b):
    return clean_df(pd.read_excel(io.BytesIO(b))), ""

def feeder_audit(df):
    if df is None or df.empty: return False, ["No parsed player rows."]
    issues=[]; total=len(df)
    fake=df["team"].astype(str).str.match(r"^Team\s+\d+$",na=False).any() or df["pitcher"].astype(str).str.match(r"^Pitcher\s+\d+$",na=False).any() or df["game"].astype(str).str.contains("Unknown Game",na=False).any()
    if fake: issues.append("Team/pitcher feed not locked.")
    # 67-player update PDFs can be valid; do not fail on count.
    if df["team"].replace("",pd.NA).dropna().nunique()<2: issues.append("Team extraction low.")
    if df["pitcher"].replace("",pd.NA).dropna().nunique()<2: issues.append("Pitcher extraction low.")
    return len(issues)==0, issues
