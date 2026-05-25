
# ============================================================
# TRUE BLENDER ENGINE ONLY REPAIR
# Purpose:
# - preserve UI/live/spinner
# - replace broken Blender runtime path only
# - correct PDF rows only
# - true matchup isolation
# - no stale/yesterday picks
# - Primary / Adjacent / WHO cannot overlap
# - repeat names refill correctly
# - Core 3 structured
# - Game Board uses true role outcome, not fake tags
# ============================================================

import re
import json
import pandas as pd
import numpy as np

MLB_TEAMS = [
"Arizona Diamondbacks","Atlanta Braves","Baltimore Orioles","Boston Red Sox","Chicago Cubs","Chicago White Sox",
"Cincinnati Reds","Cleveland Guardians","Colorado Rockies","Detroit Tigers","Houston Astros","Kansas City Royals",
"Los Angeles Angels","Los Angeles Dodgers","Miami Marlins","Milwaukee Brewers","Minnesota Twins","New York Mets",
"New York Yankees","Athletics","Oakland Athletics","Philadelphia Phillies","Pittsburgh Pirates","San Diego Padres",
"San Francisco Giants","Seattle Mariners","St. Louis Cardinals","Tampa Bay Rays","Texas Rangers","Toronto Blue Jays",
"Washington Nationals"
]
TEAM_RE = re.compile("|".join([re.escape(t) for t in sorted(MLB_TEAMS, key=len, reverse=True)]), re.I)

def _txt(x):
    try:
        if x is None or pd.isna(x): return ""
    except Exception:
        pass
    return str(x).strip()

def _num(x, default=np.nan):
    try:
        if x is None or pd.isna(x): return default
        s = str(x).replace("%","").replace("+","").replace(",","").strip()
        if s.lower() in {"","nan","none","null","-","—"}: return default
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group(0)) if m else default
    except Exception:
        return default

def _compact(s):
    return str(s).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")

def _find_col(df, aliases):
    cmap = {_compact(c): c for c in df.columns}
    for a in aliases:
        aa = _compact(a)
        if aa in cmap: return cmap[aa]
    for a in aliases:
        aa = _compact(a)
        for k,v in cmap.items():
            if aa in k or k in aa:
                return v
    return None

def _extract_matchup_from_row(row):
    # Do not use team vs pitcher. Only true team-vs-team or trusted existing matchup.
    blob = " | ".join([_txt(v) for v in row.values])
    pitcher = _txt(row.get("pitcher",""))

    # Existing game_key/game is trusted if it has vs/@ and does not contain the pitcher name.
    for key in ["game_key","game","matchup"]:
        g = _txt(row.get(key,""))
        if (" vs " in g or "@" in g) and not (pitcher and pitcher in g):
            found = TEAM_RE.findall(g)
            if len(found) >= 2 and found[0].lower() != found[1].lower():
                return f"{found[0]} vs {found[1]}"
            # Preserve already-grouped matchup even if team names are abbreviated or not in dictionary.
            left_right = re.split(r"\s+(?:vs\.?|@)\s+", g, flags=re.I)
            if len(left_right) >= 2 and left_right[0].strip() and left_right[1].strip():
                return f"{left_right[0].strip()} vs {left_right[1].strip()}"

    teams = TEAM_RE.findall(blob)
    if len(teams) >= 2 and teams[0].lower() != teams[1].lower():
        return f"{teams[0]} vs {teams[1]}"

    team = _txt(row.get("team",""))
    opp = _txt(row.get("opponent",""))
    if team and opp and team.lower() != opp.lower():
        return f"{team} vs {opp}"
    return ""

def normalize_feed_engine_only(df):
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    raw = df.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    out = pd.DataFrame(index=raw.index)

    aliases = {
        "player":["player","hitter","batter","name"],
        "team":["team","club","bat_team","batter_team"],
        "opponent":["opponent","opp","vs"],
        "pitcher":["pitcher","sp","starter","opposing_pitcher","probable"],
        "game":["game","matchup"],
        "lineup_slot":["lineup_slot","slot","order","batting_order","bo"],
        "pull_pct":["pull_pct","pull%","pull","pull rate"],
        "hard_hit_pct":["hard_hit_pct","hardhit%","hard_hit%","hard hit%","hh%","hh"],
        "barrel_pct":["barrel_pct","barrel%","brl%","barrel"],
        "sweet_spot_pct":["sweet_spot_pct","sweet%","sweet spot","launch","launch_angle","la"],
        "dmg":["dmg","damage","ult","ultimate","adj","adjusted"],
        "hpi":["hpi","model","rating","hr score","score"],
        "hr_lane":["hr_lane","hr_pa","hr/pa","hr rate","hr_rate","hr9","hr/9","pitcher_hr9"],
        "pitch_edge":["pitch_edge","pitch edge","edge"],
        "notes":["notes","note","tag","status"]
    }

    for target, names in aliases.items():
        col = _find_col(raw, names)
        out[target] = raw[col] if col is not None else ""

    # If player column failed, choose best name-like column that is NOT pitcher.
    if out["player"].astype(str).str.strip().eq("").all() or out["player"].astype(str).str.contains("pitcher|starter", case=False, na=False).mean() > .4:
        best_col, best_score = None, -1
        for c in raw.columns:
            cl = str(c).lower()
            if "pitch" in cl or "starter" in cl: 
                continue
            vals = raw[c].fillna("").astype(str).head(100)
            score = 0
            for v in vals:
                vv = v.strip()
                if 2 <= len(vv.split()) <= 4 and re.search(r"[A-Za-z]", vv) and not re.search(r"\d{2,}", vv):
                    score += 1
            if score > best_score:
                best_score, best_col = score, c
        if best_col is not None and best_score > 0:
            out["player"] = raw[best_col]

    for c in ["player","team","opponent","pitcher","game","notes"]:
        out[c] = out[c].apply(_txt)

    metric_cols = ["lineup_slot","pull_pct","hard_hit_pct","barrel_pct","sweet_spot_pct","dmg","hpi","hr_lane","pitch_edge"]
    for c in metric_cols:
        out[c] = out[c].apply(_num)

    # Matchup isolation
    game_keys = []
    for idx, r in pd.concat([out, raw.add_prefix("raw_")], axis=1).iterrows():
        game_keys.append(_extract_matchup_from_row(r))
    out["game_key"] = game_keys

    # Remove bad rows: pitcher as player, headers, non-player fallback
    bad = []
    for _, r in out.iterrows():
        p = _txt(r.get("player",""))
        pit = _txt(r.get("pitcher",""))
        low = p.lower()
        is_bad = False
        if not p: is_bad = True
        if pit and (low == pit.lower() or low in pit.lower() or pit.lower() in low): is_bad = True
        if any(x in low for x in ["pitcher","starter","probable","download","page","copyright","pull%","barrel","hard hit","team","game"]): is_bad = True
        if not _txt(r.get("game_key","")): is_bad = True
        bad.append(is_bad)
    out = out[~pd.Series(bad, index=out.index)].copy()

    # Preserve official MLB slate columns when attached by app.
    for _c in ["game_pk","game_time_et","game_time_utc","game_status","away_team","home_team","away_probable_pitcher","home_probable_pitcher","official_source","official_date","official_slate_attached"]:
        if _c in raw.columns:
            out[_c] = raw[_c]

    out["metric_count"] = out[metric_cols].notna().sum(axis=1)
    out["parser_status"] = out["metric_count"].apply(lambda x: "READY" if x >= 3 else "AUDIT_ONLY")
    if "slate_window" not in out.columns:
        out["slate_window"] = raw["slate_window"] if "slate_window" in raw.columns else "Unknown"

    return out.reset_index(drop=True)

def true_game_count(df):
    df = normalize_feed_engine_only(df)
    if df.empty:
        return 0
    if "game_pk" in df.columns:
        s = df["game_pk"].dropna().astype(str).str.strip()
        s = s[(s!="") & (s!="nan")]
        if len(s):
            return int(s.nunique())
    if "game_key" not in df.columns:
        return 0
    return int(df["game_key"].dropna().astype(str).str.strip().replace("", pd.NA).dropna().nunique())

def gate_strength(x, floor, elite, pts):
    if x is None or pd.isna(x): return 0.0
    x = float(x)
    if x < floor: return 0.0
    if x >= elite: return float(pts)
    return float(pts) * (x - floor) / max(1, elite - floor)

def evaluate_row(row):
    pull = _num(row.get("pull_pct"), 0)
    hard = _num(row.get("hard_hit_pct"), 0)
    barrel = _num(row.get("barrel_pct"), 0)
    sweet = _num(row.get("sweet_spot_pct"), 0)
    dmg = _num(row.get("dmg"), 0)
    hpi = _num(row.get("hpi"), 0)
    hr = _num(row.get("hr_lane"), 0)
    edge = _num(row.get("pitch_edge"), -99)
    slot = _num(row.get("lineup_slot"), 0)
    notes = _txt(row.get("notes")).lower()
    metric_count = int(row.get("metric_count", 0) or 0)

    gates = []
    def add(step, gate, score, max_score, verdict=None, reason=""):
        if verdict is None:
            verdict = "PASS" if score > 0 else "KILL"
        gates.append({"step":step,"gate":gate,"verdict":verdict,"gate_score":round(max(0,float(score)),2),"max_score":float(max_score),"reason":reason})

    trigger = pull>=30 or hard>=30 or barrel>=5 or dmg>=.8 or hpi>=20 or hr>=.8 or edge>=0
    if metric_count < 3 or not trigger:
        add(0,"PDF metric qualification",0,10,"KILL",f"metric_count={metric_count}, trigger={trigger}")
        return False, 0, 0, "NO PICK", "Audit only — insufficient metrics", gates, metric_count

    add(0,"Correct PDF row only",10,10,"PASS","Valid player row from current PDF")
    add(1,"Matchup isolated",8 if _txt(row.get("game_key")) else 0,8, reason=_txt(row.get("game_key")))
    add(2,"Pitcher HR lane",max(gate_strength(hr,.8,2.2,10),gate_strength(edge,0,12,10),gate_strength(dmg,.8,2.0,10),gate_strength(hpi,20,65,10)),10)
    add(3,"Pitch-type kill switch",8 if edge>=0 else 0,8, reason=f"edge={edge}")
    add(4,"Pull-air / launch",max(gate_strength(pull,30,52,12),gate_strength(sweet,20,35,12),gate_strength(barrel,5,14,12)),12)
    add(5,"Damage / barrel",max(gate_strength(dmg,.8,2.2,12),gate_strength(barrel,5,14,12),gate_strength(hpi,20,70,12)),12)
    add(6,"True HR conversion",max(gate_strength(hpi,20,70,12),gate_strength(hr,.8,2.2,12),gate_strength(dmg,.8,2.2,12)),12)
    add(7,"Opportunity / lineup",7 if slot==0 or slot<=7 else 0,7, reason=f"slot={slot}")
    add(8,"Hard-hit support",max(gate_strength(hard,30,55,7),gate_strength(barrel,5,14,7),gate_strength(dmg,.8,2.0,7)),7)
    add(9,"Adjacent / decoy",5 if any(x in notes for x in ["adjacent","decoy","transfer"]) else 2,5,"PASS" if any(x in notes for x in ["adjacent","decoy","transfer"]) else "WEAK")
    add(10,"WHO / chaos",6 if ("who" in notes or "chaos" in notes or (pull>=30 and hard>=30 and hpi<45)) else 2,6,"PASS" if ("who" in notes or "chaos" in notes or (pull>=30 and hard>=30 and hpi<45)) else "WEAK")
    add(11,"Trap audit",8 if "trap" not in notes else 0,8)
    fin = 0
    if pull >= 35:
        fin = max(gate_strength(hard,30,55,12),gate_strength(barrel,5,14,12),gate_strength(dmg,.8,2.0,12),gate_strength(hpi,20,70,12))
    add(12,"Finisher gate",fin,12)
    add(13,"Final model confirmation",max(gate_strength(pull,30,52,10),gate_strength(hard,30,55,10),gate_strength(dmg,.8,2.0,10),gate_strength(hpi,20,70,10),gate_strength(hr,.8,2.2,10)),10)

    raw = sum(g["gate_score"] for g in gates)
    maxraw = sum(g["max_score"] for g in gates)
    blender_score = round(max(1,min(100,(raw/maxraw)*100)),1)
    support_score = round(max(1,min(100,min(pull,65)*.16+min(hard,70)*.12+min(barrel,25)*.5+min(dmg,8)*2.8+min(hpi,100)*.10+min(hr,6)*2.0+(max(min(edge,30),-20)*.2 if edge!=-99 else 0))),1)

    primary = gate_strength(pull,35,52,20)+gate_strength(barrel,6,14,20)+gate_strength(dmg,1,2.2,20)+gate_strength(hpi,25,70,15)+gate_strength(hr,1,2.5,15)+gate_strength(edge,0,20,10)
    adjacent = (35 if any(x in notes for x in ["adjacent","decoy","transfer"]) else 0)+gate_strength(pull,30,45,18)+gate_strength(hard,30,48,18)+gate_strength(dmg,.8,1.8,14)+gate_strength(hpi,20,55,10)
    who = (35 if ("who" in notes or "chaos" in notes) else 0)+gate_strength(pull,28,40,15)+gate_strength(hard,30,45,15)+gate_strength(hr,.8,1.8,15)+gate_strength(edge,0,12,10)+(10 if hpi<45 else 0)
    role_scores = {"Primary":primary,"Adjacent":adjacent,"WHO":who}
    role = max(role_scores, key=role_scores.get)
    if blender_score < 55:
        role = "NO PICK"
    archetype = {"Primary":"Primary HR Owner","Adjacent":"Adjacent / Decoy Transfer","WHO":"WHO / Chaos Owner"}.get(role,"Audit only")
    return role!="NO PICK", blender_score, support_score, role, archetype, gates, metric_count

def true_blender_run(df):
    df = normalize_feed_engine_only(df)
    if df.empty:
        return empty_results("No usable current-PDF rows after normalization.")

    survivors, board, role_rows = [], [], []
    for idx, r in df.iterrows():
        row = r.to_dict()
        ok, b, s, role, arch, gates, mc = evaluate_row(row)
        row.update({"row_id":idx,"blender_eligible":ok,"blender_score":b,"support_score":s,"score":b,"official_core_role":role,"archetype":arch,"metric_count":mc,"final_reason": f"{role} survived true gate path" if ok else "NO PICK"})
        row["gate_trace_json"] = json.dumps(gates)
        survivors.append(row)
        for g in gates:
            board.append({"game_key":row.get("game_key"),"player":row.get("player"),"role":role,**g,"blender_score":b})
        role_rows.append({"game_key":row.get("game_key"),"player":row.get("player"),"assigned_role":role,"archetype":arch,"blender_score":b,"support_score":s})

    survivors = pd.DataFrame(survivors)
    game_board = pd.DataFrame(board)
    role_board = pd.DataFrame(role_rows)

    owners = []
    for game, g in survivors.groupby("game_key", dropna=False):
        eg = g[g["blender_eligible"] == True].copy()
        if eg.empty: 
            continue
        pick = eg.sort_values(["blender_score","support_score"], ascending=[False,False]).iloc[0].to_dict()
        pick["game_owner"] = game
        owners.append(pick)
    owners = pd.DataFrame(owners)
    if not owners.empty:
        owners = owners.sort_values(["blender_score","support_score"], ascending=[False,False]).drop_duplicates(["game_key","player"]).reset_index(drop=True)

    # structured Core 3: attempt Primary, Adjacent, WHO once each, then refill no overlap
    used = set()
    core_parts = []
    for role in ["Primary","Adjacent","WHO"]:
        pool = owners[(owners["official_core_role"] == role) & (~owners["player"].astype(str).isin(used))].copy() if not owners.empty else pd.DataFrame()
        if not pool.empty:
            p = pool.sort_values(["blender_score","support_score"], ascending=[False,False]).head(1)
            core_parts.append(p)
            used.update(p["player"].astype(str).tolist())
    core = pd.concat(core_parts, ignore_index=True) if core_parts else pd.DataFrame()
    if not owners.empty and len(core) < 3:
        refill = owners[~owners["player"].astype(str).isin(used)].head(3-len(core))
        if not refill.empty:
            core = pd.concat([core, refill], ignore_index=True)
    if not core.empty:
        core = core.head(3).copy()
        core["ticket_role"] = "CORE"

    used = set(core["player"].astype(str).tolist()) if not core.empty and "player" in core else set()
    alt = owners[~owners["player"].astype(str).isin(used)].head(3).copy() if not owners.empty and "player" in owners else pd.DataFrame()
    if not alt.empty: alt["ticket_role"] = "ALT"
    used.update(alt["player"].astype(str).tolist() if not alt.empty and "player" in alt else [])
    chaos = owners[(owners["official_core_role"] == "WHO") & (~owners["player"].astype(str).isin(used))].head(3).copy() if not owners.empty and "player" in owners else pd.DataFrame()
    if chaos.empty and not owners.empty and "player" in owners:
        chaos = owners[~owners["player"].astype(str).isin(used)].head(3).copy()
    if not chaos.empty: chaos["ticket_role"] = "WHO"

    meta = {"engine_version":"TRUE_ENGINE_ONLY_REPAIR","input_rows":len(df),"games":true_game_count(df),"eligible_rows":int(survivors["blender_eligible"].sum()),"owners_locked":len(owners),"core_count":len(core),"message":f"Blender repaired run complete: {len(owners)} owners from {true_game_count(df)} games; Core={len(core)}."}
    return {"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"game_board":game_board,"role_board":role_board,"meta":meta}

def empty_results(msg):
    return {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"game_board":pd.DataFrame(),"role_board":pd.DataFrame(),"meta":{"engine_version":"TRUE_ENGINE_ONLY_REPAIR","owners_locked":0,"games":0,"message":msg}}
