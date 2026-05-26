from __future__ import annotations
import json, re
from pathlib import Path
from typing import Any, Dict, List
import numpy as np
import pandas as pd
from official_mlb_slate import fetch_official_mlb_slate, attach_official_slate_to_feed, official_game_count
from feeder import actual_game_count

DATA_DIR=Path('data'); LOCK_PATH=DATA_DIR/'locked_owners.json'
ENGINE_VERSION='V0207_LOCKED_18_GATE_OWNER_ENGINE'

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
        m=re.search(r'[-+]?\d*\.?\d+',s)
        return float(m.group(0)) if m else default
    except Exception: return default

def _key(s): return str(s).lower().replace(' ','').replace('_','').replace('%','').replace('/','').replace('-','')
def _safe_df(x): return x if isinstance(x,pd.DataFrame) else pd.DataFrame()
def csv_bytes(df): return _safe_df(df).to_csv(index=False).encode('utf-8')
def strength(x,floor,elite,pts):
    x=_num(x,0.0)
    if x<floor: return 0.0
    if x>=elite: return float(pts)
    return float(pts)*((x-floor)/max(.0001,elite-floor))

def _field(row,names,default=0.0):
    cmap={_key(k):k for k in row.keys()}
    for n in names:
        if _key(n) in cmap: return _num(row.get(cmap[_key(n)]),default)
    for n in names:
        nn=_key(n)
        for ck,real in cmap.items():
            if nn in ck or ck in nn: return _num(row.get(real),default)
    return default

def fetch_live_public_slate(date_str=None): return fetch_official_mlb_slate(date_str)
def fetch_live_public_hitter_pool(date_str=None): return fetch_official_mlb_slate(date_str)
def attach_slate_matchup_context(df, public_context=None): return attach_official_slate_to_feed(df, public_context)
def merge_public_context(df, public_context=None): return attach_slate_matchup_context(df, public_context)

def _df_to_records(df):
    if not isinstance(df,pd.DataFrame) or df.empty: return []
    return df.replace({np.nan:None}).to_dict(orient='records')

def empty_results(message):
    return {'owners':pd.DataFrame(),'core':pd.DataFrame(),'alt':pd.DataFrame(),'chaos':pd.DataFrame(),'survivors':pd.DataFrame(),'cuts':pd.DataFrame(),'game_board':pd.DataFrame(),'role_board':pd.DataFrame(),'environment_board':pd.DataFrame(),'state_log':pd.DataFrame(),'meta':{'engine_version':ENGINE_VERSION,'message':message,'owners_locked':0,'core_count':0,'passed_rows':0,'cut_rows':0,'core_rule':'CORE_3_FROM_FINAL_ISOLATED_OWNERS_ONLY','fallback_sorting':False,'best_remaining_logic':False,'projection_fallback':False}}

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
        teams=[]
        for team,tdf in gdf.groupby('team',dropna=False):
            team=_txt(team)
            if not team: continue
            vals=[env_score(r.to_dict()) for _,r in tdf.iterrows()]
            teams.append((team,max(vals)+(sum(vals)/max(1,len(vals)))*.15,len(tdf)))
        if not teams: continue
        teams.sort(key=lambda x:x[1],reverse=True)
        team,score,count=teams[0]
        locks[str(gid)]=team
        rows.append({'game_id':str(gid),'game_key':_txt(gdf.iloc[0].get('game_key') or gdf.iloc[0].get('game')),'locked_attack_side':team,'attack_score':round(float(score),2),'candidate_rows':int(count),'engine_rule':'HARD LOCK: eliminate only inside this side; opposite side cannot refill'})
    return locks,pd.DataFrame(rows)

def add_gate(gates,step,gate,passed,score,max_score,reason,hard_gate=True):
    gates.append({'step':step,'gate':gate,'result':'PASS' if passed else 'CUT','score':round(float(max(score,0)),2),'max_score':float(max_score),'reason':reason,'hard_gate':bool(hard_gate),'cut':bool(hard_gate and not passed)})

def _notes(row):
    return ' '.join([_txt(row.get(k)) for k in row.keys() if any(x in str(k).lower() for x in ['note','tag','raw','status','event','signal'])]).lower()

def evaluate_candidate(row,locks):
    v=metrics(row); player=_txt(row.get('player')); team=_txt(row.get('team')); gid=game_id(row); gkey=_txt(row.get('game_key') or row.get('game')); locked=locks.get(str(gid),'')
    notes=_notes(row)
    pull,hard,barrel,sweet,dmg,hpi,hr,edge,slot=[v[k] for k in ['pull','hard','barrel','sweet','dmg','hpi','hr','edge','slot']]
    mc=metric_count(v); gates=[]
    add_gate(gates,0,'PDF row / feed row exists',bool(player and gkey),8 if player and gkey else 0,8,f'player={player}; game={gkey}')
    side_locked=bool(locked); add_gate(gates,1,'LOCK ATTACK SIDE',side_locked,8 if side_locked else 0,8,f'locked_attack_side={locked}')
    within_side=bool(side_locked and team==locked); add_gate(gates,2,'ELIMINATE WITHIN SIDE ONLY',within_side,10 if within_side else 0,10,f'team={team}; locked={locked}')
    trigger=pull>=25 or hard>=28 or barrel>=3 or dmg>=.5 or hpi>=10 or hr>=.5 or edge>=0
    add_gate(gates,3,'No-empty-bat data gate',mc>=3 and trigger,10 if mc>=3 and trigger else 0,10,f'metric_count={mc}; trigger={trigger}')
    lane=max(strength(hr,.5,2.4,11),strength(edge,0,16,11),strength(dmg,.5,2.5,11),strength(hpi,10,90,11)); add_gate(gates,4,'Pitcher HR lane gate',lane>0,lane,11,f'hr={hr}; edge={edge}; dmg={dmg}; hpi={hpi}')
    launch=max(strength(pull,25,60,13),strength(sweet,18,40,13),strength(barrel,3,18,13)); add_gate(gates,5,'Pull-air / launch window gate',launch>0,launch,13,f'pull={pull}; sweet={sweet}; barrel={barrel}')
    hh=strength(hard,28,64,8); add_gate(gates,6,'Hard-hit validation gate',hh>0,hh,8,f'hard={hard}')
    shape=max(strength(barrel,3,18,9),strength(sweet,18,40,9)); add_gate(gates,7,'Barrel / sweet-spot shape gate',shape>0,shape,9,f'barrel={barrel}; sweet={sweet}',False)
    pitchkill=max(strength(edge,0,18,10),strength(hr,.5,2.5,10)); add_gate(gates,8,'Pitch-type kill switch',pitchkill>0,pitchkill,10,f'edge={edge}; hr_lane={hr}')
    mistake=max(strength(dmg,.5,2.5,10),strength(hpi,10,90,10),strength(barrel,3,18,10)); add_gate(gates,9,'Mistake-pitch recipient gate',mistake>0,mistake,10,f'dmg={dmg}; hpi={hpi}; barrel={barrel}')
    opp=6 if slot==0 or slot<=7 else 1; add_gate(gates,10,'Lineup opportunity gate',opp>=5,opp,6,f'slot={slot}',False)
    adj_flag=any(x in notes for x in ['adjacent','decoy','transfer','coverage','pressure','behind','after','weak slot'])
    adj_score=(8 if adj_flag else 2)+strength(pull,27,52,5)+strength(hard,28,58,5); add_gate(gates,10.5,'Adjacent / book-decoy audit',True,adj_score,18,f'adjacent_signal={adj_flag}',False)
    bullpen_score=max(strength(hr,.5,2.0,6),strength(edge,0,14,6),2); add_gate(gates,11,'Bullpen continuation proxy',True,bullpen_score,6,'proxy only; no projection fallback',False)
    chaos_flag=any(x in notes for x in ['who','chaos','low owned','low-owned','bottom','random']) or (pull>=30 and hard>=32 and hpi<45 and barrel>=3)
    chaos_score=(9 if chaos_flag else 2)+strength(pull,25,50,5)+strength(hard,30,56,5); add_gate(gates,12,'Game script / WHO chaos gate',True,chaos_score,19,f'chaos_signal={chaos_flag}',False)
    history=max(strength(dmg,.6,2.6,9),strength(hpi,18,90,9),strength(hr,.6,2.7,9)); add_gate(gates,13,'True HR conversion history proxy',history>0,history,9,f'dmg={dmg}; hpi={hpi}; hr_lane={hr}',False)
    trap='trap' in notes or 'red flag' in notes or 'fade' in notes or 'pitch around' in notes; add_gate(gates,14,'Trap / pitch-around audit',not trap,8 if not trap else 0,8,'no trap' if not trap else 'trap/fade/pitch-around flag')
    fin=max(strength(pull,30,60,7),strength(hard,28,64,7),strength(barrel,3,18,7),strength(dmg,.5,2.5,7),strength(hpi,10,90,7),strength(hr,.5,2.5,7)); add_gate(gates,15,'Finisher strength gate',fin>0,fin,7,f'finisher={round(fin,2)}')
    event=(lane*.32)+(launch*.28)+(mistake*.36)+(hh*.14)+(fin*.25)+(adj_score*.03)+(chaos_score*.03); add_gate(gates,16,'Event ownership isolation gate',event>=3.0,event,12,f'event_ownership={round(event,2)}')
    add_gate(gates,17,'Resolve ONE owner per game BEFORE roles',True,1,1,'pending resolver: this row cannot become core until isolated',False)
    add_gate(gates,18,'Raw gate memory / zero fallback lock',True,1,1,'gate trace rendered; no projection fallback; no best-remaining refill',False)
    hard_cuts=[g for g in gates if g['cut']]
    pass_depth=sum(1 for g in gates if g['result']=='PASS'); cut_depth=sum(1 for g in gates if g['result']=='CUT'); raw=sum(g['score'] for g in gates); maxs=sum(g['max_score'] for g in gates)
    quality=raw/max(1,maxs); fingerprint=((sum(ord(c) for c in (player+gkey+team))%73)-36)/10.0
    score=round(max(1,min(96.7,14+(pass_depth*1.55)+(quality*15)+(event*3.0)+(lane*.75)+(launch*.55)+(mistake*.7)+fingerprint-(cut_depth*9.5))),1)
    eligible=len(hard_cuts)==0 and event>=3.0 and mc>=3 and within_side
    if not eligible: score=round(min(score,54.9),1)
    stop='' if eligible else (hard_cuts[0]['gate'] if hard_cuts else 'event ownership')
    result={**row,'game_id':gid,'locked_attack_side':locked,'blender_eligible':bool(eligible),'blender_score':score,'support_score':round(raw,2),'elimination_score':score,'score':score,'official_core_role':'PENDING_OWNER_ROLE' if eligible else 'CUT','true_role_path':'PENDING_OWNER_ROLE' if eligible else 'CUT','archetype':'Pending one-owner resolver' if eligible else 'Cut by gates','metric_count':mc,'pass_depth':pass_depth,'cut_depth':cut_depth,'event_ownership':round(event,2),'adjacent_signal':bool(adj_flag),'chaos_signal':bool(chaos_flag),'stop_gate':stop,'final_reason':'SURVIVED SIDE-ONLY ELIMINATION — waiting for one-owner resolver' if eligible else 'CUT — eliminated by locked Blender gates','gate_trace_json':json.dumps(gates)}
    return result,gates

def role_from_owner(r):
    adj=bool(r.get('adjacent_signal',False)); chaos=bool(r.get('chaos_signal',False))
    pull=_num(r.get('pull_pct',0)); hard=_num(r.get('hard_hit_pct',0)); barrel=_num(r.get('barrel_pct',0)); dmg=_num(r.get('dmg',0)); hpi=_num(r.get('hpi',0)); hr=_num(r.get('hr_lane',0)); edge=_num(r.get('pitch_edge',-99))
    primary=strength(pull,33,60,23)+strength(barrel,5,18,23)+strength(dmg,.7,2.7,18)+strength(hpi,18,90,17)+strength(hr,.6,2.7,16)+strength(edge,0,22,12)
    adjacent=strength(pull,27,52,16)+strength(hard,28,58,16)+strength(dmg,.5,2.1,14)+strength(hr,.5,2.0,10)+(34 if adj else 0)
    who=strength(pull,25,50,13)+strength(hard,30,56,13)+strength(barrel,3,14,10)+strength(hr,.5,1.8,12)+strength(edge,0,14,10)+(38 if chaos else 0)
    scores={'Primary':round(primary,2),'Adjacent':round(adjacent,2),'WHO':round(who,2)}
    role=max(scores,key=scores.get)
    if role=='Adjacent' and not adj and scores['Adjacent']<scores['Primary']+12: role='Primary'
    if role=='WHO' and not chaos and scores['WHO']<scores['Primary']+15: role='Primary'
    archetype={'Primary':'Primary HR Owner','Adjacent':'Adjacent / Decoy Transfer Owner','WHO':'WHO / Chaos Owner'}[role]
    return role,archetype,scores

def resolve_owners(survivors):
    passed=survivors[survivors['blender_eligible']==True].copy()
    if passed.empty: return pd.DataFrame(), pd.DataFrame()
    rows=[]; role_rows=[]; used=set()
    for gid,g in passed.groupby('game_id',dropna=False):
        if not _txt(gid): continue
        g=g.copy(); g['_owner']=g['event_ownership'].fillna(0)*1000+g['pass_depth'].fillna(0)*100+g['support_score'].fillna(0)
        g=g.sort_values(['_owner','elimination_score'],ascending=[False,False])
        owner=None
        for _,r in g.iterrows():
            player=_txt(r.get('player')).lower()
            if player and player not in used:
                used.add(player); owner=r.drop(labels=['_owner'],errors='ignore').to_dict(); break
        if owner:
            role,arch,rs=role_from_owner(owner)
            owner['official_core_role']=role; owner['true_role_path']=role; owner['archetype']=arch
            owner['final_reason']='LOCKED OWNER — role built after survivor behavior, not before isolation'
            rows.append(owner)
            role_rows.append({'game_id':owner.get('game_id',''),'game_key':owner.get('game_key',''),'player':owner.get('player',''),'assigned_role':role,'archetype':arch,'Primary_score':rs.get('Primary',0),'Adjacent_score':rs.get('Adjacent',0),'WHO_score':rs.get('WHO',0),'event_ownership':owner.get('event_ownership',0),'elimination_score':owner.get('elimination_score',0),'role_rule':'ROLE BUILT AFTER ONE OWNER ISOLATED'})
    if not rows: return pd.DataFrame(), pd.DataFrame()
    owners=pd.DataFrame(rows)
    owners['_rank']=owners['event_ownership'].fillna(0)*1000+owners['pass_depth'].fillna(0)*100+owners['elimination_score'].fillna(0)
    owners=owners.sort_values('_rank',ascending=False).drop(columns=['_rank'],errors='ignore').reset_index(drop=True)
    return owners,pd.DataFrame(role_rows)

def build_core_top3(owners):
    if not isinstance(owners,pd.DataFrame) or owners.empty: return pd.DataFrame()
    core=owners.head(3).copy()
    core['core_slot']=[f'CORE {i+1}' for i in range(len(core))]
    core['ticket_role']='CORE'
    return core.reset_index(drop=True)

def run_true_blender(df,*args,**kwargs):
    work=normalize_feed(df)
    if work.empty: return empty_results('No usable feed rows loaded.')
    locks,environment_board=lock_attack_sides(work); survivor_rows=[]; board_rows=[]
    for idx,r in work.iterrows():
        cand,gates=evaluate_candidate(r.to_dict(),locks); cand['row_id']=idx; survivor_rows.append(cand)
        for g in gates:
            board_rows.append({'game_id':cand.get('game_id',''),'game_key':cand.get('game_key',''),'player':cand.get('player',''),'team':cand.get('team',''),'locked_attack_side':cand.get('locked_attack_side',''),'role':cand.get('official_core_role',''),**g,'blender_score':cand.get('blender_score',0)})
    survivors=pd.DataFrame(survivor_rows)
    cuts=survivors[survivors['blender_eligible']!=True].copy() if not survivors.empty else pd.DataFrame()
    game_board=pd.DataFrame(board_rows)
    owners,role_board=resolve_owners(survivors)
    core=build_core_top3(owners)
    used=set(core['player'].astype(str).str.lower().tolist()) if not core.empty and 'player' in core.columns else set()
    alt=owners[~owners['player'].astype(str).str.lower().isin(used)].head(3).copy() if not owners.empty and 'player' in owners.columns else pd.DataFrame()
    if not alt.empty: alt['ticket_role']='ALT'; used.update(alt['player'].astype(str).str.lower().tolist())
    chaos=owners[(owners['official_core_role']=='WHO') & (~owners['player'].astype(str).str.lower().isin(used))].head(3).copy() if not owners.empty and 'official_core_role' in owners.columns and 'player' in owners.columns else pd.DataFrame()
    if not chaos.empty: chaos['ticket_role']='WHO'
    games=official_game_count(work) or actual_game_count(work)
    meta={'engine_version':ENGINE_VERSION,'games':int(games),'input_rows':int(len(work)),'passed_rows':int((survivors['blender_eligible']==True).sum()) if not survivors.empty else 0,'cut_rows':int((survivors['blender_eligible']!=True).sum()) if not survivors.empty else 0,'owners_locked':int(len(owners)),'core_count':int(len(core)),'core_rule':'CORE_3_FROM_FINAL_ISOLATED_OWNERS_ONLY','core_slots':core.get('core_slot',pd.Series(dtype=str)).tolist() if not core.empty else [],'projection_fallback':False,'best_remaining_logic':False,'generic_refill':False,'fallback_sorting':False,'role_before_owner':False,'side_only_elimination':True,'message':f"V0207 locked owner engine: Core={len(core)} from {len(owners)} isolated owners. Opposite side removed before elimination. No projection fallback / no best-remaining refill."}
    state_log=pd.DataFrame([
        {'order':1,'rule':'Lock attack side','status':'ON'},
        {'order':2,'rule':'Eliminate within side only','status':'ON'},
        {'order':3,'rule':'Resolve ONE owner per side before roles','status':'ON'},
        {'order':4,'rule':'Build role identity from survivor behavior','status':'ON'},
        {'order':5,'rule':'Build Core 3 from final isolated owners only','status':'ON'},
        {'order':6,'rule':'Render raw gate memory directly','status':'ON'},
        {'order':7,'rule':'Zero projection fallback','status':'ON'},
        {'order':8,'rule':'Zero best remaining hitter logic','status':'ON'},
    ])
    results={'owners':owners,'core':core,'alt':alt,'chaos':chaos,'survivors':survivors,'cuts':cuts,'game_board':game_board,'role_board':role_board,'environment_board':environment_board,'state_log':state_log,'meta':meta}
    save_locked_results(results); return results
