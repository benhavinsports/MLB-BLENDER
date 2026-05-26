
from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
from official_mlb_slate import fetch_official_mlb_slate, attach_official_slate_to_feed, official_game_count
from feeder import actual_game_count
DATA_DIR=Path('data'); LOCK_PATH=DATA_DIR/'locked_owners.json'

def _txt(x):
    try:
        if x is None or pd.isna(x): return ''
    except Exception: pass
    return str(x).strip()
def _num(x, default=0.0):
    try:
        if x is None or pd.isna(x): return default
        s=str(x).replace('%','').replace('+','').replace(',','').strip()
        if s.lower() in {'','nan','none','null','-','—'}: return default
        m=re.search(r'[-+]?\d*\.?\d+',s); return float(m.group(0)) if m else default
    except Exception: return default
def _key(s): return str(s).lower().replace(' ','').replace('_','').replace('%','').replace('/','').replace('-','')
def _field(row,names,default=0.0):
    cmap={_key(k):k for k in row.keys()}
    for n in names:
        if _key(n) in cmap: return _num(row.get(cmap[_key(n)]),default)
    for n in names:
        nn=_key(n)
        for ck,real in cmap.items():
            if nn in ck or ck in nn: return _num(row.get(real),default)
    return default
def _safe_df(x): return x if isinstance(x,pd.DataFrame) else pd.DataFrame()
def csv_bytes(df): return _safe_df(df).to_csv(index=False).encode('utf-8')
def strength(x,floor,elite,pts):
    x=_num(x,0.0)
    if x<floor: return 0.0
    if x>=elite: return float(pts)
    return float(pts)*((x-floor)/max(1.0,elite-floor))

def fetch_live_public_slate(date_str=None): return fetch_official_mlb_slate(date_str)
def fetch_live_public_hitter_pool(date_str=None): return fetch_official_mlb_slate(date_str)
def attach_slate_matchup_context(df, public_context=None): return attach_official_slate_to_feed(df, public_context)
def merge_public_context(df, public_context=None): return attach_slate_matchup_context(df, public_context)

def _df_to_records(df):
    if not isinstance(df,pd.DataFrame) or df.empty: return []
    return df.replace({np.nan:None}).to_dict(orient='records')
def _records_to_df(records): return pd.DataFrame(records or [])
def empty_results(message):
    return {'owners':pd.DataFrame(),'core':pd.DataFrame(),'alt':pd.DataFrame(),'chaos':pd.DataFrame(),'survivors':pd.DataFrame(),'cuts':pd.DataFrame(),'game_board':pd.DataFrame(),'role_board':pd.DataFrame(),'environment_board':pd.DataFrame(),'state_log':pd.DataFrame(),'meta':{'engine_version':'V0206_TRUE_OWNER_HARD_LOCK_NO_967','message':message,'owners_locked':0,'core_count':0,'passed_rows':0,'cut_rows':0,'core_rule':'CORE_3_FROM_ISOLATED_OWNERS_NO_REFILL_NO_967_CLAMP'}}
def save_locked_results(results):
    DATA_DIR.mkdir(exist_ok=True)
    payload={k:_df_to_records(results.get(k)) for k in ['owners','core','alt','chaos','survivors','cuts','game_board','role_board','environment_board','state_log']}
    payload['meta']=results.get('meta',{})
    LOCK_PATH.write_text(json.dumps(payload,indent=2))
def load_locked_results(): return empty_results('Run the Blender first.')
ALIASES={'pull':['pull_pct','pull%','pull'],'hard':['hard_hit_pct','hardhit%','hard_hit%','hard hit%','hh%'],'barrel':['barrel_pct','barrel%','brl%','barrel'],'sweet':['sweet_spot_pct','sweet%','sweet spot','launch','la'],'dmg':['dmg','damage','ult','ultimate','adj'],'hpi':['hpi','model','rating','hr score'],'hr':['hr_lane','hr_pa','hr/pa','hr9','hr/9'],'edge':['pitch_edge','pitch edge','edge'],'slot':['lineup_slot','slot','order','bo']}
def metrics(row): return {k:_field(row,n,-99 if k=='edge' else 0) for k,n in ALIASES.items()}
def metric_count(v): return sum(1 for k,x in v.items() if (x!=-99 if k=='edge' else x not in [None,0] and not pd.isna(x)))
def game_id(row):
    pk=_txt(row.get('game_pk'))
    return pk if pk and pk.lower() not in {'nan','none'} else _txt(row.get('game_key') or row.get('game'))
def normalize_feed(df):
    df=_safe_df(df).copy()
    if df.empty: return df
    if 'game_key' not in df.columns: df['game_key']=df['game'] if 'game' in df.columns else ''
    if 'official_slate_attached' not in df.columns: df['official_slate_attached']=False
    if 'player' in df.columns and 'pitcher' in df.columns:
        df=df[df['player'].astype(str).str.lower().str.strip()!=df['pitcher'].astype(str).str.lower().str.strip()].copy()
    df['_gid']=df.apply(lambda r: game_id(r.to_dict()),axis=1)
    return df.reset_index(drop=True)
def env_score(row):
    v=metrics(row)
    return strength(v['hr'],.5,2.6,18)+strength(v['edge'],0,18,15)+strength(v['dmg'],.5,2.6,13)+strength(v['hpi'],10,90,11)+strength(v['barrel'],3,18,10)+strength(v['pull'],25,60,8)+strength(v['hard'],25,64,6)
def lock_attack_sides(df):
    locks={}; rows=[]
    if df.empty: return locks,pd.DataFrame()
    for gid,gdf in df.groupby('_gid',dropna=False):
        if not _txt(gid): continue
        ts=[]
        for team,tdf in gdf.groupby('team',dropna=False):
            team=_txt(team)
            if not team: continue
            vals=[env_score(r.to_dict()) for _,r in tdf.iterrows()]
            ts.append((team,max(vals)+(sum(vals)/max(1,len(vals)))*.15,len(tdf)))
        if not ts: continue
        ts.sort(key=lambda x:x[1],reverse=True); team,score,count=ts[0]; locks[str(gid)]=team
        rows.append({'game_id':str(gid),'game_key':_txt(gdf.iloc[0].get('game_key') or gdf.iloc[0].get('game')),'locked_attack_side':team,'attack_score':round(float(score),2),'candidate_rows':int(count),'engine_rule':'ATTACK SIDE HARD LOCK - NON LOCKED SIDE CUT'})
    return locks,pd.DataFrame(rows)
def add_gate(gates,step,gate,passed,score,max_score,reason,hard_gate=True): gates.append({'step':step,'gate':gate,'result':'PASS' if passed else 'CUT','score':round(float(max(score,0)),2),'max_score':float(max_score),'reason':reason,'hard_gate':bool(hard_gate),'cut':bool(hard_gate and not passed)})
def role_lane(v,notes):
    pull,hard,barrel,dmg,hpi,hr,edge=v['pull'],v['hard'],v['barrel'],v['dmg'],v['hpi'],v['hr'],v['edge']
    adj=any(x in notes for x in ['adjacent','decoy','transfer','coverage','pressure','behind','after','weak slot'])
    who=any(x in notes for x in ['who','chaos','low owned','low-owned','bottom','random']) or (pull>=30 and hard>=32 and hpi<45 and barrel>=4)
    primary=strength(pull,33,60,23)+strength(barrel,5,18,23)+strength(dmg,.7,2.7,18)+strength(hpi,18,90,17)+strength(hr,.6,2.7,16)+strength(edge,0,22,12)
    adjacent=strength(pull,27,52,16)+strength(hard,28,58,16)+strength(dmg,.5,2.1,14)+strength(hr,.5,2.0,10)+(34 if adj else 0)
    who_score=strength(pull,25,50,13)+strength(hard,30,56,13)+strength(barrel,3,14,10)+strength(hr,.5,1.8,12)+strength(edge,0,14,10)+(38 if who else 0)
    scores={'Primary':round(primary,2),'Adjacent':round(adjacent,2),'WHO':round(who_score,2)}; role=max(scores,key=scores.get)
    if role=='Adjacent' and not adj and scores['Adjacent']<scores['Primary']+12: role='Primary'
    if role=='WHO' and not who and scores['WHO']<scores['Primary']+15: role='Primary'
    return role,scores,{'Adjacent':adj,'WHO':who}
def evaluate_candidate(row,locks):
    v=metrics(row); player=_txt(row.get('player')); team=_txt(row.get('team')); gid=game_id(row); gkey=_txt(row.get('game_key') or row.get('game')); locked=locks.get(str(gid),'')
    notes=' '.join([_txt(row.get(k)) for k in row.keys() if any(x in str(k).lower() for x in ['note','tag','raw','status','event'])]).lower()
    pull,hard,barrel,sweet,dmg,hpi,hr,edge,slot=[v[k] for k in ['pull','hard','barrel','sweet','dmg','hpi','hr','edge','slot']]
    mc=metric_count(v); gates=[]
    add_gate(gates,0,'PDF row',bool(player and gkey),8 if player and gkey else 0,8,f'player={player}; game={gkey}')
    attack_pass=bool(locked and team==locked); add_gate(gates,1,'Attack-side HARD LOCK',attack_pass,8 if attack_pass else 0,8,f'locked={locked}; team={team}',True)
    trigger=pull>=25 or hard>=28 or barrel>=3 or dmg>=.5 or hpi>=10 or hr>=.5 or edge>=0
    add_gate(gates,2,'Metric survival',mc>=3 and trigger,10 if mc>=3 and trigger else 0,10,f'metric_count={mc}; trigger={trigger}')
    lane=max(strength(hr,.5,2.4,11),strength(edge,0,16,11),strength(dmg,.5,2.5,11),strength(hpi,10,90,11)); add_gate(gates,3,'Pitcher HR lane',lane>0,lane,11,f'hr={hr}; edge={edge}; dmg={dmg}; hpi={hpi}')
    launch=max(strength(pull,25,60,13),strength(sweet,18,40,13),strength(barrel,3,18,13)); add_gate(gates,4,'Pull-air launch',launch>0,launch,13,f'pull={pull}; sweet={sweet}; barrel={barrel}')
    conversion=max(strength(dmg,.5,2.5,13),strength(barrel,3,18,13),strength(hpi,10,90,13),strength(hr,.5,2.5,13)); add_gate(gates,5,'Conversion DNA',conversion>0,conversion,13,f'dmg={dmg}; barrel={barrel}; hpi={hpi}; hr={hr}')
    opp=6 if slot==0 or slot<=7 else 1; add_gate(gates,6,'Lineup opportunity',opp>=5,opp,6,f'slot={slot}',False)
    support=max(strength(hard,28,64,8),strength(barrel,3,18,8),strength(dmg,.5,2.5,8)); add_gate(gates,7,'Hard-hit support',support>0,support,8,f'hard={hard}; barrel={barrel}; dmg={dmg}',False)
    role,role_scores,triggers=role_lane(v,notes); add_gate(gates,8,'Role lane',True,role_scores.get(role,0),max(1,max(role_scores.values())),f'role={role}; scores={role_scores}; triggers={triggers}',False)
    trap='trap' in notes or 'red flag' in notes or 'fade' in notes; add_gate(gates,9,'Trap audit',not trap,8 if not trap else 0,8,'no trap' if not trap else 'trap/fade flag')
    fin=max(strength(pull,30,60,7),strength(hard,28,64,7),strength(barrel,3,18,7),strength(dmg,.5,2.5,7),strength(hpi,10,90,7),strength(hr,.5,2.5,7)); add_gate(gates,10,'Finisher strength',fin>0,fin,7,f'finisher={round(fin,2)}')
    event=(lane*.32)+(launch*.28)+(conversion*.36)+(support*.14)+(fin*.25)+(role_scores.get(role,0)*.04); add_gate(gates,11,'Event ownership',event>=3.0,event,12,f'event_ownership={round(event,2)}')
    hard_cuts=[g for g in gates if g['cut']]; pass_depth=sum(1 for g in gates if g['result']=='PASS'); cut_depth=sum(1 for g in gates if g['result']=='CUT'); raw=sum(g['score'] for g in gates); maxs=sum(g['max_score'] for g in gates)
    quality=raw/max(1,maxs); event_shape=(event*4.25)+(lane*1.4)+(launch*1.1)+(conversion*1.35); fingerprint=((sum(ord(c) for c in (player+gkey+team))%73)-36)/10.0
    raw_score=14+(pass_depth*1.85)+(quality*14)+(event*3.1)+(lane*.75)+(launch*.55)+(conversion*.7)+fingerprint-(cut_depth*8.5)
    score=round(max(1,min(99.9,raw_score)),1)
    eligible=len(hard_cuts)==0 and event>=3.0 and mc>=3
    if not eligible: score=round(min(score,54.9),1)
    final_role=role if eligible else 'CUT'; archetype={'Primary':'Primary HR Owner','Adjacent':'Adjacent / Decoy Transfer','WHO':'WHO / Chaos Owner','CUT':'Cut by gates'}[final_role]
    result={**row,'game_id':gid,'locked_attack_side':locked,'blender_eligible':bool(eligible),'blender_score':score,'support_score':round(raw,2),'elimination_score':score,'score':score,'official_core_role':final_role,'true_role_path':role,'archetype':archetype,'metric_count':mc,'pass_depth':pass_depth,'cut_depth':cut_depth,'event_ownership':round(event,2),'role_Primary_score':role_scores.get('Primary',0),'role_Adjacent_score':role_scores.get('Adjacent',0),'role_WHO_score':role_scores.get('WHO',0),'stop_gate':'' if eligible else (hard_cuts[0]['gate'] if hard_cuts else 'event ownership'),'final_reason':f'{final_role} survived true event-owner path' if eligible else 'CUT — eliminated by Blender gates','gate_trace_json':json.dumps(gates),'role_scores_json':json.dumps(role_scores)}
    return result,gates,role_scores
def _role_from_survivor(row):
    scores={
        'Primary':_num(row.get('role_Primary_score'),0),
        'Adjacent':_num(row.get('role_Adjacent_score'),0),
        'WHO':_num(row.get('role_WHO_score'),0),
    }
    role=max(scores,key=scores.get)
    return role

def resolve_owners(survivors):
    passed=survivors[survivors['blender_eligible']==True].copy()
    if passed.empty: return pd.DataFrame()
    rows=[]
    for gid,g in passed.groupby('game_id',dropna=False):
        if not _txt(gid): continue
        g=g.copy()
        # ONE TRUE OWNER ONLY: no cross-game duplicate refill, no projection fallback.
        g['_owner']=g['event_ownership'].fillna(0)*1000+g['pass_depth'].fillna(0)*100+g['support_score'].fillna(0)
        g=g.sort_values(['_owner','elimination_score'],ascending=[False,False])
        r=g.iloc[0].drop(labels=['_owner'],errors='ignore').to_dict()
        # Role identity is assigned AFTER isolation from survivor behavior.
        post_role=_role_from_survivor(r)
        r['official_core_role']=post_role
        r['archetype']={'Primary':'Primary HR Owner','Adjacent':'Adjacent / Decoy Transfer','WHO':'WHO / Chaos Owner'}[post_role]
        r['resolved_owner']=True
        r['final_reason']=f'{post_role} isolated as the one true owner for this game; no refill/fallback used.'
        rows.append(r)
    owners=pd.DataFrame(rows)
    owners['_rank']=owners['event_ownership'].fillna(0)*1000+owners['pass_depth'].fillna(0)*100+owners['elimination_score'].fillna(0)
    return owners.sort_values('_rank',ascending=False).drop(columns=['_rank'],errors='ignore').reset_index(drop=True)
def build_core_top3(owners):
    if not isinstance(owners,pd.DataFrame) or owners.empty: return pd.DataFrame()
    core=owners.head(3).copy(); core['core_slot']=[f'CORE {i+1}' for i in range(len(core))]; core['ticket_role']='CORE'; return core.reset_index(drop=True)
def run_true_blender(df,*args,**kwargs):
    work=normalize_feed(df)
    if work.empty: return empty_results('No usable feed rows loaded.')
    locks,environment_board=lock_attack_sides(work); survivor_rows=[]; board_rows=[]; role_rows=[]
    for idx,r in work.iterrows():
        cand,gates,role_scores=evaluate_candidate(r.to_dict(),locks); cand['row_id']=idx; survivor_rows.append(cand)
        for g in gates: board_rows.append({'game_id':cand.get('game_id',''),'game_key':cand.get('game_key',''),'player':cand.get('player',''),'team':cand.get('team',''),'locked_attack_side':cand.get('locked_attack_side',''),'role':cand.get('official_core_role',''),**g,'blender_score':cand.get('blender_score',0)})
        role_rows.append({'game_id':cand.get('game_id',''),'game_key':cand.get('game_key',''),'player':cand.get('player',''),'assigned_role':cand.get('official_core_role',''),'true_role_path':cand.get('true_role_path',''),'Primary_score':role_scores.get('Primary',0),'Adjacent_score':role_scores.get('Adjacent',0),'WHO_score':role_scores.get('WHO',0),'pass_depth':cand.get('pass_depth',0),'cut_depth':cand.get('cut_depth',0),'event_ownership':cand.get('event_ownership',0),'elimination_score':cand.get('elimination_score',0)})
    survivors=pd.DataFrame(survivor_rows); cuts=survivors[survivors['blender_eligible']!=True].copy(); game_board=pd.DataFrame(board_rows); role_board=pd.DataFrame(role_rows); owners=resolve_owners(survivors); core=build_core_top3(owners)
    used=set(core['player'].astype(str).str.lower().tolist()) if not core.empty and 'player' in core.columns else set()
    alt=owners[~owners['player'].astype(str).str.lower().isin(used)].head(3).copy() if not owners.empty and 'player' in owners.columns else pd.DataFrame()
    if not alt.empty: alt['ticket_role']='ALT'; used.update(alt['player'].astype(str).str.lower().tolist())
    chaos=owners[(owners['official_core_role']=='WHO') & (~owners['player'].astype(str).str.lower().isin(used))].head(3).copy() if not owners.empty and 'official_core_role' in owners.columns and 'player' in owners.columns else pd.DataFrame()
    if not chaos.empty: chaos['ticket_role']='WHO'
    games=official_game_count(work) or actual_game_count(work)
    meta={'engine_version':'V0206_TRUE_OWNER_HARD_LOCK_NO_967','games':int(games),'input_rows':int(len(work)),'passed_rows':int((survivors['blender_eligible']==True).sum()),'cut_rows':int((survivors['blender_eligible']!=True).sum()),'owners_locked':int(len(owners)),'core_count':int(len(core)),'core_rule':'CORE_3_FROM_ISOLATED_OWNERS_NO_REFILL_NO_967_CLAMP','core_slots':core.get('core_slot',pd.Series(dtype=str)).tolist() if not core.empty else [],'generic_refill':False,'fallback_sorting':False,'role_recycling':False,'attack_side_hard_kill':True,'message':f"V0206 hard-lock true owner engine: Core={len(core)} from {len(owners)} owners. Pass rows={int((survivors['blender_eligible']==True).sum())}; cuts={int((survivors['blender_eligible']!=True).sum())}."}
    results={'owners':owners,'core':core,'alt':alt,'chaos':chaos,'survivors':survivors,'cuts':cuts,'game_board':game_board,'role_board':role_board,'environment_board':environment_board,'state_log':pd.DataFrame([{'rule':'TRUE_EVENT_OWNER_ENGINE','no_score_cluster':True,'attack_side_hard_kill':True,'generic_refill':False,'fallback_sorting':False,'role_recycling':False}]),'meta':meta}
    save_locked_results(results); return results
