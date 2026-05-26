
# true_blender_structure.py
# Compatibility shim for V157.
# This file exists because engine.py imports true_blender_structure.
# It provides run_true_blender_structure without changing the app UI.

import pandas as pd
import json
import re

def _txt(x):
    try:
        if x is None or pd.isna(x): return ""
    except Exception:
        pass
    return str(x).strip()

def _num(x, default=0.0):
    try:
        if x is None or pd.isna(x): return default
        s = str(x).replace("%","").replace("+","").replace(",","").strip()
        if s.lower() in {"","nan","none","null","-","—"}: return default
        m = re.search(r"[-+]?\d*\.?\d+", s)
        return float(m.group(0)) if m else default
    except Exception:
        return default

def _get(row, names, default=0.0):
    compact = {str(k).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-",""): k for k in row.keys()}
    for n in names:
        nn = str(n).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")
        if nn in compact:
            return _num(row.get(compact[nn]), default)
    for n in names:
        nn = str(n).lower().replace(" ","").replace("_","").replace("%","").replace("/","").replace("-","")
        for ck, real in compact.items():
            if nn in ck or ck in nn:
                return _num(row.get(real), default)
    return default

def _strength(x, floor, elite, pts):
    x = float(x or 0)
    if x < floor: return 0.0
    if x >= elite: return float(pts)
    return float(pts) * ((x - floor) / max(1, elite - floor))

def _evaluate(row):
    pull = _get(row, ["pull_pct","pull%","pull"], 0)
    hard = _get(row, ["hard_hit_pct","hardhit%","hard hit%","hh%"], 0)
    barrel = _get(row, ["barrel_pct","barrel%","brl%"], 0)
    dmg = _get(row, ["dmg","damage","ult","adj"], 0)
    hpi = _get(row, ["hpi","model","rating"], 0)
    hr = _get(row, ["hr_lane","hr_pa","hr/pa","hr9"], 0)
    edge = _get(row, ["pitch_edge","edge"], -99)
    slot = _get(row, ["lineup_slot","slot","order","bo"], 0)

    player = _txt(row.get("player"))
    game = _txt(row.get("game_key") or row.get("game"))
    team = _txt(row.get("team"))
    pitcher = _txt(row.get("pitcher"))
    notes = " ".join([_txt(row.get(k)) for k in row.keys() if any(x in str(k).lower() for x in ["note","tag","raw","status"])]).lower()

    gates = []
    def add(step, gate, passed, score, max_score, reason, hard_gate=True):
        gates.append({
            "step": step, "gate": gate,
            "result": "PASS" if passed else "CUT",
            "score": round(float(max(0, score)), 2),
            "max_score": float(max_score),
            "reason": reason,
            "hard_gate": bool(hard_gate),
            "cut": bool(hard_gate and not passed),
        })

    metric_count = sum([
        pull > 0, hard > 0, barrel > 0, dmg > 0, hpi > 0, hr > 0, edge != -99, slot > 0
    ])
    trigger = pull >= 30 or hard >= 30 or barrel >= 5 or dmg >= .8 or hpi >= 20 or hr >= .8 or edge >= 0

    add(0, "PDF row", bool(player), 8 if player else 0, 8, f"player={player}")
    add(1, "Game context", bool(game and team and pitcher), 8 if game and team and pitcher else 0, 8, f"{team} / {game} / {pitcher}")
    add(2, "Metric survival", metric_count >= 3 and trigger, 10 if metric_count >= 3 and trigger else 0, 10, f"metrics={metric_count}; trigger={trigger}")
    lane = max(_strength(hr,.8,2.4,10), _strength(edge,0,14,10), _strength(dmg,.8,2.2,10), _strength(hpi,20,75,10))
    add(3, "Pitcher HR lane", lane > 0, lane, 10, f"hr={hr}; edge={edge}; dmg={dmg}; hpi={hpi}")
    launch = max(_strength(pull,30,55,12), _strength(barrel,5,16,12))
    add(4, "Pull-air / launch", launch > 0, launch, 12, f"pull={pull}; barrel={barrel}")
    conversion = max(_strength(dmg,.8,2.4,12), _strength(barrel,5,16,12), _strength(hpi,20,80,12), _strength(hr,.8,2.4,12))
    add(5, "Conversion DNA", conversion > 0, conversion, 12, f"dmg={dmg}; barrel={barrel}; hpi={hpi}; hr={hr}")
    add(6, "Opportunity", slot == 0 or slot <= 7, 6 if slot == 0 or slot <= 7 else 2, 6, f"slot={slot}", hard_gate=False)
    trap = "trap" in notes or "red flag" in notes
    add(7, "Trap audit", not trap, 8 if not trap else 0, 8, "no trap" if not trap else "trap/red flag")
    fin = max(_strength(hard,30,58,14), _strength(barrel,5,16,14), _strength(dmg,.8,2.4,14), _strength(hpi,20,80,14), _strength(hr,.8,2.4,14)) if pull >= 34 else 0
    add(8, "Finisher gate", fin > 0, fin, 14, f"pull={pull}; hard={hard}; barrel={barrel}; dmg={dmg}; hpi={hpi}; hr={hr}")
    add(9, "Adjacent audit", True, 5 if any(x in notes for x in ["adjacent","decoy","transfer","coverage"]) else 2, 5, "checked", hard_gate=False)
    who_trigger = ("who" in notes or "chaos" in notes or (pull >= 30 and hard >= 30 and hpi < 45))
    add(10, "WHO audit", True, 6 if who_trigger else 2, 6, "checked", hard_gate=False)

    hard_cut = any(g["cut"] for g in gates)
    raw = sum(g["score"] for g in gates)
    mx = sum(g["max_score"] for g in gates)
    score = round(max(1, min(92, (raw / max(1,mx)) * 88 + (pull+hard)/45 + barrel/3 + dmg + hpi/40 + hr)), 1)
    if hard_cut: score = round(min(score, 59.9), 1)

    primary = _strength(pull,36,55,22)+_strength(barrel,7,16,20)+_strength(dmg,1,2.4,18)+_strength(hpi,30,80,15)+_strength(hr,1,2.5,15)+_strength(edge,0,20,10)
    adjacent = _strength(pull,30,46,18)+_strength(hard,30,52,18)+_strength(dmg,.8,1.8,15)+_strength(hpi,20,60,10)
    if any(x in notes for x in ["adjacent","decoy","transfer","coverage"]): adjacent += 35
    who = _strength(pull,28,42,16)+_strength(hard,30,48,16)+_strength(hr,.8,1.8,16)+_strength(edge,0,12,10)
    if who_trigger: who += 35
    if hpi < 45: who += 8
    role_scores = {"Primary": round(primary,1), "Adjacent": round(adjacent,1), "WHO": round(who,1)}
    role = max(role_scores, key=role_scores.get)
    eligible = not hard_cut and score >= 55
    if not eligible: role = "CUT"
    archetype = {"Primary":"Primary HR Owner","Adjacent":"Adjacent / Decoy Transfer","WHO":"WHO / Chaos Owner","CUT":"Cut by gates"}[role]
    return eligible, score, role, archetype, gates, role_scores

def run_true_blender_structure(df):
    if not isinstance(df, pd.DataFrame) or df.empty:
        return {"owners":pd.DataFrame(),"core":pd.DataFrame(),"alt":pd.DataFrame(),"chaos":pd.DataFrame(),"survivors":pd.DataFrame(),"cuts":pd.DataFrame(),"game_board":pd.DataFrame(),"role_board":pd.DataFrame(),"meta":{"engine_version":"V157_IMPORT_FIXED","message":"No feed.","owners_locked":0}}

    data = df.copy()
    if "game_key" not in data.columns:
        data["game_key"] = data["game"] if "game" in data.columns else ""

    survivors, board, roles = [], [], []
    for idx, r in data.iterrows():
        row = r.to_dict()
        ok, score, role, arch, gates, role_scores = _evaluate(row)
        row.update({
            "row_id": idx, "blender_eligible": ok, "blender_score": score, "support_score": score,
            "score": score, "official_core_role": role, "archetype": arch,
            "final_reason": f"{role} survived hard gates" if ok else "CUT — see gate trace",
            "gate_trace_json": json.dumps(gates),
            "role_scores_json": json.dumps(role_scores),
        })
        survivors.append(row)
        for g in gates:
            board.append({"game_key": row.get("game_key",""), "player": row.get("player",""), "role": role, **g, "blender_score": score})
        roles.append({"game_key":row.get("game_key",""), "player":row.get("player",""), "assigned_role":role, **role_scores, "blender_score":score})

    survivors = pd.DataFrame(survivors)
    passed = survivors[survivors["blender_eligible"] == True].copy()
    cuts = survivors[survivors["blender_eligible"] != True].copy()

    # One owner per game.
    owners = []
    for game, g in passed.groupby("game_key", dropna=False):
        if str(game).strip() == "" or str(game).lower() == "nan": continue
        pick = g.sort_values(["blender_score"], ascending=False).iloc[0].to_dict()
        pick["game_owner"] = game
        owners.append(pick)
    owners = pd.DataFrame(owners)
    if not owners.empty:
        owners = owners.sort_values(["blender_score"], ascending=False).reset_index(drop=True)

    # Core slots: Primary / Adjacent / WHO, no duplicate game unless unavoidable.
    used_players, used_games, parts = set(), set(), []
    def gid(r): return str(r.get("game_pk") or r.get("game_key") or "")
    for slot, roles_allowed in [("PRIMARY",["Primary"]),("ADJACENT",["Adjacent"]),("WHO",["WHO"])]:
        pool = owners[owners["official_core_role"].isin(roles_allowed)].copy() if not owners.empty and "official_core_role" in owners.columns else pd.DataFrame()
        if not pool.empty:
            pool = pool[~pool["player"].astype(str).isin(used_players)]
            pool["_gid"] = pool.apply(gid, axis=1)
            nd = pool[~pool["_gid"].isin(used_games)]
            if not nd.empty: pool = nd
            pick = pool.sort_values("blender_score", ascending=False).head(1).copy()
            if not pick.empty:
                pick["core_slot"] = slot
                parts.append(pick.drop(columns=["_gid"], errors="ignore"))
                used_players.update(pick["player"].astype(str).tolist())
                used_games.update(pick["_gid"].astype(str).tolist())

    for slot in ["PRIMARY REFILL","ADJACENT REFILL","WHO REFILL"]:
        if len(parts) >= 3 or owners.empty: break
        pool = owners[~owners["player"].astype(str).isin(used_players)].copy()
        if pool.empty: break
        pool["_gid"] = pool.apply(gid, axis=1)
        nd = pool[~pool["_gid"].isin(used_games)]
        if not nd.empty: pool = nd
        pick = pool.sort_values("blender_score", ascending=False).head(1).copy()
        if not pick.empty:
            pick["core_slot"] = slot
            parts.append(pick.drop(columns=["_gid"], errors="ignore"))
            used_players.update(pick["player"].astype(str).tolist())
            used_games.update(pick["_gid"].astype(str).tolist())

    core = pd.concat(parts, ignore_index=True).head(3) if parts else pd.DataFrame()
    if not core.empty: core["ticket_role"] = "CORE"

    used = set(core["player"].astype(str).tolist()) if not core.empty and "player" in core.columns else set()
    alt = owners[~owners["player"].astype(str).isin(used)].head(3).copy() if not owners.empty and "player" in owners.columns else pd.DataFrame()
    if not alt.empty: alt["ticket_role"] = "ALT"
    used.update(alt["player"].astype(str).tolist() if not alt.empty and "player" in alt.columns else [])
    chaos = owners[(owners["official_core_role"]=="WHO") & (~owners["player"].astype(str).isin(used))].head(3).copy() if not owners.empty and "official_core_role" in owners.columns else pd.DataFrame()
    if chaos.empty and not owners.empty and "player" in owners.columns:
        chaos = owners[~owners["player"].astype(str).isin(used)].head(3).copy()
    if not chaos.empty: chaos["ticket_role"] = "WHO"

    games = int(data["game_key"].dropna().astype(str).replace("", pd.NA).dropna().nunique()) if "game_key" in data.columns else 0
    meta = {
        "engine_version": "V157_IMPORT_FIXED",
        "games": games, "input_rows": len(data), "passed_rows": len(passed), "cut_rows": len(cuts),
        "owners_locked": len(owners), "core_count": len(core),
        "core_slots": core.get("core_slot", pd.Series(dtype=str)).tolist() if not core.empty else [],
        "message": f"V157 fixed: {len(owners)} owners, {len(passed)} pass rows, {len(cuts)} cuts."
    }
    return {"owners":owners,"core":core,"alt":alt,"chaos":chaos,"survivors":survivors,"cuts":cuts,"game_board":pd.DataFrame(board),"role_board":pd.DataFrame(roles),"meta":meta}
