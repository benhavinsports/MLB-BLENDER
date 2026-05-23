
"""
BLENDER AI OIL LAYER

This module is the smart assistant layer around the locked Blender engine.
It does NOT freestyle picks. It only:
1. repairs messy slate rows,
2. validates fields,
3. explains gate results,
4. detects chaos/WHO patterns,
5. calibrates weights from recap history,
6. optionally uses OpenAI API when OPENAI_API_KEY is available.

The locked Blender gates remain the boss.
"""

import os
import json
import re
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

AI_DIR = Path("data/ai_oil")
AI_DIR.mkdir(parents=True, exist_ok=True)

FIELD_ALIASES = {
    "player": ["player", "hitter", "batter", "name", "player_name"],
    "team": ["team", "bat_team", "batter_team", "club"],
    "opponent": ["opponent", "opp", "vs", "pitcher_team"],
    "pitcher": ["pitcher", "sp", "starter", "opposing_pitcher", "probable"],
    "game": ["game", "matchup"],
    "lineup_slot": ["lineup_slot", "slot", "order", "batting_order", "bo"],
    "pull_pct": ["pull_pct", "pull%", "pull", "pull rate", "pull_percent"],
    "sweet_spot_pct": ["sweet_spot_pct", "sweet%", "sweet spot", "sweet_spot", "launch", "launch_angle", "la"],
    "barrel_pct": ["barrel_pct", "barrel%", "brl%", "barrel"],
    "hard_hit_pct": ["hard_hit_pct", "hardhit%", "hard_hit%", "hard hit%", "hh%", "hardhit", "hard hit"],
    "dmg": ["dmg", "damage", "ult", "ultimate", "adj", "adjusted"],
    "hr_pa": ["hr_pa", "hr/pa", "hr rate", "hr_rate", "hr9", "hr/9", "pitcher_hr9"],
    "hpi": ["hpi", "score", "rating", "model", "hr score"],
    "pitch_edge": ["pitch_edge", "pitch edge", "edge", "pitch", "pitchtype edge"],
    "notes": ["notes", "note", "tag", "status"],
}

CORE_FIELDS = ["player", "team", "opponent", "pitcher", "game"]
NUMERIC_FIELDS = ["lineup_slot", "pull_pct", "sweet_spot_pct", "barrel_pct", "hard_hit_pct", "dmg", "hr_pa", "hpi", "pitch_edge"]

def _txt(x):
    try:
        if x is None or pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()

def _num(x, default=np.nan):
    try:
        if x is None or pd.isna(x):
            return default
        s = str(x).replace("%", "").replace("+", "").replace(",", "").strip()
        if s.lower() in {"", "nan", "none", "null", "-", "—"}:
            return default
        return float(s)
    except Exception:
        return default

def _find_col(df, aliases):
    low = {str(c).lower().strip(): c for c in df.columns}
    for a in aliases:
        if a.lower().strip() in low:
            return low[a.lower().strip()]
    for c in df.columns:
        cl = str(c).lower().strip()
        for a in aliases:
            if a.lower().strip() in cl:
                return c
    return None

def ai_field_mapper(df):
    """Map messy feed columns into locked Blender schema."""
    if df is None or len(df) == 0:
        return pd.DataFrame(), {"mapped": {}, "missing": CORE_FIELDS, "warnings": ["Empty dataframe"]}

    raw = df.copy()
    raw.columns = [str(c).strip() for c in raw.columns]
    mapped = pd.DataFrame()
    mapping = {}
    warnings = []

    for target, aliases in FIELD_ALIASES.items():
        col = _find_col(raw, aliases)
        if col is not None:
            mapped[target] = raw[col]
            mapping[target] = col
        else:
            mapped[target] = ""
            mapping[target] = None

    for c in CORE_FIELDS + ["notes"]:
        mapped[c] = mapped[c].apply(_txt)

    for c in NUMERIC_FIELDS:
        mapped[c] = mapped[c].apply(_num)

    # Preserve unknown columns for audit
    for c in raw.columns:
        if c not in mapping.values():
            mapped[f"raw_{c}"] = raw[c]

    # Remove obvious header repeats and empty rows
    mapped = mapped[mapped["player"].astype(str).str.strip().ne("")]
    mapped = mapped[~mapped["player"].astype(str).str.lower().isin(["player", "hitter", "batter", "name"])]

    # Repair game label
    blank_game = mapped["game"].astype(str).str.strip().eq("")
    mapped.loc[blank_game, "game"] = (
        mapped.loc[blank_game, "team"].astype(str).replace("", "TEAM")
        + " vs "
        + mapped.loc[blank_game, "opponent"].astype(str).replace("", "OPP")
    )

    missing = [f for f in CORE_FIELDS if mapped[f].astype(str).str.strip().eq("").all()]
    if missing:
        warnings.append("Missing full-column fields: " + ", ".join(missing))

    return mapped.reset_index(drop=True), {"mapped": mapping, "missing": missing, "warnings": warnings}

def ai_feed_validator(df):
    """Validate feed quality before Blender gates."""
    if df is None or len(df) == 0:
        return {
            "status": "BAD",
            "score": 0,
            "issues": ["No rows loaded"],
            "fixes": ["Upload a slate file or live pool"],
            "summary": "No feed rows were loaded."
        }

    issues = []
    fixes = []
    score = 100

    if "player" not in df or df["player"].astype(str).str.strip().eq("").all():
        issues.append("No usable player names found")
        fixes.append("Check PDF/table parsing or upload CSV")
        score -= 40

    if "team" not in df or df["team"].astype(str).str.strip().eq("").mean() > 0.7:
        issues.append("Most rows missing team")
        fixes.append("AI can still run recovery, but team field should be improved")
        score -= 15

    if "pitcher" not in df or df["pitcher"].astype(str).str.strip().eq("").mean() > 0.7:
        issues.append("Most rows missing pitcher")
        fixes.append("Add probable pitcher column for stronger target selection")
        score -= 15

    metric_count = 0
    for c in NUMERIC_FIELDS:
        if c in df:
            metric_count += df[c].notna().sum()
    possible = max(1, len(df) * len(NUMERIC_FIELDS))
    metric_ratio = metric_count / possible

    if metric_ratio < 0.15:
        issues.append("Very low numeric metric coverage")
        fixes.append("Upload star-tool CSV/PDF with Pull, HH, Barrel, DMG, HPI, pitch edge")
        score -= 25
    elif metric_ratio < 0.35:
        issues.append("Partial metric coverage")
        fixes.append("Recovery owners may be used; add more metrics for cleaner locks")
        score -= 10

    dupes = df["player"].astype(str).str.lower().duplicated().sum() if "player" in df else 0
    if dupes:
        issues.append(f"{dupes} duplicate player rows found")
        fixes.append("Duplicates are allowed but should be reviewed")
        score -= min(10, dupes)

    status = "GOOD" if score >= 80 else ("USABLE" if score >= 55 else "WEAK")
    return {
        "status": status,
        "score": max(0, int(score)),
        "issues": issues,
        "fixes": fixes,
        "summary": f"Feed quality: {status} ({max(0, int(score))}/100). Rows={len(df)}."
    }

def ai_chaos_who_detector(df):
    """Detect games where WHO/chaos owner should be elevated."""
    if df is None or len(df) == 0:
        return pd.DataFrame()

    rows = []
    gcol = "game" if "game" in df.columns else None
    if not gcol:
        return pd.DataFrame()

    for game, g in df.groupby(gcol):
        pull = pd.to_numeric(g.get("pull_pct", pd.Series(dtype=float)), errors="coerce")
        hard = pd.to_numeric(g.get("hard_hit_pct", pd.Series(dtype=float)), errors="coerce")
        barrel = pd.to_numeric(g.get("barrel_pct", pd.Series(dtype=float)), errors="coerce")
        hrpa = pd.to_numeric(g.get("hr_pa", pd.Series(dtype=float)), errors="coerce")
        notes = " ".join(g.get("notes", pd.Series(dtype=str)).astype(str).str.lower().tolist())

        flags = []
        if len(g) >= 6:
            flags.append("large player pool")
        if hrpa.max(skipna=True) >= 1.5:
            flags.append("pitcher HR lane")
        if (pull.fillna(0).between(30, 40) & hard.fillna(0).between(30, 45)).sum() >= 2:
            flags.append("multiple secondary bats fit chaos band")
        if barrel.fillna(0).std(skipna=True) <= 3 and barrel.notna().sum() >= 3:
            flags.append("no clear barrel separation")
        if "chaos" in notes or "who" in notes:
            flags.append("feed tag says chaos/WHO")

        level = "HIGH" if len(flags) >= 3 else ("MEDIUM" if len(flags) >= 2 else "LOW")
        rows.append({"game": game, "chaos_level": level, "flags": "; ".join(flags), "flag_count": len(flags)})

    return pd.DataFrame(rows)

def ai_explain_results(results):
    """Make readable audit copy from gate results without changing picks."""
    if not isinstance(results, dict):
        return "No results object found."

    owners = results.get("owners", pd.DataFrame())
    meta = results.get("meta", {})
    if owners is None or len(owners) == 0:
        return "Blender ran but no owners were locked. Check feed quality and parsing."

    lines = []
    lines.append(meta.get("message", "Blender complete."))
    for _, r in owners.head(20).iterrows():
        player = _txt(r.get("player"))
        game = _txt(r.get("game")) or _txt(r.get("game_owner"))
        role = _txt(r.get("official_core_role"))
        score = _txt(r.get("score"))
        status = _txt(r.get("data_status"))
        hard_fails = _txt(r.get("hard_fails"))
        if hard_fails:
            why = f"{player} locked as {role} in {game} with score {score}. Data status: {status}. Watch gates: {hard_fails}."
        else:
            why = f"{player} locked as {role} in {game} with score {score}. Data status: {status}. Cleanest isolated owner for that game."
        lines.append(why)
    return "\n".join(lines)

def ai_calibrate_from_recap(recap_path="data/recap_history.csv"):
    """Read recap history and produce suggested weights. Does not mutate engine unless app applies it."""
    path = Path(recap_path)
    if not path.exists():
        return {
            "status": "NO_HISTORY",
            "weights": {
                "pull_air": 1.00,
                "hard_hit": 1.00,
                "barrel": 1.00,
                "pitch_edge": 1.00,
                "chaos": 1.00,
            },
            "notes": "No recap history yet."
        }

    try:
        hist = pd.read_csv(path)
    except Exception as e:
        return {"status": "BAD_HISTORY", "weights": {}, "notes": str(e)}

    hit_col = None
    for c in hist.columns:
        if c.lower() in {"hr", "hit_hr", "homer", "result", "hr_result"}:
            hit_col = c
            break

    weights = {
        "pull_air": 1.00,
        "hard_hit": 1.00,
        "barrel": 1.00,
        "pitch_edge": 1.00,
        "chaos": 1.00,
    }

    notes = []
    if hit_col:
        s = hist[hit_col].astype(str).str.lower()
        hr_rate = s.isin(["1", "true", "yes", "hr", "hit", "home run"]).mean()
        if hr_rate < 0.12:
            weights["chaos"] = 1.08
            weights["pull_air"] = 1.10
            notes.append("Low hit rate: slightly boost pull-air and chaos discovery.")
        elif hr_rate > 0.22:
            weights["barrel"] = 1.08
            weights["pitch_edge"] = 1.05
            notes.append("Strong hit rate: preserve barrel/pitch-edge weighting.")
    else:
        notes.append("No HR result column found; default weights retained.")

    return {"status": "OK", "weights": weights, "notes": " ".join(notes), "rows": len(hist)}

def openai_available():
    return bool(os.environ.get("OPENAI_API_KEY"))

def ai_openai_parse_text_to_rows(text, model="gpt-4.1-mini"):
    """
    Optional OpenAI parser. Safe fallback returns empty frame if no key or package.
    Use only to clean slate text into rows; never to pick players directly.
    """
    if not openai_available():
        return pd.DataFrame(), {"used_openai": False, "reason": "OPENAI_API_KEY not set"}

    try:
        from openai import OpenAI
        client = OpenAI()
        prompt = (
            "Convert this MLB slate/player-pool text into JSON rows only. "
            "Fields: player, team, opponent, pitcher, game, lineup_slot, pull_pct, sweet_spot_pct, "
            "barrel_pct, hard_hit_pct, dmg, hr_pa, hpi, pitch_edge, notes. "
            "Do not invent missing data. Use null for missing numbers.\n\nTEXT:\n" + str(text)[:50000]
        )
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=0,
        )
        content = resp.choices[0].message.content
        m = re.search(r"\[.*\]", content, re.S)
        rows = json.loads(m.group(0) if m else content)
        df = pd.DataFrame(rows)
        df, audit = ai_field_mapper(df)
        audit["used_openai"] = True
        return df, audit
    except Exception as e:
        return pd.DataFrame(), {"used_openai": False, "reason": str(e)}

def save_ai_audit(feed_audit, validation, chaos, explanation):
    payload = {
        "created_at": datetime.now().isoformat(),
        "feed_audit": feed_audit,
        "validation": validation,
        "chaos": chaos.to_dict(orient="records") if isinstance(chaos, pd.DataFrame) else [],
        "explanation": explanation,
    }
    path = AI_DIR / "latest_ai_audit.json"
    path.write_text(json.dumps(payload, indent=2, default=str))
    return str(path)
