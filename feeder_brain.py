
import re, io
import pandas as pd

try:
    import fitz
except Exception:
    fitz=None

CANON = [
    "page","game","team","opponent","pitcher","player","bats","lineup_slot",
    "pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa",
    "pitch_type","pitch_edge","hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon",
    "weak_slots","odds","public_pct","weather_score","bullpen_dmg","confirmed_lineup",
    "dob","jersey","result_hr","raw_block","notes"
]

TEAM_NAMES = [
"Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox",
"Cincinnati Reds","Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals",
"Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets",
"New York Yankees","Athletics","Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres","San Francisco Giants",
"Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers","Toronto Blue Jays","Washington Nationals"
]

TEAM_ABBR = {
"ARI":"Arizona Diamondbacks","ATL":"Atlanta Braves","BAL":"Baltimore Orioles","BOS":"Boston Red Sox",
"CHC":"Chicago Cubs","CHW":"Chicago White Sox","CIN":"Cincinnati Reds","CLE":"Cleveland Guardians",
"COL":"Colorado Rockies","DET":"Detroit Tigers","HOU":"Houston Astros","KC":"Kansas City Royals","KCR":"Kansas City Royals",
"LAA":"Los Angeles Angels","LAD":"Los Angeles Dodgers","MIA":"Miami Marlins","MIL":"Milwaukee Brewers",
"MIN":"Minnesota Twins","NYM":"New York Mets","NYY":"New York Yankees","OAK":"Athletics","ATH":"Athletics",
"PHI":"Philadelphia Phillies","PIT":"Pittsburgh Pirates","SD":"San Diego Padres","SF":"San Francisco Giants",
"SEA":"Seattle Mariners","STL":"St. Louis Cardinals","TB":"Tampa Bay Rays","TBR":"Tampa Bay Rays",
"TEX":"Texas Rangers","TOR":"Toronto Blue Jays","WSH":"Washington Nationals","WAS":"Washington Nationals"
}

BAD_WORDS = set("""
dmg hpi line cond alert hot cold warm moderate elevated low high fresh effort page https star tool projected weak slot home away none upload slate summary details hand bats team pitcher player vs lineup pull sweet barrel damage ownership public
""".split())

ALIASES={
"player":["player","name","batter","hitter","player_name","batter_name"],
"team":["team","tm","bat_team","batter_team"],
"pitcher":["pitcher","opp_pitcher","opposing_pitcher","starter","sp"],
"game":["game","matchup","game_key"],
"lineup_slot":["lineup_slot","slot","batting_order","order","lineup","bo"],
"pull_pct":["pull_pct","pull%","pull","pull_percent"],
"barrel_pct":["barrel_pct","barrel%","barrel"],
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

def is_player_name(s):
    s=str(s).strip()
    if len(s)<3 or re.search(r"\d",s): return False
    if s.lower() in BAD_WORDS or "http" in s.lower(): return False
    parts=s.split()
    if not (1 <= len(parts) <= 4): return False
    return all(re.match(r"^[A-Za-zÀ-ÿ.'’\\-]+$",p) for p in parts)

def team_name(s):
    u=str(s).upper().strip()
    u=re.sub(r"[^A-Z .'-]","",u).strip()
    for ab,full in TEAM_ABBR.items():
        if re.fullmatch(ab,u): return full
    for t in TEAM_NAMES:
        if t.upper() in u: return t
    if u in ["A'S","AS","ATHLETICS"]: return "Athletics"
    if u.isupper() and 1<=len(u.split())<=4 and not re.search(r"\d",u):
        bad=["PROJECTED","DMG","HPI","ALERT","LINEUP","WEAK","HR/PA","PULL","COND","STAR TOOL","TODAY","BATS","HAND","SLOT"]
        if not any(x in u for x in bad):
            return u.title()
    return ""

def nfloat(x):
    if x is None or pd.isna(x): return None
    if isinstance(x,(int,float)): return float(x)
    s=str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    if s in ["","-","—","None","nan"]: return None
    try: return float(s)
    except Exception: return None

def nbool(x):
    if isinstance(x,bool): return x
    return str(x).strip().lower() in ["true","1","yes","y","alert","hot","x","confirmed","✅","up"]

def clean_df(df):
    if df is None or df.empty:
        return pd.DataFrame(columns=CANON)
    df=df.copy()
    norm={c:re.sub(r"[^a-z0-9]+","_",str(c).lower()).strip("_") for c in df.columns}
    ren={}
    for canon,als in ALIASES.items():
        opts=[re.sub(r"[^a-z0-9]+","_",a.lower()).strip("_") for a in als]
        for c,n in norm.items():
            if n in opts:
                ren[c]=canon
    df=df.rename(columns=ren)
    for c in CANON:
        if c not in df.columns:
            df[c]=None
    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","odds","public_pct","weather_score","bullpen_dmg","jersey"]:
        df[c]=df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","confirmed_lineup","result_hr"]:
        df[c]=df[c].apply(nbool)
    df["player"]=df["player"].astype(str).str.strip()
    df=df[df["player"].apply(is_player_name)].copy()
    for c in ["team","pitcher","game"]:
        df[c]=df[c].fillna("").astype(str)
    df.loc[df["game"].str.strip()=="","game"]=df["team"]+" vs "+df["pitcher"]
    df.loc[df["game"].str.strip()==" vs ","game"]="Unknown Game"
    return df[CANON]

def pdf_pages(file_bytes):
    if fitz is None:
        return []
    doc=fitz.open(stream=file_bytes,filetype="pdf")
    pages=[]
    for i,page in enumerate(doc, start=1):
        text=page.get_text("text")
        lines=[x.strip() for x in text.splitlines() if x.strip()]
        pages.append({"page":i,"text":text,"lines":lines})
    return pages

def clean_pitcher(s):
    s=str(s).strip()
    s=re.sub(r"^[vV][sS]\.?\s+","",s).strip()
    s=re.sub(r"\s+[~|].*$","",s).strip()
    s=re.sub(r"\s+\d+-\d+K.*$","",s).strip()
    s=re.sub(r"\s+[LR]$","",s).strip()
    s=re.sub(r"\s{2,}"," ",s).strip()
    return s

def maybe_pitcher(s):
    s=clean_pitcher(s)
    if not s or len(s)>55: return ""
    if any(x in s.upper() for x in ["PROJECTED","DMG","HPI","HR/PA","LINEUP SLOT","WEAK","ALERT","PULL","COND"]): return ""
    parts=s.split()
    if 1<=len(parts)<=4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\\-]+$",p) for p in parts):
        return s
    return ""

def detect_headers(lines):
    headers=[]
    for i,line in enumerate(lines):
        m=re.search(r"([A-Z][A-Z .'\-]{2,}?)\s+PROJECTED\s+v(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s*$)",line,re.I)
        if m:
            tm=team_name(m.group(1)) or m.group(1).strip().title()
            pit=clean_pitcher(m.group(2))
            if tm and pit:
                headers.append((i,tm,pit))
                continue
        if "PROJECTED" in line.upper():
            tm=""; pit=""
            for b in range(0,16):
                j=i-b
                if j>=0:
                    tm=team_name(lines[j])
                    if tm: break
            joined=" ".join(lines[i:i+14])
            m2=re.search(r"\bv(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)",joined,re.I)
            if m2: pit=clean_pitcher(m2.group(1))
            if not pit:
                for f in range(1,16):
                    j=i+f
                    if j<len(lines):
                        cand=maybe_pitcher(lines[j])
                        if cand and not team_name(cand):
                            pit=cand; break
            if tm and pit:
                headers.append((i,tm,pit))
    out=[]; seen=set()
    for h in headers:
        key=(h[0],h[1],h[2])
        if key not in seen:
            out.append(h); seen.add(key)
    return out

def metric(block, patterns):
    for pat in patterns:
        m=re.search(pat,block,re.I)
        if m:
            return nfloat(m.group(1))
    return None

def metrics_from_block(block):
    sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
    slot=int(sm.group(1)) if sm else None
    pull=metric(block,[r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?"])
    if pull is None:
        vals=[]
        for pv in re.findall(r"(?<![A-Za-z])([+-]?\d+(?:\.\d+)?)%",block):
            val=nfloat(pv)
            if val is not None and 5<=abs(val)<=70: vals.append(val)
        if vals: pull=vals[0]
    sweet=metric(block,[r"(?:LINE|Sweet|Sweet Spot)\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?"])
    hrpa=metric(block,[r"([0-9]+(?:\.\d+)?)%\s+HR/PA"])
    dmg=metric(block,[r"([0-9]+(?:\.\d+)?)\s+DMG"])
    hpi=metric(block,[r"HPI\s*\+?\s*(\d+)"])
    if hpi is None:
        pluses=[int(x) for x in re.findall(r"\+\s*(\d+)",block) if 10<=int(x)<=90]
        if pluses: hpi=pluses[-1]
    pitch_edge=None; pitch_type=None
    pairs=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
    pairs=[(nfloat(a),b) for a,b in pairs if b.lower() not in ["hr","line","cond","pull","park"]]
    pairs=[p for p in pairs if p[0] is not None]
    if pairs:
        pitch_edge,pitch_type=pairs[-1]
    return {"lineup_slot":slot,"pull_pct":pull,"sweet_spot_pct":sweet,"hr_pa":hrpa,"dmg":dmg,"hpi":hpi,"pitch_edge":pitch_edge,"pitch_type":pitch_type,"hr_alert":"ALERT" in block or "HR ALERT" in block,"cond_up":"COND ↑" in block or "COND UP" in block.upper(),"weak_slot_tag":"Weak Slot" in block,"laser":"Laser" in block,"rakes":"Rakes" in block,"platoon":"Platoon" in block}

def player_blocks_from_lines(lines):
    blocks=[]; i=0
    while i<len(lines):
        line=lines[i].strip()
        player=None; start=i
        if re.fullmatch(r"\d+",line) and i+1<len(lines) and is_player_name(lines[i+1]):
            player=lines[i+1].strip(); start=i+1
        if player is None:
            m=re.match(r"^(\d+)\s+([A-Z][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-Z][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?",line)
            if m and is_player_name(m.group(2)):
                player=m.group(2).strip(); start=i
        if player is None and is_player_name(line):
            nxt=" ".join(lines[i:i+10])
            prev=lines[i-1].strip() if i>0 else ""
            if re.fullmatch(r"\d+",prev) or ("HR/PA" in nxt and ("DMG" in nxt or "★★★★★" in nxt or "ALERT" in nxt)):
                player=line; start=i
        if player:
            block_lines=lines[start:start+38]
            block=" ".join(block_lines)
            blocks.append({"player":player,"start":start,"block":block})
            i+=8
            continue
        i+=1
    return blocks

def parse_pages_to_rows(pages):
    rows=[]; active_team=""; active_pitcher=""; header_hits=0; page_debug=[]
    for page in pages:
        pno=page["page"]; lines=page["lines"]
        headers=detect_headers(lines)
        header_hits += len(headers)
        page_debug.append({"page":pno,"headers":headers[:4],"line_count":len(lines)})
        spans=[]
        if headers:
            if active_team and active_pitcher and headers[0][0]>0:
                spans.append((0,headers[0][0],active_team,active_pitcher))
            for idx,(start,tm,pit) in enumerate(headers):
                end=headers[idx+1][0] if idx+1<len(headers) else len(lines)
                spans.append((start,end,tm,pit))
                active_team,active_pitcher=tm,pit
        else:
            found_team=""; found_pitcher=""
            for j,line in enumerate(lines[:45]):
                if not found_team: found_team=team_name(line)
                if not found_pitcher:
                    cand=maybe_pitcher(line)
                    nearby=" ".join(lines[max(0,j-8):min(len(lines),j+8)]).upper()
                    if cand and not team_name(cand) and ("PROJECTED" in nearby or " VS " in nearby or "VS." in nearby):
                        found_pitcher=cand
                if found_team and found_pitcher: break
            if found_team and found_pitcher:
                active_team,active_pitcher=found_team,found_pitcher
            spans.append((0,len(lines),active_team,active_pitcher))
        for start,end,tm,pit in spans:
            subset=lines[start:end]
            for blk in player_blocks_from_lines(subset):
                metrics=metrics_from_block(blk["block"])
                row={c:None for c in CANON}
                row.update({"page":pno,"game":f"{tm} vs {pit}" if tm and pit else "Unknown Game","team":tm,"opponent":"","pitcher":pit,"player":blk["player"],"bats":"","barrel_pct":None,"hard_hit_pct":None,"weak_slots":"","odds":None,"public_pct":None,"weather_score":None,"bullpen_dmg":None,"confirmed_lineup":False,"dob":None,"jersey":None,"result_hr":False,"raw_block":blk["block"],"notes":f"page={pno}; headers_found_total={header_hits}"})
                row.update(metrics)
                rows.append(row)
    df=pd.DataFrame(rows)
    if df.empty: return pd.DataFrame(columns=CANON), page_debug
    for c in CANON:
        if c not in df.columns: df[c]=None
    return df[CANON], page_debug

def read_pdf(file_bytes):
    pages=pdf_pages(file_bytes)
    df,debug=parse_pages_to_rows(pages)
    raw_text="\n".join(p["text"] for p in pages)
    return df, raw_text, debug

def read_csv(file_bytes):
    raw=pd.read_csv(io.BytesIO(file_bytes))
    if raw.shape[1]<=3:
        text="\n".join(raw.astype(str).fillna("").agg(" ".join,axis=1).tolist())
        fake_pages=[{"page":1,"text":text,"lines":[x.strip() for x in text.splitlines() if x.strip()]}]
        df,debug=parse_pages_to_rows(fake_pages)
        if not df.empty: return df,text,debug
    return clean_df(raw), "", []

def read_xlsx(file_bytes):
    raw=pd.read_excel(io.BytesIO(file_bytes))
    return clean_df(raw), "", []

def read_file(name,file_bytes):
    n=name.lower()
    if n.endswith(".pdf"): return read_pdf(file_bytes)
    if n.endswith(".csv"): return read_csv(file_bytes)
    return read_xlsx(file_bytes)
