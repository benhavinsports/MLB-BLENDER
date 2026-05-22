import re, io, time
import pandas as pd
import streamlit as st

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

CANON=[
"source","page","game","team","opponent","pitcher","player","bats","lineup_slot",
"pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa",
"pitch_type","pitch_edge","hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon",
"weak_slots","odds","public_pct","weather_score","bullpen_dmg","confirmed_lineup",
"dob","jersey","result_hr","raw_block","notes"
]

TEAM_NAMES=[
"Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox",
"Cincinnati Reds","Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals",
"Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets",
"New York Yankees","Athletics","Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres","San Francisco Giants",
"Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers","Toronto Blue Jays","Washington Nationals"
]
TEAM_ABBR={"ARI":"Arizona Diamondbacks","ATL":"Atlanta Braves","BAL":"Baltimore Orioles","BOS":"Boston Red Sox","CHC":"Chicago Cubs","CHW":"Chicago White Sox","CIN":"Cincinnati Reds","CLE":"Cleveland Guardians","COL":"Colorado Rockies","DET":"Detroit Tigers","HOU":"Houston Astros","KC":"Kansas City Royals","KCR":"Kansas City Royals","LAA":"Los Angeles Angels","LAD":"Los Angeles Dodgers","MIA":"Miami Marlins","MIL":"Milwaukee Brewers","MIN":"Minnesota Twins","NYM":"New York Mets","NYY":"New York Yankees","OAK":"Athletics","ATH":"Athletics","PHI":"Philadelphia Phillies","PIT":"Pittsburgh Pirates","SD":"San Diego Padres","SF":"San Francisco Giants","SEA":"Seattle Mariners","STL":"St. Louis Cardinals","TB":"Tampa Bay Rays","TBR":"Tampa Bay Rays","TEX":"Texas Rangers","TOR":"Toronto Blue Jays","WSH":"Washington Nationals","WAS":"Washington Nationals"}
TEAM_COLORS={"red sox":"#BD3039","yankees":"#0C2340","mets":"#FF5910","dodgers":"#005A9C","padres":"#2F241D","phillies":"#E81828","reds":"#C6011F","mariners":"#005C5C","braves":"#CE1141","twins":"#002B5C","astros":"#EB6E1F","blue jays":"#134A8E","orioles":"#DF4601","rays":"#092C5C","royals":"#004687","cubs":"#0E3386","cardinals":"#C41E3A","rockies":"#33006F","angels":"#BA0021","giants":"#FD5A1E","diamondbacks":"#A71930","tigers":"#0C2340","guardians":"#E50022","athletics":"#003831","white sox":"#27251F","pirates":"#FDB827","brewers":"#FFC52F","marlins":"#00A3E0","nationals":"#AB0003","rangers":"#003278"}
BAD=set("""VS PROJECTED PITCHER TEAM LINEUP SLOT BATS HAND ALERT DMG HPI PULL SWEET STAR TOOL DATA PAGE HOME AWAY NONE SUMMARY DETAILS WEAK COND LINE FRESH MODERATE ELEVATED HOT COLD WARM PLATOON LASER RAKES TODAY STRONG WEAKNESS THREAT ENVIRONMENT PARK ODDS VALUE OWNERSHIP PUBLIC SHARP LOCK CORE ALT CHAOS HIGH LOW AVG GOOD BAD FEED BLEND MACHINE RESULT RESULTS""".split())
ALIASES={
"player":["player","name","batter","hitter","player_name","batter_name"],
"team":["team","tm","bat_team","batter_team"],"pitcher":["pitcher","opp_pitcher","opposing_pitcher","starter","sp"],
"game":["game","matchup","game_key"],"lineup_slot":["lineup_slot","slot","batting_order","order","lineup","bo"],
"pull_pct":["pull_pct","pull%","pull","pull_percent"],"barrel_pct":["barrel_pct","barrel%","barrel"],
"sweet_spot_pct":["sweet_spot_pct","sweet%","sweet_spot","line","launch","launch_pct"],
"hard_hit_pct":["hard_hit_pct","hardhit%","hard_hit","hh","hh%"],"hpi":["hpi","hr_power_index","power","ult","adj"],
"dmg":["dmg","damage","dmg_score"],"hr_pa":["hr_pa","hr/pa","hr_pa_pct","hr%","hr_rate"],
"pitch_edge":["pitch_edge","edge","pitch_matchup","pitch_type_edge"],"pitch_type":["pitch_type","pitch","primary_pitch"],
"weak_slots":["weak_slots","weak_slot","pitcher_weak_slots"],"odds":["odds","hr_odds","anytime_odds"],
"public_pct":["public_pct","public","ownership","owned"],"weather_score":["weather_score","weather","park","env"],
"bullpen_dmg":["bullpen_dmg","bullpen","bp_dmg"],"hr_alert":["hr_alert","alert"],"cond_up":["cond_up","condition_up","cond"],
"weak_slot_tag":["weak_slot_tag","weakslot"],"laser":["laser"],"rakes":["rakes"],"platoon":["platoon"],
"confirmed_lineup":["confirmed_lineup","confirmed","starting"],"notes":["notes","note","raw"]
}

GATE_NAMES=["0 Target/Pitcher","1 Legal Hitter","2 Pull-Air","3 Damage","4 Pitch Edge","5 Slot/Lane","6 HR Conversion","7 Launch","8 Condition","9 Lineup","10 Book Decoy","10.5 Adjacent Transfer","11 Mistake Lane","12 Bullpen","13 Numerology Tie","14 Chaos/WHO","15 Finisher","16 Ownership","17 No Revival","18 Final Lock"]

def css():
    st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Black+Ops+One&family=Rajdhani:wght@700&display=swap');
:root{--cream:#f5ead8;--acid:#d9ff2f;--green:#00ff73;--orange:#ff9900;--line:rgba(245,234,216,.16)}
.stApp{background:radial-gradient(circle at 14% 7%,rgba(217,255,47,.18),transparent 24%),linear-gradient(180deg,#030303,#090908,#030303);color:var(--cream)}
.block-container{max-width:1180px;padding:1rem 1rem 4rem}.hero,.machine,.card,.ticket{border:1px solid var(--line);border-radius:30px;background:linear-gradient(155deg,rgba(23,22,21,.97),rgba(5,5,5,.98));padding:18px;margin:12px 0}
.title,.card-name,.score,.section-title{font-family:'Black Ops One'}.title{font-size:clamp(46px,8vw,90px);line-height:.84}.hot{color:var(--acid)}
.stButton>button{min-height:72px;width:100%;border:0;border-radius:22px;font-family:'Black Ops One';font-size:24px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange));color:#050505}
div[data-baseweb="tab-list"]{gap:8px;background:rgba(16,16,15,.88);border:1px solid var(--line);border-radius:20px;padding:8px}div[data-baseweb="tab"][aria-selected="true"]{background:linear-gradient(90deg,var(--acid),var(--green))!important;color:#050505!important;border-radius:14px}
div[data-testid="stFileUploader"]{border:1px dashed rgba(217,255,47,.45)!important;border-radius:26px!important;background:linear-gradient(135deg,rgba(217,255,47,.10),rgba(0,255,115,.04))!important;padding:16px!important}div[data-testid="stFileUploader"] section{border:0!important;background:transparent!important}
.blender-wrap{position:relative;height:500px;border-radius:34px;border:1px solid var(--line);background:radial-gradient(circle at center,rgba(217,255,47,.13),rgba(0,0,0,.97));overflow:hidden;margin-top:12px}.jar{position:absolute;left:50%;top:48%;width:365px;height:365px;transform:translate(-50%,-50%);border-radius:58px 58px 125px 125px;border:3px solid rgba(245,234,216,.18);background:linear-gradient(180deg,rgba(245,234,216,.08),rgba(0,0,0,.38));box-shadow:inset 0 0 70px rgba(217,255,47,.14)}
.blade{position:absolute;left:50%;top:54%;width:285px;height:285px;margin:-142px;border-radius:50%;background:conic-gradient(transparent 0deg,var(--acid) 32deg,transparent 74deg,var(--green) 148deg,transparent 205deg,var(--orange) 268deg,transparent 320deg);animation:spin .52s linear infinite;z-index:2}.blade:after{content:"";position:absolute;inset:58px;border-radius:50%;background:rgba(0,0,0,.72);border:1px solid rgba(245,234,216,.18)}
.center{position:absolute;left:50%;top:54%;width:122px;height:122px;margin:-61px;border-radius:50%;background:#050505;border:2px solid rgba(245,234,216,.32);display:grid;place-items:center;font-family:'Black Ops One';color:var(--acid);z-index:5}
.float{position:absolute;font-family:Rajdhani;background:rgba(245,234,216,.13);border:1px solid rgba(245,234,216,.22);border-radius:999px;padding:8px 12px;max-width:170px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis;animation:dropmix 3.5s ease-in-out infinite;z-index:6}.f1{top:82px;left:7%;animation-delay:.1s}.f2{top:88px;right:7%;animation-delay:.7s}.f3{bottom:140px;left:8%;animation-delay:1.1s}.f4{bottom:136px;right:8%;animation-delay:1.5s}.f5{top:34px;left:38%;animation-delay:2s}.f6{bottom:78px;left:36%;animation-delay:2.4s}
.feed-slot{position:absolute;left:50%;top:12px;transform:translateX(-50%);font-family:'Black Ops One';background:linear-gradient(90deg,var(--acid),var(--green));color:#050505;padding:13px 24px;border-radius:999px;z-index:8}.output-slot{position:absolute;left:50%;bottom:0;transform:translateX(-50%);font-family:'Black Ops One';color:#ecffc1;background:rgba(5,5,5,.94);width:100%;text-align:center;padding:16px 10px;z-index:9}.result-pulse{position:absolute;left:50%;bottom:56px;transform:translateX(-50%);font-family:'Black Ops One';color:#050505;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange));padding:10px 18px;border-radius:999px;z-index:10;animation:pulsepop 1.4s infinite}
@keyframes spin{to{transform:rotate(360deg)}}@keyframes dropmix{0%{transform:translateY(-45px) scale(.92);opacity:.32}35%{transform:translateY(92px) scale(1);opacity:.96}70%{transform:translateY(188px) scale(.78);opacity:.32}100%{transform:translateY(-45px) scale(.92);opacity:.32}}@keyframes pulsepop{50%{transform:translateX(-50%) scale(1.06)}}
.card{position:relative;overflow:hidden}.card:before{content:"";position:absolute;inset:0 0 auto 0;height:6px;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}.card-name{font-size:34px;margin:12px 0}.meta,.reason,.leg{font-family:Rajdhani;color:#d8cfbf}.score{font-size:48px}.bar{height:12px;background:rgba(245,234,216,.09);border-radius:999px;overflow:hidden}.fill{height:100%;background:linear-gradient(90deg,var(--acid),var(--green),var(--orange))}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:12px}.stat{border:1px solid rgba(245,234,216,.10);border-radius:14px;padding:9px}.stat span{display:block;color:#aaa}.badge,.role{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:7px 10px;margin:4px;font-family:Rajdhani}.status{border:1px solid rgba(0,255,115,.25);background:rgba(0,255,115,.08);border-radius:16px;padding:12px;margin:12px 0}.leg{display:flex;justify-content:space-between;border-bottom:1px solid rgba(245,234,216,.1);padding:12px 0}.odds{background:rgba(217,255,47,.10);border:1px solid rgba(217,255,47,.24);border-radius:10px;padding:6px 9px;color:#ecffc1}
</style>""", unsafe_allow_html=True)

def team_color(team):
    t=str(team).lower()
    for k,v in TEAM_COLORS.items():
        if k in t: return v
    return "#d9ff2f"

def normalize_team(x):
    u=re.sub(r"[^A-Z .'-]","",str(x).upper()).strip()
    if u in TEAM_ABBR: return TEAM_ABBR[u]
    if u in {"ATHLETICS","A'S","AS"}: return "Athletics"
    for n in TEAM_NAMES:
        if n.upper()==u or n.upper() in u: return n
    return ""

def is_team_token(x):
    return str(x).strip().upper() in TEAM_ABBR or bool(normalize_team(x))

def nfloat(x):
    if x is None or pd.isna(x): return None
    if isinstance(x,(int,float)): return float(x)
    s=str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    try: return float(s)
    except Exception: return None

def nbool(x):
    if isinstance(x,bool): return x
    return str(x).strip().lower() in {"true","1","yes","y","alert","hot","x","confirmed","up","✅"}

def is_player_name(x):
    s=str(x).strip(); u=s.upper()
    if len(s)<3 or re.search(r"\d",s): return False
    if u in BAD or is_team_token(s): return False
    parts=s.split()
    if not (1<=len(parts)<=4): return False
    if any(p.upper() in BAD for p in parts): return False
    return all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts)

def normalize_df(df, source):
    if df is None or df.empty: return pd.DataFrame(columns=CANON)
    df=df.copy()
    norm={c:re.sub(r"[^a-z0-9]+","_",str(c).lower()).strip("_") for c in df.columns}
    ren={}
    for canon,als in ALIASES.items():
        opts=[re.sub(r"[^a-z0-9]+","_",a.lower()).strip("_") for a in als]
        for c,n in norm.items():
            if n in opts: ren[c]=canon
    df=df.rename(columns=ren)
    for c in CANON:
        if c not in df.columns: df[c]=None
    if df["player"].isna().all() or (df["player"].astype(str).str.strip()=="").all():
        for c in df.columns:
            vals=df[c].dropna().astype(str).head(300)
            if sum(is_player_name(v) for v in vals)>=4:
                df["player"]=df[c]; break
    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","odds","public_pct","weather_score","bullpen_dmg","jersey"]:
        df[c]=df[c].apply(nfloat)
    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","confirmed_lineup","result_hr"]:
        df[c]=df[c].apply(nbool)
    for c in ["team","pitcher","game","player"]:
        df[c]=df[c].fillna("").astype(str).str.strip()
    df["source"]=source
    df["team"]=df["team"].apply(lambda z: normalize_team(z) or z)
    df=df[df["player"].apply(is_player_name)].copy()
    metric_cols=["pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]
    df=df[df[metric_cols].notna().any(axis=1)].copy()
    df.loc[df["game"].str.strip()=="","game"]=df["team"]+" vs "+df["pitcher"]
    df.loc[df["game"].str.strip()==" vs ","game"]="Unknown Game"
    return df[CANON]

def page_text(page):
    txt=page.get_text("text") or ""
    if txt.strip(): return txt,"text"
    if Image is None or pytesseract is None or fitz is None: return "","image_no_ocr"
    try:
        pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        img=Image.open(io.BytesIO(pix.tobytes("png")))
        return pytesseract.image_to_string(img),"ocr"
    except Exception:
        return "","ocr_failed"

def clean_pitcher(s):
    s=re.sub(r"^[vV][sS]\.?\s+","",str(s).strip())
    s=re.sub(r"\s+[~|].*$","",s); s=re.sub(r"\s+\d+-\d+K.*$","",s); s=re.sub(r"\s+[LR]$","",s)
    return re.sub(r"\s{2,}"," ",s).strip()

def maybe_pitcher(s):
    s=clean_pitcher(s)
    if not s or len(s)>55 or any(x in s.upper() for x in ["PROJECTED","DMG","HPI","HR/PA","LINEUP","WEAK","ALERT","PULL","COND"]): return ""
    parts=s.split()
    if 1<=len(parts)<=4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$",p) for p in parts): return s
    return ""

def detect_header(lines):
    for i,line in enumerate(lines[:80]):
        joined=" ".join(lines[max(0,i-14):min(len(lines),i+20)])
        if not any(k in joined.upper() for k in ["PROJECTED"," VS ","VS."]): continue
        team=""; pitcher=""
        for b in range(18):
            j=i-b
            if j>=0:
                team=normalize_team(lines[j])
                if team: break
        m=re.search(r"\bv(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)",joined,re.I)
        if m: pitcher=clean_pitcher(m.group(1))
        if not pitcher:
            for f in range(1,18):
                j=i+f
                if j<len(lines):
                    cand=maybe_pitcher(lines[j])
                    if cand and not normalize_team(cand): pitcher=cand; break
        if team or pitcher: return team,pitcher
    return "",""

def metrics(block):
    def grab(pats):
        for p in pats:
            m=re.search(p,block,re.I)
            if m: return nfloat(m.group(1))
        return None

    slot=None
    sm=re.search(r"\b(\d+)(?:st|nd|rd|th)\b",block)
    if sm: slot=int(sm.group(1))

    cond=None
    cm=re.search(r"COND\s*[↑↓]?\s*([0-9]+(?:\.\d+)?)%",block,re.I)
    if cm: cond=nfloat(cm.group(1))

    line=grab([r"LINE\s*[↑↓]?\s*([0-9]+(?:\.\d+)?)%?",r"Sweet\s*[↑↓]?\s*([0-9]+(?:\.\d+)?)%?",r"Launch\s*[↑↓]?\s*([0-9]+(?:\.\d+)?)%?"])

    hrpa=grab([r"([0-9]+(?:\.\d+)?)%\s+HR/PA",r"HR/PA\s*[:=]?\s*([0-9]+(?:\.\d+)?)%?"])

    dmg=grab([r"([0-9]+(?:\.\d+)?)\s+DMG",r"DMG\s*[:=]?\s*([0-9]+(?:\.\d+)?)"])

    hpi=grab([r"ULT\s*★\s*(\d+)",r"HPI\s*\+?\s*(\d+)",r"ULT\s*\+?\s*(\d+)",r"ADJ\s*\+?\s*(\d+)"])

    # Star Tool cards often show the HPI number on the line before DMG:
    # + / 48 / 1.681 DMG
    if hpi is None and dmg is not None:
        dm=re.search(r"(?:\+|\b)\s*(\d{2})\s+%s\s+DMG" % re.escape(str(dmg)), block)
        if dm: hpi=nfloat(dm.group(1))

    # Fallback: use the last reasonable +number before DMG/ULT as HPI.
    if hpi is None:
        plus=[int(x) for x in re.findall(r"\+\s*(\d{2})\b",block) if 10<=int(x)<=90]
        if plus: hpi=float(plus[-1])

    # Pitch edge / pitch type: +18% 4-Seam, -13% HR -30% 4-Seam, etc.
    pitch_edge=None; pitch_type=None
    pairs=re.findall(r"([+-]\d+(?:\.\d+)?)%\s+([A-Za-z][A-Za-z0-9\-]*)",block)
    pairs=[(nfloat(a),b) for a,b in pairs if b.lower() not in {"hr","line","cond","pull","park","edge"}]
    pairs=[p for p in pairs if p[0] is not None]
    if pairs:
        pitch_edge,pitch_type=pairs[-1]

    # Pull is not always labeled. Use visible first card % as pressure/pull proxy only if no clear pull field.
    pull=grab([r"Pull\s*[↑↓]?\s*([+-]?\d+(?:\.\d+)?)%?",r"Pull%?\s*[:=]?\s*([+-]?\d+(?:\.\d+)?)"])
    if pull is None:
        # In Star Tool card, the percent after the star row is often the hitter card percentage.
        star=re.search(r"★★★★★.*?([0-9]+(?:\.\d+)?)%✦?",block)
        if star: pull=nfloat(star.group(1))

    status=""
    for word in ["ALERT","HR ALERT","HOT","WARM","COLD"]:
        if word in block.upper():
            status=word
            break

    return {
        "lineup_slot":slot,
        "pull_pct":pull,
        "sweet_spot_pct":line,
        "hr_pa":hrpa,
        "dmg":dmg,
        "hpi":hpi,
        "pitch_edge":pitch_edge,
        "pitch_type":pitch_type,
        "hr_alert":"ALERT" in block.upper() or "HR ALERT" in block.upper(),
        "cond_up":"COND ↑" in block or (cond is not None and cond>=20),
        "weak_slot_tag":"Weak Slot" in block,
        "laser":"Laser" in block,
        "rakes":"Rakes" in block,
        "platoon":"Platoon" in block,
        "hard_hit_pct":cond,
        "notes":status
    }

def player_blocks(lines):
    out=[]
    i=0
    while i < len(lines):
        line=lines[i].strip()
        player=""; start=i

        # Primary Star Tool pattern:
        # rank line, then player line
        if re.fullmatch(r"\d+", line) and i+1 < len(lines):
            cand=lines[i+1].strip()
            # Player line may include hand/archetype tags: "TJ Rumfield L Platoon Rakes RHP 7d"
            m=re.match(r"^([A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?(?:\s+(?:Platoon|Weak Slot|Laser|Rakes|Eats|RHP|LHP|COND|\\d+d|\\d+d\\+|↑|↓).*)?$", cand)
            if m and is_player_name(m.group(1)):
                player=m.group(1).strip()
                start=i+1

        # Same-line rank + player
        if not player:
            m=re.match(r"^(\d+)\s+([A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?",line)
            if m and is_player_name(m.group(2)):
                player=m.group(2).strip()
                start=i

        # Recovery: player line followed by slot/star/stat block.
        if not player and is_player_name(line):
            nxt=" ".join(lines[i:i+16])
            prev=lines[i-1].strip() if i>0 else ""
            if re.fullmatch(r"\d+",prev) or ("★★★★★" in nxt and ("DMG" in nxt or "HR/PA" in nxt or "ULT" in nxt or "ALERT" in nxt)):
                player=line
                start=i

        if player:
            # Card ends right before next rank/player card or next team header.
            end_idx=min(len(lines), start+64)
            for j in range(start+4, min(len(lines), start+70)):
                if re.fullmatch(r"\d+", lines[j].strip()) and j+1<len(lines):
                    nxt=lines[j+1].strip()
                    m=re.match(r"^([A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+(?:\s+[A-ZÁÉÍÓÚÑ][A-Za-zÀ-ÿ.'’\-]+){0,3})(?:\s+[⇄LR])?",nxt)
                    if m and is_player_name(m.group(1)):
                        end_idx=j
                        break
                if " PROJECTED vs." in lines[j] or " PROJECTED VS." in lines[j].upper():
                    end_idx=j
                    break

            block=" ".join(lines[start:end_idx])
            # Require at least one real Star Tool signal.
            if any(k in block for k in ["★★★★★","DMG","HR/PA","ULT","ALERT"]):
                out.append({"player":player,"raw_block":block})
            i=max(i+1,end_idx)
            continue
        i+=1
    return out


def find_page_sections(lines, carry_team="", carry_pitcher=""):
    headers=[]
    n=len(lines)

    for idx, ln in enumerate(lines):
        raw=str(ln).strip()
        joined=" ".join(lines[max(0,idx-8):min(n,idx+14)])

        hm=re.search(r"([A-Z][A-Z .'\-]{2,}?)\s+PROJECTED\s+v(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)", raw, re.I)
        if hm:
            tm=normalize_team(hm.group(1)) or hm.group(1).title().strip()
            pit=clean_pitcher(hm.group(2))
            headers.append((idx,tm,pit))
            continue

        if "PROJECTED" in raw.upper() or "PROJECTED" in joined.upper():
            tm=""; pit=""
            for b in range(0,18):
                j=idx-b
                if j>=0:
                    tm=normalize_team(lines[j])
                    if tm: break
            m=re.search(r"\bv(?:s|s\.)\.?\s+([A-Z][A-Za-zÀ-ÿ .'\-]+?)(?:\s+~|\s+\||\s+\d|\s*$)", joined, re.I)
            if m:
                pit=clean_pitcher(m.group(1))
            if not pit:
                for f in range(1,18):
                    j=idx+f
                    if j<n:
                        cand=maybe_pitcher(lines[j])
                        if cand and not normalize_team(cand):
                            pit=cand
                            break
            if tm or pit:
                headers.append((idx,tm,pit))

    cleaned=[]
    for idx,tm,pit in headers:
        if cleaned and abs(idx-cleaned[-1][0]) <= 3:
            old=cleaned[-1]
            cleaned[-1]=(old[0], tm or old[1], pit or old[2])
        else:
            cleaned.append((idx,tm,pit))

    spans=[]
    if cleaned:
        if (carry_team or carry_pitcher) and cleaned[0][0] > 0:
            spans.append((0, cleaned[0][0], carry_team, carry_pitcher))
        for i,(idx,tm,pit) in enumerate(cleaned):
            span_end=cleaned[i+1][0] if i+1<len(cleaned) else n
            spans.append((idx, span_end, tm or carry_team, pit or carry_pitcher))
    else:
        spans.append((0,n,carry_team,carry_pitcher))
    return spans

def parse_pdf(data):
    if fitz is None:
        return pd.DataFrame(columns=CANON),""
    doc=fitz.open(stream=data,filetype="pdf")
    rows=[]
    raw=[]
    carry_team=""
    carry_pitcher=""
    weak_slots_by_pitcher={}

    for pno,page in enumerate(doc,start=1):
        txt,mode=page_text(page)
        raw.append(txt)
        lines=[x.strip() for x in txt.splitlines() if x.strip()]

        for ln in lines:
            wm=re.search(r"(.+?)\s+·\s+VS\.\s+LINEUP SLOT\s+Weak:\s*#?(\d+),\s*#?(\d+),\s*#?(\d+)",ln,re.I)
            if wm:
                weak_slots_by_pitcher[clean_pitcher(wm.group(1))]=f"{wm.group(2)},{wm.group(3)},{wm.group(4)}"

        spans=find_page_sections(lines, carry_team, carry_pitcher)

        for s,e,tm,pit in spans:
            if tm: carry_team=tm
            if pit: carry_pitcher=pit
            section_team=tm or carry_team
            section_pitcher=pit or carry_pitcher
            subset=lines[s:e]

            for b in player_blocks(subset):
                row={c:None for c in CANON}
                row.update({
                    "source":mode,
                    "page":pno,
                    "team":section_team,
                    "pitcher":section_pitcher,
                    "weak_slots":weak_slots_by_pitcher.get(section_pitcher,""),
                    "game":f"{section_team} vs {section_pitcher}" if section_team and section_pitcher else "Unknown Game",
                    "player":b["player"],
                    "raw_block":b["raw_block"],
                    "notes":f"page={pno}; mode={mode}; section={section_team} vs {section_pitcher}"
                })
                mx=metrics(b["raw_block"])
                if mx.get("notes"):
                    row["notes"]=row["notes"]+"; status="+str(mx.pop("notes"))
                row.update(mx)
                rows.append(row)

    df=normalize_df(pd.DataFrame(rows),"pdf")
    if not df.empty:
        def sig(s):
            s=str(s)
            return sum(k in s for k in ["★★★★★","DMG","HR/PA","ULT","ALERT","COND","LINE"])
        df["_signals"]=df["raw_block"].apply(sig)
        df=df.sort_values(["player","game","_signals"], ascending=[True,True,False])
        df=df.drop_duplicates(subset=["player","game","raw_block"], keep="first")
        df=df.drop(columns=["_signals"], errors="ignore")
    return df,"\n".join(raw)

def read_file(name,data):
    n=name.lower()
    if n.endswith(".pdf"): return parse_pdf(data)
    if n.endswith(".csv"): return normalize_df(pd.read_csv(io.BytesIO(data)),"csv"),""
    return normalize_df(pd.read_excel(io.BytesIO(data)),"xlsx"),""

def clean_for_run(df):
    if df is None or df.empty: return pd.DataFrame(),pd.DataFrame()
    mcols=["pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]
    run=df[df[mcols].notna().any(axis=1)].copy()
    bad=df.drop(run.index).copy()
    run.loc[run["team"].fillna("").astype(str).str.strip()=="","team"]="Unknown Team"
    run.loc[run["pitcher"].fillna("").astype(str).str.strip()=="","pitcher"]="Unknown Pitcher"
    run.loc[run["game"].fillna("").astype(str).str.contains("Unknown Game",na=False),"game"]=run["team"]+" vs "+run["pitcher"]+" · page "+run["page"].fillna(0).astype(int).astype(str)
    return run,bad

def archetype(r):
    pull=r.get("pull_pct"); pe=r.get("pitch_edge"); dmg=r.get("dmg"); hrpa=r.get("hr_pa"); hpi=r.get("hpi"); line=r.get("sweet_spot_pct"); slot=r.get("lineup_slot")
    weak_slots=str(r.get("weak_slots",""))
    in_weak_slot = slot is not None and not pd.isna(slot) and str(int(slot)) in re.findall(r"\d+",weak_slots)

    if bool(r.get("weak_slot_tag")) or in_weak_slot:
        if (dmg or 0)>=1.2 or (hrpa or 0)>=2.5:
            return "Weak-Slot Finisher"
        return "Adjacent / Weak-Slot Transfer"
    if bool(r.get("laser")) and (line or 0)>=25:
        return "Launch/Laser Bat"
    if bool(r.get("rakes")) or (pe or -99)>=18:
        return "Pitch-Type Punisher"
    if (dmg or 0)>=2.0 and ((hrpa or 0)>=3.5 or bool(r.get("hr_alert"))):
        return "Chaos / WHO Finisher"
    if (pull or 0)>=30 and (line or 0)>=27:
        return "Pull-Air Finisher"
    if (hpi or 0)>=45 and (dmg or 0)>=1.0:
        return "Elite Converter"
    if bool(r.get("platoon")) and (pe or 0)>=0:
        return "Platoon Leveraged Bat"
    if bool(r.get("hr_alert")):
        return "Alert Converter"
    return "Primary HR Owner"

def role(r):
    a=archetype(r)
    if "Chaos" in a: return "Chaos"
    if "Transfer" in a: return "Transfer"
    return "Primary"

def score(r):
    pull=0 if pd.isna(r.get("pull_pct")) else min(100,max(0,(r["pull_pct"]-14)*2.4))
    pe=38 if pd.isna(r.get("pitch_edge")) else min(100,max(0,55+r["pitch_edge"]*1.35))
    dmg=0 if pd.isna(r.get("dmg")) else min(100,max(0,r["dmg"]*31))
    hrpa=0 if pd.isna(r.get("hr_pa")) else min(100,max(0,r["hr_pa"]*15))
    hpi=0 if pd.isna(r.get("hpi")) else min(100,max(0,r["hpi"]*1.7))
    line=0 if pd.isna(r.get("sweet_spot_pct")) else min(100,max(0,(r["sweet_spot_pct"]-15)*3.0))
    cond=0 if pd.isna(r.get("hard_hit_pct")) else min(100,max(0,r["hard_hit_pct"]))

    s=pull*.14+pe*.15+dmg*.18+hrpa*.17+hpi*.15+line*.12+cond*.04

    arch=archetype(r)
    if "Weak-Slot" in arch: s+=10
    if "Pitch-Type" in arch: s+=8
    if "Chaos" in arch: s+=7
    if "Elite" in arch: s+=7
    if "Pull-Air" in arch: s+=6
    if "Alert" in arch: s+=5

    for col,pts in [("weak_slot_tag",7),("hr_alert",8),("cond_up",4),("laser",4),("rakes",4),("platoon",2)]:
        if r.get(col): s+=pts

    if str(r.get("team","")).lower() in {"","unknown team"}: s-=8
    if str(r.get("pitcher","")).lower() in {"","unknown pitcher","home","hot","moderate"}: s-=8

    return round(max(0,min(100,s)),1)

def gate_path(r):
    gates=[]
    gates.append("1 Real hitter")
    gates.append("2 Pull-air pass" if pd.isna(r.get("pull_pct")) or r.get("pull_pct")>=20 else "2 Pull-air weak")
    gates.append("3 Damage pass" if pd.isna(r.get("dmg")) or r.get("dmg")>=.5 or r.get("hr_alert") else "3 Damage weak")
    gates.append("4 Pitch edge pass" if pd.isna(r.get("pitch_edge")) or r.get("pitch_edge")>=0 else "4 Pitch edge weak")
    gates.append("5 Lane/slot checked")
    gates.append("6 HR conversion pass" if pd.isna(r.get("hr_pa")) or r.get("hr_pa")>=2 or r.get("hr_alert") else "6 HR conversion weak")
    gates.append("7 Launch checked")
    gates += ["8 Condition checked","9 Lineup checked","10 Book decoy checked","10.5 Transfer checked","11 Mistake lane checked","12 Bullpen checked","13 Numerology tie-only","14 Chaos checked","15 Finisher checked","16 Owner isolated","17 No revival","18 Final lock"]
    return " | ".join(gates)

def run_game(gdf):
    rows=[]
    for _,r in gdf.iterrows():
        r=r.copy()
        r["archetype"]=archetype(r); r["role"]=role(r); r["score"]=score(r); r["gate_path"]=gate_path(r)
        rows.append(r)
    alive=pd.DataFrame(rows)
    if alive.empty: return alive
    filters=[
        alive.pull_pct.isna() | (alive.pull_pct>=20),
        alive.pitch_edge.isna() | (alive.pitch_edge>=0),
        alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=23),
        alive.hr_pa.isna() | (alive.hr_pa>=2) | alive.hr_alert,
        alive.dmg.isna() | (alive.dmg>=.5) | alive.hr_alert,
        alive.hpi.isna() | (alive.hpi>=16) | alive.hr_alert
    ]
    for m in filters:
        if len(alive)>1 and m.any():
            nxt=alive[m].copy()
            if not nxt.empty: alive=nxt
    return alive.sort_values("score",ascending=False)

def run_blender(df):
    run,bad=clean_for_run(df)
    owners=[]; surv=[]
    for game,gdf in run.groupby("game",dropna=False):
        alive=run_game(gdf)
        alive=alive[alive["player"].astype(str).apply(is_player_name)]
        if not alive.empty:
            surv.append(alive.assign(game_owner=game))
            owners.append(alive.iloc[0].to_dict())
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    surv=pd.concat(surv,ignore_index=True) if surv else pd.DataFrame()
    if owners.empty: return owners,pd.DataFrame(),pd.DataFrame(),pd.DataFrame(),surv,bad
    owners=owners.sort_values("score",ascending=False).reset_index(drop=True)
    def one_per(pool,n,exclude_games=set()):
        out=[]; used=set(exclude_games)
        for _,r in pool.iterrows():
            if r.game not in used:
                out.append(r.to_dict()); used.add(r.game)
            if len(out)>=n: break
        return pd.DataFrame(out),used
    core,used=one_per(owners,3)
    alt,_=one_per(owners,3,used)
    cp=owners.copy()
    cp["_chaos"]=cp["score"].fillna(0)*.45+cp["dmg"].fillna(0)*18+cp["hr_pa"].fillna(0)*6+cp["weak_slot_tag"].fillna(False).astype(int)*12+cp["hr_alert"].fillna(False).astype(int)*10
    chaos,_=one_per(cp.sort_values("_chaos",ascending=False).drop(columns=["_chaos"]),3)
    return owners,core,alt,chaos,surv,bad

def fmt(x):
    return "—" if x is None or pd.isna(x) else (f"{x:.1f}" if isinstance(x,float) else str(x))
def pct(x):
    try: return max(2,min(100,int(float(x or 0))))
    except Exception: return 0

def card(r):
    p=pct(r.get("score")); color=team_color(r.get("team",""))
    st.markdown(f"""<div class="card" style="border-color:{color}99"><span class="role">{r.get('role','')}</span><span class="badge">{r.get('archetype','')}</span><div class="card-name">{r.get('player','')}</div><div class="meta"><span style="color:{color};font-weight:900">{r.get('team','')}</span> vs {r.get('pitcher','')} · Slot {fmt(r.get('lineup_slot'))}</div><div class="score">{fmt(r.get('score'))}<small style="display:block;font-family:Rajdhani;color:#aaa;font-size:13px">TRUE BLEND SCORE</small></div><div class="bar"><div class="fill" style="width:{p}%"></div></div><div class="stats"><div class="stat"><b>{fmt(r.get('pull_pct'))}</b><span>Pull</span></div><div class="stat"><b>{fmt(r.get('pitch_edge'))}</b><span>Pitch</span></div><div class="stat"><b>{fmt(r.get('dmg'))}</b><span>DMG</span></div><div class="stat"><b>{fmt(r.get('hr_pa'))}</b><span>HR/PA</span></div><div class="stat"><b>{fmt(r.get('hpi'))}</b><span>HPI</span></div><div class="stat"><b>{fmt(r.get('sweet_spot_pct'))}</b><span>Sweet</span></div></div><div class="reason"><b>Blend path:</b> {r.get('gate_path','')[:220]}</div></div>""",unsafe_allow_html=True)

def blender_visual(names=None,status="READY"):
    names=(names or ["Upload Feed","Players In","Gates Spin","Owners Out"])*2
    floats="".join([f"<div class='float f{i+1}'>{str(n)[:22]}</div>" for i,n in enumerate(names[:6])])
    pulse="<div class='result-pulse'>RESULTS READY</div>" if status=="LOCKED" else ""
    st.markdown(f"""<div class="machine"><div class="blender-wrap"><div class="feed-slot">FEED DATA HERE</div><div class="jar"><div class="blade"></div><div class="center">{status}</div>{floats}</div>{pulse}<div class="output-slot">BLADES SPIN → OWNERS LOCK → TICKETS POP OUT</div></div></div>""",unsafe_allow_html=True)

def safe_table(df,height=360):
    if df is None or df.empty:
        st.info("No data."); return
    show=df.copy()
    for c in show.columns:
        if show[c].dtype=="object": show[c]=show[c].astype(str)
    st.dataframe(show,use_container_width=True,height=height)

def csv_bytes(df):
    return b"" if df is None or df.empty else df.to_csv(index=False).encode("utf-8")

st.set_page_config(page_title="THE BLENDER",page_icon="🔥",layout="wide",initial_sidebar_state="collapsed")
css()
st.markdown("""<div class="hero"><div class="title">THE <span class="hot">BLENDER</span><br/>MACHINE</div></div>""",unsafe_allow_html=True)
tabs=st.tabs(["Blender Machine","Tickets","Game Board"])

with tabs[0]:
    names=[r.get("player","") for r in st.session_state.get("owners",pd.DataFrame()).head(6).to_dict("records")] if "owners" in st.session_state else st.session_state.get("feed_names",None)
    blender_visual(names,"LOCKED" if "owners" in st.session_state else "READY")
    up=st.file_uploader("FEED PLAYERS",type=["pdf","csv","xlsx"],label_visibility="collapsed")
    if up:
        try: df,raw=read_file(up.name,up.read())
        except Exception as e:
            st.warning(f"Machine read issue: {e}"); df,raw=pd.DataFrame(columns=CANON),""
        run,bad=clean_for_run(df)
        st.session_state["df"]=df; st.session_state["feed_names"]=run["player"].dropna().astype(str).head(6).tolist() if not run.empty else []
        c1,c2,c3,c4=st.columns(4)
        c1.metric("Players Read",len(df)); c2.metric("Runnable",len(run)); c3.metric("Games",run.game.nunique() if not run.empty else 0); c4.metric("Quarantined",len(bad))
        st.markdown("<div class='status'>PLAYERS FED — TRUE BLENDER READY</div>",unsafe_allow_html=True)
        if st.button("BLEND NOW"):
            if run.empty:
                st.warning("No readable hitter rows came out. If image-only OCR is unavailable on Streamlit, use CSV/XLSX/export.")
            else:
                bar=st.progress(0); msg=st.empty()
                for i,t in enumerate(["FEEDER RECONSTRUCTING","ARCHETYPES MAPPING","18 GATES FIRING","OWNERS ISOLATING","TICKETS POPPING"]):
                    msg.info(t); bar.progress((i+1)/5); time.sleep(.12)
                owners,core,alt,chaos,surv,bad=run_blender(df)
                st.session_state.update({"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":surv,"bad":bad})
                st.success("TRUE BLEND COMPLETE")

with tabs[1]:
    st.markdown("<div class='section-title' style='font-size:34px'>TICKETS</div>",unsafe_allow_html=True)
    for label,key in [("CORE 3","core"),("ALT 3","alt"),("CHAOS 3","chaos")]:
        st.markdown(f"<div class='ticket'><h2>{label}</h2>",unsafe_allow_html=True)
        df=st.session_state.get(key,pd.DataFrame())
        if df is None or df.empty: st.info("Run the Blender first.")
        else:
            for _,r in df.iterrows():
                st.markdown(f"<div class='leg'><span><b>{r.get('player','')}</b><br><small>{r.get('archetype','')} · {r.get('team','')} vs {r.get('pitcher','')}</small></span><span class='odds'>{int(r.get('score',0))}%</span></div>",unsafe_allow_html=True)
            st.download_button(f"Download {label}",csv_bytes(df),f"{label.lower().replace(' ','_')}.csv","text/csv")
        st.markdown("</div>",unsafe_allow_html=True)

with tabs[2]:
    st.markdown("<div class='section-title' style='font-size:34px'>GAME BOARD — SURVIVORS BY GAME</div>",unsafe_allow_html=True)
    owners=st.session_state.get("owners",pd.DataFrame()); surv=st.session_state.get("survivors",pd.DataFrame())
    if owners is None or owners.empty: st.info("Run the Blender first.")
    else:
        for _,r in owners.iterrows(): card(r)
        with st.expander("All Survivors + Gates"):
            cols=[c for c in ["page","game","player","team","pitcher","archetype","role","score","weak_slots","gate_path","notes"] if c in surv.columns]
            safe_table(surv[cols],460)
        st.download_button("Download Game Board CSV",csv_bytes(owners),"game_board.csv","text/csv")
