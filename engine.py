from pathlib import Path
import urllib.parse
import io
import re
import json
import urllib.request
import pandas as pd
import urllib.request, json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
RECAP_LOG_FILE = DATA_DIR / "recap_log.csv"

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
        right = text.split(" vs ", 1)[1]
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
    out["game_key"] = out.apply(
        lambda r: canonical_game_key(r.get("team",""), r.get("opponent",""), r.get("pitcher",""), r.get("game","")),
        axis=1
    )
    out["game"] = out.apply(
        lambda r: r.get("game") if str(r.get("game","")).strip() else f"{r.get('team','')} vs {r.get('pitcher','')}",
        axis=1
    )
    return out.drop_duplicates(subset=["game_key","team","pitcher","player"], keep="first").reset_index(drop=True)

def actual_game_count(df):
    if df is None or getattr(df, "empty", True):
        return 0
    if "game_key" in df.columns:
        return int(df["game_key"].nunique())
    return int(df["game"].nunique()) if "game" in df.columns else 0

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


def fetch_live_public_slate(date_iso=None):
    if date_iso is None:
        date_iso = datetime.now(ZoneInfo("America/New_York")).date().isoformat()

    meta = {"source":"MLB Stats API", "date":date_iso, "games":0, "rows":0}
    rows = []

    try:
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_iso}&hydrate=probablePitcher,team"
        with urllib.request.urlopen(url, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        meta["error"] = str(e)
        return pd.DataFrame(), meta

    for d in data.get("dates", []):
        for g in d.get("games", []):
            try:
                teams = g.get("teams", {})
                away = teams.get("away", {}).get("team", {}).get("name", "")
                home = teams.get("home", {}).get("team", {}).get("name", "")
                away_p = teams.get("away", {}).get("probablePitcher", {}).get("fullName", "")
                home_p = teams.get("home", {}).get("probablePitcher", {}).get("fullName", "")
                game_pk = g.get("gamePk", "")
                game_key = canonical_game_key(away, home, home_p, f"{away} vs {home}")
                rows.append({"game_pk":game_pk,"game_key":game_key,"game":f"{away} vs {home}","team":away,"opponent":home,"pitcher":home_p,"player":"","source":"PUBLIC_SLATE"})
                rows.append({"game_pk":game_pk,"game_key":game_key,"game":f"{away} vs {home}","team":home,"opponent":away,"pitcher":away_p,"player":"","source":"PUBLIC_SLATE"})
            except Exception:
                continue

    df = pd.DataFrame(rows)
    if not df.empty:
        df = normalize_game_frame(df)
    meta["games"] = int(df["game_key"].nunique()) if not df.empty and "game_key" in df.columns else 0
    meta["rows"] = int(len(df))
    return df, meta



def merge_public_context(feed_df, public_df):
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
        try:
            return normalize_game_frame(feed_df)
        except Exception:
            return feed_df if feed_df is not None else pd.DataFrame()


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


# ===============================
# V77 TRUE 18-GATE ENGINE OVERRIDE
# ===============================

# -------------------- v78 LIVE + ADAPTIVE HELPERS --------------------
DEFAULT_GATE_WEIGHTS = {
    "pull": 1.25, "launch": 1.10, "damage": 1.20, "pitch": 1.25,
    "conversion": 1.15, "opportunity": .75, "chaos": .70, "gate19": 1.20
}


def grade_gate_board(gates):
    weights = load_adaptive_weights()
    key_map = {
        "5 Pull-air":"pull", "6 Launch/Sweet":"launch", "7 Damage/Barrel":"damage",
        "4 Pitch-type lane":"pitch", "8 Conversion DNA":"conversion", "9 Opportunity":"opportunity",
        "11 WHO/Chaos":"chaos", "19 HR model confirmation":"gate19"
    }
    score = 0.0
    max_score = 0.0
    hard_kill = False
    for name, passed, hard in gates:
        w = weights.get(key_map.get(name, ""), 1.0)
        max_score += w
        if passed: score += w
        elif hard: hard_kill = True
    return (round((score/max_score)*100, 1) if max_score else 0.0), hard_kill

def fetch_team_roster_hitters(team_id):
    try:
        url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/roster?rosterType=active"
        with urllib.request.urlopen(url, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rows = []
        for item in data.get("roster", []):
            if item.get("position", {}).get("abbreviation", "") == "P":
                continue
            person = item.get("person", {})
            rows.append({"player": person.get("fullName", ""), "mlb_id": person.get("id", "")})
        return rows
    except Exception:
        return []


def _safe_read_csv_url(url, timeout=20):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            raw = resp.read()
        return pd.read_csv(io.BytesIO(raw))
    except Exception:
        return pd.DataFrame()

def _coerce_pct(v):
    try:
        if pd.isna(v): return None
        s = str(v).replace("%","").strip()
        x = float(s)
        if 0 < x <= 1: x *= 100
        return x
    except Exception:
        return None

def _first_existing_col(df, aliases):
    low = {str(c).lower().strip(): c for c in df.columns}
    for a in aliases:
        if a.lower().strip() in low:
            return low[a.lower().strip()]
    return None

def _normalize_savant_batter_metrics(raw):
    if raw is None or raw.empty:
        return pd.DataFrame()
    out = pd.DataFrame()
    for target, aliases in FULL_LIVE_METRIC_ALIASES.items():
        col = _first_existing_col(raw, aliases)
        if col is not None:
            out[target] = raw[col]
    if "player" not in out.columns:
        return pd.DataFrame()
    if "mlb_id" not in out.columns:
        out["mlb_id"] = ""
    for c in ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct"]:
        if c in out.columns:
            out[c] = out[c].apply(_coerce_pct)
    for c in ["dmg","hr_pa","hpi"]:
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out.drop_duplicates(subset=["player"], keep="first")

def fetch_public_statcast_batter_metrics(year=None, min_pa=25):
    if year is None:
        year = datetime.now(ZoneInfo("America/New_York")).year
    selections = ",".join(["player_name","player_id","pa","b_home_run","barrel_batted_rate","hard_hit_percent","sweet_spot_percent","pull_percent","xba","xslg","xwoba"])
    urls = [
        "https://baseballsavant.mlb.com/leaderboard/custom?" + urllib.parse.urlencode({"year": year, "type": "batter", "filter": "", "min": min_pa, "selections": selections, "csv": "true"}),
        "https://baseballsavant.mlb.com/leaderboard/statcast?" + urllib.parse.urlencode({"type":"batter","year":year,"csv":"true"}),
    ]
    for url in urls:
        raw = _safe_read_csv_url(url)
        norm = _normalize_savant_batter_metrics(raw)
        if not norm.empty:
            try: norm.to_csv(SAVANT_BATTER_CACHE, index=False)
            except Exception: pass
            return norm
    try:
        if SAVANT_BATTER_CACHE.exists():
            return pd.read_csv(SAVANT_BATTER_CACHE)
    except Exception:
        pass
    return pd.DataFrame()

def enrich_with_live_batter_metrics(df, metrics_df=None):
    if df is None or getattr(df, "empty", True):
        return df
    out = df.copy()
    if metrics_df is None:
        metrics_df = fetch_public_statcast_batter_metrics()
    if metrics_df is None or metrics_df.empty or "player" not in metrics_df.columns:
        return out
    m = metrics_df.copy()
    m["_player_key"] = m["player"].astype(str).str.lower().str.replace(r"[^a-z ]","", regex=True).str.strip()
    out["_player_key"] = out["player"].astype(str).str.lower().str.replace(r"[^a-z ]","", regex=True).str.strip()
    cols = ["_player_key"] + [c for c in ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi"] if c in m.columns]
    merged = out.merge(m[cols].drop_duplicates("_player_key"), on="_player_key", how="left", suffixes=("", "_live"))
    for c in ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi"]:
        live = c + "_live"
        if live in merged.columns:
            if c not in merged.columns: merged[c] = None
            merged[c] = merged[c].where(merged[c].notna(), merged[live])
            merged = merged.drop(columns=[live])
    return merged.drop(columns=["_player_key"], errors="ignore")

def calculate_pitch_edge_from_context(df, pitcher_df=None):
    if df is None or getattr(df, "empty", True):
        return df
    out = df.copy()
    if "pitch_edge" not in out.columns:
        out["pitch_edge"] = None
    return out

def recalc_adaptive_weights_from_history():
    weights = dict(DEFAULT_GATE_WEIGHTS)
    try:
        if RECAP_LOG_FILE.exists():
            hist = pd.read_csv(RECAP_LOG_FILE)
            if "hit_hr" in hist.columns and len(hist) >= 8:
                hit = hist[hist["hit_hr"].astype(str).str.lower().isin(["true","1","yes"])]
                miss = hist[~hist.index.isin(hit.index)]
                def gap(col):
                    if col not in hist.columns or hit.empty or miss.empty: return 0
                    return pd.to_numeric(hit[col], errors="coerce").mean() - pd.to_numeric(miss[col], errors="coerce").mean()
                if gap("pull_pct") > 4: weights["pull"] += .25
                if gap("sweet_spot_pct") > 3: weights["launch"] += .20
                if gap("dmg") > .25: weights["damage"] += .25
                if gap("hpi") > 4: weights["conversion"] += .20
                if gap("pitch_edge") > 2: weights["pitch"] += .20
        ADAPTIVE_WEIGHTS_FILE.write_text(json.dumps(weights, indent=2))
    except Exception:
        pass
    return weights

def load_adaptive_weights():
    try:
        if ADAPTIVE_WEIGHTS_FILE.exists():
            saved = json.loads(ADAPTIVE_WEIGHTS_FILE.read_text())
            base = dict(DEFAULT_GATE_WEIGHTS)
            base.update({k: float(v) for k, v in saved.items() if k in base})
            return base
    except Exception:
        pass
    return recalc_adaptive_weights_from_history()

def fetch_live_public_hitter_pool(date_iso=None, max_hitters_per_team=9):
    slate, meta = fetch_live_public_slate(date_iso)
    if slate is None or slate.empty:
        return pd.DataFrame(), meta
    if date_iso is None:
        date_iso = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    team_ids = {}
    try:
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_iso}&hydrate=probablePitcher,team"
        with urllib.request.urlopen(url, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        for d in data.get("dates", []):
            for g in d.get("games", []):
                for side in ["away","home"]:
                    t = g.get("teams", {}).get(side, {}).get("team", {})
                    team_ids[t.get("name","")] = t.get("id")
    except Exception:
        pass
    rows = []
    for _, s in slate.iterrows():
        hitters = fetch_team_roster_hitters(team_ids.get(s.get("team","")))[:max_hitters_per_team] if team_ids.get(s.get("team","")) else []
        for idx, h in enumerate(hitters, 1):
            rows.append({"game": s.get("game",""), "game_key": s.get("game_key",""), "team": s.get("team",""), "opponent": s.get("opponent",""), "pitcher": s.get("pitcher",""), "player": h.get("player",""), "mlb_id": h.get("mlb_id",""), "lineup_slot": idx, "source": "LIVE_PUBLIC_POOL", "pull_pct": None, "sweet_spot_pct": None, "barrel_pct": None, "hard_hit_pct": None, "dmg": None, "hr_pa": None, "hpi": None, "pitch_edge": None})
    df = pd.DataFrame(rows)
    if not df.empty:
        df = normalize_game_frame(df)
        df = enrich_with_live_batter_metrics(df)
        df = calculate_pitch_edge_from_context(df)
    meta["hitter_rows"] = int(len(df)) if df is not None else 0
    meta["metric_rows"] = int(df[["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi"]].notna().any(axis=1).sum()) if df is not None and not df.empty else 0
    return df, meta

def rebuild_live_blender_feed(upload_df=None, public_context=None, use_live_pool=False):
    if upload_df is not None and not getattr(upload_df, "empty", True):
        df = merge_public_context(upload_df, public_context)
    elif use_live_pool:
        df, _ = fetch_live_public_hitter_pool()
    elif public_context is not None and not getattr(public_context, "empty", True):
        df = public_context.copy()
    else:
        df = pd.DataFrame()
    df = enrich_with_live_batter_metrics(df)
    df = calculate_pitch_edge_from_context(df)
    return normalize_game_frame(df) if df is not None and not df.empty else df

BLENDER_GATE_NAMES = [
    "0 Environment", "1 Pool legality", "2 Side lock", "3 Pitcher weakness", "4 Pitch-type lane",
    "5 Pull-air", "6 Launch/Sweet", "7 Damage/Barrel", "8 Conversion DNA", "9 Opportunity",
    "10 Hard-hit support", "10.5 Adjacent transfer", "11 WHO/Chaos", "12 Game script",
    "13 Recap DNA calibration", "14 Anti-chalk trap", "15 Bullpen continuation", "16 Finisher gate",
    "17 One-owner isolation", "18 Final lock", "19 HR model confirmation"
]

def is_player_name_safe(x):
    s=str(x or '').strip()
    bad={'low effort','medium effort','high effort','effort','fresh','moderate','elevated','hot','cold','home','away','cond','eats lhp','eats rhp'}
    return bool(s) and len(s)>2 and s.lower() not in bad and not s.replace('.','').isdigit()

def _present_v77(r,k):
    try:
        v=r.get(k)
        return v is not None and not pd.isna(v)
    except Exception:
        return False

def _slot_match_v77(r):
    slot=safe_num(r.get('lineup_slot'), None)
    weak=str(r.get('weak_slots',''))
    vals=[x.strip() for x in weak.split(',') if x.strip()]
    return slot is not None and str(int(slot)) in vals


def _present(r, k):
    try:
        v = r.get(k)
        return v is not None and not pd.isna(v)
    except Exception:
        return False

def _slot_match(r):
    try:
        slot = safe_num(r.get("lineup_slot"), None)
        weak = str(r.get("weak_slots", ""))
        vals = [x.strip() for x in weak.split(",") if x.strip()]
        return slot is not None and str(int(slot)) in vals
    except Exception:
        return False

def evaluate_18_gates(r):
    pull=safe_num(r.get("pull_pct")); sweet=safe_num(r.get("sweet_spot_pct"))
    barrel=safe_num(r.get("barrel_pct")); hh=safe_num(r.get("hard_hit_pct"))
    dmg=safe_num(r.get("dmg")); hrpa=safe_num(r.get("hr_pa"))
    hpi=safe_num(r.get("hpi")); pe=safe_num(r.get("pitch_edge"))
    slot=safe_num(r.get("lineup_slot"), None)
    weak_slot=_slot_match(r) or bool(r.get("weak_slot_tag"))
    platoon=bool(r.get("platoon")); alert=bool(r.get("hr_alert")); chalk=bool(r.get("chalk_trap", False))
    metrics=sum(_present(r,k) for k in ["pull_pct","sweet_spot_pct","dmg","hr_pa","hpi","pitch_edge"])
    env_ok=str(r.get("team","")).strip() not in ["","Unknown Team","Public Feed"] and str(r.get("pitcher","")).strip() not in ["","Unknown Pitcher","Today MLB Slate"]
    pool_ok=is_player_name_safe(r.get("player","")) and metrics>=4
    pitch=pe>=0 and _present(r, "pitch_edge")
    pull_air=pull>=40 or (pull>=28 and sweet>=28 and dmg>=1.4)
    launch=sweet>=24 or barrel>=10 or hh>=42
    damage=dmg>=1.5 or hrpa>=2.0 or alert
    conversion=hpi>=35 or hrpa>=1.5 or dmg>=1.5
    opp=slot is not None or weak_slot or platoon
    hh_support=hh>=38 or barrel>=8 or dmg>=1.5
    transfer=weak_slot or platoon or bool(r.get("adjacent_transfer"))
    chaos=alert and damage and conversion and pitch and (weak_slot or hrpa>=3.0 or dmg>=1.8)
    script=bool(r.get("cond_up")) or bool(r.get("environment_hot"))
    recap_dna=sum([pull>=40,dmg>=1.5,hpi>=35,hrpa>=1.5,sweet>=24])>=3
    anti=not chalk
    bullpen=not bool(r.get("bullpen_kill", False))
    finisher=pull_air and damage and conversion and pitch
    gate19=hr_model_confirm(r)[0] if "hr_model_confirm" in globals() else recap_dna
    gates=[
        ("0 Environment",env_ok,False),("1 Pool legality",pool_ok,True),("2 Side lock",env_ok,True),
        ("3 Pitcher weakness",pitch or alert or dmg>=1.8,True),("4 Pitch-type lane",pitch,True),
        ("5 Pull-air",pull_air,True),("6 Launch/Sweet",launch,True),("7 Damage/Barrel",damage,True),
        ("8 Conversion DNA",conversion,True),("9 Opportunity",opp,False),("10 Hard-hit support",hh_support,False),
        ("10.5 Adjacent transfer",transfer,False),("11 WHO/Chaos",chaos,False),("12 Game script",script,False),
        ("13 Recap DNA calibration",recap_dna,False),("14 Anti-chalk trap",anti,True),("15 Bullpen continuation",bullpen,False),
        ("16 Finisher gate",finisher,True),("17 One-owner isolation",True,True),("18 Final lock",True,True),
        ("19 HR model confirmation",gate19,True)
    ]
    hard=[n for n,p,h in gates if h and not p]
    soft=[n for n,p,h in gates if (not h) and not p]
    grade, hard_kill = grade_gate_board(gates)
    return {"gates":gates,"hard_failed":hard,"soft_failed":soft,"grade":grade,"hard_kill":hard_kill,
            "clean_owner":len(hard)==0,"adjacent_owner":len(hard)==0 and transfer and not chaos,"who_owner":len(hard)==0 and chaos}


def hard_gate_result(r):
    e=evaluate_18_gates(r)
    return {'real_metrics':'1 Pool legality' not in e['hard_failed'],'pull_air':'5 Pull-air' not in e['hard_failed'],
            'damage':'7 Damage/Barrel' not in e['hard_failed'],'pitch':'4 Pitch-type lane' not in e['hard_failed'],
            'conversion':'8 Conversion DNA' not in e['hard_failed'],'launch':'6 Launch/Sweet' not in e['hard_failed'],
            'gate19':'19 HR model confirmation' not in e['hard_failed'],'clean_owner':e['clean_owner'],
            'adjacent_owner':e['adjacent_owner'],'who_owner':e['who_owner'],'grade':e['grade'],
            'hard_failed':e['hard_failed'],'soft_failed':e['soft_failed'],'gate_board':e['gates']}

def gate_fail_reason(gates):
    return gates.get('hard_failed',[''])[0] if gates.get('hard_failed') else ''

def role_bucket(r):
    g=hard_gate_result(r)
    if g['who_owner']: return 'WHO'
    if g['adjacent_owner']: return 'Adjacent'
    if g['clean_owner']: return 'Primary'
    return 'NO PLAY'

def archetype(r):
    g=hard_gate_result(r)
    if not g['clean_owner']: return 'No Clean Owner'
    if g['who_owner']: return 'WHO / Chaos Finisher'
    if g['adjacent_owner']: return 'Adjacent / Transfer Owner'
    pull=safe_num(r.get('pull_pct')); dmg=safe_num(r.get('dmg')); hpi=safe_num(r.get('hpi')); pe=safe_num(r.get('pitch_edge')); hrpa=safe_num(r.get('hr_pa'))
    if pull>=40 and dmg>=1.5 and hpi>=35: return 'Elite Converter'
    if pe>=12: return 'Pitch-Type Punisher'
    if hrpa>=2.5: return 'Nuke Lane Finisher'
    return 'Primary HR Owner'

def blend_score(r):
    g=hard_gate_result(r)
    if not g['clean_owner']: return min(39.0,g['grade'])
    pull=safe_num(r.get('pull_pct')); sweet=safe_num(r.get('sweet_spot_pct')); barrel=safe_num(r.get('barrel_pct'))
    hh=safe_num(r.get('hard_hit_pct')); dmg=safe_num(r.get('dmg')); hrpa=safe_num(r.get('hr_pa')); hpi=safe_num(r.get('hpi')); pe=safe_num(r.get('pitch_edge'))
    score=min(18,max(0,(pull-25)*.9))+min(12,max(0,(sweet-20)*.8))+min(10,max(0,barrel*.7))+min(8,max(0,hh*.15))+min(18,dmg*7.5)+min(14,hrpa*3.2)+min(12,hpi*.28)+min(8,max(0,pe*.35+3))+g['grade']*.10
    if g.get('adjacent_owner'): score+=4
    if g.get('who_owner'): score+=5
    return round(max(0,min(100,score)),1)

def build_player_gate_path(r, owner_rank=None):
    e=evaluate_18_gates(r); parts=[]
    for name,passed,hard in e['gates']:
        mark='PASS' if passed else ('KILL' if hard else 'WEAK')
        parts.append(f'{name}: {mark}')
    parts.append('FINAL: GAME OWNER LOCKED' if e['clean_owner'] and owner_rank==1 else ('FINAL: SURVIVOR RANK '+str(owner_rank) if e['clean_owner'] and owner_rank else 'FINAL: NO PLAY / DEAD PROFILE'))
    return ' | '.join(parts)

def gate_path(r):
    return build_player_gate_path(r)

def run_game(gdf):
    pool=gdf.copy()
    if pool.empty: return pool
    for col in ['pull_pct','sweet_spot_pct','barrel_pct','hard_hit_pct','dmg','hr_pa','hpi','pitch_edge','lineup_slot','weak_slots']:
        if col not in pool: pool[col]=None
    pool['_gate_obj']=pool.apply(hard_gate_result,axis=1)
    pool['score']=pool.apply(blend_score,axis=1)
    pool['official_core_role']=pool.apply(role_bucket,axis=1)
    pool['archetype']=pool.apply(archetype,axis=1)
    pool['gate_grade']=pool['_gate_obj'].apply(lambda x:x.get('grade',0))
    pool['hard_fails']=pool['_gate_obj'].apply(lambda x:', '.join(x.get('hard_failed',[])))
    pool['soft_fails']=pool['_gate_obj'].apply(lambda x:', '.join(x.get('soft_failed',[])))
    alive=pool[pool['_gate_obj'].apply(lambda x:x.get('clean_owner',False))].copy()
    if alive.empty:
        dead=pool.sort_values(['gate_grade','score'],ascending=False).head(1).copy()
        dead['official_core_role']='NO PLAY'; dead['archetype']='No Clean Owner'; dead['score']=dead['score'].apply(lambda x:min(x,39.0))
        dead['gate_path']=[build_player_gate_path(row,None) for _,row in dead.iterrows()]
        return dead.drop(columns=[c for c in ['_gate_obj'] if c in dead.columns])
    alive['_owner_score']=alive['score']+alive['gate_grade']*.25
    alive=alive.sort_values('_owner_score',ascending=False).reset_index(drop=True)
    alive['gate_path']=[build_player_gate_path(row,i+1) for i,row in alive.iterrows()]
    return alive.drop(columns=[c for c in ['_gate_obj','_owner_score'] if c in alive.columns])

def build_tickets_from_owners(owners, survivors):
    if owners is None or owners.empty: return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    owners=owners.copy()
    if 'official_core_role' in owners.columns: owners=owners[owners['official_core_role'].fillna('')!='NO PLAY'].copy()
    if owners.empty: return pd.DataFrame(),pd.DataFrame(),pd.DataFrame()
    owners=owners.sort_values('score',ascending=False).drop_duplicates(subset=['player','team','pitcher'],keep='first').reset_index(drop=True)
    elite=owners[owners['archetype'].astype(str).str.contains('Elite|Primary|Pitch-Type|Nuke',case=False,na=False)]
    who=owners[owners['official_core_role'].eq('WHO') | owners['archetype'].astype(str).str.contains('WHO|Chaos',case=False,na=False)]
    stack=owners[owners['official_core_role'].eq('Adjacent') | owners['archetype'].astype(str).str.contains('Adjacent|Transfer',case=False,na=False)]
    core=pd.concat([elite.head(1),who.head(1),stack.head(1),owners],ignore_index=True).drop_duplicates(subset=['player','team','pitcher']).head(3).copy()
    if not core.empty: core['ticket_role']='CORE'
    used=set(core['player'].astype(str)) if not core.empty else set()
    alt=owners[~owners['player'].astype(str).isin(used)].head(3).copy()
    if not alt.empty:
        alt['ticket_role']='ALT'; used.update(alt['player'].astype(str))
    chaos=who[~who['player'].astype(str).isin(used)].head(3).copy()
    if chaos.empty: chaos=owners[~owners['player'].astype(str).isin(used)].head(3).copy()
    if not chaos.empty: chaos['ticket_role']='WHO'
    return core,alt,chaos

def run_true_blender(df):
    df = rebuild_live_blender_feed(upload_df=df)
    meta = {
        "input_rows": 0 if df is None else int(len(df)),
        "games": 0,
        "owners_locked": 0,
        "no_play_games": 0,
        "message": ""
    }
    if df is None or df.empty:
        meta["message"] = "No feed rows available."
        empty={"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"meta":meta}
        save_locked_results(empty)
        return empty

    try:
        meta["games"] = actual_game_count(df)
    except Exception:
        meta["games"] = int(df["game_key"].nunique()) if "game_key" in df.columns else int(df["game"].nunique()) if "game" in df.columns else 0

    owners=[]; survivors=[]; group_col="game_key" if "game_key" in df.columns else "game"
    for game,gdf in df.groupby(group_col,dropna=False):
        alive=run_game(gdf)
        if alive.empty:
            continue
        survivors.append(alive.assign(game_owner=game))
        top=alive.iloc[0].to_dict()
        if top.get("official_core_role")!="NO PLAY":
            owners.append(top)

    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    survivors=pd.concat(survivors,ignore_index=True) if survivors else pd.DataFrame()

    meta["owners_locked"] = int(len(owners))
    if not survivors.empty and "official_core_role" in survivors.columns:
        meta["no_play_games"] = int((survivors["official_core_role"].astype(str)=="NO PLAY").sum())

    if owners.empty:
        meta["message"] = "Blender ran, but no clean owners survived the hard gates. Game Board shows the KILL reasons."
        results={"owners":owners,"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":survivors,"meta":meta}
        save_locked_results(results)
        return results

    owners=owners.sort_values("score",ascending=False).drop_duplicates(subset=["player","team","pitcher"],keep="first").reset_index(drop=True)
    core,alt,chaos=build_tickets_from_owners(owners,survivors)
    meta["message"] = f"Blender complete: {len(owners)} owners locked from {meta['games']} games."
    results={"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"meta":meta}
    save_locked_results(results)
    return results



# ============================================================
# RESTORED LIVE/SPINNER FIX PATCH
# Keeps original live pull + UI behavior.
# Fixes dead slate, meta persistence, extra args TypeError.
# ============================================================

_LOCKED_ORIGINAL_RUN_TRUE_BLENDER = run_true_blender

def _bf_safe_df(x):
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()

def _bf_records(df):
    df = _bf_safe_df(df)
    if df.empty:
        return []
    safe = df.copy()
    for c in safe.columns:
        safe[c] = safe[c].apply(lambda x: None if pd.isna(x) else x)
    return safe.to_dict("records")

def save_locked_results(results):
    """Patched: save meta too, and save into data folder so Streamlit Cloud keeps path clean."""
    payload = {
        "saved_at_et": datetime.now(ZoneInfo("America/New_York")).isoformat(),
        "meta": results.get("meta", {}) if isinstance(results, dict) else {},
        "owners": _bf_records(results.get("owners", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()),
        "core": _bf_records(results.get("core", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()),
        "alt": _bf_records(results.get("alt", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()),
        "chaos": _bf_records(results.get("chaos", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()),
        "survivors": _bf_records(results.get("survivors", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()),
    }
    try:
        p = DATA_DIR / "locked_owners.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        pass
    return payload

def load_locked_results():
    try:
        p = DATA_DIR / "locked_owners.json"
        with open(p, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return {"owners":pd.DataFrame(), "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":pd.DataFrame(), "meta":{}}
    return {
        "owners": pd.DataFrame(payload.get("owners", [])),
        "core": pd.DataFrame(payload.get("core", [])),
        "alt": pd.DataFrame(payload.get("alt", [])),
        "chaos": pd.DataFrame(payload.get("chaos", [])),
        "survivors": pd.DataFrame(payload.get("survivors", [])),
        "meta": payload.get("meta", {}),
        "saved_at_et": payload.get("saved_at_et")
    }

def _bf_promote_recovery(results):
    """If strict gates kill every owner, promote best survivor per game as clearly marked recovery owner."""
    if not isinstance(results, dict):
        return {"owners":pd.DataFrame(), "core":pd.DataFrame(), "alt":pd.DataFrame(), "chaos":pd.DataFrame(), "survivors":pd.DataFrame(), "meta":{"message":"Engine returned invalid results."}}

    for k in ["owners","core","alt","chaos","survivors"]:
        if k not in results or results[k] is None:
            results[k] = pd.DataFrame()

    meta = results.get("meta", {}) or {}
    survivors = _bf_safe_df(results.get("survivors"))
    owners = _bf_safe_df(results.get("owners"))

    if owners.empty and not survivors.empty:
        group_col = "game_owner" if "game_owner" in survivors.columns else ("game_key" if "game_key" in survivors.columns else ("game" if "game" in survivors.columns else None))
        if group_col:
            rows = []
            for game, g in survivors.groupby(group_col, dropna=False):
                g = g.copy()
                if "score" not in g.columns:
                    g["score"] = 40.0
                # prefer non-NO PLAY, otherwise best audit row
                if "official_core_role" in g.columns:
                    cand = g[g["official_core_role"].astype(str).ne("NO PLAY")].copy()
                    if cand.empty:
                        cand = g.copy()
                else:
                    cand = g.copy()
                pick = cand.sort_values("score", ascending=False).iloc[0].to_dict()
                if str(pick.get("official_core_role","")) == "NO PLAY" or not str(pick.get("official_core_role","")).strip():
                    pick["official_core_role"] = "Recovery"
                pick["archetype"] = pick.get("archetype") if str(pick.get("archetype","")).strip() and str(pick.get("archetype","")) != "No Clean Owner" else "Recovery Owner / Audit Survivor"
                pick["game_owner"] = game
                pick["recovery_owner"] = True
                pick["clean_owner"] = False
                pick["data_status"] = pick.get("data_status", "RECOVERY")
                pick["gate_path"] = str(pick.get("gate_path","")) + " | FINAL: RECOVERY OWNER LOCKED SO GAME BOARD/TICKETS DO NOT DIE"
                try:
                    pick["score"] = max(40.0, min(float(pick.get("score", 40)), 68.0))
                except Exception:
                    pick["score"] = 52.0
                rows.append(pick)
            owners = pd.DataFrame(rows).sort_values("score", ascending=False).reset_index(drop=True)
            results["owners"] = owners
            try:
                core, alt, chaos = build_tickets_from_owners(owners, survivors)
                # build_tickets_from_owners may return empty if roles weird, so force fallback tickets
                if core is None or core.empty:
                    core = owners.head(3).copy(); core["ticket_role"] = "CORE"
                if alt is None or alt.empty:
                    alt = owners.iloc[3:6].copy() if len(owners)>3 else owners.tail(min(3,len(owners))).copy()
                    if not alt.empty: alt["ticket_role"] = "ALT"
                if chaos is None or chaos.empty:
                    chaos = owners[owners["official_core_role"].astype(str).str.contains("WHO|Recovery", case=False, na=False)].head(3).copy()
                    if chaos.empty: chaos = owners.tail(min(3,len(owners))).copy()
                    if not chaos.empty: chaos["ticket_role"] = "WHO"
                results["core"], results["alt"], results["chaos"] = core, alt, chaos
            except Exception:
                core = owners.head(3).copy(); core["ticket_role"] = "CORE"
                alt = owners.iloc[3:6].copy() if len(owners)>3 else owners.tail(min(3,len(owners))).copy()
                if not alt.empty: alt["ticket_role"] = "ALT"
                chaos = owners.tail(min(3,len(owners))).copy()
                if not chaos.empty: chaos["ticket_role"] = "WHO"
                results["core"], results["alt"], results["chaos"] = core, alt, chaos

            meta["owners_locked"] = int(len(owners))
            meta["recovery_owners"] = int(len(owners))
            meta["message"] = f"Blender complete: {len(owners)} recovery game owners locked from {meta.get('games', len(owners))} games. Strict gates produced no clean owners, so recovery owners are marked clearly."
            results["meta"] = meta

    if "owners_locked" not in meta:
        meta["owners_locked"] = int(len(_bf_safe_df(results.get("owners"))))
    results["meta"] = meta
    return results

def run_true_blender(df, *args, **kwargs):
    """Patched run path: original full engine + recovery + no TypeError."""
    try:
        results = _LOCKED_ORIGINAL_RUN_TRUE_BLENDER(df)
    except TypeError:
        results = _LOCKED_ORIGINAL_RUN_TRUE_BLENDER(df)
    except Exception as e:
        meta = {"input_rows": 0 if df is None else int(len(df)), "games":0, "owners_locked":0, "message":f"Engine failed safely: {e}"}
        results = {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"meta":meta}
    results = _bf_promote_recovery(results)
    try:
        save_locked_results(results)
    except Exception:
        pass
    return results


# ============================================================
# TRUE BLENDER SCORE SEPARATION PATCH
# Fixes flat/default scores by creating player-specific score
# separation from actual feed fields + text signals.
# ============================================================

_PRE_TRUE_SCORE_RUN_TRUE_BLENDER = run_true_blender

def _ts_num(x, default=0.0):
    try:
        if x is None or pd.isna(x):
            return default
        s = str(x).replace("%","").replace("+","").replace(",","").strip()
        if s.lower() in {"", "nan", "none", "null", "-", "—"}:
            return default
        return float(s)
    except Exception:
        return default

def _ts_text(x):
    try:
        if x is None or pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()

def _ts_get(row, names, default=0.0):
    # exact first
    for n in names:
        if n in row:
            v = row.get(n)
            try:
                if pd.isna(v):
                    continue
            except Exception:
                pass
            if v is not None:
                return v
    # fuzzy through raw/PDF columns
    keys = {str(k).lower().replace(" ","").replace("_","").replace("%","").replace("/",""): k for k in row.keys()}
    for n in names:
        nk = str(n).lower().replace(" ","").replace("_","").replace("%","").replace("/","")
        for compact, real in keys.items():
            if nk in compact or compact in nk:
                return row.get(real)
    return default

def _ts_metric_count(row):
    groups = [
        ["pull_pct","pull%","pull"], ["hard_hit_pct","hardhit%","hard_hit%","hh%"],
        ["barrel_pct","barrel%","brl%"], ["sweet_spot_pct","sweet%","launch","la"],
        ["dmg","damage","ult","adj"], ["hpi","score","rating"],
        ["hr_pa","hr/pa","hr9","hr/9"], ["pitch_edge","edge"], ["lineup_slot","slot","order"]
    ]
    ct = 0
    for aliases in groups:
        val = _ts_get(row, aliases, None)
        if val is not None:
            try:
                if not pd.isna(val):
                    float(str(val).replace("%","").replace("+",""))
                    ct += 1
            except Exception:
                pass
    return ct

def _ts_true_score(row, existing_score=0.0):
    pull = _ts_num(_ts_get(row, ["pull_pct","pull%","pull","raw_pull%","raw_pull"]), 0)
    hard = _ts_num(_ts_get(row, ["hard_hit_pct","hardhit%","hard_hit%","hard hit%","hh%","raw_hh%","raw_hard_hit%"]), 0)
    barrel = _ts_num(_ts_get(row, ["barrel_pct","barrel%","brl%","barrel","raw_barrel%"]), 0)
    sweet = _ts_num(_ts_get(row, ["sweet_spot_pct","sweet%","sweet spot","launch","launch_angle","la"]), 0)
    dmg = _ts_num(_ts_get(row, ["dmg","damage","ult","ultimate","adj","adjusted"]), 0)
    hpi = _ts_num(_ts_get(row, ["hpi","hr score","model","rating"]), 0)
    hrpa = _ts_num(_ts_get(row, ["hr_pa","hr/pa","hr rate","hr_rate","hr9","hr/9","pitcher_hr9"]), 0)
    edge = _ts_num(_ts_get(row, ["pitch_edge","pitch edge","edge"]), 0)
    slot = _ts_num(_ts_get(row, ["lineup_slot","slot","order","batting_order","bo"]), 0)

    player = _ts_text(row.get("player"))
    team = _ts_text(row.get("team"))
    pitcher = _ts_text(row.get("pitcher"))
    notes = " ".join([_ts_text(row.get(k)) for k in row.keys() if "note" in str(k).lower() or "tag" in str(k).lower() or "raw" in str(k).lower()]).lower()
    metric_count = _ts_metric_count(row)

    # Start low. Every real field must earn separation.
    score = 18.0
    score += min(max(pull, 0), 65) * 0.18
    score += min(max(hard, 0), 70) * 0.14
    score += min(max(barrel, 0), 25) * 0.56
    score += min(max(sweet, 0), 45) * 0.10
    score += min(max(dmg, 0), 8) * 3.2
    score += min(max(hpi, 0), 100) * 0.12
    score += min(max(hrpa, 0), 6) * 3.0
    score += max(min(edge, 35), -25) * 0.25

    if slot > 0:
        if slot <= 4: score += 5
        elif slot <= 6: score += 3
        elif slot <= 8: score += 1
        else: score -= 3

    pos = ["elite","green","primary","core","launch","pull","barrel","damage","edge","hot","hr","target","plus","strong"]
    chaos = ["who","chaos","secondary","adjacent","decoy","transfer"]
    neg = ["trap","red","cold","weak","fade","kill","suppression","bad"]
    score += sum(1.5 for w in pos if w in notes)
    score += sum(1.2 for w in chaos if w in notes)
    score -= sum(3.5 for w in neg if w in notes)

    score += min(metric_count, 9) * 1.7

    # Tiny tie-breaker only. Prevents identical scores for totally blank rows.
    score += ((sum(ord(c) for c in (player + team + pitcher)) % 19) - 9) * 0.11

    # Very light gate boost only; never let previous recovery default dominate.
    old = _ts_num(existing_score, 40)
    score += max(0, min(old, 99) - 50) * 0.10

    if metric_count <= 1:
        score = min(52, max(34, score))
    elif metric_count <= 3:
        score = min(66, score)

    hard_fails = _ts_text(row.get("hard_fails")).lower()
    if hard_fails and hard_fails not in {"nan", "none"}:
        score -= min(16, len([x for x in hard_fails.split(",") if x.strip()]) * 3.5)
    if "trap" in notes:
        score -= 12

    return round(max(1, min(96, score)), 1)

def _ts_rescore_frame(df):
    df = _bf_safe_df(df).copy()
    if df.empty:
        return df
    df["score"] = [_ts_true_score(r.to_dict(), r.get("score", r.get("blender_score", 40))) for _, r in df.iterrows()]
    df["blender_score"] = df["score"]
    if "official_core_role" in df.columns:
        df.loc[(df["score"] >= 74) & ~df["official_core_role"].astype(str).str.contains("WHO|Adjacent", case=False, na=False), "official_core_role"] = "Primary"
        df.loc[(df["score"] < 58) & df["official_core_role"].astype(str).eq("Primary"), "official_core_role"] = "Recovery"
    return df

def _ts_rebuild_owners_from_survivors(survivors):
    survivors = _ts_rescore_frame(survivors)
    if survivors.empty:
        return survivors, pd.DataFrame()
    group_col = "game_owner" if "game_owner" in survivors.columns else ("game_key" if "game_key" in survivors.columns else ("game" if "game" in survivors.columns else None))
    if not group_col:
        return survivors, survivors.sort_values("score", ascending=False).head(3)
    owners = []
    for game, g in survivors.groupby(group_col, dropna=False):
        g = g.copy().sort_values("score", ascending=False)
        pick = g.iloc[0].to_dict()
        pick["game_owner"] = game
        if not _ts_text(pick.get("official_core_role")) or _ts_text(pick.get("official_core_role")) == "NO PLAY":
            pick["official_core_role"] = "Recovery" if _ts_num(pick.get("score")) < 70 else "Primary"
        owners.append(pick)
    owners = pd.DataFrame(owners).sort_values("score", ascending=False).reset_index(drop=True)
    return survivors, owners

def _ts_rebuild_tickets(owners):
    owners = _ts_rescore_frame(owners).sort_values("score", ascending=False).reset_index(drop=True)
    if owners.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    core_rows = []
    for pattern in ["Primary", "WHO|Recovery", "Adjacent", ""]:
        pool = owners if pattern == "" else owners[owners["official_core_role"].astype(str).str.contains(pattern, case=False, na=False)]
        for _, r in pool.iterrows():
            if len(core_rows) >= 3: break
            if r.get("player") not in [x.get("player") for x in core_rows]:
                core_rows.append(r.to_dict())
        if len(core_rows) >= 3: break
    core = pd.DataFrame(core_rows).head(3)
    if not core.empty: core["ticket_role"] = "CORE"

    used = set(core["player"].astype(str)) if not core.empty and "player" in core else set()
    alt = owners[~owners["player"].astype(str).isin(used)].head(3).copy() if "player" in owners else owners.iloc[3:6].copy()
    if alt.empty:
        alt = owners.tail(min(3, len(owners))).copy()
    if not alt.empty: alt["ticket_role"] = "ALT"

    used.update(alt["player"].astype(str).tolist() if not alt.empty and "player" in alt else [])
    chaos = owners[
        owners["official_core_role"].astype(str).str.contains("WHO|Recovery", case=False, na=False)
        & ~owners["player"].astype(str).isin(used)
    ].head(3).copy() if "player" in owners and "official_core_role" in owners else pd.DataFrame()
    if chaos.empty:
        chaos = owners[~owners["player"].astype(str).isin(used)].head(3).copy() if "player" in owners else owners.tail(min(3, len(owners))).copy()
    if chaos.empty:
        chaos = owners.tail(min(3, len(owners))).copy()
    if not chaos.empty: chaos["ticket_role"] = "WHO"
    return core, alt, chaos

def run_true_blender(df, *args, **kwargs):
    results = _PRE_TRUE_SCORE_RUN_TRUE_BLENDER(df, *args, **kwargs)
    if not isinstance(results, dict):
        return results

    survivors = _bf_safe_df(results.get("survivors"))
    owners = _bf_safe_df(results.get("owners"))

    if not survivors.empty:
        survivors, owners = _ts_rebuild_owners_from_survivors(survivors)
    elif not owners.empty:
        owners = _ts_rescore_frame(owners)

    core, alt, chaos = _ts_rebuild_tickets(owners)
    results["survivors"] = survivors
    results["owners"] = owners
    results["core"] = core
    results["alt"] = alt
    results["chaos"] = chaos

    meta = results.get("meta", {}) or {}
    meta["score_engine"] = "TRUE_DIFFERENTIATED_SCORE_V2"
    meta["owners_locked"] = int(len(owners))
    meta["message"] = f"Blender complete: {len(owners)} game owners locked with true differentiated scores. Scores separate by Pull/HH/Barrel/DMG/HPI/HR lane/pitch edge/text signals."
    results["meta"] = meta

    try:
        save_locked_results(results)
    except Exception:
        pass
    return results
