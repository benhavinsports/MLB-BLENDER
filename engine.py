
import re
import json
from pathlib import Path
import pandas as pd
import numpy as np

APP_ENGINE_VERSION = "v142_CLEAN_PRODUCTION_STRENGTHENED"

RECENT_REPEAT_NAMES = {
    "kyle schwarber", "austin riley", "byron buxton", "james wood", "nick kurtz",
    "jac caglianone", "kazuma okamoto"
}

PRIMARY_STAR_NAMES = {
    "kyle schwarber","austin riley","aaron judge","shohei ohtani","mookie betts",
    "freddie freeman","matt olson","jose ramirez","josé ramírez","vladimir guerrero jr",
    "vladimir guerrero jr.","bobby witt jr","bobby witt jr.","james wood","byron buxton",
    "pete alonso","yordan alvarez","juan soto","rafael devers","nick kurtz"
}

SYNTHETIC_NAMES = {
    "", "nan", "none", "weak slot", "recovery", "data recovery", "visible recovery",
    "audit survivor", "parse audit", "slot weakness", "pitcher weakness", "team slot"
}

BOARD_GATES = [
    ("START", "start"),
    ("Pool", "pool"),
    ("Weak Slot", "weakslot"),
    ("Pitcher Lane", "pitcher"),
    ("Pitch Type", "pitch"),
    ("Pull-Air", "pull"),
    ("Launch", "launch"),
    ("Damage", "damage"),
    ("Conversion", "conversion"),
    ("Opportunity", "opportunity"),
    ("Hard-Hit", "hardhit"),
    ("Adjacent Pressure", "adjacent"),
    ("WHO Trigger", "who"),
    ("Game Script", "script"),
    ("Finisher", "finisher"),
    ("Event Isolation", "isolation"),
    ("OWNER", "owner"),
]

def _s(x):
    return re.sub(r"\s+", " ", str(x or "").strip())

def _key(x):
    return _s(x).lower()

def _num(row, col, default=0.0):
    try:
        v = row.get(col, default)
        if pd.isna(v):
            return default
        return float(v)
    except Exception:
        return default

def _txt(row):
    return " ".join(str(row.get(c, "")) for c in [
        "gate_path", "soft_fails", "hard_fails", "event_note", "fresh_note",
        "archetype", "official_core_role", "tags", "parse_note", "lane_note", "event_role"
    ]).lower()

def csv_bytes(df):
    try:
        if df is None:
            df = pd.DataFrame()
        return df.to_csv(index=False).encode("utf-8")
    except Exception:
        return b""

def json_bytes(obj):
    try:
        return json.dumps(obj, default=str, indent=2).encode("utf-8")
    except Exception:
        return b"{}"

def empty_results():
    return {
        "owners": pd.DataFrame(),
        "survivors": pd.DataFrame(),
        "core": pd.DataFrame(),
        "alt": pd.DataFrame(),
        "chaos": pd.DataFrame(),
        "meta": {"engine_version": APP_ENGINE_VERSION},
    }

def safe_results(res=None):
    if not isinstance(res, dict):
        return empty_results()
    out = empty_results()
    out.update(res)
    return out

def load_locked_results(*args, **kwargs):
    return empty_results()

def save_locked_results(*args, **kwargs):
    return True

def clear_locked_results(*args, **kwargs):
    return True

def normalize_game_frame(df):
    if df is None:
        return pd.DataFrame()
    out = df.copy()
    for col in ["player", "team", "pitcher", "game"]:
        if col in out.columns:
            out[col] = out[col].astype(str).map(_s)
    if "game" not in out.columns:
        out["game"] = ""
    if "team" in out.columns and "pitcher" in out.columns:
        out["game"] = out.apply(
            lambda r: f"{r.get('team','')} vs {r.get('pitcher','')}" if _s(r.get("pitcher","")) else _s(r.get("game","")),
            axis=1
        )
    return out

def normalize_feed(df):
    return normalize_game_frame(df)

def normalize_columns(df):
    return normalize_game_frame(df)

def merge_public_context(df, public_context=None):
    # Uploaded PDF/feed stays source of truth.
    return normalize_game_frame(df)

def attach_slate_matchup_context(feed_df, public_context=None):
    return merge_public_context(feed_df, None)

def fetch_live_public_slate(*args, **kwargs):
    return pd.DataFrame(), {"source": "disabled_pdf_source_of_truth", "games": 0}

def fetch_live_public_hitter_pool(*args, **kwargs):
    return pd.DataFrame(), {"source": "disabled_pdf_source_of_truth", "players": 0}

def recalc_adaptive_weights_from_history(*args, **kwargs):
    return {"ok": True, "engine_version": APP_ENGINE_VERSION}

def attack_pool_count(df):
    if df is None or not hasattr(df, "empty") or df.empty:
        return 0
    d = normalize_game_frame(df)
    if "game" in d.columns:
        return int(d["game"].dropna().astype(str).map(_key).replace("", np.nan).dropna().nunique())
    return 0

def actual_game_count(df):
    return attack_pool_count(df)

def slate_game_count_from_public_context(public_context=None, fallback_df=None):
    return attack_pool_count(fallback_df) if fallback_df is not None else 0

def _ensure_numeric(out):
    aliases = {
        "pull": "pull_pct",
        "sweet": "sweet_spot_pct",
        "sweet_spot": "sweet_spot_pct",
        "barrel": "barrel_pct",
        "hardhit": "hard_hit_pct",
        "hard_hit": "hard_hit_pct",
        "hrpa": "hr_pa",
        "pitch": "pitch_edge",
    }
    for src, dst in aliases.items():
        if dst not in out.columns and src in out.columns:
            out[dst] = out[src]
    for c in ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi","pitch_edge","score"]:
        if c not in out.columns:
            out[c] = 0.0
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)
    return out

def _is_real_player(row):
    name = _key(row.get("player", ""))
    if name in SYNTHETIC_NAMES:
        return False
    if name.startswith("weak ") or name.endswith(" slot") or "parse audit" in name:
        return False
    if not _s(row.get("team", "")) or not _s(row.get("pitcher", "")):
        return False
    if len(name.split()) < 2:
        metric_count = sum(
            1 for c in ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi"]
            if c in row and pd.notna(row.get(c))
        )
        if metric_count < 4:
            return False
    return True

def prepare_candidates(df):
    if df is None or not hasattr(df, "empty") or df.empty:
        return pd.DataFrame()
    out = normalize_game_frame(df)
    out = _ensure_numeric(out)
    for c in ["player", "team", "pitcher", "hard_fails", "soft_fails", "gate_path", "official_core_role", "archetype", "tags", "parse_note"]:
        if c not in out.columns:
            out[c] = ""
    out = out[out.apply(_is_real_player, axis=1)].copy()
    if out.empty:
        return out
    out = out.drop_duplicates(subset=["player", "team", "pitcher"], keep="first").reset_index(drop=True)
    return out

def _weak_count(row):
    txt = _txt(row)
    soft = str(row.get("soft_fails", "")).lower()
    count = 0
    for g in ["pull-air","conversion","opportunity","adjacent","who","chaos","finisher"]:
        if g in soft or f"{g}: weak" in txt:
            count += 1
    return count

def _repeat_exception(row):
    txt = _txt(row)
    flags = 0
    if "adjacent" in txt and "pass" in txt: flags += 1
    if ("who" in txt or "chaos" in txt) and "pass" in txt: flags += 1
    if "game script" in txt and "pass" in txt: flags += 1
    if "anti-chalk" in txt and "pass" in txt: flags += 1
    if "pitch type" in txt and "pass" in txt: flags += 1
    if _num(row, "pull_pct") >= 35 and _num(row, "dmg") >= 1.6: flags += 1
    if _num(row, "barrel_pct") >= 11 and _num(row, "hr_pa") >= 2.0: flags += 1
    return flags >= 4

def _repeat_cut(row):
    name = _key(row.get("player", ""))
    return name in RECENT_REPEAT_NAMES and not _repeat_exception(row)

def _dna(row):
    pull = _num(row, "pull_pct"); sweet = _num(row, "sweet_spot_pct"); barrel = _num(row, "barrel_pct")
    hard = _num(row, "hard_hit_pct"); dmg = _num(row, "dmg"); hrpa = _num(row, "hr_pa"); hpi = _num(row, "hpi")
    return (
        (22 if pull >= 35 else 16 if pull >= 30 else 8 if pull >= 25 else 2) +
        (10 if sweet >= 28 else 5 if sweet >= 24 else 1) +
        (14 if barrel >= 10 else 8 if barrel >= 7 else 1) +
        (8 if hard >= 42 else 3) +
        (18 if dmg >= 1.8 else 12 if dmg >= 1.35 else 5 if dmg >= 1.0 else 0) +
        (18 if hrpa >= 3 else 12 if hrpa >= 1.8 else 6 if hrpa >= 1.0 else 0) +
        (6 if hpi >= 40 else 3 if hpi >= 28 else 0)
    )

def _primary_ok(row):
    txt = _txt(row)
    if str(row.get("hard_fails", "")).strip(): return False
    if _repeat_cut(row): return False
    if "pull-air: weak" in txt or "finisher: weak" in txt or "conversion: weak" in txt: return False
    return _num(row, "pull_pct") >= 30 and _num(row, "dmg") >= 1.25 and (_num(row, "hr_pa") >= 1.2 or _num(row, "barrel_pct") >= 7)

def _adjacent_ok(row):
    txt = _txt(row)
    if str(row.get("hard_fails", "")).strip(): return False
    if _repeat_cut(row): return False
    if "adjacent" not in txt or "weak" in txt and "adjacent" in txt: return False
    if _key(row.get("player", "")) in PRIMARY_STAR_NAMES and _primary_ok(row): return False
    return _num(row, "pull_pct") >= 25 and _num(row, "dmg") >= 1.0

def _who_ok(row):
    txt = _txt(row)
    if str(row.get("hard_fails", "")).strip(): return False
    if _repeat_cut(row): return False
    if "who" not in txt and "chaos" not in txt: return False
    if "who/chaos: weak" in txt or "chaos: weak" in txt: return False
    if _primary_ok(row): return False
    if _key(row.get("player", "")) in PRIMARY_STAR_NAMES: return False
    return _num(row, "pull_pct") >= 22 and _num(row, "dmg") >= 0.8

def _role(row):
    if _repeat_cut(row): return "ROTATED"
    if _primary_ok(row): return "Primary"
    if _adjacent_ok(row): return "Adjacent"
    if _who_ok(row): return "WHO"
    return "CUT"

def _ceiling(row, role):
    weak = _weak_count(row)
    if role in ["CUT", "ROTATED"]: return 49
    if weak >= 3: return 59
    if weak == 2: return 74
    if weak == 1: return 88
    return 100

def _score(row):
    role = _role(row)
    raw = _num(row, "raw_blender_score", _num(row, "score"))
    dna = _dna(row)
    mistake = 10 if _num(row, "pitch_edge") > 0 and _num(row, "dmg") >= 1.25 else 0
    if role == "Primary":
        score = raw * 0.18 + dna * 0.78 + mistake
    elif role == "Adjacent":
        score = raw * 0.10 + dna * 0.55 + 24 + mistake
    elif role == "WHO":
        score = raw * 0.06 + dna * 0.45 + 28 + mistake
    elif role == "ROTATED":
        score = min(raw, 35)
    else:
        score = min(raw, 49)
    return round(max(0, min(_ceiling(row, role), score)), 1)

def _gate_status(row, label, key):
    txt = _txt(row)
    soft = str(row.get("soft_fails", "")).lower()
    hard = str(row.get("hard_fails", "")).lower()
    role = str(row.get("event_role", ""))
    label_l = label.lower()
    if label_l in hard or key in hard or f"{label_l}: cut" in txt or f"{label_l}: fail" in txt:
        return "CUT"
    if label_l in soft or key in soft or f"{label_l}: weak" in txt:
        return "SOFT"
    if f"{label_l}: pass" in txt or f"{label_l}: owner" in txt:
        return "PASS"
    if key == "start": return "PASS"
    if key == "pool": return "PASS"
    if key == "weakslot": return "PASS" if _num(row, "dmg") >= 1.25 else "SOFT"
    if key == "pull": return "PASS" if _num(row, "pull_pct") >= 30 else "SOFT" if _num(row, "pull_pct") >= 25 else "CUT"
    if key == "launch": return "PASS" if _num(row, "sweet_spot_pct") >= 26 else "SOFT" if _num(row, "sweet_spot_pct") >= 22 else "CUT"
    if key == "damage": return "PASS" if _num(row, "barrel_pct") >= 8 or _num(row, "dmg") >= 1.35 else "SOFT" if _num(row, "dmg") >= 1.0 else "CUT"
    if key == "conversion": return "PASS" if _num(row, "hr_pa") >= 1.8 else "SOFT" if _num(row, "hr_pa") >= 1.0 else "CUT"
    if key == "opportunity": return "PASS" if _num(row, "hpi") >= 35 else "SOFT" if _num(row, "hpi") >= 25 else "CUT"
    if key == "hardhit": return "PASS" if _num(row, "hard_hit_pct") >= 40 else "SOFT" if _num(row, "hard_hit_pct") >= 34 else "CUT"
    if key == "adjacent": return "PASS" if role == "Adjacent" else "SOFT" if "adjacent" in txt else "CUT"
    if key == "who": return "PASS" if role == "WHO" else "SOFT" if "who" in txt or "chaos" in txt else "CUT"
    if key in ["finisher", "isolation", "owner"]: return "PASS" if role in ["Primary", "Adjacent", "WHO"] else "CUT"
    return "PASS" if role in ["Primary", "Adjacent", "WHO"] else "SOFT"

def apply_board_memory(df):
    if df is None or not hasattr(df, "empty") or df.empty:
        return df
    out = df.copy()
    fulls, passes, softs, cuts = [], [], [], []
    for _, row in out.iterrows():
        full, p, s, c = [], [], [], []
        for label, key in BOARD_GATES:
            st = _gate_status(row, label, key)
            full.append(f"{label}: {st}")
            if st == "PASS": p.append(label)
            elif st == "SOFT": s.append(label)
            else: c.append(label)
        fulls.append(" | ".join(full))
        passes.append(", ".join(p))
        softs.append(", ".join(s))
        cuts.append(", ".join(c))
    out["gate_trace_full"] = fulls
    out["pass_gates"] = passes
    out["soft_gates"] = softs
    out["cut_gates"] = cuts
    out["pass_count"] = [len(x.split(", ")) if x else 0 for x in passes]
    out["soft_count"] = [len(x.split(", ")) if x else 0 for x in softs]
    out["cut_count"] = [len(x.split(", ")) if x else 0 for x in cuts]
    out["board_lane_label"] = out.apply(
        lambda r: f"{str(r.get('event_role') or r.get('official_core_role') or 'Audit')} lane • PASS {int(r.get('pass_count', 0))} / SOFT {int(r.get('soft_count', 0))} / CUT {int(r.get('cut_count', 0))}",
        axis=1
    )
    out["lane_note"] = out["board_lane_label"]
    return out

def evaluate_candidates(df):
    out = prepare_candidates(df)
    if out.empty:
        return out
    if "raw_blender_score" not in out.columns:
        out["raw_blender_score"] = out["score"]
    out["repeat_exception"] = out.apply(_repeat_exception, axis=1)
    out["weak_gate_count"] = out.apply(_weak_count, axis=1)
    out["conversion_dna"] = out.apply(_dna, axis=1).round(1)
    out["event_role"] = out.apply(_role, axis=1)
    out["score_ceiling"] = out.apply(lambda r: _ceiling(r, r["event_role"]), axis=1)
    out["event_isolation_score"] = out.apply(_score, axis=1)
    out["score"] = out["event_isolation_score"]
    out["ownership_eligible"] = out["event_role"].isin(["Primary", "Adjacent", "WHO"])
    out["fresh_note"] = out.apply(
        lambda r: "REPEAT_ALLOWED_TIERED_DOWN" if _key(r.get("player","")) in RECENT_REPEAT_NAMES and r["repeat_exception"]
        else ("REPEAT_ROTATED_CUT" if _key(r.get("player","")) in RECENT_REPEAT_NAMES else "FRESH_PROFILE"),
        axis=1
    )
    out["event_note"] = out["event_role"].map({
        "Primary":"PRIMARY_EVENT_OWNER",
        "Adjacent":"ADJACENT_TRANSFER_EVENT_OWNER",
        "WHO":"WHO_CHAOS_EVENT_OWNER",
        "ROTATED":"ROTATED_OUT_REPEAT",
        "CUT":"CUT_BY_ROLE_LOCK"
    })
    return apply_board_memory(out.sort_values("score", ascending=False).reset_index(drop=True))

def _take(pool, used, n=1, fresh_first=True):
    if pool is None or pool.empty:
        return pd.DataFrame()
    d = pool.copy()
    if "player" in d.columns:
        d = d[~d["player"].astype(str).str.lower().str.strip().isin(used)]
        d = d.drop_duplicates(subset=["player"], keep="first")
    if d.empty:
        return pd.DataFrame()
    if fresh_first and "fresh_note" in d.columns:
        fresh = d[~d["fresh_note"].astype(str).str.contains("REPEAT_ROTATED_CUT", na=False)].copy()
        if not fresh.empty:
            d = fresh
    return d.sort_values("score", ascending=False).head(n).copy()

def build_tickets_from_owners(owners, survivors=None):
    ranked = owners if owners is not None and hasattr(owners, "empty") and not owners.empty else survivors
    if ranked is None or not hasattr(ranked, "empty") or ranked.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    if "ownership_eligible" in ranked.columns:
        eligible = ranked[ranked["ownership_eligible"].astype(bool)].copy()
    else:
        eligible = ranked[ranked["event_role"].isin(["Primary","Adjacent","WHO"])].copy() if "event_role" in ranked.columns else ranked.copy()
    if eligible.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    used, parts = set(), []
    for role, arch in [("Primary","Primary Event Owner"),("Adjacent","Adjacent / Transfer Event Owner"),("WHO","WHO / Chaos Event Owner")]:
        pool = eligible[eligible["event_role"].eq(role)].copy() if "event_role" in eligible.columns else pd.DataFrame()
        one = _take(pool, used, 1)
        source = "TRUE_ROLE"
        if one.empty:
            one = _take(eligible, used, 1)
            source = "ROLE_SUPPORT_FALLBACK"
        if not one.empty:
            one["official_core_role"] = role
            one["archetype"] = arch if source == "TRUE_ROLE" else f"{role} Support Fallback"
            one["core_slot_source"] = source
            used.update(one["player"].astype(str).str.lower().str.strip().tolist())
            parts.append(one)
    core = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if not core.empty:
        hi = set(core.sort_values("score", ascending=False).head(2)["player"].astype(str).str.lower().str.strip())
        core["main_core_highlight"] = core["player"].astype(str).str.lower().str.strip().isin(hi)
        order = {"Primary":0, "Adjacent":1, "WHO":2}
        core["__order"] = core["official_core_role"].map(order).fillna(9)
        core = core.sort_values("__order").drop(columns=["__order"]).reset_index(drop=True)
    alt = _take(eligible, used, 3)
    if not alt.empty:
        alt["official_core_role"] = "ALT"
        alt["archetype"] = "Unified Alternate"
    chaos_pool = eligible[eligible["event_role"].eq("WHO")].copy() if "event_role" in eligible.columns else pd.DataFrame()
    chaos = _take(chaos_pool, used, 3)
    if not chaos.empty:
        chaos["official_core_role"] = "WHO"
        chaos["archetype"] = "WHO / Chaos Event Owner"
    return apply_board_memory(core), apply_board_memory(alt), apply_board_memory(chaos)

def run_true_blender(df, *args, **kwargs):
    survivors = evaluate_candidates(df)
    owners = survivors[survivors["ownership_eligible"].astype(bool)].copy() if "ownership_eligible" in survivors.columns else survivors.copy()
    core, alt, chaos = build_tickets_from_owners(owners, survivors)
    return {
        "owners": owners,
        "survivors": survivors,
        "core": core,
        "alt": alt,
        "chaos": chaos,
        "meta": {
            "engine_version": APP_ENGINE_VERSION,
            "pipeline": "clean_production_strengthened",
            "players": int(len(prepare_candidates(df))),
            "owners": int(len(owners)),
            "core": int(len(core)),
            "games": int(attack_pool_count(df)),
        }
    }

def get_game_board(results):
    results = safe_results(results)
    return apply_board_memory(results.get("survivors", pd.DataFrame()))

def clean_results_for_display(results):
    results = safe_results(results)
    for k in ["owners","survivors","core","alt","chaos"]:
        d = results.get(k)
        if d is not None and hasattr(d, "empty") and not d.empty:
            results[k] = apply_board_memory(d)
    return results

def export_results_csv(results):
    results = safe_results(results)
    parts = []
    for name in ["core", "alt", "chaos", "owners", "survivors"]:
        d = results.get(name, pd.DataFrame())
        if d is not None and hasattr(d, "empty") and not d.empty:
            x = d.copy()
            x.insert(0, "section", name)
            parts.append(x)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()

def get_ticket_frames(results):
    results = safe_results(results)
    return results.get("core", pd.DataFrame()), results.get("alt", pd.DataFrame()), results.get("chaos", pd.DataFrame())

# Backward-compatible names app/ui may import.
def run_blender(df, *args, **kwargs): return run_true_blender(df, *args, **kwargs)
def run_public_blender(*args, **kwargs): return run_true_blender(kwargs.get("df", pd.DataFrame()))
def score_candidates(df, *args, **kwargs): return evaluate_candidates(df)
def enrich_feed(df, *args, **kwargs): return normalize_game_frame(df)
def build_feed_from_public(*args, **kwargs): return pd.DataFrame()
def load_public_slate(*args, **kwargs): return pd.DataFrame()
def get_current_feed_summary(df): return {"players": int(len(df)) if df is not None and hasattr(df, "__len__") else 0, "games": attack_pool_count(df)}
def make_summary(df): return get_current_feed_summary(df)
def summarize_feed(df): return get_current_feed_summary(df)
def calibrate_model_weights(*args, **kwargs): return {"ok": True}
def recalibrate_model_weights(*args, **kwargs): return {"ok": True}
def apply_model_calibration(df, *args, **kwargs): return df
def reset_model_calibration(*args, **kwargs): return True
def explain_candidate(row): return str(row.get("event_note", "")) if hasattr(row, "get") else ""
def player_team_integrity_guard(df): return normalize_game_frame(df)
def validate_player_team_integrity(df): return normalize_game_frame(df)
def role_locked_ticket_builder(owners, survivors=None): return build_tickets_from_owners(owners, survivors)
def event_isolation_engine(df): return evaluate_candidates(df)
def apply_event_isolation(df): return evaluate_candidates(df)
def anti_repeat_engine(df): return evaluate_candidates(df)
def rotation_redistribution_engine(df): return evaluate_candidates(df)
def repeat_cut_refill_engine(df): return evaluate_candidates(df)
