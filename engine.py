from __future__ import annotations
import re
from typing import Any
import pandas as pd

ENGINE_VERSION = "v137_CORE5_ARCHETYPE_FIRST_FULL_18_GATE_NO_DRIFT"

GATE_ORDER = [
    "G00 Pitcher weakness archetype lock",
    "G01 Hitter must match pitcher archetype",
    "G02 Data/lineup row integrity",
    "G03 Lineup slot + pitcher weak-slot check",
    "G04 Platoon / handedness lane",
    "G05 Pitch-type weakness match",
    "G06 Pull-air / launch window",
    "G07 Hard-hit / damage floor",
    "G08 HR conversion profile",
    "G09 Recent condition / rhythm",
    "G10 Opportunity / batting-order pressure",
    "G10.5 Book-decoy / adjacent transfer overlay",
    "G11 Weak-slot ownership isolation",
    "G12 Bullpen / park / environment continuation",
    "G13 WHO / chaos detector",
    "G14 Game-script volatility",
    "G15 Finisher gate",
    "G16 One-owner-per-game isolation",
    "G17 Final no-fluke audit",
    "G18 Lock result",
]


def _num(x, default=0.0):
    try:
        m = re.search(r"-?\d+(?:\.\d+)?", str(x or "").replace("%", ""))
        return float(m.group(0)) if m else default
    except Exception:
        return default


def _txt(x) -> str:
    return str(x or "").strip()


def normalize_players(data: Any) -> pd.DataFrame:
    df = data.copy() if isinstance(data, pd.DataFrame) else pd.DataFrame(data or [])
    if df.empty:
        return df
    ren = {}
    for c in df.columns:
        k = str(c).lower().strip().replace(" ", "_").replace("/", "_")
        ren[c] = {
            "hitter": "player", "batter": "player", "name": "player",
            "offense_team": "team", "target_pitcher": "pitcher", "opp_pitcher": "pitcher",
            "lineup_slot": "slot", "batting_order": "slot", "hr_pa": "hr_pa",
            "damage": "dmg", "edge": "pitch_edge", "tags": "badges",
            "badge_text": "badges", "pitcher_weak_slots": "weak_slots",
            "weak_slot": "weak_slots", "line_drive": "line", "line_drive_%": "line",
            "hard_hit_%": "hard_hit", "barrel_%": "barrel", "pull_%": "pull",
            "sweet_spot_%": "sweet_spot", "park_edge": "park_edge",
        }.get(k, k)
    df = df.rename(columns=ren)
    for c in ["player", "team", "game", "pitcher", "badges", "weak_slots", "raw_block"]:
        if c not in df:
            df[c] = ""
    for c in [
        "slot", "hr_pa", "dmg", "hpi", "pitch_edge", "hr_edge", "cond", "line",
        "effort", "fatigue", "rank", "hard_hit", "barrel", "pull", "sweet_spot", "park_edge"
    ]:
        if c not in df:
            df[c] = 0
        df[c] = df[c].map(_num)
    df["player"] = df["player"].astype(str).str.strip()
    df = df[df.player.str.len() > 1].copy()
    if df.empty:
        return df
    if df["game"].astype(str).str.strip().eq("").all():
        df["game"] = df["team"].astype(str) + " vs " + df["pitcher"].astype(str)
    return df.reset_index(drop=True)


def weak_slot_match(r) -> bool:
    slot = int(_num(r.get("slot"))) if _num(r.get("slot")) else 0
    weak = set(re.findall(r"\d+", _txt(r.get("weak_slots"))))
    return bool(slot and str(slot) in weak) or ("weak slot" in _txt(r.get("badges")).lower())


def hitter_attack_tags(r) -> set[str]:
    b = (_txt(r.get("badges")) + " " + _txt(r.get("raw_block"))).lower()
    tags: set[str] = set()
    if weak_slot_match(r):
        tags.add("WEAK_SLOT_ATTACK")
    if _num(r.get("pitch_edge")) >= 8 or _num(r.get("hr_edge")) >= 3:
        tags.add("PITCH_TYPE_DAMAGE")
    if _num(r.get("cond")) >= 20 or _num(r.get("line")) >= 25 or _num(r.get("pull")) >= 38 or "laser" in b or "launch" in b:
        tags.add("PULL_AIR_LIFT")
    if _num(r.get("hr_pa")) >= 3 or _num(r.get("dmg")) >= 1.20 or _num(r.get("hpi")) >= 40 or _num(r.get("hard_hit")) >= 40 or _num(r.get("barrel")) >= 9:
        tags.add("POWER_CONVERSION")
    if _num(r.get("rank")) >= 5 and (weak_slot_match(r) or _num(r.get("dmg")) >= 1.2 or _num(r.get("hr_pa")) >= 3):
        tags.add("WHO_CHAOS_RECIPIENT")
    if "platoon" in b or "rakes" in b or "eats lhp" in b:
        tags.add("PLATOON_EDGE")
    if "park edge" in b or _num(r.get("park_edge")) > 0:
        tags.add("PARK_ENVIRONMENT")
    return tags


def lock_pitcher_archetype(side: pd.DataFrame) -> tuple[str, set[str]]:
    """Pitcher weakness archetype is decided BEFORE hitter gates.
    This is not final-player labeling. This is the required lane for the game side.
    """
    counts = {k: 0 for k in ["WEAK_SLOT_ATTACK", "PITCH_TYPE_DAMAGE", "PULL_AIR_LIFT", "POWER_CONVERSION", "WHO_CHAOS_RECIPIENT", "PARK_ENVIRONMENT"]}
    for _, r in side.iterrows():
        for t in hitter_attack_tags(r):
            if t in counts:
                counts[t] += 1

    locked: list[str] = []
    # Pitcher weakness comes first: slot leaks + pitch edge + lift window.
    if counts["WEAK_SLOT_ATTACK"]:
        locked.append("WEAK_SLOT_ATTACK")
    if counts["PITCH_TYPE_DAMAGE"]:
        locked.append("PITCH_TYPE_DAMAGE")
    if counts["PULL_AIR_LIFT"]:
        locked.append("PULL_AIR_LIFT")
    if not locked and counts["POWER_CONVERSION"]:
        locked.append("POWER_CONVERSION")
    if counts["WHO_CHAOS_RECIPIENT"] >= 2 and (counts["WEAK_SLOT_ATTACK"] or counts["PITCH_TYPE_DAMAGE"]):
        locked.append("WHO_CHAOS_RECIPIENT")
    if not locked:
        locked.append("SURVIVAL_RECOVERY")
    return " + ".join(locked), set(locked)


def archetype_match(r, required: set[str]) -> bool:
    if "SURVIVAL_RECOVERY" in required:
        return True
    tags = hitter_attack_tags(r)
    return bool(tags & required) and (_num(r.get("hr_pa")) > 0 or _num(r.get("dmg")) >= .65 or _num(r.get("hpi")) >= 24)


def feature_score(r):
    b = (_txt(r.get("badges")) + " " + _txt(r.get("raw_block"))).lower()
    hrpa, dmg, hpi, pitch, hredge, cond, line = [_num(r.get(k)) for k in ["hr_pa", "dmg", "hpi", "pitch_edge", "hr_edge", "cond", "line"]]
    hard, barrel, pull, sweet, park = [_num(r.get(k)) for k in ["hard_hit", "barrel", "pull", "sweet_spot", "park_edge"]]
    tags = hitter_attack_tags(r)
    pull_air = max(cond, 0) * 0.20 + max(line, 0) * 0.18 + max(pull, 0) * 0.10 + max(sweet, 0) * 0.08
    power = max(hrpa, 0) * 7 + max(dmg, 0) * 12 + max(hpi, 0) * 0.52 + max(hredge, 0) * 1.4 + max(pitch, 0) * 0.65 + max(hard, 0) * 0.10 + max(barrel, 0) * 0.7
    badge = 0
    for term, pts in [("platoon", 5), ("rakes", 5), ("laser", 6), ("launch", 7), ("weak slot", 8), ("park edge", 4), ("alert", 4), ("hot", 3), ("2g hr", 4), ("10g h", 2)]:
        if term in b:
            badge += pts
    if "WEAK_SLOT_ATTACK" in tags: badge += 10
    if "PITCH_TYPE_DAMAGE" in tags: badge += 7
    if "PULL_AIR_LIFT" in tags: badge += 5
    if _num(r.get("rank")) in (1, 2, 3): badge += 3
    return round(power + pull_air + badge, 2), {"power": round(power, 2), "pull_air": round(pull_air, 2), "badge": badge, "tags": sorted(tags)}


def gate_rows(side: pd.DataFrame, archetype_name: str, required: set[str]) -> pd.DataFrame:
    rows = []
    side_slots = set(int(_num(x)) for x in side.get("slot", []) if _num(x))
    for _, r in side.iterrows():
        score, detail = feature_score(r)
        b = (_txt(r.get("badges")) + " " + _txt(r.get("raw_block"))).lower()
        path = [f"G00: pass — pitcher weakness archetype locked BEFORE hitter selection: {archetype_name}"]
        kill = False
        soft_kills = 0

        def p(g, why):
            path.append(f"{g}: pass — {why}")
        def w(g, why):
            nonlocal soft_kills
            soft_kills += 1
            path.append(f"{g}: warning — {why}")
        def k(g, why):
            nonlocal kill
            kill = True
            path.append(f"{g}: KILL — {why}")

        tags = set(detail["tags"])
        slot = int(_num(r.get("slot"))) if _num(r.get("slot")) else 0

        # G01-G18 restored full system. Hard kill only for true breakage; weak signals are pressure warnings.
        if archetype_match(r, required): p("G01", f"hitter matches locked pitcher weakness lane: {', '.join(sorted(tags & required)) or ', '.join(sorted(tags))}")
        else: k("G01", f"does not match locked pitcher weakness archetype: {archetype_name}")

        if _txt(r.get("team")) and _txt(r.get("player")) and _txt(r.get("pitcher")): p("G02", "player/team/pitcher row intact")
        else: k("G02", "missing player/team/pitcher row data")

        if slot > 0:
            if weak_slot_match(r): p("G03", f"slot {slot} is in pitcher weak-slot lane")
            else: w("G03", f"slot {slot} not marked weak, must survive through other archetype edges")
        else: k("G03", "missing lineup slot")

        if "PLATOON_EDGE" in tags or "SURVIVAL_RECOVERY" in required or _num(r.get("hr_edge")) >= -3:
            p("G04", "platoon/handedness lane alive")
        else:
            w("G04", "no explicit platoon boost")

        if "PITCH_TYPE_DAMAGE" in tags or _num(r.get("pitch_edge")) >= -12 or _num(r.get("hr_edge")) >= 1:
            p("G05", "pitch-type weakness not killing hitter")
        else:
            k("G05", "pitch-type edge is a hard negative")

        if detail["pull_air"] >= 4.5 or "PULL_AIR_LIFT" in tags or "laser" in b or "launch" in b:
            p("G06", "pull-air / launch window present")
        else:
            w("G06", "pull-air/lift signal thin")

        if detail["power"] >= 16 or _num(r.get("dmg")) >= .95 or _num(r.get("hpi")) >= 30:
            p("G07", "damage/hard-hit floor survives")
        else:
            k("G07", "damage floor too low")

        if _num(r.get("hr_pa")) > 0 or _num(r.get("dmg")) >= .75 or "POWER_CONVERSION" in tags:
            p("G08", "HR conversion profile alive")
        else:
            k("G08", "empty HR conversion profile")

        if not (_num(r.get("cond")) <= 0 and _num(r.get("line")) <= 12 and "cold" in b):
            p("G09", "recent condition/rhythm not dead")
        else:
            w("G09", "cold/low rhythm warning")

        if 1 <= slot <= 9:
            if slot <= 6 or weak_slot_match(r) or _num(r.get("rank")) <= 4:
                p("G10", "opportunity/batting-order pressure survives")
            else:
                w("G10", "lower order needs chaos/weak-slot help")
        else:
            k("G10", "no batting-order opportunity")

        # G10.5 overlay is calculated later but a note belongs in path.
        p("G10.5", "adjacent/decoy transfer checked only after lane survival")

        if weak_slot_match(r) or "PITCH_TYPE_DAMAGE" in tags or "PULL_AIR_LIFT" in tags:
            p("G11", "pitcher-lane ownership can be isolated")
        else:
            w("G11", "ownership not isolated yet")

        if "PARK_ENVIRONMENT" in tags or _num(r.get("hr_edge")) >= -12 or _num(r.get("pitch_edge")) >= -12:
            p("G12", "park/bullpen/environment continuation not blocking")
        else:
            w("G12", "environment continuation weak")

        entropy = 0
        if _num(r.get("rank")) >= 5: entropy += 1
        if weak_slot_match(r): entropy += 1
        if _num(r.get("dmg")) >= 1.2 or _num(r.get("hr_pa")) >= 3: entropy += 1
        if "WHO_CHAOS_RECIPIENT" in tags: entropy += 1
        if entropy >= 2: p("G13", f"WHO/chaos detector alive ({entropy} flags)")
        else: w("G13", f"WHO/chaos low ({entropy} flags)")

        if len(side_slots) >= 7 or entropy >= 2 or "PARK_ENVIRONMENT" in tags:
            p("G14", "game-script volatility accounted for")
        else:
            w("G14", "low volatility; needs clean lane")

        finisher_votes = 0
        if detail["pull_air"] >= 4.5 or "PULL_AIR_LIFT" in tags: finisher_votes += 1
        if detail["power"] >= 18 or "POWER_CONVERSION" in tags: finisher_votes += 1
        if weak_slot_match(r) or "PITCH_TYPE_DAMAGE" in tags: finisher_votes += 1
        if _num(r.get("hr_pa")) >= 2.5 or _num(r.get("dmg")) >= 1.15: finisher_votes += 1
        if finisher_votes >= 2: p("G15", f"finisher gate passed ({finisher_votes} votes)")
        else: k("G15", f"finisher gate failed ({finisher_votes} votes)")

        p("G16", "eligible for one-owner-per-game isolation")

        # Final no-fluke audit: too many warnings means remove even if no hard kill.
        if soft_kills <= 4 or score >= 45 or weak_slot_match(r):
            p("G17", f"no-fluke audit survives with {soft_kills} warnings")
        else:
            k("G17", f"too many weak gates ({soft_kills} warnings)")

        if not kill:
            p("G18", "LOCKABLE survivor after full 18-gate system")

        d = r.to_dict()
        d.update(
            raw_score=score,
            score_detail=detail,
            attack_tags=" / ".join(sorted(tags)),
            target_archetype=archetype_name,
            gate_path=path,
            eliminated=kill,
            warning_count=soft_kills,
            entropy_flags=entropy,
            finisher_votes=finisher_votes,
        )
        rows.append(d)
    return pd.DataFrame(rows)


def apply_transfer(live: pd.DataFrame) -> pd.DataFrame:
    if live.empty:
        return live
    df = live.copy()
    top = df.sort_values("raw_score", ascending=False).iloc[0]
    top_slot = int(_num(top.get("slot")))
    top_rank = _num(top.get("rank"))
    std = df.raw_score.std() if len(df) > 1 else 99
    for idx, r in df.iterrows():
        bonus, notes = 0.0, []
        slot = int(_num(r.get("slot")))
        entropy = int(_num(r.get("entropy_flags")))
        # Adjacent transfer is an OVERLAY after the hitter already survived the archetype gate.
        if top_rank <= 2 and abs(slot - top_slot) == 1 and idx != top.name:
            bonus += 10; notes.append("G10.5: adjacent to chalk/decoy after lane survival")
        if weak_slot_match(r):
            bonus += 4; notes.append("G10.5: weak-slot ownership boost")
        if len(df) >= 5: entropy += 1
        if std < 10: entropy += 1
        if _num(r.get("rank")) >= 5 and _num(r.get("dmg")) >= 1.15: entropy += 1
        if entropy >= 3:
            bonus += 6; notes.append("G13: WHO entropy threshold overlay")
        # Penalty for warning count so gate survival pressure beats raw stat sorting.
        penalty = _num(r.get("warning_count")) * 1.75
        df.loc[idx, "post_transfer_score"] = round(float(r.raw_score) + bonus - penalty, 2)
        df.loc[idx, "transfer_notes"] = " | ".join(notes)
        df.loc[idx, "entropy_flags"] = entropy
        # Append overlay notes to gate path.
        path = list(r.get("gate_path", []))
        if notes:
            path.append("OVERLAY: " + " | ".join(notes))
        path.append(f"FINAL PRESSURE SCORE: raw {float(r.raw_score):.2f} + overlay {bonus:.2f} - warnings {penalty:.2f}")
        df.at[idx, "gate_path"] = path
    return df


def final_role(c):
    notes = _txt(c.get("transfer_notes")).lower()
    tags = _txt(c.get("attack_tags"))
    if _num(c.get("entropy_flags")) >= 3 and _num(c.get("rank")) >= 4:
        return "WHO / Chaos Event Owner"
    if "adjacent" in notes:
        return "Adjacent / Decoy Transfer Owner"
    if "WEAK_SLOT_ATTACK" in tags:
        return "Weak-Slot Pitcher-Lane Owner"
    if "PITCH_TYPE_DAMAGE" in tags:
        return "Pitch-Type Damage Owner"
    if "PULL_AIR_LIFT" in tags:
        return "Pull-Air / Clean Lane Owner"
    return "Last Valid 18-Gate Survivor"


def choose_side_owner(side: pd.DataFrame) -> dict:
    archetype_name, required = lock_pitcher_archetype(side)
    allg = gate_rows(side, archetype_name, required)
    live = allg[~allg.eliminated].copy()
    recovery = False
    if live.empty:
        # Emergency visibility only. This does NOT pretend the gates passed.
        live = allg.sort_values("raw_score", ascending=False).head(3).copy()
        live["post_transfer_score"] = live["raw_score"] - 20
        live["transfer_notes"] = "RECOVERY DISPLAY ONLY — no clean 18-gate survivor"
        recovery = True
    else:
        live = apply_transfer(live)
    live = live.sort_values(["post_transfer_score", "finisher_votes", "raw_score"], ascending=False).reset_index(drop=True)
    own = live.iloc[0].to_dict()
    own["role"] = final_role(own)
    own["locked_owner"] = not recovery
    own["recovery_used"] = recovery
    own["final_score"] = float(own.get("post_transfer_score", own.get("raw_score", 0)))
    return {"side": f"{own.get('team','')} vs {own.get('pitcher','')}", "owner": own, "survivors": live.to_dict("records"), "eliminated": allg[allg.eliminated].to_dict("records")}


def choose_game_owner(game_df: pd.DataFrame) -> dict:
    side_results = [choose_side_owner(s) for _, s in game_df.groupby(["team", "pitcher"], sort=False)]
    owners = [s["owner"] for s in side_results]
    own = sorted(owners, key=lambda x: (not x.get("recovery_used", False), x.get("final_score", 0)), reverse=True)[0]
    return {"game": own.get("game", ""), "owner": own, "side_results": side_results, "status": "LOCKED OWNER" if not own.get("recovery_used") else "NO CLEAN LOCK — RECOVERY DISPLAY"}


def build_core(owners):
    cards = sorted([o["owner"] for o in owners], key=lambda x: (not x.get("recovery_used", False), x.get("final_score", 0)), reverse=True)
    clean = [c for c in cards if not c.get("recovery_used")]
    pool = clean or cards
    core, seen = [], set()
    # Core 3 should diversify archetypes but never bypass gate survival.
    for c in pool:
        arche = c.get("target_archetype", "")
        if len(core) < 3 and (arche not in seen or len(pool) - len(core) <= 3):
            core.append(c); seen.add(arche)
    for c in pool:
        if len(core) >= 3: break
        if c not in core: core.append(c)
    alt = [c for c in pool if c not in core][:3]
    chaos = sorted(pool, key=lambda x: (x.get("entropy_flags", 0), x.get("final_score", 0)), reverse=True)[:3]
    return {"core": core, "alt": alt, "chaos": chaos, "all_owners": cards}


def run_true_blender(data):
    df = normalize_players(data)
    if df.empty:
        return {"engine_version": ENGINE_VERSION, "message": "No readable hitter rows found.", "owners": [], "core": [], "alt": [], "chaos": [], "gate_order": GATE_ORDER}
    owners = [choose_game_owner(g) for _, g in df.groupby("game", sort=False)]
    return {
        "engine_version": ENGINE_VERSION,
        "message": f"Blender complete: {len(owners)} game owners processed. Correct flow: pitcher archetype first → matching hitters only → FULL 18-gate elimination → one owner.",
        "owners": owners,
        **build_core(owners),
        "gate_order": GATE_ORDER,
    }
