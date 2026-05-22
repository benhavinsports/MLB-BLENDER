
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
    """
    Real archetype comes from gate behavior, not labels.
    """
    pull=safe_num(r.get("pull_pct"))
    pe=safe_num(r.get("pitch_edge"))
    dmg=safe_num(r.get("dmg"))
    hrpa=safe_num(r.get("hr_pa"))
    hpi=safe_num(r.get("hpi"))
    sweet=safe_num(r.get("sweet_spot_pct"))
    hh=safe_num(r.get("hard_hit_pct"))
    slot=safe_num(r.get("lineup_slot"), None)
    weak_slots=str(r.get("weak_slots",""))
    in_weak = slot is not None and str(int(slot)) in [x.strip() for x in weak_slots.split(",") if x.strip()]

    # WHO must be chaos/entropy, not random.
    if (bool(r.get("hr_alert")) or dmg >= 2.0 or hrpa >= 3.5) and (in_weak or bool(r.get("weak_slot_tag")) or pe >= 8):
        return "WHO / Chaos Finisher"

    # Adjacent is transfer/weak-slot/platoon leverage, not just second-best.
    if (in_weak or bool(r.get("weak_slot_tag")) or bool(r.get("platoon"))) and (pull >= 18 or sweet >= 24 or pe >= 0):
        return "Adjacent / Weak-Slot Transfer"

    if pe >= 12 and (pull >= 18 or hpi >= 20):
        return "Pitch-Type Punisher"

    if pull >= 24 and sweet >= 25 and hrpa >= 1.4:
        return "Elite Converter"

    if hpi >= 35 and dmg >= 0.8:
        return "Primary HR Owner"

    if bool(r.get("laser")) or bool(r.get("rakes")):
        return "Launch Pressure"

    return "Primary HR Owner"



def role_bucket(r):
    a = str(r.get("archetype","")).lower()
    if "who" in a or "chaos" in a:
        return "WHO"
    if "adjacent" in a or "transfer" in a or "weak-slot" in a or "platoon" in a:
        return "Adjacent"
    return "Primary"



def blend_score(r):
    """
    Score is AFTER gate logic. It supports elimination, it does not replace it.
    """
    pull=safe_num(r.get("pull_pct"))
    sweet=safe_num(r.get("sweet_spot_pct"))
    hh=safe_num(r.get("hard_hit_pct"))
    dmg=safe_num(r.get("dmg"))
    hrpa=safe_num(r.get("hr_pa"))
    hpi=safe_num(r.get("hpi"))
    pe=safe_num(r.get("pitch_edge"))
    slot=safe_num(r.get("lineup_slot"), None)
    weak_slots=str(r.get("weak_slots",""))
    in_weak = slot is not None and str(int(slot)) in [x.strip() for x in weak_slots.split(",") if x.strip()]

    score = 0
    score += max(0, min(20, (pull-16)*1.15))
    score += max(0, min(16, (sweet-20)*1.20))
    score += max(0, min(12, hh*.35))
    score += max(0, min(18, dmg*9.0))
    score += max(0, min(16, hrpa*4.0))
    score += max(0, min(14, hpi*.35))
    score += max(0, min(12, pe*.65 + 4))

    if bool(r.get("hr_alert")): score += 8
    if bool(r.get("cond_up")): score += 4
    if bool(r.get("laser")): score += 3
    if bool(r.get("rakes")): score += 3
    if bool(r.get("platoon")): score += 3
    if bool(r.get("weak_slot_tag")) or in_weak: score += 7

    if str(r.get("team","")).strip().lower() in {"", "unknown team", "public feed"}: score -= 15
    if str(r.get("pitcher","")).strip().lower() in {"", "unknown pitcher", "today mlb slate"}: score -= 15
    if "weak" in str(r.get("gate_path","")).lower(): score -= 8

    return round(max(0, min(100, score)), 1)




def build_player_gate_path(r, owner_rank=None):
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

    parts = []
    parts.append("0 ENV OK")
    parts.append("1 REAL HITTER")
    parts.append("2 POOL OK")

    if pull >= 24 and sweet >= 25:
        parts.append(f"3 ELITE PULL-AIR {pull:.1f}/{sweet:.1f}")
    elif pull >= 20 or sweet >= 25:
        parts.append(f"3 PARTIAL AIR {pull:.1f}/{sweet:.1f}")
    else:
        parts.append(f"3 PULL-AIR WEAK {pull:.1f}/{sweet:.1f}")

    if dmg >= 1.5 or bool(r.get("hr_alert")):
        parts.append(f"4 DAMAGE PASS {dmg:.1f}")
    elif dmg >= .7:
        parts.append(f"4 DAMAGE OK {dmg:.1f}")
    else:
        parts.append(f"4 DAMAGE WEAK {dmg:.1f}")

    if hrpa >= 3.0:
        parts.append(f"5 HR/PA ELITE {hrpa:.1f}")
    elif hrpa >= 1.4:
        parts.append(f"5 HR/PA PASS {hrpa:.1f}")
    else:
        parts.append(f"5 HR/PA WEAK {hrpa:.1f}")

    if pe >= 12:
        parts.append(f"6 PITCH EDGE FIRE {pe:.1f}")
    elif pe >= 0:
        parts.append(f"6 PITCH EDGE OK {pe:.1f}")
    else:
        parts.append(f"6 PITCH EDGE WEAK {pe:.1f}")

    if weak_slot or bool(r.get("weak_slot_tag")):
        parts.append(f"7 SLOT/TRANSFER BOOST {int(slot) if slot is not None else '-'}")
    else:
        parts.append(f"7 SLOT CHECK {int(slot) if slot is not None else '-'}")

    if hpi >= 35:
        parts.append(f"8 CONVERSION HIGH {hpi:.1f}")
    elif hpi >= 18:
        parts.append(f"8 CONVERSION OK {hpi:.1f}")
    else:
        parts.append(f"8 CONVERSION WEAK {hpi:.1f}")

    if bool(r.get("hr_alert")):
        parts.append("9 HR ALERT ON")
    elif bool(r.get("cond_up")):
        parts.append("9 CONDITION UP")
    else:
        parts.append("9 CONDITION NEUTRAL")

    role = r.get("official_core_role","") or role_bucket(r)
    arch = r.get("archetype","") or archetype(r)
    parts.append(f"10.5 ROLE {role}")
    parts.append(f"11 ARCH {arch}")

    if owner_rank is not None:
        if owner_rank == 1:
            parts.append("12 GAME OWNER LOCKED")
        else:
            parts.append(f"12 SURVIVOR RANK {owner_rank}")

    return " | ".join(parts)



def gate_path(r):
    return build_player_gate_path(r)



def run_game(gdf):
    alive = gdf.copy()
    if alive.empty:
        return alive

    metric_cols = ["pull_pct","sweet_spot_pct","dmg","hr_pa","hpi","pitch_edge"]
    for col in metric_cols:
        if col not in alive:
            alive[col] = None

    alive["archetype"] = alive.apply(archetype, axis=1)
    alive["official_core_role"] = alive.apply(role_bucket, axis=1)

    alive["_metric_count"] = alive[metric_cols].notna().sum(axis=1)
    alive["_pull_launch"] = (alive["pull_pct"].fillna(0) >= 20) | (alive["sweet_spot_pct"].fillna(0) >= 25)
    alive["_damage_conversion"] = (alive["dmg"].fillna(0) >= .7) | (alive["hr_pa"].fillna(0) >= 1.4) | alive["hr_alert"].fillna(False)
    alive["_pitch_lane"] = (alive["pitch_edge"].fillna(0) >= 0) | alive["hr_alert"].fillna(False)
    alive["_conversion_intent"] = (alive["hpi"].fillna(0) >= 18) | alive["hr_alert"].fillna(False) | (alive["dmg"].fillna(0) >= 1.5)

    def apply_gate(pool, mask):
        if pool.empty or len(pool) <= 1:
            return pool
        mask = mask.reindex(pool.index).fillna(False)
        if mask.any():
            return pool[mask].copy()
        return pool

    alive = apply_gate(alive, alive["_metric_count"] >= 3)
    alive = apply_gate(alive, alive["_pull_launch"])
    alive = apply_gate(alive, alive["_damage_conversion"])
    alive = apply_gate(alive, alive["_pitch_lane"])
    alive = apply_gate(alive, alive["_conversion_intent"])

    slot_vals = alive["lineup_slot"].fillna(-1).astype(float).astype(int).astype(str)
    weak_text = alive["weak_slots"].fillna("").astype(str)
    weak_match = [slot_vals.iloc[i] in [x.strip() for x in weak_text.iloc[i].split(",") if x.strip()] for i in range(len(alive))]
    alive["_weak_match"] = weak_match
    alive["_transfer_score"] = (
        alive["_weak_match"].astype(int)*12
        + alive["weak_slot_tag"].fillna(False).astype(int)*10
        + alive["platoon"].fillna(False).astype(int)*4
    )

    alive["score"] = alive.apply(blend_score, axis=1)
    alive["archetype"] = alive.apply(archetype, axis=1)
    alive["official_core_role"] = alive.apply(role_bucket, axis=1)

    alive["_owner_score"] = (
        alive["score"].fillna(0)
        + alive["_transfer_score"].fillna(0)
        + alive["hr_alert"].fillna(False).astype(int)*5
        + (alive["official_core_role"]=="WHO").astype(int)*3
    )

    alive = alive.sort_values("_owner_score", ascending=False).reset_index(drop=True)
    alive["gate_path"] = [build_player_gate_path(row, owner_rank=i+1) for i, row in alive.iterrows()]

    drop_cols=["_owner_score","_transfer_score","_weak_match","_metric_count","_pull_launch","_damage_conversion","_pitch_lane","_conversion_intent"]
    return alive.drop(columns=[c for c in drop_cols if c in alive.columns])


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

    owners = owners.sort_values("score", ascending=False).drop_duplicates(subset=["player","team","pitcher"], keep="first").reset_index(drop=True)

    core = owners.head(3).copy()
    if not core.empty:
        core["ticket_role"] = core.get("official_core_role", "CORE")

    used = set(core["player"].astype(str).tolist()) if not core.empty else set()

    alt_pool = owners[~owners["player"].astype(str).isin(used)].copy()
    alt = alt_pool.head(3).copy()
    if not alt.empty:
        alt["ticket_role"] = "ALT"
        used.update(alt["player"].astype(str).tolist())

    chaos_pool = survivors.copy() if survivors is not None and not survivors.empty else owners.copy()
    if chaos_pool is None or chaos_pool.empty:
        chaos = pd.DataFrame()
    else:
        chaos_pool = chaos_pool[~chaos_pool["player"].astype(str).isin(used)].copy()
        if chaos_pool.empty:
            chaos_pool = survivors.copy() if survivors is not None and not survivors.empty else owners.copy()

        for col in ["score","dmg","hr_pa"]:
            if col not in chaos_pool:
                chaos_pool[col]=0
        for col in ["weak_slot_tag","hr_alert"]:
            if col not in chaos_pool:
                chaos_pool[col]=False
        if "official_core_role" not in chaos_pool:
            chaos_pool["official_core_role"]=""

        chaos_pool["_chaos_score"] = (
            chaos_pool["score"].fillna(0)*.35
            + chaos_pool["dmg"].fillna(0)*20
            + chaos_pool["hr_pa"].fillna(0)*7
            + chaos_pool["weak_slot_tag"].fillna(False).astype(int)*15
            + chaos_pool["hr_alert"].fillna(False).astype(int)*12
            + (chaos_pool["official_core_role"]=="WHO").astype(int)*18
        )
        chaos = chaos_pool.sort_values("_chaos_score", ascending=False).drop_duplicates(subset=["player","team","pitcher"], keep="first").drop(columns=["_chaos_score"]).head(3).copy()
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
        owners.append(alive.iloc[0].to_dict())

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
