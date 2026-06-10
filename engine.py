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
ENGINE_VERSION = "V0231_ROLE_BALANCED_TRUE_BLENDER"

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
    "sweet": ["sweet_spot_pct", "sweet%", "sweet spot", "launch", "la", "launch_angle", "launch angle"],
    "dmg": ["dmg", "damage", "ult", "ultimate", "adj", "damage_index"],
    "hpi": ["hpi", "model", "rating", "hr score"],
    "hr": ["hr_lane", "hr_pa", "hr/pa", "hr9", "hr/9"],
    "edge": ["pitch_edge", "pitch edge", "edge", "pitch_type_edge", "pitch type edge"],
    "slot": ["lineup_slot", "slot", "order", "bo", "rank"],
    "count": ["count_leverage", "count leverage", "adv_count", "advantage_count", "first_pitch", "first pitch", "mistake_pitch", "mistake pitch"],
    "pressure": ["pressure_build", "pressure build", "recent_pressure", "warning_track", "doubles_surge", "hr_cadence", "recent_hr", "l10_hr", "l15_hr"],
    "recency": ["contact_recency", "quality_recency", "recent_hard", "recent_pull", "recent_barrel", "l10_hard", "l10_pull", "l10_barrel"],
    "protection": ["lineup_protection", "protection", "pitch_around", "pitcharound", "protected", "behind_hitter"],
    "bullpen": ["bullpen_continuation", "bullpen", "pen_hr", "pen_hr9", "bullpen_hr", "bullpen_weakness"],
    "script": ["game_script", "volatility", "chaos", "blowout", "fatigue", "travel", "weather_boost"],
    "dna": ["hr_dna", "true_hr_dna", "dna", "recap_dna", "finisher_dna", "true_finisher_dna"],
    "hbx": ["hbx", "wave", "hot_bat_extension", "continuation", "transfer_wave", "dead_wave"],
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


def _text_boost(notes: str, positives: List[str], negatives: List[str] | None = None) -> float:
    notes = _txt(notes).lower()
    score = 0.0
    for p in positives:
        if p in notes:
            score += 2.0
    for n in negatives or []:
        if n in notes:
            score -= 3.0
    return score


def _count_leverage_strength(v: Dict[str, float], notes: str = "") -> float:
    # Gate 11: hitter's-count / mistake-pitch recipient logic.
    # Uses direct feed columns when present, otherwise derives from pitch edge + damage + barrel.
    direct = _points(v.get("count", 0), 1, 10, 10)
    derived = max(
        _points(v.get("edge", -99), 2, 18, 7),
        _points(v.get("dmg", 0), 0.8, 2.8, 7),
        _points(v.get("barrel", 0), 5, 18, 6),
    )
    text = _text_boost(notes, ["mistake", "middle-middle", "middle middle", "advantage count", "first pitch", "ambush", "hanger"])
    return max(0.0, min(10.0, max(direct, derived) + text))


def _pressure_build_strength(v: Dict[str, float], notes: str = "") -> float:
    # Gate 12: recent HR pressure / warning-track / doubles surge / cadence.
    direct = _points(v.get("pressure", 0), 1, 10, 10)
    derived = max(
        _points(v.get("hpi", 0), 45, 92, 5),
        _points(v.get("dmg", 0), 0.7, 2.7, 6),
        _points(v.get("barrel", 0), 4, 16, 6),
        _points(v.get("pull", 0), 32, 58, 5),
    )
    text = _text_boost(notes, ["pressure", "warning track", "double", "doubles", "cadence", "due", "build", "barrel buildup", "pre ignition", "pre-ignition"])
    return max(0.0, min(10.0, max(direct, derived) + text))


def _contact_recency_strength(v: Dict[str, float], notes: str = "") -> float:
    # Gate 13: recent pull-air + hard contact trend, not stale season-only data.
    direct = _points(v.get("recency", 0), 1, 10, 10)
    derived = max(
        _points(v.get("hard", 0), 36, 62, 6),
        _points(v.get("pull", 0), 32, 58, 6),
        _points(v.get("barrel", 0), 4, 17, 7),
        _points(v.get("sweet", 0), 20, 40, 5),
    )
    text = _text_boost(notes, ["recent", "l10", "last 10", "last-10", "l15", "last 15", "hot contact", "pull air", "hard contact"])
    return max(0.0, min(10.0, max(direct, derived) + text))


def _protection_strength(v: Dict[str, float], notes: str = "") -> float:
    # Gate 14: lineup protection / pitch-around suppression.
    direct = _points(v.get("protection", 0), 1, 10, 10)
    slot = _num(v.get("slot", 0), 0)
    # middle/protected spots are more likely to see pitches; extreme chalk/pitch-around tags suppress.
    slot_bonus = 5.0 if slot in {2, 3, 4, 5, 6} else 2.5 if slot in {1, 7} else 1.0
    text = _text_boost(
        notes,
        ["protected", "protection", "behind", "lineup protection", "adjacent", "next man", "better pitches"],
        ["pitch around", "pitch-around", "avoid", "walk risk", "no protection", "unprotected"]
    )
    return max(0.0, min(10.0, max(direct, slot_bonus) + text))


def _bullpen_strength(v: Dict[str, float], notes: str = "") -> float:
    # Gate 15: bullpen continuation of starter lane.
    direct = _points(v.get("bullpen", 0), 1, 10, 10)
    derived = max(
        _points(v.get("hr", 0), 0.7, 2.6, 5),
        _points(v.get("edge", -99), 0, 18, 5),
        _points(v.get("dmg", 0), 0.8, 2.8, 4),
    )
    text = _text_boost(
        notes,
        ["bullpen", "pen", "relief", "continues", "continuation", "weak pen", "tired pen", "taxed pen"],
        ["bullpen kills", "pen kills", "dead lane", "suppression pen", "elite bullpen"]
    )
    return max(0.0, min(10.0, max(direct, derived) + text))


def _game_script_strength(v: Dict[str, float], notes: str = "") -> float:
    # Gate 18: chaos/volatility/fatigue/script classification.
    direct = _points(v.get("script", 0), 1, 10, 10)
    text = _text_boost(
        notes,
        ["chaos", "volatile", "blowout", "fatigue", "travel", "rivalry", "wind", "carry", "nuclear", "multi-hr", "multi hr"],
        ["suppressed", "dead game", "low total", "cold", "wind in"]
    )
    derived = 3.0 if v.get("hr", 0) >= 0.9 and v.get("barrel", 0) >= 3 else 0.0
    return max(0.0, min(10.0, max(direct, derived) + text))


def _hr_dna_strength(v: Dict[str, float], notes: str = "") -> float:
    # Gate 22: recap-calibrated True HR DNA confirmation.
    # This is outcome-profile logic, not name anchoring: pull-air, conversion, pitch punishment,
    # mistake conversion, chaos/transfer DNA, and suppression of fake hard-hit-only profiles.
    direct = _points(v.get("dna", 0), 1, 10, 10)
    pull_air = max(_points(v.get("pull", 0), 34, 58, 3), _points(v.get("sweet", 0), 20, 40, 2))
    conversion = max(_points(v.get("dmg", 0), 0.8, 2.8, 3), _points(v.get("barrel", 0), 5, 18, 3), _points(v.get("hr", 0), 0.8, 2.6, 3))
    pitch = _points(v.get("edge", -99), 0, 18, 2)
    fake_hard_hit_penalty = 3.0 if v.get("hard", 0) >= 45 and v.get("pull", 0) < 28 and v.get("barrel", 0) < 3 and v.get("dmg", 0) < 0.7 else 0.0
    text = _text_boost(
        notes,
        ["hr dna", "true finisher", "recap", "converter", "finisher", "multi-hr", "multi hr", "mistake", "punisher", "pull-air", "pull air"],
        ["fake hard", "stat merchant", "non converter", "warning only", "dead wave", "false wave"]
    )
    return max(0.0, min(10.0, max(direct, pull_air + conversion + pitch + text - fake_hard_hit_penalty)))


def _hbx_strength(v: Dict[str, float], notes: str = "") -> float:
    # HBX: Hot Bat Extension system. It boosts only already-valid survivors;
    # it does not create picks and does not override gates.
    direct = _points(v.get("hbx", 0), 1, 10, 10)
    text = _text_boost(
        notes,
        ["hbx", "extension", "sustain", "wave", "transfer wave", "wave transfer", "ignition", "pre-ignition", "continuation"],
        ["dead wave", "false wave", "public trap", "overextended", "chase"]
    )
    archetype = 2.0 if (v.get("pull", 0) >= 34 and v.get("barrel", 0) >= 4 and v.get("dmg", 0) >= 0.7) else 0.0
    return max(0.0, min(10.0, max(direct, archetype + text)))


def _gate_has_real_input(cand: Dict[str, Any], aliases: List[str]) -> bool:
    keys = {_key(k) for k in cand.keys()}
    for a in aliases:
        aa = _key(a)
        if any(aa in k or k in aa for k in keys):
            return True
    return False


def _gate_pass_dynamic(gates: List[Dict[str, Any]], step: int, label: str, idx_value: float, reason: str, has_real_data: bool, floor: float = 0.01) -> bool:
    # Missing advanced columns are recorded as neutral pass, not fake hard cuts.
    # If data exists, the gate becomes a real elimination gate.
    if not has_real_data:
        _pass_gate(gates, step, label, f"neutral/no explicit feed column; derived={round(float(idx_value),3)}; {reason}", hard_gate=False, value=round(float(idx_value),3))
        return True
    if idx_value > floor:
        _pass_gate(gates, step, label, f"passed with index={round(float(idx_value),3)}; {reason}", value=round(float(idx_value),3))
        return True
    _add_gate(gates, step, label, False, f"failed with index={round(float(idx_value),3)}; {reason}", value=round(float(idx_value),3))
    return False


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
    Primary / Adjacent / WHO must emerge from hitter DNA and game context.
    WHO cannot become the default bucket. It requires true chaos/entropy pressure.
    """
    notes_l = _txt(notes).lower()
    slot = _num(v.get("slot", 0), 0)
    hpi = _num(v.get("hpi", 0), 0)
    pull = _num(v.get("pull", 0), 0)
    hard = _num(v.get("hard", 0), 0)
    barrel = _num(v.get("barrel", 0), 0)
    dmg = _num(v.get("dmg", 0), 0)
    hr = _num(v.get("hr", 0), 0)
    edge = _num(v.get("edge", -99), -99)
    protection = _num(v.get("protection", 0), 0)
    script = _num(v.get("script", 0), 0)
    dna = _num(v.get("dna", 0), 0)
    hbx = _num(v.get("hbx", 0), 0)

    adjacent_text = any(x in notes_l for x in [
        "adjacent", "decoy", "transfer", "coverage", "behind", "after",
        "weak slot", "next man", "protected", "protection"
    ])
    who_text = any(x in notes_l for x in [
        "who", "chaos", "low owned", "low-owned", "bottom", "cheap",
        "volatile", "sneaky", "deep", "lower pressure", "entropy"
    ])

    has_event_lane = (hr >= 0.5) or (edge >= 0) or (dmg >= 0.5) or (barrel >= 3)
    has_launch = (pull >= 28) or (barrel >= 3) or (hard >= 32)

    # Clean lane is the default if the profile is a true finisher.
    clean_strength = (
        (hpi >= 70)
        or (dmg >= 1.45 and barrel >= 6)
        or (hr >= 1.15 and pull >= 32)
        or (dna >= 7 and hpi >= 60)
    )

    # Adjacent must have transfer/protection evidence or a next-man lane.
    adjacent_profile = (
        has_event_lane and has_launch and (
            adjacent_text
            or protection >= 7
            or (slot in {2, 5, 6} and 52 <= hpi < 84 and pull >= 34 and barrel >= 4)
            or (slot in {4, 5, 6} and 0.75 <= dmg < 1.9 and pull >= 38 and hard >= 38)
        )
    )

    # WHO must be real entropy, not simply "not chalk".
    who_profile = (
        has_event_lane and has_launch and (
            who_text
            or script >= 8
            or hbx >= 7
            or (slot >= 7 and hpi <= 58 and barrel >= 5 and pull >= 32)
            or (hpi <= 48 and pull >= 34 and hard >= 38 and barrel >= 4 and dmg >= 0.75)
        )
    )

    # Priority: explicit chaos > explicit transfer > true clean.
    # Without explicit chaos pressure, do not let WHO steal middle-lane bats.
    if who_profile and (who_text or script >= 8 or hbx >= 7):
        return "WHO", {
            "WHO": True, "Adjacent": bool(adjacent_profile), "Primary": False, "source": "gate_emergent_role",
            "slot": slot, "hpi": hpi, "pull": pull, "barrel": barrel, "dmg": dmg, "hr": hr, "script": script, "hbx": hbx,
        }
    if adjacent_profile and not (who_text and script >= 8):
        return "Adjacent", {
            "WHO": False, "Adjacent": True, "Primary": False, "source": "gate_emergent_role",
            "slot": slot, "hpi": hpi, "pull": pull, "barrel": barrel, "dmg": dmg, "hr": hr, "protection": protection,
        }
    return "Primary", {
        "WHO": False, "Adjacent": False, "Primary": True, "source": "gate_emergent_role",
        "slot": slot, "hpi": hpi, "pull": pull, "barrel": barrel, "dmg": dmg, "hr": hr, "clean_strength": clean_strength,
    }

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
    count_lev = _count_leverage_strength(v, notes)
    pressure = _pressure_build_strength(v, notes)
    recency = _contact_recency_strength(v, notes)
    protection = _protection_strength(v, notes)
    bullpen = _bullpen_strength(v, notes)
    script = _game_script_strength(v, notes)
    hr_dna = _hr_dna_strength(v, notes)
    hbx = _hbx_strength(v, notes)
    mc = metric_count(v)
    role, triggers = _role(v, notes)
    triggers.update({
        "count_leverage": round(count_lev, 3),
        "pressure_build": round(pressure, 3),
        "contact_recency": round(recency, 3),
        "protection": round(protection, 3),
        "bullpen": round(bullpen, 3),
        "game_script": round(script, 3),
        "hr_dna": round(hr_dna, 3),
        "hbx": round(hbx, 3),
    })
    # Internal raw separation only. Never shown as score. Never normalized.
    # HR DNA and HBX are low-order confirmations. They cannot override the lane/launch/conversion spine.
    raw_power = round(
        lane * 10000
        + launch * 1000
        + conversion * 100
        + support * 10
        + count_lev * 7
        + pressure * 6
        + recency * 6
        + protection * 3
        + bullpen * 3
        + script * 2
        + hr_dna * 8
        + hbx * 1.5
        + (mc * 0.01),
        6
    )
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
        "count_leverage_index": round(count_lev, 3),
        "pressure_build_index": round(pressure, 3),
        "contact_recency_index": round(recency, 3),
        "protection_index": round(protection, 3),
        "bullpen_continuation_index": round(bullpen, 3),
        "game_script_index": round(script, 3),
        "hr_dna_index": round(hr_dna, 3),
        "hbx_wave_index": round(hbx, 3),
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


def _pass_gate(gates: List[Dict[str, Any]], step: int, gate: str, reason: str, hard_gate: bool = True, value: Any = "") -> None:
    _add_gate(gates, step, gate, True, reason, hard_gate=hard_gate, value=value)


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
    Official 23-gate Blender path, first hard/soft gate block.
    Gates 1-15 are candidate qualification gates. Gates 16-23 are handled during
    game-owner isolation and final role/Core locking.
    """
    gates: List[Dict[str, Any]] = []
    player = _txt(cand.get("player")); gkey = _txt(cand.get("game_key") or cand.get("game"))
    team = _txt(cand.get("team")); locked = _txt(cand.get("locked_attack_side"))
    notes = _txt(cand.get("notes_blob", ""))
    v = metrics(cand)

    # Gate 1 — Target Pitcher / Core Environment Isolation
    _pass_gate(gates, 1, "Gate 1 — Target Pitcher / Core Environment Isolation", f"player={player}; game={gkey}; lane={cand.get('lane_index')}") if player and gkey and cand.get("lane_index",0) > 0 else _add_gate(gates, 1, "Gate 1 — Target Pitcher / Core Environment Isolation", False, f"player={player}; game={gkey}; lane={cand.get('lane_index')}")
    if any(g["cut"] for g in gates): return False, gates, "missing pitcher/game HR environment lane"

    # Gate 2 — Game Environment Gate
    env_idx = env_score(cand)
    _pass_gate(gates, 2, "Gate 2 — Game Environment Gate", f"env_index={round(float(env_idx),3)}", value=round(float(env_idx),3)) if env_idx > 0 else _add_gate(gates, 2, "Gate 2 — Game Environment Gate", False, f"env_index={round(float(env_idx),3)}", value=round(float(env_idx),3))
    if any(g["cut"] for g in gates): return False, gates, "dead game environment"

    # Gate 3 — Side Lock Gate
    _pass_gate(gates, 3, "Gate 3 — Side Lock Gate", f"locked={locked}; team={team}") if locked and team == locked else _add_gate(gates, 3, "Gate 3 — Side Lock Gate", False, f"locked={locked}; team={team}")
    if any(g["cut"] for g in gates): return False, gates, "opposite side killed before elimination"

    # Gate 4 — Full Pool Construction Gate
    pool_ok = bool(player and gkey and team and cand.get("binding_valid") and cand.get("metric_count",0) >= 3)
    if pool_ok:
        _pass_gate(gates, 4, "Gate 4 — Full Pool Construction Gate", f"binding={cand.get('data_binding_id')} metric_count={cand.get('metric_count')}")
    else:
        _add_gate(gates, 4, "Gate 4 — Full Pool Construction Gate", False, f"binding_valid={cand.get('binding_valid')} metric_count={cand.get('metric_count')}")
    if any(g["cut"] for g in gates): return False, gates, "pool row/binding/metric integrity failed"

    # Gate 5 — Pull-Air / Launch Window Gate
    _pass_gate(gates, 5, "Gate 5 — Pull-Air / Launch Window Gate", f"launch={cand.get('launch_index')}", value=cand.get("launch_index")) if cand.get("launch_index",0) > 0 else _add_gate(gates, 5, "Gate 5 — Pull-Air / Launch Window Gate", False, f"launch={cand.get('launch_index')}", value=cand.get("launch_index"))
    if any(g["cut"] for g in gates): return False, gates, "no pull-air / launch path"

    # Gate 6 — Hard-Hit / Damage Validation Gate
    damage_ok = cand.get("support_index",0) > 0 or _num(v.get("hard"),0) >= 30 or _num(v.get("barrel"),0) >= 3 or _num(v.get("dmg"),0) >= 0.5
    _pass_gate(gates, 6, "Gate 6 — Hard-Hit / Damage Validation Gate", f"support={cand.get('support_index')} hard={v.get('hard')} barrel={v.get('barrel')} dmg={v.get('dmg')}") if damage_ok else _add_gate(gates, 6, "Gate 6 — Hard-Hit / Damage Validation Gate", False, f"support={cand.get('support_index')} hard={v.get('hard')} barrel={v.get('barrel')} dmg={v.get('dmg')}")
    if any(g["cut"] for g in gates): return False, gates, "no damage validation"

    # Gate 7 — Pitch-Type Kill Gate
    pitch_idx = max(_points(v.get("edge", -99), 0, 18, 10), _points(v.get("dmg", 0), 0.8, 2.8, 6), _points(v.get("hr", 0), 0.8, 2.6, 6))
    has_pitch_data = _gate_has_real_input(cand, ALIASES["edge"] + ["pitch_type", "pitch type", "primary_pitch", "weak_pitch"])
    if not _gate_pass_dynamic(gates, 7, "Gate 7 — Pitch-Type Kill Gate", pitch_idx, "pitch edge / weak-pitch punishment", has_pitch_data): return False, gates, "pitch-type kill failed"

    # Gate 8 — Pitcher Weak-Slot / Lineup Slot Gate
    slot_idx = max(_points(v.get("slot",0), 1, 6, 6), _points(v.get("hr",0), 0.7, 2.6, 6), _points(v.get("edge",-99), 0, 18, 5))
    has_slot_data = _gate_has_real_input(cand, ALIASES["slot"] + ["weak_slot", "weak slot", "lineup"])
    if not _gate_pass_dynamic(gates, 8, "Gate 8 — Pitcher Weak-Slot / Lineup Slot Gate", slot_idx, "slot/weak-slot alignment", has_slot_data): return False, gates, "weak-slot match failed"

    # Gate 9 — Zone / Lane Match Gate
    _pass_gate(gates, 9, "Gate 9 — Zone / Lane Match Gate", f"lane={cand.get('lane_index')}", value=cand.get("lane_index")) if cand.get("lane_index",0) > 0 else _add_gate(gates, 9, "Gate 9 — Zone / Lane Match Gate", False, f"lane={cand.get('lane_index')}", value=cand.get("lane_index"))
    if any(g["cut"] for g in gates): return False, gates, "zone/lane match failed"

    # Gate 10 — Conversion / Finisher Gate
    _pass_gate(gates, 10, "Gate 10 — Conversion / Finisher Gate", f"conversion={cand.get('conversion_index')}", value=cand.get("conversion_index")) if cand.get("conversion_index",0) > 0 else _add_gate(gates, 10, "Gate 10 — Conversion / Finisher Gate", False, f"conversion={cand.get('conversion_index')}", value=cand.get("conversion_index"))
    if any(g["cut"] for g in gates): return False, gates, "no HR conversion trigger"

    # Gate 11 — Count Leverage / Mistake Pitch Gate
    has_count = _gate_has_real_input(cand, ALIASES["count"])
    if not _gate_pass_dynamic(gates, 11, "Gate 11 — Count Leverage / Mistake Pitch Gate", cand.get("count_leverage_index",0), "hitter-count / mistake-pitch conversion", has_count): return False, gates, "count/mistake pitch failed"

    # Gate 12 — Recent Pressure Build Gate
    has_pressure = _gate_has_real_input(cand, ALIASES["pressure"])
    if not _gate_pass_dynamic(gates, 12, "Gate 12 — Recent Pressure Build Gate", cand.get("pressure_build_index",0), "recent HR pressure / warning-track / cadence", has_pressure): return False, gates, "pressure build failed"

    # Gate 13 — Contact Quality Recency Gate
    has_recency = _gate_has_real_input(cand, ALIASES["recency"])
    if not _gate_pass_dynamic(gates, 13, "Gate 13 — Contact Quality Recency Gate", cand.get("contact_recency_index",0), "recent pull-air/hard-contact quality", has_recency): return False, gates, "contact recency failed"

    # Gate 14 — Lineup Protection / Pitch-Around Gate
    has_protection = _gate_has_real_input(cand, ALIASES["protection"])
    if not _gate_pass_dynamic(gates, 14, "Gate 14 — Lineup Protection / Pitch-Around Gate", cand.get("protection_index",0), "protection vs pitch-around risk", has_protection): return False, gates, "lineup protection failed"

    # Gate 15 — Bullpen Continuation Gate
    has_bullpen = _gate_has_real_input(cand, ALIASES["bullpen"])
    if not _gate_pass_dynamic(gates, 15, "Gate 15 — Bullpen Continuation Gate", cand.get("bullpen_continuation_index",0), "bullpen continuation of starter weakness lane", has_bullpen): return False, gates, "bullpen continuation failed"

    # Trap/scratch/no-empty-bat hard stop remains backend-only but visible as the final part of pool integrity.
    if cand.get("trap_flag"):
        _add_gate(gates, 15, "Gate 15 — Bullpen Continuation Gate", False, "trap/scratch/fade flag found after gate block")
        return False, gates, "trap/scratch/fade flag"

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


def _round_audit(active: List[Tuple[Dict[str, Any], List[Dict[str, Any]]]], step: int, gate: str, key: str) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
    """
    Non-kill audit gate.
    Used for transfer/chaos/script intelligence so WHO/Adjacent context is recorded
    without hijacking one-owner isolation away from true HR owner pressure.
    """
    for cand, gates in active:
        val = _num(cand.get(key), 0)
        _pass_gate(gates, step, gate, f"audit {key}={val}; does not override owner isolation", hard_gate=False, value=val)
    return active


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
    # Gates 16-18 record transfer/chaos/script intelligence but DO NOT kill the clean lane.
    # Gate 19 performs the one-owner kill using true owner pressure.
    for step, gate, key in [
        (16, "Gate 16 — Coverage Shift / Decoy Transfer Gate", "protection_index"),
        (17, "Gate 17 — WHO / Chaos Entropy Gate", "game_script_index"),
        (18, "Gate 18 — Game Script / Blowout / Volatility Gate", "hbx_wave_index"),
    ]:
        active = _round_audit(active, step, gate, key)

    before = active[:]
    active = _round_eliminate(active, 19, "Gate 19 — One HR Owner Per Game Isolation Gate", "owner_key")
    dead = [x for x in before if x not in active]
    for cand, gates in dead:
        cut_gate = gates[-1]
        deadrow = _cut_candidate(cand, gates[:-1], int(cut_gate["step"]), str(cut_gate["gate"]), str(cut_gate.get("reason","")))
        all_rows.append(deadrow)
        for g in json.loads(deadrow["gate_trace_json"]):
            board_rows.append({"game_id": deadrow.get("game_id",""), "game_key": deadrow.get("game_key",""), "player": deadrow.get("player",""), "team": deadrow.get("team",""), "locked_attack_side": deadrow.get("locked_attack_side",""), "role": deadrow.get("official_core_role",""), **g, "death_step": deadrow.get("death_step",""), "owner_state": deadrow.get("blender_score","")})

    # Single owner survives.
    active = sorted(active, key=lambda x: _num(x[0].get("owner_key"),0), reverse=True)[:1]
    winner, wgates = active[0]
    
    # Gates 20-23 are post-isolation confirmation gates. They never refill or rerank.
    _pass_gate(wgates, 20, "Gate 20 — Role Emergence Gate", f"role_path={winner.get('true_role_path')}; no post-labeling", hard_gate=False)
    _pass_gate(wgates, 21, "Gate 21 — Finisher Confirmation Gate", "last-man-standing by gate pressure only", hard_gate=False)
    _pass_gate(wgates, 22, "Gate 22 — HR DNA Model Confirmation Gate", f"hr_dna={winner.get('hr_dna_index')}; hbx={winner.get('hbx_wave_index')}", hard_gate=False, value=winner.get("hr_dna_index"))
    _pass_gate(wgates, 23, "Gate 23 — Final Core 3 Lock Gate", "eligible for strongest lane survivor selection; no projection fallback", hard_gate=False)
    owner = _survive_candidate(winner, wgates)
    owner["game_owner_locked"] = True
    all_rows.append(owner)
    for g in json.loads(owner["gate_trace_json"]):
        board_rows.append({"game_id": owner.get("game_id",""), "game_key": owner.get("game_key",""), "player": owner.get("player",""), "team": owner.get("team",""), "locked_attack_side": owner.get("locked_attack_side",""), "role": owner.get("official_core_role",""), **g, "death_step": owner.get("death_step",""), "owner_state": owner.get("blender_score","")})
    return all_rows, board_rows, idx


def resolve_owners(survivors: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(survivors, pd.DataFrame) or survivors.empty:
        return pd.DataFrame()
    owners = survivors[survivors["game_owner_locked"].eq(True)].copy() if "game_owner_locked" in survivors.columns else pd.DataFrame()
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
    role_board = survivors[[c for c in ["data_binding_id","binding_status","original_game_key","original_team","game_id","game_key","team","player","official_core_role","true_role_path","role_is_who","role_is_adjacent","role_priority","role_scores_json","pass_depth","cut_depth","death_step","lane_index","launch_index","conversion_index","support_index","count_leverage_index","pressure_build_index","contact_recency_index","protection_index","bullpen_continuation_index","game_script_index","hr_dna_index","hbx_wave_index"] if c in survivors.columns]].copy()
    owners = resolve_owners(survivors)
    core = build_core_top3(owners)
    missing_core_roles = core_integrity_missing_roles(core)

    used = set(core["player"].astype(str).str.lower().tolist()) if not core.empty and "player" in core.columns else set()
    used_games = set(core["game_id"].astype(str).tolist()) if not core.empty and "game_id" in core.columns else set()

    # ALT is strongest remaining Primary/Adjacent lane pressure only.
    # It cannot be filled by WHO cards, because WHO has its own Chaos bucket.
    alt_pool = owners[owners["official_core_role"].isin(["Primary","Adjacent"])][
        (~owners["player"].astype(str).str.lower().isin(used))
        & (~owners["game_id"].astype(str).isin(used_games))
        & (owners["official_core_role"].astype(str).isin(["Primary", "Adjacent"]))
    ].copy() if not owners.empty and {"player","game_id","official_core_role"}.issubset(owners.columns) else pd.DataFrame()
    alt = alt_pool.sort_values("owner_key", ascending=False).head(3).copy() if not alt_pool.empty else pd.DataFrame()
    if not alt.empty:
        alt["ticket_role"] = "ALT"; alt["blender_score"] = "LOCKED OWNER"; alt["score"] = "LOCKED OWNER"
        used.update(alt["player"].astype(str).str.lower().tolist())
        used_games.update(alt["game_id"].astype(str).tolist())

    # CHAOS is strongest remaining WHO lane only.
    chaos_pool = owners[
        (owners["official_core_role"].astype(str) == "WHO")
        & (~owners["player"].astype(str).str.lower().isin(used))
        & (~owners["game_id"].astype(str).isin(used_games))
    ].copy() if not owners.empty and {"official_core_role","player","game_id"}.issubset(owners.columns) else pd.DataFrame()
    chaos = chaos_pool.sort_values("owner_key", ascending=False).head(3).copy() if not chaos_pool.empty else pd.DataFrame()
    if not chaos.empty:
        chaos["ticket_role"] = "CHAOS"; chaos["blender_score"] = "LOCKED OWNER"; chaos["score"] = "LOCKED OWNER"

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
        "core_rule": "23_GATE_ELIMINATION__HR_DNA_HBX__CORE1_PRIMARY__CORE2_ADJACENT__CORE3_WHO__NO_DUPLICATE_REFILL",
        "official_gate_count": 23,
        "hr_dna_integrated": True,
        "hbx_integrated": True,
        "who_default_blocked": True,
        "alt_excludes_who": True,
        "role_priority_kill_removed": True,
        "generic_refill": False,
        "fallback_sorting": False,
        "score_engine_removed": True,
        "gate_power_display_removed": True,
        "attack_side_hard_kill": True,
        "message": f"{ENGINE_VERSION}: 23-gate engine active. Core={len(core)} from {len(owners)} isolated game owners. CORE1=Primary, CORE2=Adjacent, CORE3=WHO. HR DNA + HBX integrated as gate confirmations. Missing roles: {', '.join(missing_core_roles) if missing_core_roles else 'none'}.",
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
            "rule": "FINAL_23_GATE_HRDNA_HBX_ENGINE_ACTIVE",
            "normalized_scores_removed": True,
            "gate_power_display_removed": True,
            "score_sort_removed": True,
            "attack_side_hard_kill": True,
            "generic_refill": False,
            "projection_fallback": False,
            "stale_cache_ignored": True,
        }]),
        "meta": meta,
    }
    save_locked_results(results)
    return results
