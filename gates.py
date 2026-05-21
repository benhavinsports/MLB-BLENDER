import pandas as pd

def gate(alive,name,mask,logs):
    cut=alive.loc[~mask,"player"].tolist()
    before=len(alive)
    alive=alive[mask].copy()
    logs.append({"Gate":name,"Before":before,"Cut":len(cut),"After":len(alive),"Cut names":", ".join(cut[:16]),"Alive after":", ".join(alive.player.tolist()[:16])})
    return alive

def run_gates(gdf):
    alive=gdf.copy(); logs=[]
    logs.append({"Gate":"0","Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16])})
    alive=gate(alive,"1",alive.pull_pct.isna() | (alive.pull_pct>=20),logs)
    if len(alive)>1: alive=gate(alive,"2",alive.pitch_edge.isna() | (alive.pitch_edge>=0),logs)
    if len(alive)>1: alive=gate(alive,"4",alive.sweet_spot_pct.isna() | (alive.sweet_spot_pct>=24),logs)
    if len(alive)>1: alive=gate(alive,"5",alive.hr_pa.isna() | (alive.hr_pa>=2) | alive.hr_alert,logs)
    if len(alive)>1: alive=gate(alive,"6",alive.dmg.isna() | (alive.dmg>=0.5) | alive.hr_alert,logs)
    if len(alive)>1: alive=gate(alive,"7",alive.hpi.isna() | (alive.hpi>=18) | alive.hr_alert,logs)
    for g in ["8","9","10","10.5","11","12","13","14","15","16","17","18"]:
        if len(alive)>1:
            logs.append({"Gate":g,"Before":len(alive),"Cut":0,"After":len(alive),"Cut names":"","Alive after":", ".join(alive.player.tolist()[:16])})
    return alive, pd.DataFrame(logs)
