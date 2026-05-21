import pandas as pd

def role_type(r):
    if bool(r.get("weak_slot_tag")) or bool(r.get("laser")) or bool(r.get("rakes")):
        return "Transfer"
    if (r.get("dmg") or 0) >= 1.7 and (r.get("hr_pa") or 0) >= 4:
        return "WHO"
    return "Primary"

def score_row(r):
    pull = 0 if pd.isna(r.get("pull_pct")) else min(100, max(0, (r["pull_pct"] - 20) * 3))
    pitch = 0 if pd.isna(r.get("pitch_edge")) else min(100, max(0, 50 + r["pitch_edge"]))
    dmg = 0 if pd.isna(r.get("dmg")) else min(100, max(0, r["dmg"] * 35))
    hrpa = 0 if pd.isna(r.get("hr_pa")) else min(100, max(0, r["hr_pa"] * 16))
    hpi = 0 if pd.isna(r.get("hpi")) else min(100, max(0, r["hpi"] * 2))
    sweet = 0 if pd.isna(r.get("sweet_spot_pct")) else min(100, max(0, (r["sweet_spot_pct"] - 20) * 4))

    score = pull*.18 + pitch*.12 + dmg*.18 + hrpa*.18 + hpi*.13 + sweet*.11
    score += 10 if r.get("weak_slot_tag") else 0
    score += 10 if r.get("hr_alert") else 0
    score += 6 if r.get("cond_up") else 0
    return max(0, min(100, score))

def run_gates(gdf):
    alive = gdf.copy()
    logs = []

    def cut(name, mask):
        nonlocal alive, logs
        before = len(alive)
        dead = alive.loc[~mask, "player"].tolist()
        alive = alive[mask].copy()
        logs.append({"Gate": name, "Before": before, "Cut": len(dead), "After": len(alive), "Cut names": ", ".join(dead[:16]), "Alive after": ", ".join(alive.player.tolist()[:16])})

    logs.append({"Gate":"0", "Before":len(alive), "Cut":0, "After":len(alive), "Cut names":"", "Alive after":", ".join(alive.player.tolist()[:16])})
    cut("1 Pull-Air", alive.pull_pct.isna() | (alive.pull_pct >= 20))
    if len(alive) > 1: cut("2 Pitch Edge", alive.pitch_edge.isna() | (alive.pitch_edge >= 0))
    if len(alive) > 1: cut("3 Slot/Zone", alive.weak_slot_tag | alive.lineup_slot.notna() | alive.pitch_edge.notna())
    if len(alive) > 1: cut("4 Sweet/Launch", alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct >= 24))
    if len(alive) > 1: cut("5 HR/PA", alive.hr_pa.isna() | (alive.hr_pa >= 2) | alive.hr_alert)
    if len(alive) > 1: cut("6 DMG", alive.dmg.isna() | (alive.dmg >= .5) | alive.hr_alert)
    if len(alive) > 1: cut("7 HPI", alive.hpi.isna() | (alive.hpi >= 18) | alive.hr_alert)

    for gate in ["8 Recency", "9 Context", "10 Public/Book", "10.5 Transfer", "11 Bullpen", "12 Script", "13 Numerology", "14 Chaos", "15 Finisher", "16 Ownership", "17 Audit", "18 Lock"]:
        if len(alive) > 1:
            logs.append({"Gate":gate, "Before":len(alive), "Cut":0, "After":len(alive), "Cut names":"", "Alive after":", ".join(alive.player.tolist()[:16])})

    return alive, pd.DataFrame(logs)

def build_core_alt(owners):
    if owners.empty:
        return pd.DataFrame(), pd.DataFrame()

    owners = owners.sort_values("score", ascending=False).reset_index(drop=True)
    core = []
    used_games = set()

    for role in ["Primary", "Transfer", "WHO"]:
        for _, r in owners[owners.role == role].iterrows():
            g = r["game"]
            if g not in used_games:
                core.append(r.to_dict())
                used_games.add(g)
                break

    for _, r in owners.iterrows():
        if len(core) >= 3:
            break
        if r["game"] not in used_games:
            core.append(r.to_dict())
            used_games.add(r["game"])

    core_df = pd.DataFrame(core[:3]) if core else pd.DataFrame()

    alt = []
    alt_games = set(used_games)
    for _, r in owners.iterrows():
        if r["player"] not in (core_df["player"].tolist() if not core_df.empty else []) and r["game"] not in alt_games:
            alt.append(r.to_dict())
            alt_games.add(r["game"])
        if len(alt) >= 3:
            break

    return core_df, pd.DataFrame(alt[:3])

def run_machine(df):
    owners = []
    logs = []
    survivors = []

    for game, gdf in df.groupby("game", dropna=False):
        alive, lg = run_gates(gdf)
        if not lg.empty:
            lg.insert(0, "Game", game)
            logs.append(lg)
        if not alive.empty:
            alive = alive.copy()
            alive["role"] = alive.apply(role_type, axis=1)
            alive["score"] = alive.apply(score_row, axis=1)
            alive = alive.sort_values("score", ascending=False)
            top = alive.iloc[0].to_dict()
            owners.append(top)
            survivors.append(alive)

    owners = pd.DataFrame(owners) if owners else pd.DataFrame()
    logs = pd.concat(logs, ignore_index=True) if logs else pd.DataFrame()
    survivors = pd.concat(survivors, ignore_index=True) if survivors else pd.DataFrame()
    core, alt = build_core_alt(owners)
    return owners, core, alt, logs, survivors
