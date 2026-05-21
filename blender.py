import pandas as pd
from machine.gates import run_gates
from machine.scoring import role_type, score_row
from machine.core_builder import build_core_alt
def run_machine(df):
    owners=[]; logs=[]; survivors=[]
    for g,gdf in df.groupby("game",dropna=False):
        alive,lg=run_gates(gdf)
        if not lg.empty: lg.insert(0,"Game",g); logs.append(lg)
        if not alive.empty:
            alive=alive.copy(); alive["role"]=alive.apply(role_type,axis=1); alive["score"]=alive.apply(score_row,axis=1); alive=alive.sort_values("score",ascending=False)
            top=alive.iloc[0].to_dict(); top["game_owner_key"]=g; owners.append(top); survivors.append(alive.assign(game_owner_key=g))
    owners=pd.DataFrame(owners) if owners else pd.DataFrame()
    logs=pd.concat(logs,ignore_index=True) if logs else pd.DataFrame()
    survivors=pd.concat(survivors,ignore_index=True) if survivors else pd.DataFrame()
    core,alt=build_core_alt(owners)
    return owners,core,alt,logs,survivors
