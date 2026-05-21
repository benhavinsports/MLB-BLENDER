import pandas as pd
def build_core_alt(owners):
    core=[]; used_games=set()
    if owners.empty: return pd.DataFrame(), pd.DataFrame()
    owners=owners.sort_values("score",ascending=False).reset_index(drop=True)
    pool=owners[owners.score>=25].copy()
    if pool.empty: pool=owners.copy()
    for role in ["Primary","Transfer","WHO"]:
        for _,r in pool[pool.role==role].iterrows():
            g=r.get("game_owner_key",r.get("game",""))
            if g not in used_games:
                core.append(r.to_dict()); used_games.add(g); break
    for _,r in pool.iterrows():
        if len(core)>=3: break
        g=r.get("game_owner_key",r.get("game",""))
        if g not in used_games: core.append(r.to_dict()); used_games.add(g)
    core=pd.DataFrame(core[:3]) if core else pd.DataFrame()
    alt=[]; used_alt=set(used_games)
    for _,r in owners.iterrows():
        g=r.get("game_owner_key",r.get("game",""))
        if (core.empty or r.player not in core.player.tolist()) and g not in used_alt:
            alt.append(r.to_dict()); used_alt.add(g)
        if len(alt)>=3: break
    if len(alt)<3:
        for _,r in owners.iterrows():
            if core.empty or r.player not in core.player.tolist():
                if r.player not in [x.get("player") for x in alt]: alt.append(r.to_dict())
            if len(alt)>=3: break
    return core, pd.DataFrame(alt[:3])
