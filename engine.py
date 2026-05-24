
import re
from pathlib import Path
import pandas as pd
import numpy as np

APP_ENGINE_VERSION = "v134_RUN_BUTTON_PARSE_UPLOAD_FIX"

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
    "audit survivor", "parse audit", "slot weakness", "pitcher weakness"
}

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

def _text(row):
    return " ".join(str(row.get(c, "")) for c in [
        "player","team","pitcher","game","official_core_role","archetype",
        "gate_path","soft_fails","hard_fails","tags","parse_note"
    ]).lower()

def canonical_game_key(x):
    return _key(x)

def normalize_game_frame(df):
    if df is None:
        return pd.DataFrame()
    out = df.copy()
    for col in ["player","team","pitcher","game"]:
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

def empty_results():
    return {
        "owners": pd.DataFrame(),
        "survivors": pd.DataFrame(),
        "core": pd.DataFrame(),
        "alt": pd.DataFrame(),
        "chaos": pd.DataFrame(),
        "meta": {"engine_version": APP_ENGINE_VERSION}
    }

def safe_results(res=None):
    if not isinstance(res, dict):
        return empty_results()
    base = empty_results()
    base.update(res)
    return base

def load_locked_results(*args, **kwargs):
    return empty_results()

def save_locked_results(*args, **kwargs):
    return True

def clear_locked_results(*args, **kwargs):
    return True

def attack_pool_count(df):
    if df is None or df.empty:
        return 0
    if "game" in df.columns:
        return int(df["game"].dropna().astype(str).map(_key).replace("", np.nan).dropna().nunique())
    if "team" in df.columns and "pitcher" in df.columns:
        return int((df["team"].astype(str) + " vs " + df["pitcher"].astype(str)).map(_key).nunique())
    return 0

def merge_public_context(df, public_context=None):
    # PDF/upload rows are source of truth. Public context never overwrites player/team/pitcher.
    return normalize_game_frame(df)

def attach_slate_matchup_context(feed_df, public_context=None):
    return merge_public_context(feed_df, None)

def _is_real_player(row):
    name = _key(row.get("player",""))
    if name in SYNTHETIC_NAMES:
        return False
    if name.startswith("weak ") or name.endswith(" slot") or "parse audit" in name:
        return False
    if not _s(row.get("team","")) or not _s(row.get("pitcher","")):
        return False
    # Avoid keeping label rows without real hitter stat structure.
    if len(name.split()) < 2:
        metrics = sum(1 for c in ["pull_pct","sweet_spot_pct","barrel_pct","hard_hit_pct","dmg","hr_pa","hpi"] if c in row and pd.notna(row.get(c)))
        if metrics < 4:
            return False
    return True

def _ensure_numeric(out):
    aliases = {
        "pull": "pull_pct",
        "sweet": "sweet_spot_pct",
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

def prepare_candidates(df):
    if df is None or not hasattr(df, "empty") or df.empty:
        return pd.DataFrame()
    out = normalize_game_frame(df)
    out = _ensure_numeric(out)
    if "hard_fails" not in out.columns:
        out["hard_fails"] = ""
    if "soft_fails" not in out.columns:
        out["soft_fails"] = ""
    if "gate_path" not in out.columns:
        out["gate_path"] = ""
    if "player" not in out.columns:
        out["player"] = ""
    if "team" not in out.columns:
        out["team"] = ""
    if "pitcher" not in out.columns:
        out["pitcher"] = ""
    out = out[out.apply(_is_real_player, axis=1)].copy()
    if out.empty:
        return out
    out = out.drop_duplicates(subset=["player","team","pitcher"], keep="first").reset_index(drop=True)
    return out

def _weak_count(row):
    txt = _text(row)
    soft = str(row.get("soft_fails","")).lower()
    count = 0
    for g in ["5 pull-air","8 conversion","9 opportunity","10.5 adjacent","11 who/chaos","16 finisher"]:
        if f"{g}: weak" in txt or g in soft:
            count += 1
    return count

def _repeat_exception(row):
    txt = _text(row)
    flags = 0
    if "10.5 adjacent: pass" in txt: flags += 1
    if "11 who/chaos: pass" in txt: flags += 1
    if "12 game script: pass" in txt: flags += 1
    if "14 anti-chalk: pass" in txt: flags += 1
    if "pitch type: pass" in txt or "4 pitch type: pass" in txt: flags += 1
    if _num(row, "pull_pct") >= 35 and _num(row, "dmg") >= 1.6: flags += 1
    if _num(row, "barrel_pct") >= 11 and _num(row, "hr_pa") >= 2.0: flags += 1
    return flags >= 4

def _rotation_adjust(row):
    name = _key(row.get("player",""))
    if name not in RECENT_REPEAT_NAMES:
        return 0.0
    return -8.0 if _repeat_exception(row) else -32.0


def _repeat_cut(row):
    """Repeat names cannot keep OWNER status unless strict repeat exception passes."""
    name = _key(row.get("player",""))
    return name in RECENT_REPEAT_NAMES and not _repeat_exception(row)

def _dna(row):
    pull = _num(row,"pull_pct"); sweet = _num(row,"sweet_spot_pct"); barrel = _num(row,"barrel_pct")
    dmg = _num(row,"dmg"); hrpa = _num(row,"hr_pa"); hpi = _num(row,"hpi"); hard = _num(row,"hard_hit_pct")
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
    txt = _text(row)
    if str(row.get("hard_fails","")).strip():
        return False
    if any(x in txt for x in ["5 pull-air: weak","16 finisher: weak","8 conversion: weak"]):
        return False
    return _num(row,"pull_pct") >= 30 and _num(row,"dmg") >= 1.25 and (_num(row,"hr_pa") >= 1.2 or _num(row,"barrel_pct") >= 7)

def _adjacent_ok(row):
    txt = _text(row)
    if str(row.get("hard_fails","")).strip():
        return False
    if "10.5 adjacent: weak" in txt:
        return False
    if "10.5 adjacent: pass" not in txt:
        return False
    if _key(row.get("player","")) in PRIMARY_STAR_NAMES and _primary_ok(row):
        return False
    return _num(row,"pull_pct") >= 25 and _num(row,"dmg") >= 1.0

def _who_ok(row):
    txt = _text(row)
    if str(row.get("hard_fails","")).strip():
        return False
    if "11 who/chaos: weak" in txt:
        return False
    if "11 who/chaos: pass" not in txt and "who" not in txt and "chaos" not in txt:
        return False
    if _primary_ok(row):
        return False
    if _key(row.get("player","")) in PRIMARY_STAR_NAMES:
        return False
    return _num(row,"pull_pct") >= 22 and _num(row,"dmg") >= 0.8

def _role(row):
    if _repeat_cut(row):
        return "ROTATED"
    if _primary_ok(row):
        return "Primary"
    if _adjacent_ok(row):
        return "Adjacent"
    if _who_ok(row):
        return "WHO"
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
    mistake = 10 if _num(row,"pitch_edge") > 0 and _num(row,"dmg") >= 1.25 else 0
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
    score += _rotation_adjust(row)
    return round(max(0, min(_ceiling(row, role), score)), 1)

def evaluate_candidates(df):
    out = prepare_candidates(df)
    if out.empty:
        return out
    if "raw_blender_score" not in out.columns:
        out["raw_blender_score"] = out["score"]
    out["repeat_exception"] = out.apply(_repeat_exception, axis=1)
    out["rotation_adjust"] = out.apply(_rotation_adjust, axis=1).round(1)
    out["weak_gate_count"] = out.apply(_weak_count, axis=1)
    out["conversion_dna"] = out.apply(_dna, axis=1).round(1)
    out["event_role"] = out.apply(_role, axis=1)
    out["score_ceiling"] = out.apply(lambda r: _ceiling(r, r["event_role"]), axis=1)
    out["event_isolation_score"] = out.apply(_score, axis=1)
    out["score"] = out["event_isolation_score"]
    out["primary_status"] = out["event_role"].eq("Primary").map({True:"OWNER", False:"CUT"})
    out["adjacent_status"] = out["event_role"].eq("Adjacent").map({True:"OWNER", False:"CUT"})
    out["who_status"] = out["event_role"].eq("WHO").map({True:"OWNER", False:"CUT"})
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
    out["ownership_eligible"] = out["event_role"].isin(["Primary", "Adjacent", "WHO"])
    # Keep ROTATED rows on Game Board audit, but owners/tickets will filter them out.
    return out.sort_values("score", ascending=False).reset_index(drop=True)

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
        fresh = d[~d["fresh_note"].astype(str).str.contains("REPEAT_ROTATED_DOWN", na=False)].copy()
        if not fresh.empty:
            d = fresh
    return d.sort_values("score", ascending=False).head(n).copy()

def build_tickets_from_owners(owners, survivors=None):
    ranked = evaluate_candidates(owners if owners is not None and hasattr(owners,"empty") and not owners.empty else survivors)
    if ranked.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    ranked = ranked[ranked.get("ownership_eligible", True).astype(bool)].copy() if "ownership_eligible" in ranked.columns else ranked
    if ranked.empty:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    used = set()
    parts = []
    for role, arch in [("Primary","Primary Event Owner"),("Adjacent","Adjacent / Transfer Event Owner"),("WHO","WHO / Chaos Event Owner")]:
        pool = ranked[ranked["event_role"].eq(role)].copy()
        one = _take(pool, used, 1, fresh_first=True)
        source = "TRUE_ROLE"
        if one.empty:
            # Core 3 stays structured, but uses next best non-repeat survivor first.
            one = _take(ranked, used, 1, fresh_first=True)
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

    alt_pool = ranked.copy()
    alt = _take(alt_pool, used, 3, fresh_first=True)
    if not alt.empty:
        alt["official_core_role"] = "ALT"
        alt["archetype"] = "Unified Runtime Alternate"
        used.update(alt["player"].astype(str).str.lower().str.strip().tolist())

    chaos_pool = ranked[ranked["event_role"].eq("WHO")].copy()
    chaos = _take(chaos_pool, used, 3, fresh_first=True)
    if not chaos.empty:
        chaos["official_core_role"] = "WHO"
        chaos["archetype"] = "WHO / Chaos Event Owner"
    return core.reset_index(drop=True), alt.reset_index(drop=True), chaos.reset_index(drop=True)

def run_true_blender(df, *args, **kwargs):
    candidates = evaluate_candidates(df)
    survivors = candidates.copy()
    owners = candidates[candidates.get("ownership_eligible", True).astype(bool)].copy() if "ownership_eligible" in candidates.columns else candidates.copy()
    core, alt, chaos = build_tickets_from_owners(owners, survivors)
    return {
        "owners": owners,
        "survivors": survivors,
        "core": core,
        "alt": alt,
        "chaos": chaos,
        "meta": {
            "engine_version": APP_ENGINE_VERSION,
            "pipeline": "single_authority_clean_runtime",
            "players": int(len(prepare_candidates(df))),
            "owners": int(len(owners)),
            "core": int(len(core)),
            "attack_pools": int(attack_pool_count(df)),
        }
    }
