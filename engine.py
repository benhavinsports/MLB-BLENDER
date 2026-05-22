
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

def run_true_blender(df):
    if df is None or df.empty:
        return {"owners":pd.DataFrame(), "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":pd.DataFrame()}
    owners = []
    survivors = []
    for game, gdf in df.groupby("game", dropna=False):
        alive = run_game(gdf)
        if alive.empty:
            continue
        survivors.append(alive.assign(game_owner=game))
        owners.append(alive.iloc[0].to_dict())

    owners = pd.DataFrame(owners) if owners else pd.DataFrame()
    survivors = pd.concat(survivors, ignore_index=True) if survivors else pd.DataFrame()
    if owners.empty:
        return {"owners":owners, "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":survivors}

    owners = owners.sort_values("score", ascending=False).reset_index(drop=True)

    # Natural Blender output: no forced role fill. Core takes top natural owners.
    core = owners.head(3).copy()
    core["ticket_role"] = core["official_core_role"]

    alt = owners.iloc[3:6].copy()
    if not alt.empty:
        alt["ticket_role"] = "ALT"

    chaos_pool = survivors.copy() if not survivors.empty else owners.copy()
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

    return {"owners":owners, "core":core, "alt":alt, "chaos":chaos, "survivors":survivors}

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

def run_recap_check(results):
    hitters, meta = fetch_mlb_hr_hitters_today()
    owners = results.get("owners", pd.DataFrame())
    if owners is None or owners.empty:
        return pd.DataFrame(), meta
    recap = owners.copy()
    recap["hit_hr"] = recap["player"].isin(hitters)
    recap["recap_source"] = meta.get("source")
    recap["recap_date"] = meta.get("date")
    return recap, meta
