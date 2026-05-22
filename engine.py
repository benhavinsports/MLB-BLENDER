
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

    pull_air = pull >= 20 or (sweet >= 30 and pull >= 14)
    damage = dmg >= .8 or hrpa >= 1.6
    pitch = pe >= 0
    conversion = hpi >= 20 or hrpa >= 2.5 or dmg >= 1.5
    launch = sweet >= 24 or pull >= 24
    transfer = weak_slot or bool(r.get("weak_slot_tag")) or bool(r.get("platoon"))
    chaos = bool(r.get("hr_alert")) and damage and (transfer or pe >= 0 or hrpa >= 3.0)

    clean_owner = real_metrics >= 4 and pull_air and damage and pitch and conversion and launch
    adjacent_owner = real_metrics >= 4 and transfer and damage and pitch and conversion and (pull_air or launch)
    who_owner = real_metrics >= 4 and chaos and damage and conversion and pitch

    return {
        "real_metrics": real_metrics >= 4,
        "pull_air": pull_air,
        "damage": damage,
        "pitch": pitch,
        "conversion": conversion,
        "launch": launch,
        "transfer": transfer,
        "chaos": chaos,
        "weak_slot": weak_slot,
        "clean_owner": clean_owner,
        "adjacent_owner": adjacent_owner,
        "who_owner": who_owner,
    }



def gate_fail_reason(gates):
    for g in ["real_metrics","pull_air","damage","pitch","conversion","launch"]:
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
    parts = [
        "0 ENV CHECKED",
        "1 METRICS PASS" if gates["real_metrics"] else "1 METRICS FAIL",
        f"2 PULL-AIR {'PASS' if gates['pull_air'] else 'KILL'} {pull:.1f}/{sweet:.1f}",
        f"3 DAMAGE {'PASS' if gates['damage'] else 'KILL'} {dmg:.1f}",
        f"4 PITCH {'PASS' if gates['pitch'] else 'KILL'} {pe:.1f}",
        f"5 CONVERSION {'PASS' if gates['conversion'] else 'KILL'} {hpi:.1f}",
        f"6 HR/PA {hrpa:.1f}",
        "7 TRANSFER ACTIVE" if gates["transfer"] else "7 TRANSFER OFF",
        "8 CHAOS ACTIVE" if gates["chaos"] else "8 CHAOS OFF",
        f"9 ROLE {r.get('official_core_role','') or role_bucket(r)}",
        f"10 ARCH {r.get('archetype','') or archetype(r)}",
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

    owners = owners[owners.get("official_core_role","") != "NO PLAY"].copy()
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



def run_true_blender(df):
    df = auto_enrich_feed(df)
    if df is None or df.empty:
        empty = {"owners":pd.DataFrame(), "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":pd.DataFrame()}
        save_locked_results(empty)
        return empty

    owners=[]
    survivors=[]
    for game,gdf in df.groupby("game", dropna=False):
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

    recap = recap.drop_duplicates(subset=["player","team","pitcher"], keep="first").copy()
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
