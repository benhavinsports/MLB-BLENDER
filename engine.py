from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from official_mlb_slate import fetch_official_mlb_slate, attach_official_slate_to_feed, official_game_count
from feeder import actual_game_count

DATA_DIR = Path("data")
LOCK_PATH = DATA_DIR / "locked_owners.json"
ENGINE_VERSION = "V0219_V0215_BASELINE_PLUS_DAILY_LEARNING_ONLY"
LEARNING_PATH = DATA_DIR / "blender_daily_learning.jsonl"
LEARNING_PROFILE_PATH = DATA_DIR / "blender_learning_profile.json"

# -----------------------------------------------------------------------------
# Small safe helpers
# -----------------------------------------------------------------------------
def _txt(x: Any) -> str:
    try:
        if x is None or pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None or pd.isna(x):
            return default
        s = str(x).replace("%", "").replace("+", "").replace(",", "").strip()
        if s.lower() in {"", "nan", "none", "null", "-", "—"}:
            return default
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group(0)) if m else default
    except Exception:
        return default


def _key(s: Any) -> str:
    return str(s).lower().replace(" ", "").replace("_", "").replace("%", "").replace("/", "").replace("-", "")


def _field(row: Dict[str, Any], names: List[str], default: float = 0.0) -> float:
    cmap = {_key(k): k for k in row.keys()}
    for n in names:
        kk = _key(n)
        if kk in cmap:
            return _num(row.get(cmap[kk]), default)
    for n in names:
        nn = _key(n)
        for ck, real in cmap.items():
            if nn in ck or ck in nn:
                return _num(row.get(real), default)
    return default


def _safe_df(x: Any) -> pd.DataFrame:
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()


def csv_bytes(df: pd.DataFrame) -> bytes:
    return _safe_df(df).to_csv(index=False).encode("utf-8")


def _records(df: Any) -> List[Dict[str, Any]]:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []
    return df.replace({np.nan: None}).to_dict(orient="records")


# -----------------------------------------------------------------------------
# Public slate wrappers expected by app.py
# -----------------------------------------------------------------------------
def fetch_live_public_slate(date_str: str | None = None):
    return fetch_official_mlb_slate(date_str)


def fetch_live_public_hitter_pool(date_str: str | None = None):
    return fetch_official_mlb_slate(date_str)


def attach_slate_matchup_context(df: pd.DataFrame, public_context: Any = None) -> pd.DataFrame:
    return attach_official_slate_to_feed(df, public_context)


def merge_public_context(df: pd.DataFrame, public_context: Any = None) -> pd.DataFrame:
    return attach_slate_matchup_context(df, public_context)


# -----------------------------------------------------------------------------
# Locked results persistence
# -----------------------------------------------------------------------------
def empty_results(message: str) -> Dict[str, Any]:
    return {
        "owners": pd.DataFrame(),
        "core": pd.DataFrame(),
        "alt": pd.DataFrame(),
        "chaos": pd.DataFrame(),
        "survivors": pd.DataFrame(),
        "cuts": pd.DataFrame(),
        "game_board": pd.DataFrame(),
        "role_board": pd.DataFrame(),
        "environment_board": pd.DataFrame(),
        "state_log": pd.DataFrame(),
        "meta": {
            "engine_version": ENGINE_VERSION,
            "message": message,
            "owners_locked": 0,
            "core_count": 0,
            "passed_rows": 0,
            "cut_rows": 0,
            "core_rule": "DEATH_CHAIN_ONLY__NO_SCORE_SORT__NO_REFILL",
        },
    }


def save_locked_results(results: Dict[str, Any]) -> None:
    # SPEED RULE: Streamlit already holds the full result in session_state.
    # Writing every survivor/gate row to disk makes each run feel slow, so persist only the light ticket state.
    try:
        DATA_DIR.mkdir(exist_ok=True)
        payload = {k: _records(results.get(k)) for k in ["owners", "core", "alt", "chaos"]}
        payload["meta"] = results.get("meta", {})
        LOCK_PATH.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    except Exception:
        pass


def load_locked_results() -> Dict[str, Any]:
    # Avoid loading stale old 99-score cache. Every app launch starts clean.
    return empty_results("Run the Blender first. Stale locked cache is intentionally ignored in V0212.")




# -----------------------------------------------------------------------------
# Daily learning layer (V0219)
# -----------------------------------------------------------------------------
# This layer is intentionally non-invasive: it records anonymous gate/archetype
# patterns after a run so the model can be calibrated later without changing
# today's player pools, game board, Core/ALT/WHO logic, or one-owner-per-game flow.
def _json_safe_record(row: Dict[str, Any], allowed: List[str]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k in allowed:
        v = row.get(k, None)
        try:
            if pd.isna(v):
                v = None
        except Exception:
            pass
        if isinstance(v, (np.integer,)):
            v = int(v)
        elif isinstance(v, (np.floating,)):
            v = float(v)
        out[k] = v
    return out


def _count_values(df: pd.DataFrame, col: str) -> Dict[str, int]:
    if not isinstance(df, pd.DataFrame) or df.empty or col not in df.columns:
        return {}
    return {str(k): int(v) for k, v in df[col].fillna("").astype(str).value_counts().to_dict().items() if str(k)}


def _learning_snapshot(results: Dict[str, Any]) -> Dict[str, Any]:
    import datetime as _dt
    owners = _safe_df(results.get("owners"))
    core = _safe_df(results.get("core"))
    cuts = _safe_df(results.get("cuts"))
    board = _safe_df(results.get("game_board"))
    meta = results.get("meta", {}) or {}

    # No player names are stored in the learning profile. Learning calibrates
    # patterns only: roles, gates, lanes, launch/conversion bands, and failures.
    owner_cols = [
        "game_id", "locked_attack_side", "official_core_role", "archetype",
        "lane_index", "launch_index", "conversion_index", "support_index",
        "pass_depth", "death_step", "binding_status",
    ]
    core_cols = [
        "core_slot", "official_core_role", "archetype", "lane_index",
        "launch_index", "conversion_index", "support_index", "pass_depth",
    ]
    return {
        "timestamp_utc": _dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "engine_version": ENGINE_VERSION,
        "games": int(meta.get("games", 0) or 0),
        "input_rows": int(meta.get("input_rows", 0) or 0),
        "owners_locked": int(meta.get("owners_locked", 0) or 0),
        "core_count": int(meta.get("core_count", 0) or 0),
        "role_counts": _count_values(owners, "official_core_role"),
        "core_role_counts": _count_values(core, "official_core_role"),
        "cut_gate_counts": _count_values(cuts, "stop_gate"),
        "gate_result_counts": _count_values(board, "result"),
        "owner_patterns": [_json_safe_record(r, owner_cols) for r in _records(owners)],
        "core_patterns": [_json_safe_record(r, core_cols) for r in _records(core)],
        "learning_rule": "PATTERN_ONLY__NO_PLAYER_NAME_ANCHORING__NO_SAME_DAY_PICK_OVERRIDE",
    }


def _write_learning_snapshot(results: Dict[str, Any]) -> Dict[str, Any]:
    try:
        DATA_DIR.mkdir(exist_ok=True)
        snap = _learning_snapshot(results)
        with LEARNING_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(snap, separators=(",", ":")) + "\n")
        # Lightweight rolling profile for UI/meta; still pattern-only.
        profile = {
            "engine_version": ENGINE_VERSION,
            "last_timestamp_utc": snap.get("timestamp_utc"),
            "last_games": snap.get("games"),
            "last_owners_locked": snap.get("owners_locked"),
            "last_role_counts": snap.get("role_counts", {}),
            "last_core_role_counts": snap.get("core_role_counts", {}),
            "last_cut_gate_counts": snap.get("cut_gate_counts", {}),
            "rule": snap.get("learning_rule"),
        }
        LEARNING_PROFILE_PATH.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        return profile
    except Exception as e:
        return {"learning_error": str(e), "rule": "learning failed safely; Blender output unchanged"}


def load_learning_profile() -> Dict[str, Any]:
    try:
        if LEARNING_PROFILE_PATH.exists():
            return json.loads(LEARNING_PROFILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"rule": "No learning profile yet. Run Blender once to create pattern-only learning."}


# -----------------------------------------------------------------------------
# Metrics and normalization
# -----------------------------------------------------------------------------
ALIASES = {
    "pull": ["pull_pct", "pull%", "pull"],
    "hard": ["hard_hit_pct", "hardhit%", "hard_hit%", "hard hit%", "hh%"],
    "barrel": ["barrel_pct", "barrel%", "brl%", "barrel"],
    "sweet": ["sweet_spot_pct", "sweet%", "sweet spot", "launch", "la"],
    "dmg": ["dmg", "damage", "ult", "ultimate", "adj"],
    "hpi": ["hpi", "model", "rating", "hr score"],
    "hr": ["hr_lane", "hr_pa", "hr/pa", "hr9", "hr/9"],
    "edge": ["pitch_edge", "pitch edge", "edge"],
    "slot": ["lineup_slot", "slot", "order", "bo", "rank"],
}


def metrics(row: Dict[str, Any]) -> Dict[str, float]:
    return {k: _field(row, n, -99 if k == "edge" else 0.0) for k, n in ALIASES.items()}


def metric_count(v: Dict[str, float]) -> int:
    count = 0
    for k, x in v.items():
        if k == "edge":
            if x != -99:
                count += 1
        elif x not in [None, 0] and not pd.isna(x):
            count += 1
    return count


def game_id(row: Dict[str, Any]) -> str:
    pk = _txt(row.get("game_pk"))
    if pk and pk.lower() not in {"nan", "none"}:
        return pk
    return _txt(row.get("game_key") or row.get("game"))


def _game_participants(game_key: str) -> set[str]:
    g = _txt(game_key)
    if not g:
        return set()
    if " vs " in g:
        return {x.strip().lower().replace(".", "") for x in g.split(" vs ")[:2] if x.strip()}
    return set()


def _team_fits_game(team: str, game_key: str) -> bool:
    parts = _game_participants(game_key)
    if not parts:
        return True
    return _txt(team).lower().replace(".", "") in parts


def normalize_feed(df: pd.DataFrame) -> pd.DataFrame:
    df = _safe_df(df).copy()
    if df.empty:
        return df
    if "game_key" not in df.columns:
        df["game_key"] = df["game"] if "game" in df.columns else ""
    if "official_slate_attached" not in df.columns:
        df["official_slate_attached"] = False
    if "player" in df.columns and "pitcher" in df.columns:
        df = df[df["player"].astype(str).str.lower().str.strip() != df["pitcher"].astype(str).str.lower().str.strip()].copy()
    df["_gid"] = df.apply(lambda r: game_id(r.to_dict()), axis=1)
    if "binding_status" not in df.columns:
        df["binding_status"] = "PDF_BOUND"
    # Immutable binding ID prevents player/game renderer drift after elimination.
    df["data_binding_id"] = df.apply(lambda r: "|".join([_txt(r.get("_gid")), _txt(r.get("team")), _txt(r.get("player"))]).lower(), axis=1)
    return df.reset_index(drop=True)


def _points(x: float, floor: float, elite: float, pts: float) -> float:
    x = _num(x, 0.0)
    if x < floor:
        return 0.0
    if x >= elite:
        return float(pts)
    return float(pts) * ((x - floor) / max(1.0, elite - floor))


def _lane_strength(v: Dict[str, float]) -> float:
    return max(
        _points(v["hr"], 0.5, 2.5, 10),
        _points(v["edge"], 0, 18, 10),
        _points(v["dmg"], 0.5, 2.5, 10),
        _points(v["hpi"], 35, 92, 7),  # HPI is support, not the whole engine.
    )


def _launch_strength(v: Dict[str, float]) -> float:
    return max(
        _points(v["pull"], 25, 58, 10),
        _points(v["barrel"], 3, 17, 10),
        _points(v["sweet"], 18, 40, 8),
        _points(v["hard"], 32, 62, 5),
    )


def _conversion_strength(v: Dict[str, float]) -> float:
    return max(
        _points(v["dmg"], 0.5, 2.6, 10),
        _points(v["barrel"], 4, 18, 9),
        _points(v["hr"], 0.55, 2.6, 9),
        _points(v["hpi"], 40, 94, 6),
    )


def _support_strength(v: Dict[str, float]) -> float:
    return max(
        _points(v["hard"], 30, 64, 6),
        _points(v["pull"], 26, 58, 6),
        _points(v["barrel"], 3, 17, 6),
    )


def env_score(row: Dict[str, Any]) -> float:
    v = metrics(row)
    return _lane_strength(v) * 1.4 + _launch_strength(v) + _conversion_strength(v) + _support_strength(v) * 0.5


def lock_attack_sides(df: pd.DataFrame) -> Tuple[Dict[str, str], pd.DataFrame]:
    locks: Dict[str, str] = {}
    rows: List[Dict[str, Any]] = []
    if df.empty:
        return locks, pd.DataFrame()
    for gid, gdf in df.groupby("_gid", dropna=False):
        if not _txt(gid):
            continue
        team_scores: List[Tuple[str, float, int]] = []
        for team, tdf in gdf.groupby("team", dropna=False):
            team = _txt(team)
            if not team:
                continue
            vals = [env_score(r.to_dict()) for _, r in tdf.iterrows()]
            if not vals:
                continue
            # True side lock uses team peak + depth. It is a hard kill later.
            team_scores.append((team, max(vals) + (sum(vals) / len(vals)) * 0.25, len(vals)))
        if not team_scores:
            continue
        team_scores.sort(key=lambda x: x[1], reverse=True)
        locked, score, count = team_scores[0]
        locks[str(gid)] = locked
        rows.append({
            "game_id": str(gid),
            "game_key": _txt(gdf.iloc[0].get("game_key") or gdf.iloc[0].get("game")),
            "locked_attack_side": locked,
            "attack_side_index": round(float(score), 3),
            "candidate_rows": int(count),
            "engine_rule": "HARD SIDE LOCK — opposite side is killed before ownership.",
        })
    return locks, pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Death-chain gates: REAL elimination state machine
# -----------------------------------------------------------------------------
def _add_gate(gates: List[Dict[str, Any]], step: int, gate: str, passed: bool, reason: str, hard_gate: bool = True, value: Any = "") -> None:
    gates.append({
        "step": step,
        "gate": gate,
        "result": "PASS" if passed else "CUT",
        "reason": reason,
        "hard_gate": bool(hard_gate),
        "cut": bool(hard_gate and not passed),
        "value": value,
    })


def _notes(row: Dict[str, Any]) -> str:
    return " ".join([_txt(row.get(k)) for k in row.keys() if any(x in str(k).lower() for x in ["note", "tag", "raw", "status", "event", "role"]) ]).lower()


def _role(v: Dict[str, float], notes: str) -> Tuple[str, Dict[str, Any]]:
    adjacent_flag = any(x in notes for x in ["adjacent", "decoy", "transfer", "coverage", "behind", "after", "weak slot", "next man"])
    who_flag = any(x in notes for x in ["who", "chaos", "low owned", "low-owned", "bottom", "random", "cheap"])
    # Role is built AFTER survival behavior, never before ownership resolution.
    if who_flag or (v["pull"] >= 28 and v["hard"] >= 32 and 0 < v["hpi"] < 55 and v["barrel"] >= 3):
        return "WHO", {"WHO": True, "Adjacent": adjacent_flag, "source": "survivor_behavior"}
    if adjacent_flag or (v["slot"] in {2,3,5,6,7} and v["pull"] >= 35 and v["barrel"] >= 4 and v["hpi"] < 75):
        return "Adjacent", {"WHO": who_flag, "Adjacent": True, "source": "survivor_behavior"}
    return "Primary", {"WHO": who_flag, "Adjacent": adjacent_flag, "source": "survivor_behavior"}


def _candidate_base(row: Dict[str, Any], locks: Dict[str, str], idx: int = 0) -> Dict[str, Any]:
    v = metrics(row)
    player = _txt(row.get("player"))
    team = _txt(row.get("team"))
    gid = game_id(row)
    gkey = _txt(row.get("game_key") or row.get("game"))
    locked = locks.get(str(gid), "")
    notes = _notes(row)
    lane = _lane_strength(v)
    launch = _launch_strength(v)
    conversion = _conversion_strength(v)
    support = _support_strength(v)
    mc = metric_count(v)
    role, triggers = _role(v, notes)
    # Internal raw separation only. Never shown as score. Never normalized.
    raw_power = round(lane * 10000 + launch * 1000 + conversion * 100 + support * 10 + (mc * 0.01), 6)
    fingerprint = (sum(ord(c) for c in (player + team + gkey)) + idx * 17) % 1009
    owner_key = round(raw_power + fingerprint / 1000000, 6)
    trap = any(x in notes for x in ["trap", "red flag", "fade", "scratch", "not starting", "bench"])
    binding_valid = bool(player and gkey and team and _team_fits_game(team, gkey))
    return {
        **row,
        "game_id": gid,
        "locked_attack_side": locked,
        "metric_count": mc,
        "lane_index": round(lane, 3),
        "launch_index": round(launch, 3),
        "conversion_index": round(conversion, 3),
        "support_index": round(support, 3),
        "owner_key": owner_key,
        "raw_owner_power": raw_power,
        "true_role_path": role,
        "role_scores_json": json.dumps(triggers),
        "trap_flag": trap,
        "notes_blob": notes,
        "binding_valid": binding_valid,
        "binding_status": _txt(row.get("binding_status", "PDF_BOUND")),
        "data_binding_id": _txt(row.get("data_binding_id", "")) or "|".join([_txt(gid), team, player]).lower(),
        "original_game_key": _txt(row.get("original_game_key", row.get("game_key", ""))),
        "original_team": _txt(row.get("original_team", row.get("team", ""))),
    }


def _cut_candidate(cand: Dict[str, Any], gates: List[Dict[str, Any]], step: int, gate: str, reason: str) -> Dict[str, Any]:
    _add_gate(gates, step, gate, False, reason)
    cand = cand.copy()
    cand["blender_eligible"] = False
    cand["official_core_role"] = "CUT"
    cand["archetype"] = "Cut by death chain"
    cand["pass_depth"] = sum(1 for g in gates if g["result"] == "PASS")
    cand["cut_depth"] = sum(1 for g in gates if g["result"] == "CUT")
    cand["death_step"] = f"STEP {step}: {gate}"
    cand["stop_gate"] = gate
    cand["blender_score"] = "CUT"
    cand["score"] = "CUT"
    cand["final_reason"] = f"CUT — {reason}"
    cand["gate_trace_json"] = json.dumps(gates)
    return cand


def _pass_gate(gates: List[Dict[str, Any]], step: int, gate: str, reason: str, hard_gate: bool = True) -> None:
    _add_gate(gates, step, gate, True, reason, hard_gate=hard_gate)


def _survive_candidate(cand: Dict[str, Any], gates: List[Dict[str, Any]]) -> Dict[str, Any]:
    role = cand.get("true_role_path", "Primary")
    archetype = {
        "Primary": "Clean Lane Event Owner",
        "Adjacent": "Adjacent / Decoy Transfer Owner",
        "WHO": "WHO / Chaos Event Owner",
    }.get(role, "Event Owner")
    cand = cand.copy()
    cand["blender_eligible"] = True
    cand["official_core_role"] = role
    cand["archetype"] = archetype
    cand["pass_depth"] = sum(1 for g in gates if g["result"] == "PASS")
    cand["cut_depth"] = 0
    cand["death_step"] = "SURVIVED"
    cand["stop_gate"] = ""
    cand["blender_score"] = "LOCKED OWNER"
    cand["score"] = "LOCKED OWNER"
    cand["final_reason"] = f"{role} survived death-chain gates and won isolated ownership"
    cand["gate_trace_json"] = json.dumps(gates)
    return cand


def _initial_gates(cand: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], str]:
    gates: List[Dict[str, Any]] = []
    player = _txt(cand.get("player")); gkey = _txt(cand.get("game_key") or cand.get("game"))
    team = _txt(cand.get("team")); locked = _txt(cand.get("locked_attack_side"))
    _pass_gate(gates, 0, "PDF row integrity", f"player={player}; game={gkey}") if player and gkey else _add_gate(gates, 0, "PDF row integrity", False, f"player={player}; game={gkey}")
    if any(g["cut"] for g in gates): return False, gates, "PDF row missing player/game"
    if cand.get("binding_valid"):
        _pass_gate(gates, 0, "Immutable player-game binding", f"binding={cand.get('data_binding_id')} status={cand.get('binding_status')}")
    else:
        _add_gate(gates, 0, "Immutable player-game binding", False, f"player/team/game mismatch: player={player}; team={team}; game={gkey}; status={cand.get('binding_status')}")
    if any(g["cut"] for g in gates): return False, gates, "player-game binding mismatch"
    _pass_gate(gates, 1, "Attack-side hard lock", f"locked={locked}; team={team}") if locked and team == locked else _add_gate(gates, 1, "Attack-side hard lock", False, f"locked={locked}; team={team}")
    if any(g["cut"] for g in gates): return False, gates, "opposite side killed before elimination"
    _pass_gate(gates, 2, "Metric survival", f"metric_count={cand.get('metric_count')}") if cand.get("metric_count",0) >= 3 else _add_gate(gates, 2, "Metric survival", False, f"metric_count={cand.get('metric_count')}; need 3+")
    if any(g["cut"] for g in gates): return False, gates, "not enough readable metrics"
    _pass_gate(gates, 3, "Pitcher HR lane", f"lane={cand.get('lane_index')}") if cand.get("lane_index",0) > 0 else _add_gate(gates, 3, "Pitcher HR lane", False, f"lane={cand.get('lane_index')}")
    if any(g["cut"] for g in gates): return False, gates, "no HR lane"
    _pass_gate(gates, 4, "Pull-air / launch", f"launch={cand.get('launch_index')}") if cand.get("launch_index",0) > 0 else _add_gate(gates, 4, "Pull-air / launch", False, f"launch={cand.get('launch_index')}")
    if any(g["cut"] for g in gates): return False, gates, "no pull-air / launch path"
    _pass_gate(gates, 5, "Conversion DNA", f"conversion={cand.get('conversion_index')}") if cand.get("conversion_index",0) > 0 else _add_gate(gates, 5, "Conversion DNA", False, f"conversion={cand.get('conversion_index')}")
    if any(g["cut"] for g in gates): return False, gates, "no conversion DNA"
    if cand.get("trap_flag"):
        _add_gate(gates, 6, "Trap / scratch audit", False, "trap/scratch/fade flag found")
        return False, gates, "trap/scratch/fade flag"
    _pass_gate(gates, 6, "Trap / scratch audit", "no trap flag")
    return True, gates, ""


def _round_eliminate(active: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]], step: int, gate: str, key: str) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    if len(active) <= 1:
        return active
    vals = [_num(c.get(key), 0) for c, _ in active]
    top = max(vals)
    # Only keep the actual strongest lane for the round. Ties continue with next round.
    keep: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
    for cand, gates in active:
        val = _num(cand.get(key), 0)
        if val == top:
            _pass_gate(gates, step, gate, f"won/held {key}={val}")
            keep.append((cand, gates))
        else:
            _add_gate(gates, step, gate, False, f"died inside game: {key}={val}; owner threshold={top}")
            cand["_dead_gates"] = gates
    return keep


def resolve_game_death_chain(game_df: pd.DataFrame, locks: Dict[str, str], start_idx: int) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    all_rows: List[Dict[str, Any]] = []
    board_rows: List[Dict[str, Any]] = []
    active: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]] = []
    idx = start_idx
    # First pass: hard gates. Opposite side is killed here, before any ownership comparison.
    for row in game_df.replace({np.nan: None}).to_dict(orient="records"):
        cand = _candidate_base(row, locks, idx); cand["row_id"] = idx; idx += 1
        ok, gates, why = _initial_gates(cand)
        if ok:
            active.append((cand, gates))
        else:
            cut_gate = next((g for g in gates if g.get("cut")), gates[-1])
            dead = _cut_candidate(cand, gates[:-1], int(cut_gate["step"]), str(cut_gate["gate"]), why or str(cut_gate.get("reason","")))
            all_rows.append(dead)
            for g in json.loads(dead["gate_trace_json"]):
                board_rows.append({"game_id": dead.get("game_id",""), "game_key": dead.get("game_key",""), "player": dead.get("player",""), "team": dead.get("team",""), "locked_attack_side": dead.get("locked_attack_side",""), "role": dead.get("official_core_role",""), **g, "death_step": dead.get("death_step",""), "owner_state": dead.get("blender_score","")})
    if not active:
        return all_rows, board_rows, idx

    # Real death chain: resolve exactly ONE owner inside this game before Core roles/tickets.
    for step, gate, key in [
        (7, "Within-side owner lane isolation", "lane_index"),
        (8, "Within-side pull-air isolation", "launch_index"),
        (9, "Within-side conversion isolation", "conversion_index"),
        (10, "Within-side support isolation", "support_index"),
        (11, "Final survivor fingerprint isolation", "owner_key"),
    ]:
        before = active[:]
        active = _round_eliminate(active, step, gate, key)
        dead = [x for x in before if x not in active]
        for cand, gates in dead:
            cut_gate = gates[-1]
            deadrow = _cut_candidate(cand, gates[:-1], int(cut_gate["step"]), str(cut_gate["gate"]), str(cut_gate.get("reason","")))
            all_rows.append(deadrow)
            for g in json.loads(deadrow["gate_trace_json"]):
                board_rows.append({"game_id": deadrow.get("game_id",""), "game_key": deadrow.get("game_key",""), "player": deadrow.get("player",""), "team": deadrow.get("team",""), "locked_attack_side": deadrow.get("locked_attack_side",""), "role": deadrow.get("official_core_role",""), **g, "death_step": deadrow.get("death_step",""), "owner_state": deadrow.get("blender_score","")})
        if len(active) <= 1:
            break

    # Single owner survives.
    active = sorted(active, key=lambda x: _num(x[0].get("owner_key"),0), reverse=True)[:1]
    winner, wgates = active[0]
    _pass_gate(wgates, 12, "One-owner game lock", "only isolated survivor remains; no best-remaining refill", hard_gate=False)
    owner = _survive_candidate(winner, wgates)
    owner["game_owner_locked"] = True
    all_rows.append(owner)
    for g in json.loads(owner["gate_trace_json"]):
        board_rows.append({"game_id": owner.get("game_id",""), "game_key": owner.get("game_key",""), "player": owner.get("player",""), "team": owner.get("team",""), "locked_attack_side": owner.get("locked_attack_side",""), "role": owner.get("official_core_role",""), **g, "death_step": owner.get("death_step",""), "owner_state": owner.get("blender_score","")})
    return all_rows, board_rows, idx


def resolve_owners(survivors: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(survivors, pd.DataFrame) or survivors.empty:
        return pd.DataFrame()
    owners = survivors[survivors.get("game_owner_locked", False) == True].copy()
    if owners.empty:
        return pd.DataFrame()
    return owners.reset_index(drop=True)


def build_core_top3(owners: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(owners, pd.DataFrame) or owners.empty:
        return pd.DataFrame()
    # Core ticket is built from isolated game owners only. Internal ordering is not a displayed score.
    owners = owners.copy()
    # Role balance: one clean lane, one adjacent/decoy, one WHO/chaos when available.
    selected = []
    used_games = set()
    for role in ["Primary", "Adjacent", "WHO"]:
        pool = owners[(owners["official_core_role"] == role) & (~owners["game_id"].astype(str).isin(used_games))].sort_values("owner_key", ascending=False)
        if not pool.empty:
            r = pool.iloc[0].to_dict(); selected.append(r); used_games.add(str(r.get("game_id","")))
    if len(selected) < 3:
        pool = owners[~owners["game_id"].astype(str).isin(used_games)].sort_values("owner_key", ascending=False)
        for _, rr in pool.iterrows():
            if len(selected) >= 3: break
            r = rr.to_dict(); selected.append(r); used_games.add(str(r.get("game_id","")))
    core = pd.DataFrame(selected[:3])
    if core.empty:
        return core
    core["core_slot"] = [f"CORE {i+1}" for i in range(len(core))]
    core["ticket_role"] = "CORE"
    core["blender_score"] = "LOCKED OWNER"
    core["score"] = "LOCKED OWNER"
    return core.reset_index(drop=True)


def run_true_blender(df: pd.DataFrame, *args, **kwargs) -> Dict[str, Any]:
    work = normalize_feed(df)
    if work.empty:
        return empty_results("No usable feed rows loaded.")

    locks, environment_board = lock_attack_sides(work)
    survivor_rows: List[Dict[str, Any]] = []
    board_rows: List[Dict[str, Any]] = []
    row_idx = 0
    for gid, gdf in work.groupby("_gid", dropna=False):
        rows, board, row_idx = resolve_game_death_chain(gdf, locks, row_idx)
        survivor_rows.extend(rows); board_rows.extend(board)

    survivors = pd.DataFrame(survivor_rows)
    if survivors.empty:
        return empty_results("No candidates survived parsing.")
    cuts = survivors[survivors["blender_eligible"] != True].copy() if "blender_eligible" in survivors else pd.DataFrame()
    game_board = pd.DataFrame(board_rows)
    role_board = survivors[[c for c in ["data_binding_id","binding_status","original_game_key","original_team","game_id","game_key","team","player","official_core_role","true_role_path","role_scores_json","pass_depth","cut_depth","death_step","lane_index","launch_index","conversion_index","support_index"] if c in survivors.columns]].copy()
    owners = resolve_owners(survivors)
    core = build_core_top3(owners)

    used = set(core["player"].astype(str).str.lower().tolist()) if not core.empty and "player" in core.columns else set()
    alt = owners[~owners["player"].astype(str).str.lower().isin(used)].sort_values("owner_key", ascending=False).head(3).copy() if not owners.empty and "player" in owners.columns else pd.DataFrame()
    if not alt.empty:
        alt["ticket_role"] = "ALT"; alt["blender_score"] = "LOCKED OWNER"; alt["score"] = "LOCKED OWNER"
        used.update(alt["player"].astype(str).str.lower().tolist())
    chaos = owners[(owners["official_core_role"] == "WHO") & (~owners["player"].astype(str).str.lower().isin(used))].sort_values("owner_key", ascending=False).head(3).copy() if not owners.empty and "official_core_role" in owners.columns and "player" in owners.columns else pd.DataFrame()
    if not chaos.empty:
        chaos["ticket_role"] = "WHO"; chaos["blender_score"] = "LOCKED OWNER"; chaos["score"] = "LOCKED OWNER"

    games = official_game_count(work) or actual_game_count(work)
    meta = {
        "engine_version": ENGINE_VERSION,
        "games": int(games),
        "input_rows": int(len(work)),
        "passed_rows": int((survivors["blender_eligible"] == True).sum()),
        "cut_rows": int((survivors["blender_eligible"] != True).sum()),
        "owners_locked": int(len(owners)),
        "core_count": int(len(core)),
        "core_rule": "ONE_OWNER_PER_GAME__DEATH_CHAIN_ONLY__NO_SCORE_SORT__NO_REFILL",
        "generic_refill": False,
        "fallback_sorting": False,
        "score_engine_removed": True,
        "gate_power_display_removed": True,
        "attack_side_hard_kill": True,
        "daily_learning_active": True,
        "learning_rule": "PATTERN_ONLY__NO_PLAYER_NAME_ANCHORING__NO_SAME_DAY_PICK_OVERRIDE",
        "message": f"{ENGINE_VERSION}: Core={len(core)} from {len(owners)} isolated game owners. Immutable player-game binding added. No 99-score engine, no refill, no projection fallback. V0219 adds daily pattern-only learning without changing V0215 picks.",
    }
    results = {
        "owners": owners,
        "core": core,
        "alt": alt,
        "chaos": chaos,
        "survivors": survivors,
        "cuts": cuts,
        "game_board": game_board,
        "role_board": role_board,
        "environment_board": environment_board,
        "state_log": pd.DataFrame([{
            "rule": "FINAL_DEATH_CHAIN_ENGINE_ACTIVE",
            "normalized_scores_removed": True,
            "gate_power_display_removed": True,
            "score_sort_removed": True,
            "attack_side_hard_kill": True,
            "generic_refill": False,
            "projection_fallback": False,
            "stale_cache_ignored": True,
            "daily_learning_active": True,
            "learning_rule": "PATTERN_ONLY__NO_PLAYER_NAME_ANCHORING__NO_CORE_ALT_WHO_DRIFT",
        }]),
        "meta": meta,
    }
    save_locked_results(results)
    learning_profile = _write_learning_snapshot(results)
    results["meta"]["learning_profile"] = learning_profile
    return results
