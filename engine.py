
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


# ============================================================
# BASIC HELPERS
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


def _safe_df(x) -> pd.DataFrame:
    return x if isinstance(x, pd.DataFrame) else pd.DataFrame()


def csv_bytes(df: pd.DataFrame) -> bytes:
    return _safe_df(df).to_csv(index=False).encode("utf-8")


def gate_strength(x: float, floor: float, elite: float, pts: float) -> float:
    x = _num(x, 0)
    if x < floor:
        return 0.0
    if x >= elite:
        return float(pts)
    return float(pts) * ((x - floor) / max(1.0, elite - floor))


# ============================================================
# OFFICIAL MLB BRIDGE
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
# LOCKED RESULTS
# ============================================================

def _df_to_records(df: pd.DataFrame):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []
    return df.replace({np.nan: None}).to_dict(orient="records")


def _records_to_df(records):
    return pd.DataFrame(records or [])


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
            "engine_version": "V161_TRUE_BLENDER_MACHINE",
            "message": message,
            "owners_locked": 0,
            "core_count": 0,
            "passed_rows": 0,
            "cut_rows": 0,
            "generic_refill": False,
            "fallback_sorting": False,
        },
    }


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
        "state_log": _df_to_records(results.get("state_log")),
    }
    LOCK_PATH.write_text(json.dumps(payload, indent=2))


def load_locked_results() -> Dict[str, Any]:
    # Daily-only behavior: do not resurrect old picks unless current session creates them.
    return empty_results("Run the Blender first.")


# ============================================================
# TRUE ELIMINATION MACHINE
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


def metrics(row: Dict[str, Any]) -> Dict[str, float]:
    return {k: _field(row, names, -99 if k == "edge" else 0) for k, names in METRIC_ALIASES.items()}


def metric_count(vals: Dict[str, float]) -> int:
    count = 0
    for k, v in vals.items():
        if k == "edge":
            if v != -99:
                count += 1
        elif v not in [None, 0] and not pd.isna(v):
            count += 1
    return count


def player_equals_pitcher(row: Dict[str, Any]) -> bool:
    p = _txt(row.get("player")).lower()
    pit = _txt(row.get("pitcher")).lower()
    return bool(p and pit and p == pit)


def game_id(row: Dict[str, Any]) -> str:
    pk = _txt(row.get("game_pk"))
    if pk and pk.lower() not in {"nan", "none"}:
        return pk
    return _txt(row.get("game_key") or row.get("game"))


def normalize_feed(df: pd.DataFrame) -> pd.DataFrame:
    df = _safe_df(df).copy()
    if df.empty:
        return df
    if "game_key" not in df.columns:
        df["game_key"] = df["game"] if "game" in df.columns else ""
    if "official_slate_attached" not in df.columns:
        df["official_slate_attached"] = False
    if "player" in df.columns and "pitcher" in df.columns:
        df = df[~df.apply(lambda r: player_equals_pitcher(r.to_dict()), axis=1)].copy()
    df["_gid"] = df.apply(lambda r: game_id(r.to_dict()), axis=1)
    return df.reset_index(drop=True)


def env_score(row: Dict[str, Any]) -> float:
    v = metrics(row)
    return (
        gate_strength(v["hr"], 0.8, 2.4, 18)
        + gate_strength(v["edge"], 0, 15, 14)
        + gate_strength(v["dmg"], 0.8, 2.4, 12)
        + gate_strength(v["hpi"], 20, 80, 10)
        + gate_strength(v["barrel"], 5, 16, 8)
        + gate_strength(v["pull"], 30, 55, 6)
    )


def lock_attack_sides(df: pd.DataFrame) -> Tuple[Dict[str, str], pd.DataFrame]:
    locks: Dict[str, str] = {}
    rows = []
    if df.empty:
        return locks, pd.DataFrame()

    for gid, gdf in df.groupby("_gid", dropna=False):
        if not _txt(gid):
            continue
        team_rows = []
        for team, tdf in gdf.groupby("team", dropna=False):
            team = _txt(team)
            if not team:
                continue
            vals = [env_score(r.to_dict()) for _, r in tdf.iterrows()]
            # environment lock is by attack-side strength, not player ranking
            team_score = max(vals) + (sum(vals) / max(1, len(vals))) * 0.15
            team_rows.append((team, team_score, len(tdf)))

        if not team_rows:
            continue
        team_rows.sort(key=lambda x: x[1], reverse=True)
        locked_team, score, n = team_rows[0]
        locks[str(gid)] = locked_team
        rows.append({
            "game_id": str(gid),
            "game_key": _txt(gdf.iloc[0].get("game_key") or gdf.iloc[0].get("game")),
            "locked_attack_side": locked_team,
            "attack_score": round(float(score), 2),
            "candidate_rows": int(n),
            "engine_rule": "LOCKED BEFORE PLAYER GATES",
        })
    return locks, pd.DataFrame(rows)


def add_gate(gates: List[Dict[str, Any]], step: int, gate: str, passed: bool, score: float, max_score: float, reason: str, hard_gate: bool = True):
    gates.append({
        "step": step,
        "gate": gate,
        "result": "PASS" if passed else "CUT",
        "score": round(float(max(0, score)), 2),
        "max_score": float(max_score),
        "reason": reason,
        "hard_gate": bool(hard_gate),
        "cut": bool(hard_gate and not passed),
    })


def role_path(vals: Dict[str, float], notes: str) -> Tuple[str, Dict[str, float]]:
    pull, hard, barrel, dmg, hpi, hr, edge = vals["pull"], vals["hard"], vals["barrel"], vals["dmg"], vals["hpi"], vals["hr"], vals["edge"]
    adjacent_trigger = any(x in notes for x in ["adjacent", "decoy", "transfer", "coverage", "weak slot", "pressure"])
    who_trigger = "who" in notes or "chaos" in notes or (pull >= 30 and hard >= 30 and hpi < 45)

    primary = (
        gate_strength(pull, 36, 55, 24)
        + gate_strength(barrel, 7, 16, 21)
        + gate_strength(dmg, 1.0, 2.4, 18)
        + gate_strength(hpi, 30, 80, 16)
        + gate_strength(hr, 1.0, 2.5, 15)
        + gate_strength(edge, 0, 20, 10)
    )
    adjacent = (
        gate_strength(pull, 30, 46, 18)
        + gate_strength(hard, 30, 52, 18)
        + gate_strength(dmg, 0.8, 1.8, 15)
        + gate_strength(hpi, 20, 60, 10)
        + (40 if adjacent_trigger else 0)
    )
    who = (
        gate_strength(pull, 28, 42, 16)
        + gate_strength(hard, 30, 48, 16)
        + gate_strength(hr, 0.8, 1.8, 16)
        + gate_strength(edge, 0, 12, 10)
        + (42 if who_trigger else 0)
        + (8 if hpi < 45 else 0)
    )
    scores = {"Primary": round(primary, 2), "Adjacent": round(adjacent, 2), "WHO": round(who, 2)}
    return max(scores, key=scores.get), scores


def evaluate_candidate(row: Dict[str, Any], locks: Dict[str, str]) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, float]]:
    vals = metrics(row)
    player = _txt(row.get("player"))
    team = _txt(row.get("team"))
    pitcher = _txt(row.get("pitcher"))
    gkey = _txt(row.get("game_key") or row.get("game"))
    gid = game_id(row)
    locked_team = locks.get(str(gid), "")
    notes = " ".join([_txt(row.get(k)) for k in row.keys() if any(x in str(k).lower() for x in ["note", "tag", "raw", "status"])]).lower()

    pull, hard, barrel, sweet, dmg, hpi, hr, edge, slot = [vals[k] for k in ["pull", "hard", "barrel", "sweet", "dmg", "hpi", "hr", "edge", "slot"]]
    mc = metric_count(vals)
    trigger = pull >= 30 or hard >= 30 or barrel >= 5 or dmg >= 0.8 or hpi >= 20 or hr >= 0.8 or edge >= 0

    gates = []
    add_gate(gates, 0, "Real PDF row", bool(player and gkey), 8 if player and gkey else 0, 8, f"player={player}; game={gkey}")
    add_gate(gates, 1, "Attack side lock", bool(locked_team and team == locked_team), 10 if locked_team and team == locked_team else 0, 10, f"locked={locked_team}; row_team={team}")
    add_gate(gates, 2, "Metric survival", mc >= 3 and trigger, 10 if mc >= 3 and trigger else 0, 10, f"metric_count={mc}; trigger={trigger}")
    lane = max(gate_strength(hr, 0.8, 2.4, 10), gate_strength(edge, 0, 15, 10), gate_strength(dmg, 0.8, 2.4, 10), gate_strength(hpi, 20, 80, 10))
    add_gate(gates, 3, "Pitcher HR lane", lane > 0, lane, 10, f"hr={hr}; edge={edge}; dmg={dmg}; hpi={hpi}")
    launch = max(gate_strength(pull, 30, 55, 12), gate_strength(sweet, 20, 38, 12), gate_strength(barrel, 5, 16, 12))
    add_gate(gates, 4, "Pull-air launch", launch > 0, launch, 12, f"pull={pull}; sweet={sweet}; barrel={barrel}")
    conversion = max(gate_strength(dmg, 0.8, 2.4, 12), gate_strength(barrel, 5, 16, 12), gate_strength(hpi, 20, 80, 12), gate_strength(hr, 0.8, 2.4, 12))
    add_gate(gates, 5, "Conversion DNA", conversion > 0, conversion, 12, f"dmg={dmg}; barrel={barrel}; hpi={hpi}; hr={hr}")
    add_gate(gates, 6, "Lineup opportunity", slot == 0 or slot <= 7, 6 if slot == 0 or slot <= 7 else 2, 6, f"slot={slot}", hard_gate=False)
    support = max(gate_strength(hard, 30, 58, 8), gate_strength(barrel, 5, 16, 8), gate_strength(dmg, 0.8, 2.4, 8))
    add_gate(gates, 7, "Hard-hit support", support > 0, support, 8, f"hard={hard}; barrel={barrel}; dmg={dmg}", hard_gate=False)
    role, role_scores = role_path(vals, notes)
    add_gate(gates, 8, "Role path", True, role_scores.get(role, 0), max(1, max(role_scores.values())), f"role={role}; scores={role_scores}", hard_gate=False)
    trap = "trap" in notes or "red flag" in notes
    add_gate(gates, 9, "Trap audit", not trap, 8 if not trap else 0, 8, "no trap" if not trap else "trap/red flag")
    finisher = 0
    if pull >= 34:
        finisher = max(gate_strength(hard, 30, 58, 14), gate_strength(barrel, 5, 16, 14), gate_strength(dmg, 0.8, 2.4, 14), gate_strength(hpi, 20, 80, 14), gate_strength(hr, 0.8, 2.4, 14))
    add_gate(gates, 10, "Finisher gate", finisher > 0, finisher, 14, f"pull={pull}; hard={hard}; barrel={barrel}; dmg={dmg}; hpi={hpi}; hr={hr}")
    final_strength = max(gate_strength(pull, 30, 55, 10), gate_strength(hard, 30, 58, 10), gate_strength(barrel, 5, 16, 10), gate_strength(dmg, 0.8, 2.4, 10), gate_strength(hpi, 20, 80, 10), gate_strength(hr, 0.8, 2.4, 10))
    add_gate(gates, 11, "Gate 19 confirm", final_strength > 0, final_strength, 10, f"final_strength={round(final_strength, 2)}")

    hard_cut = any(g["cut"] for g in gates)
    pass_depth = sum(1 for g in gates if g["result"] == "PASS")
    cut_depth = sum(1 for g in gates if g["result"] == "CUT")
    raw_score = sum(g["score"] for g in gates)
    max_score = sum(g["max_score"] for g in gates)
    survival_depth_score = (pass_depth / max(1, len(gates))) * 70
    quality_score = (raw_score / max(1, max_score)) * 25
    integrity_penalty = cut_depth * 8

    blender_score = round(max(1, min(95, survival_depth_score + quality_score - integrity_penalty)), 1)
    if hard_cut:
        blender_score = round(min(blender_score, 54.9), 1)

    eligible = not hard_cut and blender_score >= 55
    final_role = role if eligible else "CUT"

    archetype = {
        "Primary": "Primary HR Owner",
        "Adjacent": "Adjacent / Decoy Transfer",
        "WHO": "WHO / Chaos Owner",
        "CUT": "Cut by gates",
    }[final_role]

    result = {
        **row,
        "game_id": gid,
        "locked_attack_side": locked_team,
        "blender_eligible": bool(eligible),
        "blender_score": blender_score,
        "support_score": round(raw_score, 2),
        "score": blender_score,
        "official_core_role": final_role,
        "archetype": archetype,
        "metric_count": mc,
        "pass_depth": pass_depth,
        "cut_depth": cut_depth,
        "elimination_score": blender_score,
        "stop_gate": "" if eligible else next((g["gate"] for g in gates if g["cut"]), "cut"),
        "final_reason": f"{final_role} survived elimination path" if eligible else "CUT — eliminated by gate path",
        "gate_trace_json": json.dumps(gates),
        "role_scores_json": json.dumps(role_scores),
    }
    return result, gates, role_scores


def resolve_owners_state_machine(survivors: pd.DataFrame) -> pd.DataFrame:
    passed = survivors[survivors["blender_eligible"] == True].copy()
    if passed.empty:
        return pd.DataFrame()

    owners = []
    used_players = set()
    for gid, g in passed.groupby("game_id", dropna=False):
        if not _txt(gid):
            continue
        # this is the only resolver: last surviving owner by elimination depth + path strength
        g = g.copy()
        g["_owner_depth"] = g["pass_depth"].fillna(0) * 100 + g["support_score"].fillna(0)
        g = g.sort_values(["_owner_depth", "elimination_score"], ascending=[False, False])
        for _, row in g.iterrows():
            player = _txt(row.get("player")).lower()
            if player and player not in used_players:
                used_players.add(player)
                owners.append(row.drop(labels=["_owner_depth"], errors="ignore").to_dict())
                break

    if not owners:
        return pd.DataFrame()
    return pd.DataFrame(owners).reset_index(drop=True)


def build_core_no_refill(owners: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(owners, pd.DataFrame) or owners.empty:
        return pd.DataFrame()

    used_players = set()
    used_games = set()
    rows = []

    for slot, role in [("PRIMARY", "Primary"), ("ADJACENT", "Adjacent"), ("WHO", "WHO")]:
        pool = owners[owners["official_core_role"].astype(str) == role].copy()
        if pool.empty:
            continue
        pool = pool[~pool["player"].astype(str).str.lower().isin(used_players)].copy()
        pool = pool[~pool["game_id"].astype(str).isin(used_games)].copy()
        if pool.empty:
            continue

        # role lane pick = deepest elimination survivor in that role, not generic best remaining
        pool["_lane_depth"] = pool["pass_depth"].fillna(0) * 100 + pool["support_score"].fillna(0)
        pick = pool.sort_values(["_lane_depth", "elimination_score"], ascending=[False, False]).head(1).copy()
        if pick.empty:
            continue
        pick["core_slot"] = slot
        pick = pick.drop(columns=["_lane_depth"], errors="ignore")
        rows.append(pick)
        used_players.update(pick["player"].astype(str).str.lower().tolist())
        used_games.update(pick["game_id"].astype(str).tolist())

    if not rows:
        return pd.DataFrame()
    core = pd.concat(rows, ignore_index=True)
    core["ticket_role"] = "CORE"
    return core.reset_index(drop=True)


def run_true_blender(df, *args, **kwargs) -> Dict[str, Any]:
    work = normalize_feed(df)
    if work.empty:
        return empty_results("No usable feed rows loaded.")

    locks, environment_board = lock_attack_sides(work)
    survivors_rows = []
    board_rows = []
    role_rows = []

    for idx, r in work.iterrows():
        row = r.to_dict()
        candidate, gates, role_scores = evaluate_candidate(row, locks)
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
            "pass_depth": candidate.get("pass_depth", 0),
            "cut_depth": candidate.get("cut_depth", 0),
            "elimination_score": candidate.get("elimination_score", 0),
        })

    survivors = pd.DataFrame(survivors_rows)
    cuts = survivors[survivors["blender_eligible"] != True].copy()
    game_board = pd.DataFrame(board_rows)
    role_board = pd.DataFrame(role_rows)

    owners = resolve_owners_state_machine(survivors)
    core = build_core_no_refill(owners)

    # ALT/Chaos also use only unused locked owners, no player recycling.
    used_players = set(core["player"].astype(str).str.lower().tolist()) if not core.empty and "player" in core.columns else set()
    alt = owners[~owners["player"].astype(str).str.lower().isin(used_players)].head(3).copy() if not owners.empty and "player" in owners.columns else pd.DataFrame()
    if not alt.empty:
        alt["ticket_role"] = "ALT"
        used_players.update(alt["player"].astype(str).str.lower().tolist())

    chaos = owners[(owners["official_core_role"] == "WHO") & (~owners["player"].astype(str).str.lower().isin(used_players))].head(3).copy() if not owners.empty and "official_core_role" in owners.columns and "player" in owners.columns else pd.DataFrame()
    if not chaos.empty:
        chaos["ticket_role"] = "WHO"

    games = official_game_count(work) or actual_game_count(work)
    meta = {
        "engine_version": "V161_TRUE_BLENDER_MACHINE",
        "games": int(games),
        "input_rows": int(len(work)),
        "passed_rows": int((survivors["blender_eligible"] == True).sum()),
        "cut_rows": int((survivors["blender_eligible"] != True).sum()),
        "owners_locked": int(len(owners)),
        "core_count": int(len(core)),
        "core_slots": core.get("core_slot", pd.Series(dtype=str)).tolist() if not core.empty else [],
        "generic_refill": False,
        "fallback_sorting": False,
        "role_recycling": False,
        "message": f"V161 true Blender: {len(owners)} locked owners, {int((survivors['blender_eligible'] == True).sum())} pass rows, {int((survivors['blender_eligible'] != True).sum())} cuts. Core slots={core.get('core_slot', pd.Series(dtype=str)).tolist() if not core.empty else []}.",
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
            "rule": "TRUE_STATE_MACHINE",
            "generic_refill": False,
            "fallback_sorting": False,
            "role_recycling": False,
            "one_player_one_role": True,
            "one_owner_per_game": True,
        }]),
        "meta": meta,
    }
    save_locked_results(results)
    return results
