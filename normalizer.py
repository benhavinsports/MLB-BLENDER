import re, pandas as pd
from config import CANON

BAD=set("dmg hpi line cond alert hot cold warm moderate elevated low high fresh effort page https star tool projected weak slot home away none upload slate summary details hand bats team pitcher player vs lineup pull sweet barrel damage ownership public".split())
ALIASES={"player":["player","name","batter","hitter","player_name","batter_name"],"team":["team","tm","bat_team","batter_team"],"pitcher":["pitcher","opp_pitcher","opposing_pitcher","starter","sp"],"game":["game","matchup","game_key"],"lineup_slot":["lineup_slot","slot","batting_order","order","lineup","bo"],"pull_pct":["pull_pct","pull%","pull","pull_percent"],"barrel_pct":["barrel_pct","barrel%","barrel"],"sweet_spot_pct":["sweet_spot_pct","sweet%","sweet_spot","line","launch","launch_pct"],"hard_hit_pct":["hard_hit_pct","hardhit%","hard_hit","hh","hh%"],"hpi":["hpi","hr_power_index","power","ult","adj"],"dmg":["dmg","damage","dmg_score"],"hr_pa":["hr_pa","hr/pa","hr_pa_pct","hr%","hr_rate"],"pitch_edge":["pitch_edge","edge","pitch_matchup","pitch_type_edge"],"pitch_type":["pitch_type","pitch","primary_pitch"],"weak_slots":["weak_slots","weak_slot","pitcher_weak_slots"],"odds":["odds","hr_odds","anytime_odds"],"public_pct":["public_pct","public","ownership","owned"],"weather_score":["weather_score","weather","park","env"],"bullpen_dmg":["bullpen_dmg","bullpen","bp_dmg"],"hr_alert":["hr_alert","alert"],"cond_up":["cond_up","condition_up","cond"],"weak_slot_tag":["weak_slot_tag","weakslot"],"laser":["laser"],"rakes":["rakes"],"platoon":["platoon"],"confirmed_lineup":["confirmed_lineup","confirmed","starting"],"notes":["notes","note","raw"]}

def is_player_name(s):
    s=str(s).strip()
    if len(s)<3 or re.search(r"\d",s): return False
    if s.lower() in BAD or "http" in s.lower(): return False
    parts=s.split()
    return 1<=len(parts)<=4 and all(re.match(r"^[A-Za-zÀ-ÿ.'’\\-]+$",p) for p in parts)

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

def map_columns(df):
    norm={c:re.sub(r"[^a-z0-9]+","_",str(c).lower()).strip("_") for c in df.columns}
    rename={}
    for canon,als in ALIASES.items():
        opts=[re.sub(r"[^a-z0-9]+","_",a.lower()).strip("_") for a in als]
        for c,n in norm.items():
            if n in opts:
                rename[c]=canon
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
        if candidates:
            df["player"]=df[sorted(candidates,reverse=True)[0][1]]
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
