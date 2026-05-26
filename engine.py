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
ENGINE_VERSION = "V0211_TRUE_GATE_DEATH_CHAIN_NO_TERMINAL_SCORE"


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
        if _key(n) in cmap:
            return _num(row.get(cmap[_key(n)]), default)
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


def strength(x: Any, floor: float, elite: float, pts: float) -> float:
    x = _num(x, 0.0)
    if x < floor:
        return 0.0
    if x >= elite:
        return float(pts)
    return float(pts) * ((x - floor) / max(1.0, elite - floor))


def fetch_live_public_slate(date_str=None):
    return fetch_official_mlb_slate(date_str)


def fetch_live_public_hitter_pool(date_str=None):
    return fetch_official_mlb_slate(date_str)


def attach_slate_matchup_context(df, public_context=None):
    return attach_official_slate_to_feed(df, public_context)


def merge_public_context(df, public_context=None):
    return attach_slate_matchup_context(df, public_context)


def _df_to_records(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []
    return df.replace({np.nan: None}).to_dict(orient="records")


def empty_results(message: str):
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
            "core_rule": "CORE_FROM_FINAL_ISOLATED_OWNERS_ONLY_NO_REFILL",
            "projection_fallback": False,
            "best_remaining_hitter_logic": False,
        },
    }


def save_locked_results(results: Dict[str, Any]) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    keys = ["owners", "core", "alt", "chaos", "survivors", "cuts", "game_board", "role_board", "environment_board", "state_log"]
    payload = {k: _df_to_records(results.get(k)) for k in keys}
    payload["meta"] = results.get("meta", {})
    LOCK_PATH.write_text(json.dumps(payload, indent=2))


def load_locked_results():
    if not LOCK_PATH.exists():
        return empty_results("Run the Blender first.")
    try:
        payload = json.loads(LOCK_PATH.read_text())
        meta = payload.get("meta", {}) or {}
        if meta.get("engine_version") != ENGINE_VERSION:
            return empty_results("Saved lock is from an older engine build. Run the Blender again.")
        out = {k: pd.DataFrame(payload.get(k, [])) for k in ["owners", "core", "alt", "chaos", "survivors", "cuts", "game_board", "role_board", "environment_board", "state_log"]}
        out["meta"] = meta
        return out
    except Exception:
        return empty_results("Saved lock file could not be loaded. Run the Blender again.")


ALIASES = {
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


def metrics(row: Dict[str, Any]) -> Dict[str, float]:
    return {k: _field(row, n, -99 if k == "edge" else 0) for k, n in ALIASES.items()}


def metric_count(v: Dict[str, float]) -> int:
    c = 0
    for k, x in v.items():
        if k == "edge":
            if x != -99:
                c += 1
        else:
            try:
                if x not in [None, 0] and not pd.isna(x):
                    c += 1
            except Exception:
                pass
    return c


def game_id(row: Dict[str, Any]) -> str:
    pk = _txt(row.get("game_pk"))
    return pk if pk and pk.lower() not in {"nan", "none"} else _txt(row.get("game_key") or row.get("game"))


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
    for col in ["player", "team", "pitcher", "game_key"]:
        if col not in df.columns:
            df[col] = ""
    return df.reset_index(drop=True)


def _env_score(row: Dict[str, Any]) -> float:
    v = metrics(row)
    return (
        strength(v["hr"], 0.5, 2.6, 22)
        + strength(v["edge"], 0, 18, 20)
        + strength(v["dmg"], 0.5, 2.6, 17)
        + strength(v["hpi"], 10, 90, 15)
        + strength(v["barrel"], 3, 18, 12)
        + strength(v["pull"], 25, 60, 9)
        + strength(v["hard"], 25, 64, 5)
    )


def lock_attack_sides(df: pd.DataFrame) -> Tuple[Dict[str, str], pd.DataFrame]:
    locks: Dict[str, str] = {}
    rows: List[Dict[str, Any]] = []
    if df.empty:
        return locks, pd.DataFrame()

    for gid, gdf in df.groupby("_gid", dropna=False):
        if not _txt(gid):
            continue
        team_scores = []
        for team, tdf in gdf.groupby("team", dropna=False):
            team = _txt(team)
            if not team:
                continue
            vals = [_env_score(r.to_dict()) for _, r in tdf.iterrows()]
            team_scores.append((team, max(vals or [0]) + (sum(vals) / max(1, len(vals))) * 0.10, len(tdf)))
        if not team_scores:
            continue
        team_scores.sort(key=lambda x: x[1], reverse=True)
        winner, score, count = team_scores[0]
        locks[str(gid)] = winner
        rows.append(
            {
                "game_id": str(gid),
                "game_key": _txt(gdf.iloc[0].get("game_key") or gdf.iloc[0].get("game")),
                "locked_attack_side": winner,
                "attack_score": round(float(score), 2),
                "candidate_rows": int(count),
                "engine_rule": "HARD LOCK — ONLY THIS SIDE ENTERS ELIMINATION",
            }
        )
    return locks, pd.DataFrame(rows)


def add_gate(path: List[Dict[str, Any]], step: int, gate: str, passed: bool, score: float, max_score: float, reason: str, hard_gate: bool = True) -> bool:
    path.append(
        {
            "step": step,
            "gate": gate,
            "result": "PASS" if passed else "CUT",
            "score": round(float(max(score, 0)), 3),
            "max_score": float(max_score),
            "reason": reason,
            "hard_gate": bool(hard_gate),
            "cut": bool(hard_gate and not passed),
        }
    )
    return bool(passed or not hard_gate)


def _notes(row: Dict[str, Any]) -> str:
    return " ".join([_txt(row.get(k)) for k in row.keys() if any(x in str(k).lower() for x in ["note", "tag", "raw", "status", "event", "role"]) ]).lower()


def _role_from_owner(row: Dict[str, Any], path: List[Dict[str, Any]], pool: pd.DataFrame | None = None) -> Tuple[str, str, Dict[str, float]]:
    """
    Role is assigned only AFTER the one-game owner survives.
    It is not a default label and it is not used to create the owner.
    """
    v = metrics(row)
    notes = _notes(row)
    hpi = v["hpi"]
    slot = v["slot"]
    pull = v["pull"]
    hard = v["hard"]
    barrel = v["barrel"]
    dmg = v["dmg"]
    hr = v["hr"]
    edge = v["edge"]

    pool = pool.copy() if isinstance(pool, pd.DataFrame) else pd.DataFrame()
    pool_size = int(len(pool)) if not pool.empty else 1

    # Context clues from the actual survivor behavior inside the locked side.
    hpi_rank = 1
    power_rank = 1
    pull_rank = 1
    if not pool.empty:
        # Missing values are made low so they do not create fake chalk status.
        hpi_rank = int(pool["hpi_metric"].rank(ascending=False, method="min").loc[row.get("_owner_pool_index", row.name if hasattr(row, "name") else pool.index[0])] ) if "hpi_metric" in pool.columns and row.get("_owner_pool_index", None) in pool.index else 1
        power_rank = int(pool["owner_power"].rank(ascending=False, method="min").loc[row.get("_owner_pool_index", row.name if hasattr(row, "name") else pool.index[0])] ) if "owner_power" in pool.columns and row.get("_owner_pool_index", None) in pool.index else 1
        pull_rank = int(pool["pull_metric"].rank(ascending=False, method="min").loc[row.get("_owner_pool_index", row.name if hasattr(row, "name") else pool.index[0])] ) if "pull_metric" in pool.columns and row.get("_owner_pool_index", None) in pool.index else 1

    adjacent_trigger = (
        any(x in notes for x in ["adjacent", "decoy", "transfer", "coverage", "pressure", "behind", "after", "weak slot"])
        or (hpi_rank > 1 and pull_rank == 1)
        or (hpi >= 55 and power_rank > 1 and pull >= 30)
    )
    who_trigger = (
        any(x in notes for x in ["who", "chaos", "low owned", "low-owned", "bottom", "random"])
        or (hpi < 45 and pull >= 28 and hard >= 30 and barrel >= 3)
        or (slot >= 6 and pull >= 28 and (barrel >= 3 or dmg >= 0.5))
    )

    primary = strength(pull, 32, 60, 28) + strength(barrel, 5, 18, 28) + strength(dmg, 0.7, 2.7, 20) + strength(hpi, 18, 90, 16) + strength(hr, 0.6, 2.7, 15) + strength(edge, 0, 22, 12)
    adjacent = strength(pull, 27, 52, 16) + strength(hard, 28, 58, 16) + strength(dmg, 0.5, 2.1, 14) + strength(hr, 0.5, 2.0, 10) + (45 if adjacent_trigger else 0)
    who = strength(pull, 25, 50, 13) + strength(hard, 30, 56, 13) + strength(barrel, 3, 14, 10) + strength(hr, 0.5, 1.8, 12) + strength(edge, 0, 14, 10) + (50 if who_trigger else 0)
    scores = {"Primary": round(primary, 2), "Adjacent": round(adjacent, 2), "WHO": round(who, 2), "pool_size": pool_size, "hpi_rank": hpi_rank, "pull_rank": pull_rank}

    # Hard identity order: WHO/chaos and adjacent-transfer are real identities, not afterthoughts.
    if who_trigger and who >= max(primary, adjacent) - 8:
        role = "WHO"
    elif adjacent_trigger and adjacent >= primary - 8:
        role = "Adjacent"
    else:
        role = "Primary"

    label = {"Primary": "Clean Lane Event Owner", "Adjacent": "Adjacent / Decoy Transfer Owner", "WHO": "WHO / Chaos Event Owner"}[role]
    return role, label, scores

def _candidate_path(row: Dict[str, Any], locks: Dict[str, str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    v = metrics(row)
    player = _txt(row.get("player"))
    team = _txt(row.get("team"))
    gid = game_id(row)
    gkey = _txt(row.get("game_key") or row.get("game"))
    pitcher = _txt(row.get("pitcher"))
    locked = locks.get(str(gid), "")
    notes = _notes(row)
    path: List[Dict[str, Any]] = []

    mc = metric_count(v)
    pull, hard, barrel, sweet, dmg, hpi, hr, edge, slot = [v[k] for k in ["pull", "hard", "barrel", "sweet", "dmg", "hpi", "hr", "edge", "slot"]]

    alive = add_gate(path, 0, "PDF row / feed row exists", bool(player and gkey), 8 if player and gkey else 0, 8, f"player={player}; game={gkey}")
    if alive:
        alive = add_gate(path, 1, "LOCK ATTACK SIDE", bool(locked and team == locked), 10 if locked and team == locked else 0, 10, f"locked_side={locked}; candidate_team={team}; hard side-only elimination")
    else:
        add_gate(path, 1, "LOCK ATTACK SIDE", False, 0, 10, "skipped after prior cut")

    trigger = pull >= 25 or hard >= 28 or barrel >= 3 or dmg >= 0.5 or hpi >= 10 or hr >= 0.5 or edge >= 0
    if alive:
        alive = add_gate(path, 2, "Readable metrics / no empty bat", mc >= 3 and trigger, 10 if mc >= 3 and trigger else 0, 10, f"metric_count={mc}; trigger={trigger}")
    else:
        add_gate(path, 2, "Readable metrics / no empty bat", False, 0, 10, "already eliminated")

    lane = max(strength(hr, 0.5, 2.4, 12), strength(edge, 0, 16, 12), strength(dmg, 0.5, 2.5, 12), strength(hpi, 10, 90, 12))
    if alive:
        alive = add_gate(path, 3, "Pitcher HR lane match", lane > 0, lane, 12, f"hr_lane={hr}; pitch_edge={edge}; dmg={dmg}; hpi={hpi}")
    else:
        add_gate(path, 3, "Pitcher HR lane match", False, 0, 12, "already eliminated")

    launch = max(strength(pull, 25, 60, 14), strength(sweet, 18, 40, 14), strength(barrel, 3, 18, 14))
    if alive:
        alive = add_gate(path, 4, "Pull-air / launch window", launch > 0, launch, 14, f"pull={pull}; sweet={sweet}; barrel={barrel}")
    else:
        add_gate(path, 4, "Pull-air / launch window", False, 0, 14, "already eliminated")

    hard_support = max(strength(hard, 28, 64, 9), strength(barrel, 3, 18, 9), strength(dmg, 0.5, 2.5, 9))
    if alive:
        alive = add_gate(path, 5, "Hard-hit support", hard_support > 0, hard_support, 9, f"hard={hard}; barrel={barrel}; dmg={dmg}")
    else:
        add_gate(path, 5, "Hard-hit support", False, 0, 9, "already eliminated")

    conversion = max(strength(dmg, 0.5, 2.5, 15), strength(barrel, 3, 18, 15), strength(hpi, 10, 90, 15), strength(hr, 0.5, 2.5, 15))
    if alive:
        alive = add_gate(path, 6, "True HR conversion DNA", conversion > 0, conversion, 15, f"dmg={dmg}; barrel={barrel}; hpi={hpi}; hr_lane={hr}")
    else:
        add_gate(path, 6, "True HR conversion DNA", False, 0, 15, "already eliminated")

    slot_ok = (slot == 0 or slot <= 9)
    if alive:
        alive = add_gate(path, 7, "Lineup opportunity", slot_ok, 7 if slot_ok else 0, 7, f"slot={slot}")
    else:
        add_gate(path, 7, "Lineup opportunity", False, 0, 7, "already eliminated")

    trap = "trap" in notes or "red flag" in notes or "fade" in notes or "suppression" in notes
    if alive:
        alive = add_gate(path, 8, "Trap / suppression audit", not trap, 8 if not trap else 0, 8, "clean" if not trap else "trap/fade/suppression flag")
    else:
        add_gate(path, 8, "Trap / suppression audit", False, 0, 8, "already eliminated")

    finisher = max(strength(pull, 30, 60, 8), strength(hard, 28, 64, 8), strength(barrel, 3, 18, 8), strength(dmg, 0.5, 2.5, 8), strength(hpi, 10, 90, 8), strength(hr, 0.5, 2.5, 8))
    event = (lane * 0.34) + (launch * 0.30) + (conversion * 0.40) + (hard_support * 0.16) + (finisher * 0.25)
    if alive:
        alive = add_gate(path, 9, "Event likelihood / owner candidate", event >= 3.25, event, 14, f"event_likelihood={round(event, 3)}; no projection fallback")
    else:
        add_gate(path, 9, "Event likelihood / owner candidate", False, 0, 14, "already eliminated")

    gate_total = sum(g["score"] for g in path if g["result"] == "PASS")
    gate_max = sum(g["max_score"] for g in path)
    owner_power = round((event * 3.8) + (lane * 1.2) + (launch * 0.9) + (conversion * 1.15) + (hard_support * 0.55) + (gate_total / max(gate_max, 1)) * 20, 3)
    status = "PRE_OWNER_SURVIVOR" if alive else "CUT"
    stop_gate = "" if alive else next((g["gate"] for g in path if g["cut"]), "eliminated")

    candidate = {
        **row,
        "game_id": gid,
        "game_key": gkey,
        "player": player,
        "team": team,
        "pitcher": pitcher,
        "locked_attack_side": locked,
        "pre_owner_survivor": bool(alive),
        "blender_eligible": False,  # only the isolated one-owner survivor becomes True later
        "owner_power": owner_power,
        "support_score": round(gate_total, 3),
        "pass_depth": int(sum(1 for g in path if g["result"] == "PASS")),
        "cut_depth": int(sum(1 for g in path if g["result"] == "CUT")),
        "event_ownership": round(event, 3),
        "hpi_metric": hpi,
        "pull_metric": pull,
        "hard_metric": hard,
        "barrel_metric": barrel,
        "official_core_role": status,
        "archetype": "Pre-owner survivor" if alive else "Cut by gates",
        "score": 0.0,
        "blender_score": 0.0,
        "elimination_score": owner_power,
        "stop_gate": stop_gate,
        "final_reason": "passed gates; awaiting one-owner isolation" if alive else f"CUT — {stop_gate}",
        "gate_trace_json": json.dumps(path),
    }
    return candidate, path


def _append_isolation_gate(path: List[Dict[str, Any]], owner_name: str, won: bool, reason: str) -> List[Dict[str, Any]]:
    new_path = list(path)
    add_gate(new_path, 10, "ONE OWNER ISOLATION", won, 12 if won else 0, 12, reason, True)
    return new_path


def _death_chain_pick(pool: pd.DataFrame) -> Tuple[Any, pd.DataFrame]:
    """Resolve one owner through sequential death-chain gates, not terminal score sorting."""
    work = pool.copy()
    for col in ["event_ownership", "pull_metric", "barrel_metric", "hard_metric", "hpi_metric", "owner_power", "support_score", "pass_depth"]:
        if col not in work.columns:
            work[col] = 0.0
        work[col] = pd.to_numeric(work[col], errors="coerce").fillna(0.0)

    rounds = [
        ("Gate-death round 1: event lane ownership", "event_ownership"),
        ("Gate-death round 2: pull-air survivor", "pull_metric"),
        ("Gate-death round 3: barrel/finish survivor", "barrel_metric"),
        ("Gate-death round 4: hard-hit support survivor", "hard_metric"),
        ("Gate-death round 5: conversion/model support", "hpi_metric"),
        ("Gate-death round 6: full gate memory depth", "pass_depth"),
    ]
    work["isolation_round_notes"] = ""
    alive = work.copy()
    for label, col in rounds:
        if len(alive) <= 1:
            break
        best = alive[col].max()
        # keep the top tier only, not a final rank sort. This mutates survivor state round-by-round.
        if col == "pass_depth":
            next_alive = alive[alive[col] == best].copy()
        else:
            margin = max(abs(best) * 0.08, 0.35)
            next_alive = alive[alive[col] >= best - margin].copy()
        killed = alive.index.difference(next_alive.index)
        for idx in killed:
            work.loc[idx, "isolation_round_notes"] += f"CUT {label}; "
        for idx in next_alive.index:
            work.loc[idx, "isolation_round_notes"] += f"SURVIVED {label}; "
        alive = next_alive

    if len(alive) > 1:
        # Last deterministic tie-break uses original feed order, not best remaining score.
        winner_idx = alive.sort_values(["row_id"], ascending=[True]).index[0] if "row_id" in alive.columns else alive.index[0]
        for idx in alive.index.difference([winner_idx]):
            work.loc[idx, "isolation_round_notes"] += "CUT final feed-order tie-break after equal gate memory; "
    else:
        winner_idx = alive.index[0]
    work.loc[winner_idx, "isolation_round_notes"] += "LOCKED as lone owner after death-chain; "
    return winner_idx, work


def resolve_owners(survivors: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    if not isinstance(survivors, pd.DataFrame) or survivors.empty:
        return pd.DataFrame(), survivors

    updated = survivors.copy()
    owner_rows: List[Dict[str, Any]] = []
    used_players = set()

    for gid, g in updated.groupby("game_id", dropna=False):
        if not _txt(gid):
            continue
        pool = g[g["pre_owner_survivor"] == True].copy()
        if pool.empty:
            continue

        winner_idx, chain_pool = _death_chain_pick(pool)
        if winner_idx is None:
            continue
        p = _txt(updated.loc[winner_idx].get("player")).lower()
        if p in used_players:
            continue
        used_players.add(p)

        winner = updated.loc[winner_idx].to_dict()
        winner["_owner_pool_index"] = winner_idx
        winner_path = json.loads(winner.get("gate_trace_json", "[]"))
        role, role_label, role_scores = _role_from_owner(winner, winner_path, chain_pool)
        iso_note = chain_pool.loc[winner_idx].get("isolation_round_notes", "won one-owner isolation")
        final_path = _append_isolation_gate(winner_path, winner.get("player", ""), True, iso_note)

        # No normalized terminal score. Confidence is raw gate-memory power and can vary by player/game.
        raw_power = round(float(winner.get("owner_power", 0)), 2)

        updated.loc[winner_idx, "blender_eligible"] = True
        updated.loc[winner_idx, "official_core_role"] = role
        updated.loc[winner_idx, "archetype"] = role_label
        updated.loc[winner_idx, "true_role_path"] = role
        updated.loc[winner_idx, "score"] = raw_power
        updated.loc[winner_idx, "blender_score"] = raw_power
        updated.loc[winner_idx, "confidence_label"] = f"Gate Power {raw_power}"
        updated.loc[winner_idx, "decision_state"] = "LOCKED OWNER"
        updated.loc[winner_idx, "final_reason"] = "FINAL ISOLATED OWNER — death-chain survivor; role assigned after survivor behavior"
        updated.loc[winner_idx, "stop_gate"] = ""
        updated.loc[winner_idx, "isolation_round_notes"] = iso_note
        updated.loc[winner_idx, "role_Primary_score"] = role_scores.get("Primary", 0)
        updated.loc[winner_idx, "role_Adjacent_score"] = role_scores.get("Adjacent", 0)
        updated.loc[winner_idx, "role_WHO_score"] = role_scores.get("WHO", 0)
        updated.loc[winner_idx, "role_scores_json"] = json.dumps(role_scores)
        updated.loc[winner_idx, "gate_trace_json"] = json.dumps(final_path)

        owner_rows.append(updated.loc[winner_idx].to_dict())

        losers = chain_pool.index.difference([winner_idx])
        for li in losers:
            loser_path = json.loads(updated.loc[li].get("gate_trace_json", "[]"))
            lose_reason = chain_pool.loc[li].get("isolation_round_notes", "lost one-owner isolation") + f" winner={winner.get('player','')}"
            lose_path = _append_isolation_gate(loser_path, winner.get("player", ""), False, lose_reason)
            updated.loc[li, "pre_owner_survivor"] = False
            updated.loc[li, "blender_eligible"] = False
            updated.loc[li, "official_core_role"] = "OWNERSHIP_LOSS"
            updated.loc[li, "archetype"] = "Cut by one-owner death-chain"
            updated.loc[li, "score"] = 0.0
            updated.loc[li, "blender_score"] = 0.0
            updated.loc[li, "confidence_label"] = "CUT"
            updated.loc[li, "decision_state"] = "CUT"
            updated.loc[li, "stop_gate"] = "ONE OWNER ISOLATION"
            updated.loc[li, "isolation_round_notes"] = lose_reason
            updated.loc[li, "final_reason"] = f"CUT — {lose_reason}"
            updated.loc[li, "gate_trace_json"] = json.dumps(lose_path)

    owners = pd.DataFrame(owner_rows)
    if owners.empty:
        return owners, updated

    # Keep natural owner-lock order; Core builder handles ticket role coverage from already-isolated owners.
    owners = owners.reset_index(drop=True)
    return owners, updated


def build_core_top3(owners: pd.DataFrame) -> pd.DataFrame:
    """Build Core 3 only from isolated owners. Never refills from non-owners."""
    if not isinstance(owners, pd.DataFrame) or owners.empty:
        return pd.DataFrame()

    remaining = owners.copy()
    picks = []
    role_order = ["Primary", "Adjacent", "WHO"]
    for role in role_order:
        if len(picks) >= 3:
            break
        subset = remaining[remaining.get("official_core_role", pd.Series(dtype=str)).astype(str).eq(role)].copy()
        if subset.empty:
            continue
        # Among already-isolated owners only: use death-chain power for ticket display order.
        subset = subset.sort_values(["owner_power", "event_ownership", "support_score"], ascending=[False, False, False])
        idx = subset.index[0]
        picks.append(idx)
        remaining = remaining.drop(index=idx)

    if len(picks) < 3 and not remaining.empty:
        extra = remaining.sort_values(["owner_power", "event_ownership", "support_score"], ascending=[False, False, False]).head(3-len(picks)).index.tolist()
        picks.extend(extra)

    core = owners.loc[picks].copy() if picks else pd.DataFrame()
    if core.empty:
        return core
    core["core_slot"] = [f"CORE {i+1}" for i in range(len(core))]
    core["ticket_role"] = "CORE"
    core["core_build_rule"] = "FINAL_ISOLATED_OWNERS_ONLY_DEATH_CHAIN_NO_NON_OWNER_REFILL"
    return core.reset_index(drop=True)

def run_true_blender(df: pd.DataFrame, *args, **kwargs):
    work = normalize_feed(df)
    if work.empty:
        return empty_results("No usable feed rows loaded.")

    locks, environment_board = lock_attack_sides(work)
    raw_rows: List[Dict[str, Any]] = []

    for idx, r in work.iterrows():
        cand, path = _candidate_path(r.to_dict(), locks)
        cand["row_id"] = idx
        raw_rows.append(cand)

    initial_survivors = pd.DataFrame(raw_rows)
    owners, final_survivors = resolve_owners(initial_survivors)

    # Rebuild board from final mutated memory so the UI shows real cuts and owner-isolation.
    board_rows: List[Dict[str, Any]] = []
    role_rows: List[Dict[str, Any]] = []
    for _, cand in final_survivors.iterrows():
        path = json.loads(cand.get("gate_trace_json", "[]"))
        for g in path:
            board_rows.append(
                {
                    "game_id": cand.get("game_id", ""),
                    "game_key": cand.get("game_key", ""),
                    "player": cand.get("player", ""),
                    "team": cand.get("team", ""),
                    "pitcher": cand.get("pitcher", ""),
                    "locked_attack_side": cand.get("locked_attack_side", ""),
                    "role": cand.get("official_core_role", ""),
                    **g,
                    "blender_score": cand.get("blender_score", 0),
                    "owner_power": cand.get("owner_power", 0),
                }
            )
        role_rows.append(
            {
                "game_id": cand.get("game_id", ""),
                "game_key": cand.get("game_key", ""),
                "player": cand.get("player", ""),
                "assigned_role": cand.get("official_core_role", ""),
                "archetype": cand.get("archetype", ""),
                "owner_power": cand.get("owner_power", 0),
                "event_ownership": cand.get("event_ownership", 0),
                "pre_owner_survivor": cand.get("pre_owner_survivor", False),
                "final_owner": cand.get("blender_eligible", False),
                "final_reason": cand.get("final_reason", ""),
            }
        )

    core = build_core_top3(owners)
    alt = owners.iloc[3:6].copy() if not owners.empty else pd.DataFrame()
    if not alt.empty:
        alt["ticket_role"] = "ALT"
    chaos = owners[owners.get("official_core_role", pd.Series(dtype=str)).astype(str).eq("WHO")].copy() if not owners.empty else pd.DataFrame()
    if not chaos.empty:
        chaos = chaos.head(3).copy()
        chaos["ticket_role"] = "WHO"

    cuts = final_survivors[final_survivors["blender_eligible"] != True].copy()
    game_board = pd.DataFrame(board_rows)
    role_board = pd.DataFrame(role_rows)
    games = official_game_count(work) or actual_game_count(work)

    meta = {
        "engine_version": ENGINE_VERSION,
        "games": int(games),
        "input_rows": int(len(work)),
        "pre_owner_survivors": int((initial_survivors["pre_owner_survivor"] == True).sum()) if not initial_survivors.empty else 0,
        "passed_rows": int((final_survivors["blender_eligible"] == True).sum()) if not final_survivors.empty else 0,
        "cut_rows": int((final_survivors["blender_eligible"] != True).sum()) if not final_survivors.empty else 0,
        "owners_locked": int(len(owners)),
        "core_count": int(len(core)),
        "core_rule": "CORE_FROM_FINAL_ISOLATED_OWNERS_ONLY_NO_REFILL",
        "projection_fallback": False,
        "best_remaining_hitter_logic": False,
        "terminal_score_removed": True,
        "death_chain_isolation": True,
        "display_confidence_is_raw_gate_power": True,
        "attack_side_hard_kill": True,
        "role_after_owner_only": True,
        "message": f"{ENGINE_VERSION}: {len(owners)} isolated owners locked from {len(work)} rows. Core={len(core)}. No projection fallback / no best-remaining refill.",
    }

    results = {
        "owners": owners,
        "core": core,
        "alt": alt,
        "chaos": chaos,
        "survivors": final_survivors,
        "cuts": cuts,
        "game_board": game_board,
        "role_board": role_board,
        "environment_board": environment_board,
        "state_log": pd.DataFrame(
            [
                {"step": 1, "rule": "LOCK ATTACK SIDE", "state": "HARD_KILL", "notes": "opposite side cannot survive"},
                {"step": 2, "rule": "ELIMINATE WITHIN SIDE ONLY", "state": "ACTIVE", "notes": "all gate cuts happen after side lock"},
                {"step": 3, "rule": "ONE OWNER PER GAME BEFORE ROLES", "state": "ACTIVE", "notes": "only isolated owner becomes blender_eligible"},
                {"step": 4, "rule": "ROLE FROM SURVIVOR BEHAVIOR", "state": "ACTIVE", "notes": "non-owners do not get Primary labels"},
                {"step": 5, "rule": "CORE 3 FROM FINAL OWNERS ONLY", "state": "ACTIVE", "notes": "no refill"},
                {"step": 6, "rule": "RAW GATE MEMORY", "state": "ACTIVE", "notes": "mutated gate trace rendered"},
                {"step": 7, "rule": "ZERO PROJECTION FALLBACK", "state": "ACTIVE", "notes": "disabled"},
                {"step": 8, "rule": "ZERO BEST REMAINING HITTER", "state": "ACTIVE", "notes": "disabled"},
            ]
        ),
        "meta": meta,
    }
    save_locked_results(results)
    return results
