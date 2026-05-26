
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

import numpy as np
import pandas as pd

from official_mlb_slate import fetch_official_mlb_slate, attach_official_slate_to_feed, official_game_count
from feeder import actual_game_count

DATA_DIR = Path("data")
LOCK_PATH = DATA_DIR / "locked_owners.json"


# ============================================================
# UTILITIES
# ============================================================

def _txt(x) -> str:
    try:
        if x is None or pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def _num(x, default: float = 0.0) -> float:
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


def _key(s: str) -> str:
    return str(s).lower().replace(" ", "").replace("_", "").replace("%", "").replace("/", "").replace("-", "")


def _field(row: Dict[str, Any], names: List[str], default: float = 0.0) -> float:
    cmap = {_key(k): k for k in row.keys()}
    for name in names:
        kk = _key(name)
        if kk in cmap:
            return _num(row.get(cmap[kk]), default)
    for name in names:
        kk = _key(name)
        for ck, real in cmap.items():
            if kk in ck or ck in kk:
                return _num(row.get(real), default)
    return default


def _strength(x: float, floor: float, elite: float, points: float) -> float:
    x = _num(x, 0.0)
    if x < floor:
        return 0.0
    if x >= elite:
        return float(points)
    return float(points) * ((x - floor) / max(1.0, elite - floor))


def _safe_df(x) -> pd.DataFrame:
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()


def csv_bytes(df: pd.DataFrame) -> bytes:
    return _safe_df(df).to_csv(index=False).encode("utf-8")


# ============================================================
# OFFICIAL MLB SLATE BRIDGE
# ============================================================

def fetch_live_public_slate(date_str=None):
    return fetch_official_mlb_slate(date_str)


def fetch_live_public_hitter_pool(date_str=None):
    return fetch_official_mlb_slate(date_str)


def attach_slate_matchup_context(df, public_context=None):
    return attach_official_slate_to_feed(df, public_context)


def merge_public_context(df, public_context=None):
    return attach_slate_matchup_context(df, public_context)


# ============================================================
# LOCKED RESULTS STORAGE
# ============================================================

def _df_to_records(df: pd.DataFrame):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []
    return df.replace({np.nan: None}).to_dict(orient="records")


def _records_to_df(records):
    return pd.DataFrame(records or [])


def save_locked_results(results: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    payload = {
        "meta": results.get("meta", {}),
        "owners": _df_to_records(results.get("owners")),
        "core": _df_to_records(results.get("core")),
        "alt": _df_to_records(results.get("alt")),
        "chaos": _df_to_records(results.get("chaos")),
        "survivors": _df_to_records(results.get("survivors")),
        "cuts": _df_to_records(results.get("cuts")),
        "game_board": _df_to_records(results.get("game_board")),
        "role_board": _df_to_records(results.get("role_board")),
        "environment_board": _df_to_records(results.get("environment_board")),
    }
    LOCK_PATH.write_text(json.dumps(payload, indent=2))


def load_locked_results() -> Dict[str, Any]:
    if not LOCK_PATH.exists():
        return empty_results("Run the Blender first.")
    try:
        payload = json.loads(LOCK_PATH.read_text())
        return {
            "meta": payload.get("meta", {}),
            "owners": _records_to_df(payload.get("owners")),
            "core": _records_to_df(payload.get("core")),
            "alt": _records_to_df(payload.get("alt")),
            "chaos": _records_to_df(payload.get("chaos")),
            "survivors": _records_to_df(payload.get("survivors")),
            "cuts": _records_to_df(payload.get("cuts")),
            "game_board": _records_to_df(payload.get("game_board")),
            "role_board": _records_to_df(payload.get("role_board")),
            "environment_board": _records_to_df(payload.get("environment_board")),
        }
    except Exception:
        return empty_results("Locked results could not be read. Re-run Blender.")


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
        "meta": {
            "engine_version": "LOCKED_REAL_BLENDER_MACHINE",
            "message": message,
            "owners_locked": 0,
            "core_count": 0,
            "passed_rows": 0,
            "cut_rows": 0,
        },
    }


# ============================================================
# LOCKED BLENDER MACHINE
# ============================================================

METRIC_ALIASES = {
    "pull": ["pull_pct", "pull%", "pull"],
    "hard": ["hard_hit_pct", "hardhit%", "hard_hit%", "hard hit%", "hh%"],
    "barrel": ["barrel_pct", "barrel%", "brl%", "barrel"],
    "sweet": ["sweet_spot_pct", "sweet%", "sweet spot", "launch", "la"],
    "dmg": ["dmg", "damage", "ult", "ultimate", "adj"],
    "hpi": ["hpi", "model", "rating", "hr score"],
    "hr": ["hr_lane", "hr_pa", "hr/pa", "hr9", "hr/9"],
    "edge": ["pitch_edge", "pitch edge", "edge"],
    "slot": ["lineup_slot", "slot", "order", "bo"],
}


def row_metrics(row: Dict[str, Any]) -> Dict[str, float]:
    return {name: _field(row, aliases, -99.0 if name == "edge" else 0.0) for name, aliases in METRIC_ALIASES.items()}


def metric_count(vals: Dict[str, float]) -> int:
    count = 0
    for k, v in vals.items():
        if k == "edge":
            if v != -99:
                count += 1
        elif v not in [None, 0] and not pd.isna(v):
            count += 1
    return count


def environment_value(row: Dict[str, Any]) -> float:
    v = row_metrics(row)
    return (
        _strength(v["hr"], 0.8, 2.4, 15)
        + _strength(v["edge"], 0, 15, 12)
        + _strength(v["dmg"], 0.8, 2.4, 12)
        + _strength(v["hpi"], 20, 80, 10)
        + _strength(v["barrel"], 5, 16, 8)
        + _strength(v["pull"], 30, 55, 6)
    )


def game_id(row: Dict[str, Any]) -> str:
    pk = _txt(row.get("game_pk"))
    if pk and pk.lower() not in {"nan", "none"}:
        return pk
    return _txt(row.get("game_key") or row.get("game"))


def player_is_pitcher(row: Dict[str, Any]) -> bool:
    player = _txt(row.get("player")).lower()
    pitcher = _txt(row.get("pitcher")).lower()
    return bool(player and pitcher and player == pitcher)


def normalize_feed(df: pd.DataFrame) -> pd.DataFrame:
    df = _safe_df(df).copy()
    if df.empty:
        return df
    if "game_key" not in df.columns:
        df["game_key"] = df["game"] if "game" in df.columns else ""
    if "player" in df.columns and "pitcher" in df.columns:
        df = df[~df.apply(lambda r: player_is_pitcher(r.to_dict()), axis=1)].copy()
    if "official_slate_attached" not in df.columns:
        df["official_slate_attached"] = False
    return df.reset_index(drop=True)


def lock_attack_sides(df: pd.DataFrame) -> Tuple[Dict[str, str], pd.DataFrame]:
    rows = []
    locks: Dict[str, str] = {}
    if df.empty:
        return locks, pd.DataFrame()

    work = df.copy()
    work["_game_id"] = work.apply(lambda r: game_id(r.to_dict()), axis=1)
    for gid, game_df in work.groupby("_game_id", dropna=False):
        if not _txt(gid):
            continue

        team_scores = []
        for team, tdf in game_df.groupby("team", dropna=False):
            if not _txt(team):
                continue
            vals = [environment_value(r.to_dict()) for _, r in tdf.iterrows()]
            side_score = max(vals) + (sum(vals) / max(1, len(vals))) * 0.25
            team_scores.append((team, side_score, len(tdf)))

        if not team_scores:
            continue

        team_scores.sort(key=lambda x: x[1], reverse=True)
        locked_team, locked_score, count = team_scores[0]
        locks[str(gid)] = _txt(locked_team)

        rows.append({
            "game_id": str(gid),
            "game_key": _txt(game_df.iloc[0].get("game_key") or game_df.iloc[0].get("game")),
            "locked_attack_side": _txt(locked_team),
            "attack_score": round(float(locked_score), 2),
            "candidate_rows": int(count),
            "side_rule": "ONE ATTACK SIDE LOCKED BEFORE HITTER GATES",
        })

    return locks, pd.DataFrame(rows)


def add_gate(gates: List[Dict[str, Any]], step: int, gate: str, passed: bool, score: float, max_score: float, reason: str, hard_gate: bool = True):
    gates.append({
        "step": step,
        "gate": gate,
        "result": "PASS" if passed else "CUT",
        "score": round(float(max(score, 0.0)), 2),
        "max_score": float(max_score),
        "reason": reason,
        "hard_gate": bool(hard_gate),
        "cut": bool(hard_gate and not passed),
    })


def evaluate_candidate(row: Dict[str, Any], locked_sides: Dict[str, str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, float]]:
    vals = row_metrics(row)

    player = _txt(row.get("player"))
    team = _txt(row.get("team"))
    pitcher = _txt(row.get("pitcher"))
    gkey = _txt(row.get("game_key") or row.get("game"))
    gid = game_id(row)
    locked_team = locked_sides.get(str(gid), "")
    notes = " ".join([_txt(row.get(k)) for k in row.keys() if any(x in str(k).lower() for x in ["note", "tag", "raw", "status"])]).lower()

    pull, hard, barrel, sweet, dmg, hpi, hr, edge, slot = [vals[k] for k in ["pull", "hard", "barrel", "sweet", "dmg", "hpi", "hr", "edge", "slot"]]
    mc = metric_count(vals)
    trigger = pull >= 30 or hard >= 30 or barrel >= 5 or dmg >= 0.8 or hpi >= 20 or hr >= 0.8 or edge >= 0

    gates: List[Dict[str, Any]] = []
    add_gate(gates, 0, "Real PDF row", bool(player and gkey), 8 if player and gkey else 0, 8, f"player={player}; game={gkey}")
    add_gate(gates, 1, "One attack side lock", bool(locked_team and team == locked_team), 10 if locked_team and team == locked_team else 0, 10, f"locked={locked_team}; row_team={team}")
    add_gate(gates, 2, "Metric survival", mc >= 3 and trigger, 10 if mc >= 3 and trigger else 0, 10, f"metric_count={mc}; trigger={trigger}")
    lane_score = max(_strength(hr, 0.8, 2.4, 10), _strength(edge, 0, 15, 10), _strength(dmg, 0.8, 2.4, 10), _strength(hpi, 20, 80, 10))
    add_gate(gates, 3, "Pitcher HR lane", lane_score > 0, lane_score, 10, f"hr={hr}; edge={edge}; dmg={dmg}; hpi={hpi}")
    launch_score = max(_strength(pull, 30, 55, 12), _strength(sweet, 20, 38, 12), _strength(barrel, 5, 16, 12))
    add_gate(gates, 4, "Pull-air / launch", launch_score > 0, launch_score, 12, f"pull={pull}; sweet={sweet}; barrel={barrel}")
    conversion_score = max(_strength(dmg, 0.8, 2.4, 12), _strength(barrel, 5, 16, 12), _strength(hpi, 20, 80, 12), _strength(hr, 0.8, 2.4, 12))
    add_gate(gates, 5, "Conversion / damage", conversion_score > 0, conversion_score, 12, f"dmg={dmg}; barrel={barrel}; hpi={hpi}; hr={hr}")
    add_gate(gates, 6, "Lineup opportunity", slot == 0 or slot <= 7, 6 if slot == 0 or slot <= 7 else 2, 6, f"slot={slot}", hard_gate=False)
    support_score = max(_strength(hard, 30, 58, 8), _strength(barrel, 5, 16, 8), _strength(dmg, 0.8, 2.4, 8))
    add_gate(gates, 7, "Hard-hit support", support_score > 0, support_score, 8, f"hard={hard}; barrel={barrel}; dmg={dmg}", hard_gate=False)

    adjacent_trigger = any(x in notes for x in ["adjacent", "decoy", "transfer", "coverage", "weak slot"])
    who_trigger = "who" in notes or "chaos" in notes or (pull >= 30 and hard >= 30 and hpi < 45)

    add_gate(gates, 8, "Adjacent / decoy audit", True, 6 if adjacent_trigger else 2, 6, "triggered" if adjacent_trigger else "checked", hard_gate=False)
    add_gate(gates, 9, "WHO / chaos audit", True, 7 if who_trigger else 2, 7, "triggered" if who_trigger else "checked", hard_gate=False)

    trap = "trap" in notes or "red flag" in notes
    add_gate(gates, 10, "Trap audit", not trap, 8 if not trap else 0, 8, "no trap" if not trap else "trap/red flag")

    finisher_score = 0
    if pull >= 34:
        finisher_score = max(
            _strength(hard, 30, 58, 14),
            _strength(barrel, 5, 16, 14),
            _strength(dmg, 0.8, 2.4, 14),
            _strength(hpi, 20, 80, 14),
            _strength(hr, 0.8, 2.4, 14),
        )
    add_gate(gates, 11, "Finisher gate", finisher_score > 0, finisher_score, 14, f"pull={pull}; hard={hard}; barrel={barrel}; dmg={dmg}; hpi={hpi}; hr={hr}")

    final_score = max(
        _strength(pull, 30, 55, 10),
        _strength(hard, 30, 58, 10),
        _strength(barrel, 5, 16, 10),
        _strength(dmg, 0.8, 2.4, 10),
        _strength(hpi, 20, 80, 10),
        _strength(hr, 0.8, 2.4, 10),
    )
    add_gate(gates, 12, "Gate 19 confirmation", final_score > 0, final_score, 10, f"final_strength={round(final_score, 2)}")

    hard_cut = any(g["cut"] for g in gates)
    raw = sum(g["score"] for g in gates)
    max_raw = sum(g["max_score"] for g in gates)
    survival_depth = sum(1 for g in gates if g["result"] == "PASS") / max(1, len(gates))

    # Score is gate survival + quality. It is NOT an odds probability and not a generic ranking score.
    quality = raw / max(1, max_raw)
    shape_bonus = (
        min(pull, 60) * 0.02
        + min(hard, 65) * 0.012
        + min(barrel, 18) * 0.12
        + min(dmg, 3) * 0.55
        + min(hpi, 85) * 0.018
        + min(hr, 3) * 0.40
        + (max(min(edge, 25), -15) * 0.03 if edge != -99 else 0)
    )
    blender_score = round(max(1, min(92, (survival_depth * 42) + (quality * 45) + shape_bonus)), 1)
    if hard_cut:
        blender_score = round(min(blender_score, 59.9), 1)

    primary_score = (
        _strength(pull, 36, 55, 22)
        + _strength(barrel, 7, 16, 20)
        + _strength(dmg, 1, 2.4, 18)
        + _strength(hpi, 30, 80, 15)
        + _strength(hr, 1, 2.5, 15)
        + _strength(edge, 0, 20, 10)
    )
    adjacent_score = (
        _strength(pull, 30, 46, 18)
        + _strength(hard, 30, 52, 18)
        + _strength(dmg, 0.8, 1.8, 15)
        + _strength(hpi, 20, 60, 10)
        + (35 if adjacent_trigger else 0)
    )
    who_score = (
        _strength(pull, 28, 42, 16)
        + _strength(hard, 30, 48, 16)
        + _strength(hr, 0.8, 1.8, 16)
        + _strength(edge, 0, 12, 10)
        + (35 if who_trigger else 0)
        + (8 if hpi < 45 else 0)
    )
    role_scores = {"Primary": round(primary_score, 1), "Adjacent": round(adjacent_score, 1), "WHO": round(who_score, 1)}

    role = max(role_scores, key=role_scores.get)
    eligible = not hard_cut and blender_score >= 55
    if not eligible:
        role = "CUT"

    archetype = {
        "Primary": "Primary HR Owner",
        "Adjacent": "Adjacent / Decoy Transfer",
        "WHO": "WHO / Chaos Owner",
        "CUT": "Cut by gates",
    }[role]

    result = {
        **row,
        "game_id": gid,
        "locked_attack_side": locked_team,
        "blender_eligible": bool(eligible),
        "blender_score": blender_score,
        "support_score": round(raw, 2),
        "score": blender_score,
        "official_core_role": role,
        "archetype": archetype,
        "metric_count": mc,
        "stop_gate": "" if eligible else next((g["gate"] for g in gates if g["cut"]), "cut"),
        "final_reason": f"{role} survived all hard gates" if eligible else "CUT — see gate trace",
        "gate_trace_json": json.dumps(gates),
        "role_scores_json": json.dumps(role_scores),
    }

    return result, gates, role_scores


def resolve_owners(survivors: pd.DataFrame) -> pd.DataFrame:
    passed = survivors[survivors["blender_eligible"] == True].copy()
    if passed.empty:
        return pd.DataFrame()

    group_col = "game_id"
    rows = []
    for gid, g in passed.groupby(group_col, dropna=False):
        if not _txt(gid):
            continue
        # Owner resolver uses gate survival state and role strength, not generic refill sorting.
        g = g.copy()
        g["_owner_quality"] = g["support_score"].fillna(0) + g["blender_score"].fillna(0)
        pick = g.sort_values(["_owner_quality", "blender_score"], ascending=[False, False]).iloc[0].drop(labels=["_owner_quality"], errors="ignore").to_dict()
        pick["game_owner"] = pick.get("game_key", gid)
        rows.append(pick)

    owners = pd.DataFrame(rows)
    if owners.empty:
        return owners
    return owners.sort_values(["support_score", "blender_score"], ascending=[False, False]).reset_index(drop=True)


def build_structured_core(owners: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(owners, pd.DataFrame) or owners.empty:
        return pd.DataFrame()

    used_players = set()
    used_games = set()
    parts = []

    def gid(row):
        return _txt(row.get("game_id") or row.get("game_pk") or row.get("game_key"))

    # No generic best-score refill. Slots can only be filled by surviving role paths.
    for slot, role in [("PRIMARY", "Primary"), ("ADJACENT", "Adjacent"), ("WHO", "WHO")]:
        pool = owners[owners["official_core_role"].astype(str) == role].copy()
        if pool.empty:
            continue

        pool = pool[~pool["player"].astype(str).isin(used_players)].copy()
        pool["_gid"] = pool.apply(gid, axis=1)
        no_dup_game = pool[~pool["_gid"].isin(used_games)].copy()
        if not no_dup_game.empty:
            pool = no_dup_game

        if pool.empty:
            continue

        pick = pool.sort_values(["support_score", "blender_score"], ascending=[False, False]).head(1).copy()
        pick["core_slot"] = slot
        parts.append(pick.drop(columns=["_gid"], errors="ignore"))
        used_players.update(pick["player"].astype(str).tolist())
        used_games.update(pick["_gid"].astype(str).tolist())

    if not parts:
        return pd.DataFrame()

    core = pd.concat(parts, ignore_index=True).head(3)
    core["ticket_role"] = "CORE"
    return core


def run_true_blender(df, *args, **kwargs) -> Dict[str, Any]:
    work = normalize_feed(df)
    if work.empty:
        return empty_results("No usable feed rows loaded.")

    locked_sides, environment_board = lock_attack_sides(work)

    survivors_rows = []
    board_rows = []
    role_rows = []

    for idx, r in work.iterrows():
        row = r.to_dict()
        candidate, gates, role_scores = evaluate_candidate(row, locked_sides)
        candidate["row_id"] = idx
        survivors_rows.append(candidate)

        for g in gates:
            board_rows.append({
                "game_id": candidate.get("game_id", ""),
                "game_key": candidate.get("game_key", ""),
                "player": candidate.get("player", ""),
                "team": candidate.get("team", ""),
                "locked_attack_side": candidate.get("locked_attack_side", ""),
                "role": candidate.get("official_core_role", ""),
                **g,
                "blender_score": candidate.get("blender_score", 0),
            })

        role_rows.append({
            "game_id": candidate.get("game_id", ""),
            "game_key": candidate.get("game_key", ""),
            "player": candidate.get("player", ""),
            "assigned_role": candidate.get("official_core_role", ""),
            "Primary_score": role_scores.get("Primary", 0),
            "Adjacent_score": role_scores.get("Adjacent", 0),
            "WHO_score": role_scores.get("WHO", 0),
            "blender_score": candidate.get("blender_score", 0),
        })

    survivors = pd.DataFrame(survivors_rows)
    game_board = pd.DataFrame(board_rows)
    role_board = pd.DataFrame(role_rows)
    cuts = survivors[survivors["blender_eligible"] != True].copy()
    owners = resolve_owners(survivors)
    core = build_structured_core(owners)

    used = set(core["player"].astype(str).tolist()) if not core.empty and "player" in core.columns else set()
    alt = owners[~owners["player"].astype(str).isin(used)].head(3).copy() if not owners.empty and "player" in owners.columns else pd.DataFrame()
    if not alt.empty:
        alt["ticket_role"] = "ALT"

    used.update(alt["player"].astype(str).tolist() if not alt.empty and "player" in alt.columns else [])
    chaos = owners[(owners["official_core_role"] == "WHO") & (~owners["player"].astype(str).isin(used))].head(3).copy() if not owners.empty and "official_core_role" in owners.columns and "player" in owners.columns else pd.DataFrame()
    if not chaos.empty:
        chaos["ticket_role"] = "WHO"

    games = official_game_count(work) or actual_game_count(work)
    meta = {
        "engine_version": "LOCKED_REAL_BLENDER_MACHINE",
        "games": int(games),
        "input_rows": int(len(work)),
        "passed_rows": int((survivors["blender_eligible"] == True).sum()),
        "cut_rows": int((survivors["blender_eligible"] != True).sum()),
        "owners_locked": int(len(owners)),
        "core_count": int(len(core)),
        "core_slots": core.get("core_slot", pd.Series(dtype=str)).tolist() if not core.empty else [],
        "message": f"Locked Blender complete: {len(owners)} owners, {int((survivors['blender_eligible'] == True).sum())} pass rows, {int((survivors['blender_eligible'] != True).sum())} cuts. Core slots={core.get('core_slot', pd.Series(dtype=str)).tolist() if not core.empty else []}.",
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
        "meta": meta,
    }
    save_locked_results(results)
    return results
