import re
import pandas as pd

CANON = [
    "source","page","game","team","opponent","pitcher","player","bats","lineup_slot",
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

TEAM_COLORS = {
"red sox":"#BD3039","yankees":"#0C2340","mets":"#FF5910","dodgers":"#005A9C","padres":"#2F241D",
"phillies":"#E81828","reds":"#C6011F","mariners":"#005C5C","braves":"#CE1141","twins":"#002B5C",
"astros":"#EB6E1F","blue jays":"#134A8E","orioles":"#DF4601","rays":"#092C5C","royals":"#004687",
"cubs":"#0E3386","cardinals":"#C41E3A","rockies":"#33006F","angels":"#BA0021","giants":"#FD5A1E",
"diamondbacks":"#A71930","tigers":"#0C2340","guardians":"#E50022","athletics":"#003831",
"white sox":"#27251F","pirates":"#FDB827","brewers":"#FFC52F","marlins":"#00A3E0",
"nationals":"#AB0003","rangers":"#003278"
}

BAD_PLAYER_TOKENS = {
"VS","PROJECTED","PITCHER","TEAM","LINEUP","SLOT","BATS","HAND","ALERT","DMG","HPI","PULL","SWEET",
"STAR","TOOL","DATA","PAGE","HOME","AWAY","NONE","SUMMARY","DETAILS","WEAK","COND","LINE"
}

ALIASES = {
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

def team_color(team):
    t = str(team).lower()
    for key, val in TEAM_COLORS.items():
        if key in t:
            return val
    return "#d9ff2f"

def normalize_team(text):
    raw = str(text).strip()
    u = re.sub(r"[^A-Z .'-]", "", raw.upper()).strip()
    if not u:
        return ""
    if u in TEAM_ABBR:
        return TEAM_ABBR[u]
    if u in {"ATHLETICS","A'S","AS"}:
        return "Athletics"
    for name in TEAM_NAMES:
        if name.upper() == u or name.upper() in u:
            return name
    return ""

def is_team_token(text):
    u = str(text).strip().upper()
    if not u:
        return True
    if u in TEAM_ABBR:
        return True
    if normalize_team(u):
        return True
    return False

def nfloat(x):
    if x is None or pd.isna(x):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace("%","").replace("+","").replace("↑","").replace("↓","").strip()
    if s in ["", "-", "—", "None", "nan", "NaN"]:
        return None
    try:
        return float(s)
    except Exception:
        return None

def nbool(x):
    if isinstance(x, bool):
        return x
    return str(x).strip().lower() in {"true","1","yes","y","alert","hot","x","confirmed","✅","up"}

def is_player_name(text):
    s = str(text).strip()
    u = s.upper()
    if len(s) < 3 or re.search(r"\d", s):
        return False
    if u in BAD_PLAYER_TOKENS:
        return False
    if is_team_token(s):
        return False
    parts = s.split()
    if not (1 <= len(parts) <= 4):
        return False
    return all(re.match(r"^[A-Za-zÀ-ÿ.'’\-]+$", p) for p in parts)

def map_structured_columns(df):
    df = df.copy()
    norm = {c: re.sub(r"[^a-z0-9]+", "_", str(c).lower()).strip("_") for c in df.columns}
    rename = {}
    for canon, aliases in ALIASES.items():
        opts = [re.sub(r"[^a-z0-9]+", "_", a.lower()).strip("_") for a in aliases]
        for c, n in norm.items():
            if n in opts:
                rename[c] = canon
    df = df.rename(columns=rename)
    for c in CANON:
        if c not in df.columns:
            df[c] = None
    return df

def normalize_df(df, source="structured"):
    if df is None or df.empty:
        return pd.DataFrame(columns=CANON)

    df = map_structured_columns(df)

    if "player" not in df or df["player"].isna().all():
        for c in df.columns:
            vals = df[c].dropna().astype(str).head(100)
            if sum(is_player_name(v) for v in vals) >= 4:
                df["player"] = df[c]
                break

    for c in ["lineup_slot","pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge","odds","public_pct","weather_score","bullpen_dmg","jersey"]:
        df[c] = df[c].apply(nfloat)

    for c in ["hr_alert","cond_up","weak_slot_tag","laser","rakes","platoon","confirmed_lineup","result_hr"]:
        df[c] = df[c].apply(nbool)

    for c in ["team","pitcher","game","player"]:
        df[c] = df[c].fillna("").astype(str).str.strip()

    df["source"] = source
    df["team"] = df["team"].apply(lambda x: normalize_team(x) or x)
    df = df[df["player"].apply(is_player_name)].copy()

    metric_cols = ["pull_pct","barrel_pct","sweet_spot_pct","hard_hit_pct","hpi","dmg","hr_pa","pitch_edge"]
    df = df[df[metric_cols].notna().any(axis=1)].copy()

    df.loc[df["game"].str.strip()=="", "game"] = df["team"] + " vs " + df["pitcher"]
    df.loc[df["game"].str.strip()==" vs ", "game"] = "Unknown Game"

    for c in CANON:
        if c not in df.columns:
            df[c] = None

    return df[CANON]
