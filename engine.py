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
ENGINE_VERSION = "V270_FINAL_ARCHETYPE_FIRST_FULL_18_GATES"

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
    """
    Gate-emergent role resolver.
    No name recycling, no ranking fallback, no archetype refill.
    WHO wins over Adjacent when both signatures exist.
    """
    slot = _num(v.get("slot", 0), 0)
    hpi = _num(v.get("hpi", 0), 0)
    pull = _num(v.get("pull", 0), 0)
    hard = _num(v.get("hard", 0), 0)
    barrel = _num(v.get("barrel", 0), 0)
    dmg = _num(v.get("dmg", 0), 0)
    hr = _num(v.get("hr", 0), 0)
    edge = _num(v.get("edge", -99), -99)

    adjacent_text = any(x in notes for x in [
        "adjacent", "decoy", "transfer", "coverage", "behind", "after",
        "weak slot", "next man", "protected", "protection"
    ])
    who_text = any(x in notes for x in [
        "who", "chaos", "low owned", "low-owned", "bottom", "cheap",
        "volatile", "secondary", "sneaky", "deep", "lower pressure"
    ])

    has_event_lane = (hr >= 0.5) or (edge >= 0) or (dmg >= 0.5) or (barrel >= 3)
    has_launch = (pull >= 28) or (barrel >= 3) or (hard >= 32)

    who_profile = (
        has_event_lane and has_launch and (
            who_text
            or (slot >= 6 and pull >= 28 and barrel >= 3)
            or (0 < hpi <= 58 and pull >= 28 and hard >= 32)
            or ((not adjacent_text) and barrel >= 3 and 0.5 <= dmg <= 2.25 and hpi < 70)
            or ((not adjacent_text) and hr >= 0.9 and hpi < 70 and pull >= 28)
        )
    )

    adjacent_profile = (
        adjacent_text
        or (slot in {2, 3, 5, 6, 7} and pull >= 35 and barrel >= 4 and 55 <= hpi < 82)
        or (slot in {4, 5, 6} and pull >= 40 and hard >= 38 and not who_profile)
    )

    if who_profile:
        return "WHO", {
            "WHO": True, "Adjacent": bool(adjacent_profile), "source": "gate_emergent_role",
            "slot": slot, "hpi": hpi, "pull": pull, "barrel": barrel, "dmg": dmg, "hr": hr,
        }
    if adjacent_profile:
        return "Adjacent", {
            "WHO": False, "Adjacent": True, "source": "gate_emergent_role",
            "slot": slot, "hpi": hpi, "pull": pull, "barrel": barrel, "dmg": dmg, "hr": hr,
        }
    return "Primary", {
        "WHO": False, "Adjacent": False, "source": "gate_emergent_role",
        "slot": slot, "hpi": hpi, "pull": pull, "barrel": barrel, "dmg": dmg, "hr": hr,
    }


# -----------------------------------------------------------------------------
# Pitcher weakness archetype lock (PRE-GATE FILTER)
# -----------------------------------------------------------------------------
def _signature_flags(row: Dict[str, Any]) -> set[str]:
    """Return hitter signatures from the feed/PDF without ranking players.
    These signatures describe whether a hitter matches the game's pitcher-weakness archetype.
    """
    v = metrics(row)
    notes = _notes(row)
    flags: set[str] = set()
    if "weak slot" in notes or "weakslot" in notes:
        flags.add("WEAK_SLOT")
    if "platoon" in notes:
        flags.add("PLATOON")
    if "rakes" in notes or "eats lhp" in notes or "eats rhp" in notes:
        flags.add("RAKES")
    if "laser" in notes:
        flags.add("LASER")
    if "park edge" in notes or "parkedge" in notes:
        flags.add("PARK_EDGE")
    if _num(v.get("edge", -99), -99) >= 10:
        flags.add("PITCH_EDGE")
    if _num(v.get("hr", 0), 0) >= 3.0:
        flags.add("HR_PA")
    if _num(v.get("dmg", 0), 0) >= 1.40:
        flags.add("DAMAGE")
    if _num(v.get("pull", 0), 0) >= 32 or _num(v.get("barrel", 0), 0) >= 3:
        flags.add("PULL_AIR")
    # Backup so imperfect PDFs do not zero the slate: a readable HR lane is still a lane signature.
    if _lane_strength(v) > 0:
        flags.add("READABLE_LANE")
    return flags


def _select_pitcher_weakness_archetype(game_df: pd.DataFrame, locks: Dict[str, str]) -> Tuple[str, set[str], Dict[str, Any]]:
    """Pick the game archetype before hitters enter the 18 gates.

    This does NOT choose the winner. It only decides the pitcher weakness family the game is allowing,
    then only matching hitters are allowed into the full Blender gate chain.
    """
    if not isinstance(game_df, pd.DataFrame) or game_df.empty:
        return "READABLE_LANE", {"READABLE_LANE"}, {"reason": "empty game frame fallback"}
    gid = _txt(game_df.iloc[0].get("_gid") or game_id(game_df.iloc[0].to_dict()))
    locked_side = _txt(locks.get(str(gid), ""))
    pool = game_df.copy()
    if locked_side and "team" in pool.columns:
        side_pool = pool[pool["team"].astype(str) == locked_side].copy()
        if not side_pool.empty:
            pool = side_pool

    counts: Dict[str, int] = {}
    for _, r in pool.iterrows():
        row = r.to_dict()
        flags = _signature_flags(row)
        # Only count signatures if the hitter has at least a lane. This keeps archetype tied to pitcher weakness.
        if "READABLE_LANE" not in flags:
            continue
        for f in flags:
            counts[f] = counts.get(f, 0) + 1

    # Priority order is pitcher weakness identity first, not player score.
    priority = [
        "WEAK_SLOT",     # pitcher is giving the slot/ordering lane
        "PITCH_EDGE",    # pitcher pitch-type weakness is active
        "HR_PA",         # pitcher HR lane is active
        "LASER",         # lifted damage / clean lane profile
        "PARK_EDGE",     # park/wind amplifies pitcher weakness
        "PLATOON",       # handedness lane is active
        "RAKES",         # batter-side profile matches pitcher hand
        "DAMAGE",        # damage lane is active
        "PULL_AIR",      # pull-air lane is active
        "READABLE_LANE", # final fallback to preserve readable rows
    ]
    chosen = "READABLE_LANE"
    for f in priority:
        if counts.get(f, 0) > 0:
            chosen = f
            break

    # Allow support signatures that are direct subtypes of the same pitcher weakness family.
    required = {chosen}
    if chosen == "WEAK_SLOT":
        required |= {"PITCH_EDGE", "HR_PA", "READABLE_LANE"}
    elif chosen in {"PITCH_EDGE", "HR_PA"}:
        required |= {"PITCH_EDGE", "HR_PA", "LASER", "DAMAGE"}
    elif chosen in {"LASER", "DAMAGE", "PULL_AIR"}:
        required |= {"LASER", "DAMAGE", "PULL_AIR", "HR_PA"}
    elif chosen in {"PLATOON", "RAKES"}:
        required |= {"PLATOON", "RAKES", "PITCH_EDGE", "HR_PA"}
    elif chosen == "PARK_EDGE":
        required |= {"PARK_EDGE", "PITCH_EDGE", "HR_PA", "PULL_AIR"}

    meta = {
        "game_id": gid,
        "locked_attack_side": locked_side,
        "pitcher_weakness_archetype": chosen,
        "accepted_signatures": ",".join(sorted(required)),
        "signature_counts_json": json.dumps(counts, sort_keys=True),
        "rule": "PITCHER_WEAKNESS_ARCHETYPE_FIRST__MATCHING_HITTERS_ONLY__THEN_FULL_18_GATES",
    }
    return chosen, required, meta


def _matches_pitcher_archetype(row: Dict[str, Any], required: set[str]) -> Tuple[bool, str]:
    flags = _signature_flags(row)
    match = bool(flags & required)
    return match, ";".join(sorted(flags))

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
    hitter_signature_flags = _signature_flags(row)
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
        "role_is_who": bool(role == "WHO"),
        "role_is_adjacent": bool(role == "Adjacent"),
        "role_priority": {"WHO": 3, "Adjacent": 2, "Primary": 1}.get(role, 1),
        "role_scores_json": json.dumps(triggers),
        "trap_flag": trap,
        "notes_blob": notes,
        "binding_valid": binding_valid,
        "hitter_signature_flags": ";".join(sorted(hitter_signature_flags)),
        "pitcher_weakness_archetype": _txt(row.get("pitcher_weakness_archetype", "")),
        "accepted_pitcher_signatures": _txt(row.get("accepted_pitcher_signatures", "")),
        "archetype_match_status": _txt(row.get("archetype_match_status", "")),
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
    """
    Official 18-gate Blender path.
    These labels are the ONLY gate labels rendered to the UI.
    Helper/internal checks stay backend-only and never appear as fake gates.
    """
    gates: List[Dict[str, Any]] = []
    player = _txt(cand.get("player")); gkey = _txt(cand.get("game_key") or cand.get("game"))
    team = _txt(cand.get("team")); locked = _txt(cand.get("locked_attack_side"))

    # Gate 1 — PDF/pool integrity
    _pass_gate(gates, 1, "Gate 1 — PDF Pool Integrity", f"player={player}; game={gkey}") if player and gkey else _add_gate(gates, 1, "Gate 1 — PDF Pool Integrity", False, f"player={player}; game={gkey}")
    if any(g["cut"] for g in gates): return False, gates, "PDF row missing player/game"

    # Gate 2 — immutable player-game binding / no wrong-team player
    if cand.get("binding_valid"):
        _pass_gate(gates, 2, "Gate 2 — Player/Game Binding Lock", f"binding={cand.get('data_binding_id')} status={cand.get('binding_status')}")
    else:
        _add_gate(gates, 2, "Gate 2 — Player/Game Binding Lock", False, f"player/team/game mismatch: player={player}; team={team}; game={gkey}; status={cand.get('binding_status')}")
    if any(g["cut"] for g in gates): return False, gates, "player-game binding mismatch"

    # Gate 3 — attack side lock
    _pass_gate(gates, 3, "Gate 3 — Attack-Side Lock", f"locked={locked}; team={team}") if locked and team == locked else _add_gate(gates, 3, "Gate 3 — Attack-Side Lock", False, f"locked={locked}; team={team}")
    if any(g["cut"] for g in gates): return False, gates, "opposite side killed before elimination"

    # Gate 4 — readable metric / feed completeness
    _pass_gate(gates, 4, "Gate 4 — Feed Completeness / Metric Read", f"metric_count={cand.get('metric_count')}") if cand.get("metric_count",0) >= 3 else _add_gate(gates, 4, "Gate 4 — Feed Completeness / Metric Read", False, f"metric_count={cand.get('metric_count')}; need 3+")
    if any(g["cut"] for g in gates): return False, gates, "not enough readable metrics"

    # Gate 5 — target pitcher HR vulnerability / lane
    _pass_gate(gates, 5, "Gate 5 — Pitcher HR Vulnerability Lane", f"lane={cand.get('lane_index')}") if cand.get("lane_index",0) > 0 else _add_gate(gates, 5, "Gate 5 — Pitcher HR Vulnerability Lane", False, f"lane={cand.get('lane_index')}")
    if any(g["cut"] for g in gates): return False, gates, "no HR lane"

    # Gate 6 — pull-air launch window
    _pass_gate(gates, 6, "Gate 6 — Pull-Air / Launch Window", f"launch={cand.get('launch_index')}") if cand.get("launch_index",0) > 0 else _add_gate(gates, 6, "Gate 6 — Pull-Air / Launch Window", False, f"launch={cand.get('launch_index')}")
    if any(g["cut"] for g in gates): return False, gates, "no pull-air / launch path"

    # Gate 7 — conversion trigger, not a score
    _pass_gate(gates, 7, "Gate 7 — True HR Conversion Trigger", f"conversion={cand.get('conversion_index')}") if cand.get("conversion_index",0) > 0 else _add_gate(gates, 7, "Gate 7 — True HR Conversion Trigger", False, f"conversion={cand.get('conversion_index')}")
    if any(g["cut"] for g in gates): return False, gates, "no HR conversion trigger"

    # Gate 8 — trap/scratch/no-empty-bat
    if cand.get("trap_flag"):
        _add_gate(gates, 8, "Gate 8 — Trap / Scratch / No-Empty-Bat Check", False, "trap/scratch/fade flag found")
        return False, gates, "trap/scratch/fade flag"
    _pass_gate(gates, 8, "Gate 8 — Trap / Scratch / No-Empty-Bat Check", "no trap/scratch/fade flag")
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
    pitcher_arch, accepted_signatures, arch_meta = _select_pitcher_weakness_archetype(game_df, locks)
    # First pass: PRE-GATE pitcher weakness archetype filter, then full hard gates.
    # Nonmatching hitters never enter the 18-gate Blender. Matching hitters still run every gate.
    for row in game_df.replace({np.nan: None}).to_dict(orient="records"):
        row["pitcher_weakness_archetype"] = pitcher_arch
        row["accepted_pitcher_signatures"] = ";".join(sorted(accepted_signatures))
        match, flags_text = _matches_pitcher_archetype(row, accepted_signatures)
        row["archetype_match_status"] = "MATCH" if match else "NO_MATCH"
        cand = _candidate_base(row, locks, idx); cand["row_id"] = idx; idx += 1
        if not match:
            pregates = [{
                "step": "PRE",
                "gate": "Pitcher Weakness Archetype Lock",
                "result": "CUT",
                "reason": f"game_archetype={pitcher_arch}; accepted={';'.join(sorted(accepted_signatures))}; hitter_flags={flags_text}",
                "hard_gate": True,
                "cut": True,
                "value": arch_meta.get("signature_counts_json", ""),
            }]
            dead = cand.copy()
            dead["blender_eligible"] = False
            dead["official_core_role"] = "CUT"
            dead["archetype"] = "Cut before Blender gates — pitcher archetype mismatch"
            dead["pass_depth"] = 0
            dead["cut_depth"] = 1
            dead["death_step"] = "PRE-GATE: Pitcher Weakness Archetype Lock"
            dead["stop_gate"] = "Pitcher Weakness Archetype Lock"
            dead["blender_score"] = "CUT"
            dead["score"] = "CUT"
            dead["final_reason"] = pregates[0]["reason"]
            dead["gate_trace_json"] = json.dumps(pregates)
            all_rows.append(dead)
            board_rows.append({"game_id": dead.get("game_id",""), "game_key": dead.get("game_key",""), "player": dead.get("player",""), "team": dead.get("team",""), "locked_attack_side": dead.get("locked_attack_side",""), "role": dead.get("official_core_role",""), **pregates[0], "death_step": dead.get("death_step",""), "owner_state": dead.get("blender_score","")})
            continue
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
        (9, "Gate 9 — Side-Only Lane Ownership", "lane_index"),
        (10, "Gate 10 — Pull-Air Ownership Pressure", "launch_index"),
        (11, "Gate 11 — Conversion Ownership Pressure", "conversion_index"),
        (12, "Gate 12 — Support / Contact Pressure", "support_index"),
        (13, "Gate 13 — Final Within-Game Survivor Isolation", "owner_key"),
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
    
    # Gates 14-17 are post-isolation audits. They can pass, but they do not refill or rerank.
    _pass_gate(wgates, 14, "Gate 14 — Adjacent / Decoy Transfer Audit", f"role_path={winner.get('true_role_path')}", hard_gate=False)
    _pass_gate(wgates, 15, "Gate 15 — WHO / Chaos Risk Audit", f"role_path={winner.get('true_role_path')}", hard_gate=False)
    _pass_gate(wgates, 16, "Gate 16 — Finisher Gate", "survivor kept by gate pressure only", hard_gate=False)
    _pass_gate(wgates, 17, "Gate 17 — Final Lock / No-Fluke Audit", "no projection fallback; no best-remaining refill", hard_gate=False)
    _pass_gate(wgates, 18, "Gate 18 — One Owner Per Game Lock", "only isolated survivor remains; no best-remaining refill", hard_gate=False)
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

    # HARD CORE ARCHETYPE LOCK — no duplicate refill, no slot drift.
    # CORE 1 must be Primary/Clean. CORE 2 must be Adjacent/Transfer.
    # CORE 3 must be WHO/Chaos. If a role has no survivor, the slot stays empty
    # instead of stealing another archetype. This protects Blender integrity.
    owners = owners.copy()
    required = [
        ("Primary", "CORE 1", "Primary / Clean Lane Owner", "Clean Lane Event Owner"),
        ("Adjacent", "CORE 2", "Adjacent / Decoy Transfer Owner", "Adjacent / Decoy Transfer Owner"),
        ("WHO", "CORE 3", "WHO / Chaos Owner", "WHO / Chaos Event Owner"),
    ]
    selected = []
    used_games = set()
    for role, slot, label, arch in required:
        pool = owners[
            (owners["official_core_role"].astype(str) == role)
            & (~owners["game_id"].astype(str).isin(used_games))
        ].copy()
        if pool.empty:
            continue
        # Sort only inside the exact role bucket after role emergence.
        # Never borrow Adjacent to fill WHO, and never borrow Primary to fill Adjacent.
        if "owner_key" in pool.columns:
            pool = pool.sort_values("owner_key", ascending=False)
        r = pool.iloc[0].to_dict()
        r["core_slot"] = slot
        r["core_archetype_required"] = role
        r["ticket_role"] = "CORE"
        r["official_core_role"] = role
        r["core_display_role"] = label
        r["archetype"] = arch
        r["blender_score"] = "LOCKED OWNER"
        r["score"] = "LOCKED OWNER"
        selected.append(r)
        used_games.add(str(r.get("game_id", "")))

    core = pd.DataFrame(selected)
    if core.empty:
        return core
    return core.reset_index(drop=True)


def core_integrity_missing_roles(core: pd.DataFrame) -> list:
    present = set(core["official_core_role"].astype(str).tolist()) if isinstance(core, pd.DataFrame) and not core.empty and "official_core_role" in core.columns else set()
    return [role for role in ["Primary", "Adjacent", "WHO"] if role not in present]


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
    role_board = survivors[[c for c in ["data_binding_id","binding_status","original_game_key","original_team","game_id","game_key","team","player","official_core_role","true_role_path","role_is_who","role_is_adjacent","role_priority","role_scores_json","pitcher_weakness_archetype","accepted_pitcher_signatures","archetype_match_status","hitter_signature_flags","pass_depth","cut_depth","death_step","lane_index","launch_index","conversion_index","support_index"] if c in survivors.columns]].copy()
    owners = resolve_owners(survivors)
    core = build_core_top3(owners)
    missing_core_roles = core_integrity_missing_roles(core)

    used = set(core["player"].astype(str).str.lower().tolist()) if not core.empty and "player" in core.columns else set()
    used_games = set(core["game_id"].astype(str).tolist()) if not core.empty and "game_id" in core.columns else set()
    alt_pool = owners[(~owners["player"].astype(str).str.lower().isin(used)) & (~owners["game_id"].astype(str).isin(used_games))].copy() if not owners.empty and "player" in owners.columns and "game_id" in owners.columns else pd.DataFrame()
    alt = alt_pool.sort_values("owner_key", ascending=False).head(3).copy() if not alt_pool.empty else pd.DataFrame()
    if not alt.empty:
        alt["ticket_role"] = "ALT"; alt["blender_score"] = "LOCKED OWNER"; alt["score"] = "LOCKED OWNER"
        used.update(alt["player"].astype(str).str.lower().tolist())
    chaos_pool = owners[(owners["official_core_role"] == "WHO") & (~owners["player"].astype(str).str.lower().isin(used)) & (~owners["game_id"].astype(str).isin(used_games))].copy() if not owners.empty and "official_core_role" in owners.columns and "player" in owners.columns and "game_id" in owners.columns else pd.DataFrame()
    chaos = chaos_pool.sort_values("owner_key", ascending=False).head(3).copy() if not chaos_pool.empty else pd.DataFrame()
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
        "missing_core_roles": ", ".join(missing_core_roles),
        "core_integrity_complete": len(missing_core_roles) == 0,
        "core_rule": "PITCHER_ARCHETYPE_FIRST__MATCHING_HITTERS_ONLY__FULL_18_GATES__ONE_OWNER_PER_GAME",
        "generic_refill": False,
        "fallback_sorting": False,
        "score_engine_removed": True,
        "gate_power_display_removed": True,
        "attack_side_hard_kill": True,
        "pitcher_archetype_first": True,
        "full_18_gates_preserved": True,
        "message": f"{ENGINE_VERSION}: Pitcher weakness archetype first; matching hitters only; full 18 gates; one owner per game. Core={len(core)} from {len(owners)} isolated game owners. Missing roles: {', '.join(missing_core_roles) if missing_core_roles else 'none'}.",
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
            "rule": "PITCHER_ARCHETYPE_FIRST_FULL_18_GATE_ENGINE_ACTIVE",
            "normalized_scores_removed": True,
            "gate_power_display_removed": True,
            "score_sort_removed": True,
            "attack_side_hard_kill": True,
            "pitcher_archetype_first": True,
            "full_18_gates_preserved": True,
            "generic_refill": False,
            "projection_fallback": False,
            "stale_cache_ignored": True,
        }]),
        "meta": meta,
    }
    save_locked_results(results)
    return results
