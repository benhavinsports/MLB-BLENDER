
import pandas as pd
import urllib.request, json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def safe_num(x, default=0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default

def archetype(r):
    pull=safe_num(r.get("pull_pct"))
    pe=safe_num(r.get("pitch_edge"))
    dmg=safe_num(r.get("dmg"))
    hrpa=safe_num(r.get("hr_pa"))
    hpi=safe_num(r.get("hpi"))
    sweet=safe_num(r.get("sweet_spot_pct"))
    slot=safe_num(r.get("lineup_slot"), None)
    weak_slots=str(r.get("weak_slots",""))
    in_weak = slot is not None and str(int(slot)) in weak_slots.split(",")

    if (r.get("weak_slot_tag") or in_weak) and (dmg >= 1.1 or hrpa >= 2.0):
        return "Adjacent / Weak-Slot Transfer"
    if dmg >= 2.0 and (hrpa >= 3.5 or bool(r.get("hr_alert"))):
        return "WHO / Chaos Finisher"
    if pe >= 12:
        return "Pitch-Type Punisher"
    if pull >= 30 and sweet >= 26:
        return "Pull-Air Primary"
    if hpi >= 42 and dmg >= 1.0:
        return "Elite Primary Converter"
    if bool(r.get("platoon")) and pe >= 0:
        return "Adjacent Platoon Lever"
    if bool(r.get("hr_alert")):
        return "Alert Converter"
    return "Primary HR Owner"

def role_bucket(r):
    a = str(r.get("archetype","")).lower()
    if "who" in a or "chaos" in a:
        return "WHO"
    if "adjacent" in a or "transfer" in a or "weak-slot" in a or "platoon lever" in a:
        return "Adjacent"
    return "Primary"

def blend_score(r):
    pull=max(0,(safe_num(r.get("pull_pct"))-14)*2.4)
    pe=38 if pd.isna(r.get("pitch_edge")) else max(0,55+safe_num(r.get("pitch_edge"))*1.35)
    dmg=max(0,safe_num(r.get("dmg"))*31)
    hrpa=max(0,safe_num(r.get("hr_pa"))*15)
    hpi=max(0,safe_num(r.get("hpi"))*1.7)
    sweet=max(0,(safe_num(r.get("sweet_spot_pct"))-15)*3.0)
    hh=max(0,safe_num(r.get("hard_hit_pct")))
    s = pull*.14 + pe*.15 + dmg*.18 + hrpa*.17 + hpi*.15 + sweet*.12 + hh*.04
    if r.get("weak_slot_tag"): s += 7
    if r.get("hr_alert"): s += 8
    if r.get("cond_up"): s += 4
    if r.get("laser"): s += 4
    if r.get("rakes"): s += 4
    if r.get("platoon"): s += 2
    if str(r.get("team","")).lower() in {"","unknown team"}: s -= 8
    if str(r.get("pitcher","")).lower() in {"","unknown pitcher"}: s -= 8
    return round(max(0,min(100,s)),1)

def gate_path(r):
    gates = []
    gates.append("1 Legal hitter")
    gates.append("2 Pull-air pass" if pd.isna(r.get("pull_pct")) or safe_num(r.get("pull_pct")) >= 20 else "2 Pull-air weak")
    gates.append("3 Damage pass" if pd.isna(r.get("dmg")) or safe_num(r.get("dmg")) >= .5 or r.get("hr_alert") else "3 Damage weak")
    gates.append("4 Pitch-edge pass" if pd.isna(r.get("pitch_edge")) or safe_num(r.get("pitch_edge")) >= 0 else "4 Pitch-edge weak")
    gates.append("5 Lane/slot checked")
    gates.append("6 HR conversion pass" if pd.isna(r.get("hr_pa")) or safe_num(r.get("hr_pa")) >= 2 or r.get("hr_alert") else "6 HR conversion weak")
    gates += ["7 Launch checked","8 Condition checked","9 Lineup checked","10 Book decoy checked","10.5 Transfer checked","11 Mistake lane checked","12 Bullpen checked","13 Numerology tie-only","14 WHO checked","15 Finisher checked","16 Owner isolated","17 No revival","18 Final lock"]
    return " | ".join(gates)

def run_game(gdf):
    alive = gdf.copy()
    alive["archetype"] = alive.apply(archetype, axis=1)
    alive["official_core_role"] = alive.apply(role_bucket, axis=1)
    alive["score"] = alive.apply(blend_score, axis=1)
    alive["gate_path"] = alive.apply(gate_path, axis=1)

    filters = [
        alive["pull_pct"].isna() | (alive["pull_pct"] >= 20),
        alive["pitch_edge"].isna() | (alive["pitch_edge"] >= 0),
        alive["sweet_spot_pct"].isna() | (alive["sweet_spot_pct"] >= 23),
        alive["hr_pa"].isna() | (alive["hr_pa"] >= 2) | alive["hr_alert"],
        alive["dmg"].isna() | (alive["dmg"] >= .5) | alive["hr_alert"],
        alive["hpi"].isna() | (alive["hpi"] >= 16) | alive["hr_alert"],
    ]
    for mask in filters:
        if len(alive) > 1 and mask.any():
            next_alive = alive[mask].copy()
            if not next_alive.empty:
                alive = next_alive
    return alive.sort_values("score", ascending=False)


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

    owners = owners.sort_values("score", ascending=False).reset_index(drop=True)

    # Natural output: no hard forcing, but keep clean ticket lanes from actual final owners.
    core = owners.head(3).copy()
    if not core.empty:
        core["ticket_role"] = core.get("official_core_role", "Core")

    alt = owners.iloc[3:6].copy()
    if not alt.empty:
        alt["ticket_role"] = "ALT"

    chaos_pool = survivors.copy() if survivors is not None and not survivors.empty else owners.copy()
    if chaos_pool is None or chaos_pool.empty:
        chaos = pd.DataFrame()
    else:
        for col in ["score","dmg","hr_pa"]:
            if col not in chaos_pool:
                chaos_pool[col] = 0
        for col in ["weak_slot_tag","hr_alert"]:
            if col not in chaos_pool:
                chaos_pool[col] = False
        if "official_core_role" not in chaos_pool:
            chaos_pool["official_core_role"] = ""
        chaos_pool["_chaos_score"] = (
            chaos_pool["score"].fillna(0)*.35
            + chaos_pool["dmg"].fillna(0)*20
            + chaos_pool["hr_pa"].fillna(0)*7
            + chaos_pool["weak_slot_tag"].fillna(False).astype(int)*15
            + chaos_pool["hr_alert"].fillna(False).astype(int)*12
            + (chaos_pool["official_core_role"]=="WHO").astype(int)*18
        )
        chaos = chaos_pool.sort_values("_chaos_score", ascending=False).drop(columns=["_chaos_score"]).head(3).copy()
        chaos["ticket_role"] = "WHO"

    return core, alt, chaos

def run_true_blender(df):
    df = auto_enrich_feed(df)
    if df is None or df.empty:
        empty = {"owners":pd.DataFrame(), "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":pd.DataFrame()}
        save_locked_results(empty)
        return empty

    owners = []
    survivors = []
    for game, gdf in df.groupby("game", dropna=False):
        alive = run_game(gdf)
        if alive.empty:
            continue
        alive = alive.sort_values("score", ascending=False).reset_index(drop=True)
        survivors.append(alive.assign(game_owner=game))
        owners.append(alive.iloc[0].to_dict())

    owners = pd.DataFrame(owners) if owners else pd.DataFrame()
    survivors = pd.concat(survivors, ignore_index=True) if survivors else pd.DataFrame()

    if owners.empty:
        results = {"owners":owners, "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":survivors}
        save_locked_results(results)
        return results

    owners = owners.sort_values("score", ascending=False).reset_index(drop=True)
    core, alt, chaos = build_tickets_from_owners(owners, survivors)

    results = {"owners":owners, "core":core, "alt":alt, "chaos":chaos, "survivors":survivors}
    save_locked_results(results)
    return results

def csv_bytes(df):
    if df is None or df.empty:
        return b""
    return df.to_csv(index=False).encode("utf-8")

def fetch_mlb_hr_hitters_today():
    # Public MLB Stats API. No login. Pulls completed games for today's NY date.
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
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
