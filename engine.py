from __future__ import annotations
import re
from typing import Any
import pandas as pd

ENGINE_VERSION = "v134_PITCHER_ARCHETYPE_FIRST_GATE_SURVIVOR"
GATES = [f"G{i:02d}" for i in range(1, 20)]


def _num(x, default=0.0):
    try:
        m = re.search(r"-?\d+(?:\.\d+)?", str(x or "").replace("%", ""))
        return float(m.group(0)) if m else default
    except Exception:
        return default


def normalize_players(data: Any) -> pd.DataFrame:
    df = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data or [])
    if df.empty:
        return df
    ren = {}
    for c in df.columns:
        k = str(c).lower().strip().replace(" ", "_")
        ren[c] = {
            "hitter": "player", "batter": "player", "name": "player",
            "offense_team": "team", "target_pitcher": "pitcher", "opp_pitcher": "pitcher",
            "lineup_slot": "slot", "hr/pa": "hr_pa", "hrpa": "hr_pa",
            "damage": "dmg", "edge": "pitch_edge", "tags": "badges",
            "badge_text": "badges", "pitcher_weak_slots": "weak_slots",
        }.get(k, k)
    df = df.rename(columns=ren)
    for c in ["player", "team", "game", "pitcher", "badges", "weak_slots"]:
        if c not in df:
            df[c] = ""
    for c in ["slot", "hr_pa", "dmg", "hpi", "pitch_edge", "hr_edge", "cond", "line", "effort", "fatigue", "rank"]:
        if c not in df:
            df[c] = 0
        df[c] = df[c].map(_num)
    df["player"] = df["player"].astype(str).str.strip()
    df = df[df.player.str.len() > 1].copy()
    if df["game"].astype(str).str.strip().eq("").all():
        df["game"] = df["team"].astype(str) + " vs " + df["pitcher"].astype(str)
    return df.reset_index(drop=True)


def weak_slot_match(r) -> bool:
    slot = int(_num(r.get("slot"))) if _num(r.get("slot")) else 0
    weak = set(re.findall(r"\d+", str(r.get("weak_slots", ""))))
    return bool(slot and str(slot) in weak) or ("weak slot" in str(r.get("badges", "")).lower())


def hitter_attack_tags(r) -> set[str]:
    b = str(r.get("badges", "")).lower()
    tags = set()
    if weak_slot_match(r):
        tags.add("WEAK_SLOT_ATTACK")
    if _num(r.get("pitch_edge")) >= 8 or _num(r.get("hr_edge")) >= 3:
        tags.add("PITCH_TYPE_DAMAGE")
    if _num(r.get("cond")) >= 20 or _num(r.get("line")) >= 25 or "laser" in b or "launch" in b:
        tags.add("PULL_AIR_LIFT")
    if _num(r.get("hr_pa")) >= 3 or _num(r.get("dmg")) >= 1.20 or _num(r.get("hpi")) >= 40:
        tags.add("POWER_CONVERSION")
    if _num(r.get("rank")) >= 5 and (weak_slot_match(r) or _num(r.get("dmg")) >= 1.2):
        tags.add("WHO_CHAOS_RECIPIENT")
    return tags


def lock_pitcher_archetype(side: pd.DataFrame) -> tuple[str, set[str]]:
    """Locks the pitcher weakness archetype BEFORE hitter elimination."""
    counts = {"WEAK_SLOT_ATTACK": 0, "PITCH_TYPE_DAMAGE": 0, "PULL_AIR_LIFT": 0, "POWER_CONVERSION": 0, "WHO_CHAOS_RECIPIENT": 0}
    for _, r in side.iterrows():
        for t in hitter_attack_tags(r):
            if t in counts:
                counts[t] += 1
    # Priority is pitcher weakness first: weak slots and pitch-type damage before generic power.
    locked = []
    if counts["WEAK_SLOT_ATTACK"]:
        locked.append("WEAK_SLOT_ATTACK")
    if counts["PITCH_TYPE_DAMAGE"]:
        locked.append("PITCH_TYPE_DAMAGE")
    if counts["PULL_AIR_LIFT"]:
        locked.append("PULL_AIR_LIFT")
    if not locked and counts["POWER_CONVERSION"]:
        locked.append("POWER_CONVERSION")
    if not locked:
        locked.append("SURVIVAL_RECOVERY")
    return " + ".join(locked), set(locked)


def archetype_match(r, required: set[str]) -> bool:
    if "SURVIVAL_RECOVERY" in required:
        return True
    tags = hitter_attack_tags(r)
    # Must match at least one locked pitcher weakness lane, and must not be an empty-contact profile.
    return bool(tags & required) and (_num(r.get("hr_pa")) > 0 or _num(r.get("dmg")) >= .75 or _num(r.get("hpi")) >= 28)


def feature_score(r):
    b = str(r.get("badges", "")).lower()
    hrpa, dmg, hpi, pitch, hredge, cond, line = [_num(r.get(k)) for k in ["hr_pa", "dmg", "hpi", "pitch_edge", "hr_edge", "cond", "line"]]
    tags = hitter_attack_tags(r)
    pull_air = max(cond, 0) * 0.22 + max(line, 0) * 0.18
    power = max(hrpa, 0) * 7 + max(dmg, 0) * 12 + max(hpi, 0) * 0.52 + max(hredge, 0) * 1.4 + max(pitch, 0) * 0.65
    badge = 0
    for term, pts in [("platoon", 6), ("rakes", 5), ("laser", 6), ("launch", 7), ("weak slot", 6), ("park edge", 4), ("alert", 4), ("hot", 3)]:
        if term in b:
            badge += pts
    if "WEAK_SLOT_ATTACK" in tags:
        badge += 12
    if _num(r.get("rank")) in (1, 2, 3):
        badge += 4
    return round(power + pull_air + badge, 2), {"power": round(power, 2), "pull_air": round(pull_air, 2), "badge": badge, "tags": sorted(tags)}


def gate_rows(side: pd.DataFrame, archetype_name: str, required: set[str]) -> pd.DataFrame:
    rows = []
    for _, r in side.iterrows():
        score, detail = feature_score(r)
        b = str(r.get("badges", "")).lower()
        path = [f"G00: PITCHER ARCHETYPE LOCKED — {archetype_name}"]
        kill = False

        def p(g, why): path.append(f"{g}: pass — {why}")
        def k(g, why):
            nonlocal kill
            path.append(f"{g}: KILL — {why}"); kill = True

        tags = set(detail["tags"])
        if archetype_match(r, required): p("G01", f"hitter matches locked pitcher lane: {', '.join(sorted(tags & required)) or ', '.join(sorted(tags))}")
        else: k("G01", f"does not match locked pitcher lane: {archetype_name}")
        if str(r.get("team", "")).strip(): p("G02", "owned row")
        else: k("G02", "missing team")
        if _num(r.get("slot")) > 0: p("G03", f"slot {int(_num(r.get('slot')))}")
        else: k("G03", "missing slot")
        if detail["power"] >= 18 or _num(r.get("hpi")) >= 28: p("G04", "power floor")
        else: k("G04", "power too low")
        if _num(r.get("hr_pa")) > 0 or _num(r.get("dmg")) >= .75: p("G05", "HR/PA or DMG")
        else: k("G05", "empty HR profile")
        if detail["pull_air"] >= 4.5 or "laser" in b or "launch" in b or "PULL_AIR_LIFT" in tags: p("G06", "pull-air/launch")
        else: k("G06", "no pull-air/launch")
        if _num(r.get("pitch_edge")) >= -35 or _num(r.get("hr_edge")) >= 1: p("G07", "pitch edge alive")
        else: k("G07", "pitch edge kill")
        if weak_slot_match(r) or _num(r.get("dmg")) >= 1.1 or _num(r.get("hpi")) >= 35: p("G08", "lane survives")
        else: k("G08", "no weak lane")
        if _num(r.get("fatigue")) < 85 or _num(r.get("effort")) >= 30: p("G09", "effort/fatigue")
        else: k("G09", "fatigue kill")
        if not (_num(r.get("cond")) <= 0 and _num(r.get("hr_pa")) <= 0 and "cold" in b): p("G10", "conversion alive")
        else: k("G10", "cold zero conversion")
        if score >= 34: p("G11", "pressure floor")
        else: k("G11", "score floor")

        d = r.to_dict(); d.update(raw_score=score, score_detail=detail, attack_tags=" / ".join(sorted(tags)), target_archetype=archetype_name, gate_path=path, eliminated=kill)
        rows.append(d)
    return pd.DataFrame(rows)


def apply_transfer(live: pd.DataFrame) -> pd.DataFrame:
    if live.empty:
        return live
    df = live.copy()
    top = df.sort_values("raw_score", ascending=False).iloc[0]
    top_slot = int(_num(top.get("slot")))
    for idx, r in df.iterrows():
        bonus, notes, entropy = 0, [], 0
        slot = int(_num(r.get("slot")))
        # Transfer is an overlay only after the hitter already matched the pitcher archetype.
        if _num(top.get("rank")) <= 2 and abs(slot - top_slot) == 1 and idx != top.name:
            bonus += 12; notes.append("G10.5 transfer overlay: adjacent to chalk inside locked lane")
        if weak_slot_match(r):
            bonus += 5; notes.append("G10.5 transfer overlay: weak-slot fit")
        if len(df) >= 5: entropy += 1
        if (df.raw_score.std() if len(df) > 1 else 99) < 10: entropy += 1
        if _num(r.get("rank")) >= 5 and _num(r.get("dmg")) >= 1.2: entropy += 1
        if "WHO_CHAOS_RECIPIENT" in str(r.get("attack_tags", "")): entropy += 1
        if entropy >= 3:
            bonus += 7; notes.append("G11 WHO overlay: entropy threshold passed")
        df.loc[idx, "post_transfer_score"] = round(float(r.raw_score) + bonus, 2)
        df.loc[idx, "transfer_notes"] = " | ".join(notes)
        df.loc[idx, "entropy_flags"] = entropy
    return df


def final_role(c):
    notes = str(c.get("transfer_notes", "")).lower()
    if _num(c.get("entropy_flags")) >= 3 and _num(c.get("rank")) >= 4:
        return "WHO / Chaos Event Owner"
    if "transfer overlay" in notes:
        return "Adjacent / Decoy Transfer Owner"
    if "WEAK_SLOT_ATTACK" in str(c.get("attack_tags", "")):
        return "Weak-Slot Pitcher-Lane Owner"
    if "PITCH_TYPE_DAMAGE" in str(c.get("attack_tags", "")):
        return "Pitch-Type Damage Owner"
    if "PULL_AIR_LIFT" in str(c.get("attack_tags", "")):
        return "Pull-Air / Clean Lane Owner"
    return "Last Valid Pitcher-Lane Survivor"


def choose_side_owner(side: pd.DataFrame) -> dict:
    archetype_name, required = lock_pitcher_archetype(side)
    allg = gate_rows(side, archetype_name, required)
    live = allg[~allg.eliminated].copy(); recovery = False
    if live.empty:
        # Recovery still respects G00 output but only uses best of failed profiles for visibility.
        live = allg.sort_values("raw_score", ascending=False).head(3).copy(); recovery = True
    live = apply_transfer(live).sort_values(["post_transfer_score", "raw_score"], ascending=False).reset_index(drop=True)
    own = live.iloc[0].to_dict()
    own["role"] = final_role(own)
    own["locked_owner"] = True
    own["recovery_used"] = recovery
    own["final_score"] = float(own.get("post_transfer_score", own.get("raw_score", 0)))
    return {"side": f"{own.get('team','')} vs {own.get('pitcher','')}", "owner": own, "survivors": live.to_dict("records"), "eliminated": allg[allg.eliminated].to_dict("records")}


def choose_game_owner(game_df: pd.DataFrame) -> dict:
    side_results = [choose_side_owner(s) for _, s in game_df.groupby(["team", "pitcher"], sort=False)]
    owners = [s["owner"] for s in side_results]
    own = sorted(owners, key=lambda x: x.get("final_score", 0), reverse=True)[0]
    return {"game": own.get("game", ""), "owner": own, "side_results": side_results, "status": "LOCKED OWNER"}


def build_core(owners):
    cards = sorted([o["owner"] for o in owners], key=lambda x: x.get("final_score", 0), reverse=True)
    core, seen = [], set()
    for c in cards:
        arche = c.get("target_archetype", "")
        if len(core) < 3 and (arche not in seen or len(cards) - len(core) <= 3):
            core.append(c); seen.add(arche)
    for c in cards:
        if len(core) >= 3: break
        if c not in core: core.append(c)
    alt = [c for c in cards if c not in core][:3]
    chaos = sorted(cards, key=lambda x: (x.get("entropy_flags", 0), x.get("final_score", 0)), reverse=True)[:3]
    return {"core": core, "alt": alt, "chaos": chaos, "all_owners": cards}


def run_true_blender(data):
    df = normalize_players(data)
    if df.empty:
        return {"engine_version": ENGINE_VERSION, "message": "No readable hitter rows found.", "owners": [], "core": [], "alt": [], "chaos": []}
    owners = [choose_game_owner(g) for _, g in df.groupby("game", sort=False)]
    return {"engine_version": ENGINE_VERSION, "message": f"Blender complete: {len(owners)} game owners locked. Pitcher archetype first → hitter match gate → survivor pressure.", "owners": owners, **build_core(owners), "gate_order": GATES}
