import re
import json
import urllib.request
import pandas as pd
import urllib.request, json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

def safe_num(x, default=0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default




TEAM_ABBR = {
    "Arizona Diamondbacks":"ARI","Atlanta Braves":"ATL","Baltimore Orioles":"BAL","Boston Red Sox":"BOS",
    "Chicago Cubs":"CHC","Chicago White Sox":"CHW","Cincinnati Reds":"CIN","Cleveland Guardians":"CLE",
    "Colorado Rockies":"COL","Detroit Tigers":"DET","Houston Astros":"HOU","Kansas City Royals":"KC",
    "Los Angeles Angels":"LAA","Los Angeles Dodgers":"LAD","Miami Marlins":"MIA","Milwaukee Brewers":"MIL",
    "Minnesota Twins":"MIN","New York Mets":"NYM","New York Yankees":"NYY","Athletics":"ATH",
    "Philadelphia Phillies":"PHI","Pittsburgh Pirates":"PIT","San Diego Padres":"SD","San Francisco Giants":"SF",
    "Seattle Mariners":"SEA","St. Louis Cardinals":"STL","Tampa Bay Rays":"TB","Texas Rangers":"TEX",
    "Toronto Blue Jays":"TOR","Washington Nationals":"WSH"
}
ABBR_TEAM = {v:k for k,v in TEAM_ABBR.items()}


def team_abbr(team):
    s = str(team or "").strip()
    if not s:
        return "UNK"
    u = s.upper().strip()
    if u in ABBR_TEAM:
        return u
    if s in TEAM_ABBR:
        return TEAM_ABBR[s]
    cleaned = "".join([c for c in u if c.isalpha()])[:3]
    return cleaned or "UNK"

def canonical_game_key(team, opponent=None, pitcher=None, game=None):
    t1 = team_abbr(team)
    text = str(game or "")
    opp = str(opponent or "").strip()

    if not opp and " vs " in text:
        left, right = text.split(" vs ", 1)
        for known_team in TEAM_ABBR:
            if known_team.lower() in right.lower():
                opp = known_team
                break

    t2 = team_abbr(opp) if opp else ""
    if t2 and t2 != "UNK" and t2 != t1:
        a, b = sorted([t1, t2])
        return f"{a}_{b}"

    raw_p = str(pitcher or "").upper()
    p = "".join([c for c in raw_p if c.isalpha()])[:10]
    return f"{t1}_VS_{p or 'UNK'}"

def normalize_game_frame(df):
    if df is None or getattr(df, "empty", True):
        return df
    out = df.copy()
    for c in ["team","opponent","pitcher","game","player"]:
        if c not in out.columns:
            out[c] = ""
    out["game_key"] = out.apply(lambda r: canonical_game_key(r.get("team",""), r.get("opponent",""), r.get("pitcher",""), r.get("game","")), axis=1)
    out["game"] = out.apply(lambda r: r.get("game") if str(r.get("game","")).strip() else f"{r.get('team','')} vs {r.get('pitcher','')}", axis=1)
    return out.drop_duplicates(subset=["game_key","team","pitcher","player"], keep="first").reset_index(drop=True)

def actual_game_count(df):
    if df is None or getattr(df, "empty", True):
        return 0
    if "game_key" in df.columns:
        return int(df["game_key"].nunique())
    return int(df["game"].nunique()) if "game" in df.columns else 0

def archetype(r):
    gates = hard_gate_result(r)
    pull=safe_num(r.get("pull_pct"))
    pe=safe_num(r.get("pitch_edge"))
    dmg=safe_num(r.get("dmg"))
    hrpa=safe_num(r.get("hr_pa"))
    hpi=safe_num(r.get("hpi"))
    sweet=safe_num(r.get("sweet_spot_pct"))

    if gates.get("who_owner"):
        return "WHO / Chaos Finisher"
    if gates.get("adjacent_owner") and not gates.get("clean_owner"):
        return "Adjacent / Transfer Owner"
    if pull >= 24 and sweet >= 25 and hrpa >= 1.6 and pe >= 0:
        return "Elite Converter"
    if hpi >= 35 and dmg >= .8 and pe >= 0:
        return "Primary HR Owner"
    if pe >= 12 and (pull >= 18 or hpi >= 20):
        return "Pitch-Type Punisher"
    return "Primary HR Owner"


def role_bucket(r):
    gates = hard_gate_result(r)
    if gates.get("who_owner"):
        return "WHO"
    if gates.get("adjacent_owner") and not gates.get("clean_owner"):
        return "Adjacent"
    return "Primary"



def blend_score(r):
    gates = hard_gate_result(r)
    pull=safe_num(r.get("pull_pct"))
    sweet=safe_num(r.get("sweet_spot_pct"))
    hh=safe_num(r.get("hard_hit_pct"))
    dmg=safe_num(r.get("dmg"))
    hrpa=safe_num(r.get("hr_pa"))
    hpi=safe_num(r.get("hpi"))
    pe=safe_num(r.get("pitch_edge"))

    # If hard gates fail, the hitter cannot look like a lock.
    if not gates["real_metrics"]:
        return 0.0
    if not gates["pitch"]:
        return min(34.0, max(0, dmg*8 + hrpa*4 + hpi*.25))
    if not gates["pull_air"]:
        return min(42.0, max(0, sweet*.7 + dmg*8 + hrpa*3))
    if not gates["damage"]:
        return min(38.0, max(0, pull*.6 + sweet*.45 + hpi*.2))
    if not gates["conversion"]:
        return min(44.0, max(0, pull*.6 + sweet*.55 + dmg*10))
    if not gates["launch"]:
        return min(48.0, max(0, pull*.7 + dmg*10 + hrpa*4))
    if not gates["gate19"]:
        return min(54.0, max(0, pull*.45 + sweet*.45 + dmg*8 + hrpa*3 + hpi*.2))

    score = 0
    score += max(0, min(18, (pull-16)*1.05))
    score += max(0, min(16, (sweet-20)*1.10))
    score += max(0, min(10, hh*.25))
    score += max(0, min(18, dmg*8.0))
    score += max(0, min(16, hrpa*3.5))
    score += max(0, min(14, hpi*.32))
    score += max(0, min(10, pe*.55 + 4))
    if gates.get("transfer"): score += 6
    if gates.get("chaos"): score += 7
    if bool(r.get("cond_up")): score += 3
    if bool(r.get("laser")): score += 2
    if bool(r.get("rakes")): score += 2

    return round(max(0, min(100, score)), 1)



def hard_gate_result(r):
    pull=safe_num(r.get("pull_pct"))
    sweet=safe_num(r.get("sweet_spot_pct"))
    dmg=safe_num(r.get("dmg"))
    hrpa=safe_num(r.get("hr_pa"))
    hpi=safe_num(r.get("hpi"))
    pe=safe_num(r.get("pitch_edge"))
    hh=safe_num(r.get("hard_hit_pct"))
    barrel=safe_num(r.get("barrel_pct"))
    slot=safe_num(r.get("lineup_slot"), None)
    weak_slots=str(r.get("weak_slots",""))
    weak_list=[x.strip() for x in weak_slots.split(",") if x.strip()]
    weak_slot = slot is not None and str(int(slot)) in weak_list
    real_metrics = sum([
        r.get("pull_pct") is not None and not pd.isna(r.get("pull_pct")),
        r.get("sweet_spot_pct") is not None and not pd.isna(r.get("sweet_spot_pct")),
        r.get("dmg") is not None and not pd.isna(r.get("dmg")),
        r.get("hr_pa") is not None and not pd.isna(r.get("hr_pa")),
        r.get("hpi") is not None and not pd.isna(r.get("hpi")),
        r.get("pitch_edge") is not None and not pd.isna(r.get("pitch_edge")),
    ])
    pull_gate = pull >= 40 or (pull >= 28 and sweet >= 28 and dmg >= 1.5)
    launch_gate = sweet >= 24 or barrel >= 10 or hh >= 42
    damage_gate = dmg >= 1.5 or hrpa >= 2.0 or bool(r.get("hr_alert"))
    pitch_gate = pe >= 0
    conversion_gate = hpi >= 35 or hrpa >= 1.5 or dmg >= 1.5
    opportunity_gate = slot is not None or weak_slot or bool(r.get("weak_slot_tag")) or bool(r.get("platoon"))
    transfer_gate = weak_slot or bool(r.get("weak_slot_tag")) or bool(r.get("platoon"))
    chaos_gate = bool(r.get("hr_alert")) and damage_gate and conversion_gate and pitch_gate
    gate19_pass, gate19_checks = hr_model_confirm(r)
    clean_owner = real_metrics >= 4 and pull_gate and launch_gate and damage_gate and pitch_gate and conversion_gate and gate19_pass
    adjacent_owner = real_metrics >= 4 and transfer_gate and damage_gate and pitch_gate and conversion_gate and launch_gate and gate19_pass
    who_owner = real_metrics >= 4 and chaos_gate and damage_gate and conversion_gate and pitch_gate and gate19_pass
    return {"real_metrics": real_metrics >= 4, "pull_air": pull_gate, "damage": damage_gate, "pitch": pitch_gate, "conversion": conversion_gate, "launch": launch_gate, "opportunity": opportunity_gate, "transfer": transfer_gate, "chaos": chaos_gate, "weak_slot": weak_slot, "gate19": gate19_pass, "gate19_checks": gate19_checks, "clean_owner": clean_owner, "adjacent_owner": adjacent_owner, "who_owner": who_owner}



def gate_fail_reason(gates):
    for g in ["real_metrics","pull_air","damage","pitch","conversion","launch","gate19"]:
        if not gates.get(g, False):
            return g
    return ""



def build_player_gate_path(r, owner_rank=None):
    gates = hard_gate_result(r)
    pull=safe_num(r.get("pull_pct"))
    sweet=safe_num(r.get("sweet_spot_pct"))
    dmg=safe_num(r.get("dmg"))
    hrpa=safe_num(r.get("hr_pa"))
    hpi=safe_num(r.get("hpi"))
    pe=safe_num(r.get("pitch_edge"))
    barrel=safe_num(r.get("barrel_pct"))
    parts = [
        "0 ENV CHECKED",
        "1 METRICS PASS" if gates["real_metrics"] else "1 METRICS FAIL",
        f"2 PULL {'PASS' if gates['pull_air'] else 'KILL'} {pull:.1f}",
        f"3 LAUNCH {'PASS' if gates['launch'] else 'KILL'} sweet {sweet:.1f} barrel {barrel:.1f}",
        f"4 DAMAGE {'PASS' if gates['damage'] else 'KILL'} {dmg:.1f}",
        f"5 PITCH {'PASS' if gates['pitch'] else 'KILL'} {pe:.1f}",
        f"6 CONVERSION {'PASS' if gates['conversion'] else 'KILL'} HPI {hpi:.1f} HRPA {hrpa:.1f}",
        "7 TRANSFER ACTIVE" if gates["transfer"] else "7 TRANSFER OFF",
        "8 CHAOS ACTIVE" if gates["chaos"] else "8 CHAOS OFF",
        "19 HR MODEL PASS" if gates["gate19"] else "19 HR MODEL FAIL",
        f"ROLE {r.get('official_core_role','') or role_bucket(r)}",
        f"ARCH {r.get('archetype','') or archetype(r)}",
    ]
    fail = gate_fail_reason(gates)
    if fail:
        parts.append(f"DEAD AT {fail.upper()}")
    elif owner_rank == 1:
        parts.append("GAME OWNER LOCKED")
    elif owner_rank is not None:
        parts.append(f"SURVIVOR RANK {owner_rank}")
    return " | ".join(parts)


def gate_path(r):
    return build_player_gate_path(r)





def run_game(gdf):
    pool = gdf.copy()
    if pool.empty:
        return pool

    for col in ["pull_pct","sweet_spot_pct","dmg","hr_pa","hpi","pitch_edge","lineup_slot","weak_slots"]:
        if col not in pool:
            pool[col] = None

    pool["_gates"] = pool.apply(hard_gate_result, axis=1)
    pool["score"] = pool.apply(blend_score, axis=1)
    pool["archetype"] = pool.apply(archetype, axis=1)
    pool["official_core_role"] = pool.apply(role_bucket, axis=1)

    # True death machine: only owner-qualified hitters survive.
    clean_mask = pool["_gates"].apply(lambda x: x.get("clean_owner") or x.get("adjacent_owner") or x.get("who_owner"))
    alive = pool[clean_mask].copy()

    # If nobody survives, mark the game as no-clean-owner instead of reviving bad hitters.
    if alive.empty:
        pool = pool.sort_values("score", ascending=False).reset_index(drop=True)
        pool["score"] = pool["score"].apply(lambda x: min(x, 39.0))
        pool["official_core_role"] = "NO PLAY"
        pool["archetype"] = "No Clean Owner"
        pool["gate_path"] = [build_player_gate_path(row, owner_rank=None) + " | GAME NO PLAY" for _, row in pool.iterrows()]
        return pool.head(1).drop(columns=[c for c in ["_gates"] if c in pool.columns])

    def owner_score(row):
        gates = row["_gates"]
        base = row["score"]
        role_bonus = 0
        if gates.get("clean_owner"): role_bonus += 12
        if gates.get("adjacent_owner"): role_bonus += 8
        if gates.get("who_owner"): role_bonus += 6
        return base + role_bonus

    alive["_owner_score"] = alive.apply(owner_score, axis=1)
    alive = alive.sort_values("_owner_score", ascending=False).reset_index(drop=True)
    alive["gate_path"] = [build_player_gate_path(row, owner_rank=i+1) for i, row in alive.iterrows()]

    return alive.drop(columns=[c for c in ["_owner_score","_gates"] if c in alive.columns])


def fetch_public_mlb_context():
    """
    Public fallback source for automatic machine mode.
    Pulls MLB schedule/probables for today's NY date.
    No Star Tool login required.
    """
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=probablePitcher"
    games = []
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return pd.DataFrame(), {"source":"MLB Stats API", "date":today, "error":"context_fetch_failed"}

    for d in data.get("dates", []):
        for g in d.get("games", []):
            teams = g.get("teams", {})
            away = teams.get("away", {}).get("team", {}).get("name", "")
            home = teams.get("home", {}).get("team", {}).get("name", "")
            away_p = teams.get("away", {}).get("probablePitcher", {}).get("fullName", "")
            home_p = teams.get("home", {}).get("probablePitcher", {}).get("fullName", "")
            if away and home:
                games.append({"team":away, "opponent":home, "pitcher":home_p, "game":f"{away} vs {home_p or home}"})
                games.append({"team":home, "opponent":away, "pitcher":away_p, "game":f"{home} vs {away_p or away}"})
    return pd.DataFrame(games), {"source":"MLB Stats API", "date":today, "games":len(games)//2}

def auto_enrich_feed(df):
    """
    If the user only uploads a Twitter slip/screenshot with names,
    keep the row, but fill missing context enough for Blender to run.
    This does NOT replace Star Tool data. It gives the machine a public-data fallback.
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    need = (
        out.get("team", pd.Series([""]*len(out))).fillna("").astype(str).str.strip().eq("")
        | out.get("pitcher", pd.Series([""]*len(out))).fillna("").astype(str).str.strip().eq("")
        | out.get("game", pd.Series([""]*len(out))).fillna("").astype(str).str.contains("Needs Enrichment|Unknown", case=False, na=False)
    )
    if not need.any():
        return out

    ctx, meta = fetch_public_mlb_context()
    # Since player→team lookup requires a heavier stats endpoint, keep unconfirmed rows in a safe public fallback bucket.
    # The Game Board will show that context is public fallback, not Star Tool precision.
    for idx in out[need].index:
        if str(out.at[idx, "team"]).strip() == "":
            out.at[idx, "team"] = "Public Feed"
        if str(out.at[idx, "pitcher"]).strip() == "":
            out.at[idx, "pitcher"] = "Today MLB Slate"
        if "Needs Enrichment" in str(out.at[idx, "game"]) or str(out.at[idx, "game"]).strip()=="":
            out.at[idx, "game"] = f"{out.at[idx,'player']} slip feed"
        note = str(out.at[idx, "notes"]) if "notes" in out.columns else ""
        out.at[idx, "notes"] = (note + "; public_auto_enrichment").strip("; ")

        # Add neutral fallback values so the machine can blend but does not fake elite confidence.
        defaults = {
            "pull_pct": 20.0, "sweet_spot_pct": 23.0, "dmg": 0.5,
            "hr_pa": 2.0, "hpi": 16.0, "pitch_edge": 0.0
        }
        for k,v in defaults.items():
            if k in out.columns and pd.isna(out.at[idx,k]):
                out.at[idx,k] = v
    return out


LOCK_FILE = "locked_owners.json"
RECAP_LOG_FILE = "recap_log.csv"

def _jsonable_records(df):
    if df is None or df.empty:
        return []
    safe = df.copy()
    for c in safe.columns:
        safe[c] = safe[c].apply(lambda x: None if pd.isna(x) else x)
    return safe.to_dict("records")

def save_locked_results(results):
    """
    Single source of truth:
    owners/core/alt/chaos/survivors are saved after every completed blend.
    Recap reads this, not feeder rows.
    """
    payload = {
        "saved_at_et": datetime.now(ZoneInfo("America/New_York")).isoformat(),
        "owners": _jsonable_records(results.get("owners", pd.DataFrame())),
        "core": _jsonable_records(results.get("core", pd.DataFrame())),
        "alt": _jsonable_records(results.get("alt", pd.DataFrame())),
        "chaos": _jsonable_records(results.get("chaos", pd.DataFrame())),
        "survivors": _jsonable_records(results.get("survivors", pd.DataFrame())),
    }
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass
    return payload

def load_locked_results():
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return {"owners":pd.DataFrame(), "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":pd.DataFrame()}
    return {
        "owners": pd.DataFrame(payload.get("owners", [])),
        "core": pd.DataFrame(payload.get("core", [])),
        "alt": pd.DataFrame(payload.get("alt", [])),
        "chaos": pd.DataFrame(payload.get("chaos", [])),
        "survivors": pd.DataFrame(payload.get("survivors", [])),
        "saved_at_et": payload.get("saved_at_et")
    }


def build_tickets_from_owners(owners, survivors):
    if owners is None or owners.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    owners = owners[owners["official_core_role"].fillna("") != "NO PLAY"].copy() if "official_core_role" in owners.columns else owners.copy()
    if owners.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    owners = owners.sort_values("score", ascending=False).drop_duplicates(subset=["player","team","pitcher"], keep="first").reset_index(drop=True)

    primary_pool = owners[owners["official_core_role"].eq("Primary")].copy()
    adjacent_pool = owners[owners["official_core_role"].eq("Adjacent")].copy()
    who_pool = owners[owners["official_core_role"].eq("WHO")].copy()

    core = pd.concat([primary_pool, adjacent_pool, who_pool, owners], ignore_index=True).drop_duplicates(subset=["player","team","pitcher"]).head(3).copy()
    core["ticket_role"] = "CORE"

    used = set(core["player"].astype(str)) if not core.empty else set()
    alt_pool = pd.concat([adjacent_pool, primary_pool, owners], ignore_index=True).drop_duplicates(subset=["player","team","pitcher"])
    alt_pool = alt_pool[~alt_pool["player"].astype(str).isin(used)]
    alt = alt_pool.head(3).copy()
    if not alt.empty:
        alt["ticket_role"] = "ALT"
        used.update(alt["player"].astype(str))

    chaos_pool = pd.concat([who_pool, owners], ignore_index=True).drop_duplicates(subset=["player","team","pitcher"])
    chaos_pool = chaos_pool[~chaos_pool["player"].astype(str).isin(used)]
    chaos = chaos_pool.head(3).copy()
    if not chaos.empty:
        chaos["ticket_role"] = "WHO"

    return core, alt, chaos





def fetch_live_public_slate(date_iso=None):
    """
    Safe optional public slate loader. It must NEVER crash the app.
    """
    if date_iso is None:
        date_iso = datetime.now(ZoneInfo("America/New_York")).date().isoformat()

    rows = []
    meta = {"source":"MLB Stats API", "date":date_iso, "games":0, "rows":0}

    try:
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_iso}&hydrate=probablePitcher,team"
        with urllib.request.urlopen(url, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        meta["error"] = str(e)
        return pd.DataFrame(), meta

    try:
        for d in data.get("dates", []):
            for g in d.get("games", []):
                teams = g.get("teams", {})
                away = teams.get("away", {}).get("team", {}).get("name", "")
                home = teams.get("home", {}).get("team", {}).get("name", "")
                away_p = teams.get("away", {}).get("probablePitcher", {}).get("fullName", "")
                home_p = teams.get("home", {}).get("probablePitcher", {}).get("fullName", "")
                game_pk = g.get("gamePk", "")
                game_key = canonical_game_key(away, home, home_p, f"{away} vs {home}")

                rows.append({"game_pk":game_pk,"game_key":game_key,"game":f"{away} vs {home}","team":away,"opponent":home,"pitcher":home_p,"player":"","source":"PUBLIC_SLATE"})
                rows.append({"game_pk":game_pk,"game_key":game_key,"game":f"{away} vs {home}","team":home,"opponent":away,"pitcher":away_p,"player":"","source":"PUBLIC_SLATE"})
    except Exception as e:
        meta["error"] = f"parse error: {e}"
        return pd.DataFrame(), meta

    df = pd.DataFrame(rows)
    if not df.empty:
        df = normalize_game_frame(df)
    meta["games"] = int(df["game_key"].nunique()) if not df.empty and "game_key" in df.columns else 0
    meta["rows"] = int(len(df))
    return df, meta



def merge_public_context(feed_df, public_df):
    """
    Public slate is only support context. If it fails, uploaded feed still runs.
    """
    try:
        if feed_df is None or getattr(feed_df, "empty", True):
            return public_df.copy() if public_df is not None else pd.DataFrame()

        feed = normalize_game_frame(feed_df)
        if public_df is None or getattr(public_df, "empty", True):
            return feed

        pub = normalize_game_frame(public_df)
        if pub.empty or "team" not in pub.columns:
            return feed

        context_cols = [c for c in ["team","opponent","pitcher","game","game_key"] if c in pub.columns]
        context = pub.drop_duplicates(subset=["team"])[context_cols].copy()
        merged = feed.merge(context, on="team", how="left", suffixes=("", "_pub"))

        for c in ["opponent","pitcher","game","game_key"]:
            pc = c + "_pub"
            if pc in merged.columns:
                if c not in merged.columns:
                    merged[c] = ""
                current = merged[c].astype(str).str.strip()
                merged[c] = merged[c].where(current.ne("") & merged[c].notna(), merged[pc])
                merged = merged.drop(columns=[pc])
        return normalize_game_frame(merged)
    except Exception:
        return normalize_game_frame(feed_df) if feed_df is not None else pd.DataFrame()


def hr_model_confirm(r):
    pull=safe_num(r.get("pull_pct"))
    barrel=safe_num(r.get("barrel_pct"))
    hh=safe_num(r.get("hard_hit_pct"))
    sweet=safe_num(r.get("sweet_spot_pct"))
    dmg=safe_num(r.get("dmg"))
    hpi=safe_num(r.get("hpi"))
    hrpa=safe_num(r.get("hr_pa"))
    pe=safe_num(r.get("pitch_edge"))
    checks = {
        "pull_priority": pull >= 40,
        "barrel": barrel >= 10 if not pd.isna(r.get("barrel_pct")) else False,
        "sweet_spot": sweet >= 24,
        "pitch_type_edge": pe >= 0,
        "dmg": dmg >= 1.5,
        "hpi": hpi >= 35,
        "conversion": hrpa >= 1.5 or dmg >= 1.5 or hpi >= 35,
        "not_chalk_trap": not bool(r.get("chalk_trap", False)),
    }
    passed = sum(bool(v) for v in checks.values())
    if not checks["barrel"] and hh >= 40:
        passed += 1
    return passed >= 5, checks


def run_true_blender(df):
    df = normalize_game_frame(auto_enrich_feed(df))
    if df is None or df.empty:
        empty = {"owners":pd.DataFrame(), "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":pd.DataFrame()}
        save_locked_results(empty)
        return empty

    owners=[]
    survivors=[]
    for game,gdf in df.groupby("game_key", dropna=False):
        alive=run_game(gdf)
        if alive.empty:
            continue
        survivors.append(alive.assign(game_owner=game))
        top = alive.iloc[0].to_dict()
        if top.get("official_core_role") != "NO PLAY":
            owners.append(top)

    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    survivors=pd.concat(survivors, ignore_index=True) if survivors else pd.DataFrame()

    if owners.empty:
        results={"owners":owners,"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":survivors}
        save_locked_results(results)
        return results

    owners=owners.sort_values("score", ascending=False).drop_duplicates(subset=["player","team","pitcher"], keep="first").reset_index(drop=True)
    core, alt, chaos = build_tickets_from_owners(owners, survivors)

    results={"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors}
    save_locked_results(results)
    return results


def csv_bytes(df):
    if df is None or df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")

def fetch_mlb_hr_hitters_today():
    # Public MLB Stats API. No login. Pulls completed games for today's NY date.
    now_et = datetime.now(ZoneInfo("America/New_York"))
    target_date = now_et.date() - timedelta(days=1) if now_et.hour < 8 else now_et.date()
    today = target_date.isoformat()
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today}&hydrate=boxscore"
    try:
        with urllib.request.urlopen(url, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return set(), {"source":"MLB Stats API", "date":today, "error":"fetch_failed"}

    hitters = set()
    for date in data.get("dates", []):
        for game in date.get("games", []):
            box = game.get("boxscore", {})
            for side in ["home","away"]:
                players = box.get("teams", {}).get(side, {}).get("players", {})
                for _, p in players.items():
                    stats = p.get("stats", {}).get("batting", {})
                    if stats.get("homeRuns", 0):
                        hitters.add(p.get("person", {}).get("fullName",""))
    return hitters, {"source":"MLB Stats API", "date":today, "count":len(hitters)}

def run_recap_check(results=None):
    """
    Recap reads locked ticket owners only:
    core + alt + chaos if available, otherwise locked owners.
    Never feeder rows. Never survivors.
    """
    if results is None or not isinstance(results, dict) or results.get("owners", pd.DataFrame()).empty:
        results = load_locked_results()

    hitters, meta = fetch_mlb_hr_hitters_today()

    frames = []
    for ticket_name in ["core", "alt", "chaos"]:
        part = results.get(ticket_name, pd.DataFrame())
        if part is not None and not part.empty:
            temp = part.copy()
            temp["ticket_group"] = ticket_name.upper()
            frames.append(temp)

    if frames:
        recap = pd.concat(frames, ignore_index=True)
    else:
        owners = results.get("owners", pd.DataFrame())
        if owners is None or owners.empty:
            return pd.DataFrame(), meta
        recap = owners.copy()
        recap["ticket_group"] = "OWNERS"

    # Remove any fake descriptor rows before recap.
    if "player" in recap.columns:
        recap = recap[~recap["player"].astype(str).str.strip().str.match(r"^(Low Effort|Medium Effort|High Effort|Effort|Fresh|Moderate|Elevated)$", case=False, na=False)].copy()

    recap = recap.drop_duplicates(subset=[c for c in ["player","team","pitcher"] if c in recap.columns], keep="first").copy()
    recap["hit_hr"] = recap["player"].isin(hitters)
    recap["recap_source"] = meta.get("source")
    recap["recap_date"] = meta.get("date")

    try:
        prior = pd.read_csv(RECAP_LOG_FILE)
        out = pd.concat([prior, recap], ignore_index=True)
    except Exception:
        out = recap
    try:
        out.to_csv(RECAP_LOG_FILE, index=False)
    except Exception:
        pass

    return recap, meta
