from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
from nhl_data import events,roster,starters,get_history,players_from
GATES=[('G0','Game/slate lock'),('G1','Environment'),('G2','Lineup/access'),('G3','Opponent attack map'),('G4','Damage mechanism'),('G5','Exact matchup alignment'),('G6','Opportunity/access'),('G7','Recurrence/sequence'),('G8','Market fingerprint'),('G9','Player × environment'),('G10','Event route'),('G10.5','Recipient separation'),('G11','Continuation'),('G12','Event ownership'),('G14','WHO/anomaly'),('G15','Finisher protection'),('G16','Final competition'),('G17','Contradiction audit'),('G18','Final audit')]
def now():return datetime.now(timezone.utc).isoformat()
def sid(*x):return hashlib.sha256('|'.join(map(str,x)).encode()).hexdigest()[:14]
def isgoal(e):
 t=str(e.get('type','')).lower().replace('_','-')
 return 'goal' in t and 'shot-on-goal' not in t
def isshot(e):return any(k in str(e.get('type','')).lower() for k in ('shot','goal','missed-shot','blocked-shot'))
def is_on_goal(e):
 t=str(e.get('type','')).lower().replace('_','-')
 return 'goal' in t or 'shot-on-goal' in t or t in ('shot','shotongoal')
def status(ok):return 'SUPPORTED' if ok else 'PENDING / NO EVIDENCE'
def gate(i,n,s,e=None,l=''):return {'gate':i,'name':n,'status':s,'evidence':e or [],'limitation':l}
def player_hist(ev,pid):
 # Attempts include on-goal shots, misses, and blocked attempts; on-goal shots are separate.
 r=[x for x in ev if x.get('shooterId')==pid]; goals=[x for x in r if isgoal(x)]
 sog=[x for x in r if is_on_goal(x)]
 assists=[x for x in ev if isgoal(x) and pid in (x.get('assist1Id'),x.get('assist2Id'))]
 dates=sorted({x.get('date') for x in r if x.get('date')},reverse=True)
 goal_dates=sorted({x.get('date') for x in goals if x.get('date')},reverse=True)
 return {'historicalShots':len(sog),'historicalAttempts':len(r),'historicalGoals':len(goals),'historicalAssists':len(assists),
 'shotToGoalObserved':round(len(goals)/len(sog),3) if sog else None,
 'shotTypes':dict(Counter(x.get('shotType','unknown') for x in r)),
 'goalShotTypes':dict(Counter(x.get('shotType','unknown') for x in goals)),
 'goalZones':dict(Counter(str(x.get('zone') or 'unknown') for x in goals)),
 'datesWithShots':dates,'datesWithGoals':goal_dates,'recentShotEvents':r[:10],
 'recentGoalEvents':goals[:10], 'goalGameCount':len(goal_dates)}
def goalie_hist(ev,gid):
 # Goalie faced-shot denominators must exclude missed and blocked attempts.
 r=[x for x in ev if x.get('goalieId')==gid and is_on_goal(x)]; goals=[x for x in r if isgoal(x)]
 faced=Counter(x.get('shotType','unknown') for x in r); allowed=Counter(x.get('shotType','unknown') for x in goals)
 by_type={k:{'shotsFaced':n,'goalsAllowed':allowed.get(k,0),'observedGoalRate':round(allowed.get(k,0)/n,3) if n else None} for k,n in faced.items()}
 zones=Counter(str(x.get('zone') or 'unknown') for x in r); goals_z=Counter(str(x.get('zone') or 'unknown') for x in goals)
 by_zone={k:{'shotsFaced':n,'goalsAllowed':goals_z.get(k,0),'observedGoalRate':round(goals_z.get(k,0)/n,3) if n else None} for k,n in zones.items()}
 return {'shotsObserved':len(r),'goalsAgainstObserved':len(goals),'saveRateObserved':round((len(r)-len(goals))/len(r),3) if r else None,
 'shotTypesFaced':dict(faced),'goalsAgainstByShotType':dict(allowed),'shotTypeOutcomes':by_type,
 'zonesFaced':dict(zones),'goalsAgainstByZone':dict(goals_z),'zoneOutcomes':by_zone}
def direct(ev,pid,gid):
 r=[x for x in ev if x.get('shooterId')==pid and x.get('goalieId')==gid]
 goals=[x for x in r if isgoal(x)]
 return {'directEvents':len(r),'directGoals':len(goals),'directShotTypes':dict(Counter(x.get('shotType','unknown') for x in r)),
 'directGoalShotTypes':dict(Counter(x.get('shotType','unknown') for x in goals)),
 'directZones':dict(Counter(str(x.get('zone') or 'unknown') for x in r)),
 'directGoalZones':dict(Counter(str(x.get('zone') or 'unknown') for x in goals)),
 'directDates':sorted({x.get('date') for x in r if x.get('date')},reverse=True)}
def analyze(bundle,mode,limit=8):
 game=bundle['game']; land=bundle.get('landing') or {}; box=bundle.get('boxscore') or {}; errs=list(bundle.get('errors') or [])
 home,away=game.get('homeAbbrev','HOME'),game.get('awayAbbrev','AWAY'); date=game.get('gameDate','')
 hp=roster(box,land,'home',home); ap=roster(box,land,'away',away)
 if not hp: errs.append(f'{home}: no roster returned from game payload or current team roster')
 if not ap: errs.append(f'{away}: no roster returned from game payload or current team roster')
 ps=[]
 for p in hp:ps.append({**p,'team':home,'opponent':away})
 for p in ap:ps.append({**p,'team':away,'opponent':home})
 sk=[p for p in ps if p.get('section')!='goalies' and str(p.get('position','')).upper() not in ('G','GOALIE')]
 current=events(bundle.get('plays')); sm=starters(box); hist={}; goalie_rows=[]
 for team in (home,away):
  hb,he=get_history(team,date,limit); errs.extend(he); ev=[]; names={}
  for b in hb:
   for x in events(b.get('plays')):x['date']=b['game'].get('gameDate');x['gameId']=b['game'].get('gameId');ev.append(x)
   for side in ('home','away'):
    for p in players_from(b.get('landing'),side,'history'):names[p['playerId']]=p['name']
  hist[team]={'bundles':hb,'events':ev,'names':names}
 team_context={}
 for team in (home,away):
  past=sorted((b.get('game') or {}).get('gameDate','') for b in hist[team]['bundles'] if (b.get('game') or {}).get('gameDate'))
  last_date=past[-1] if past else None
  try: gap=(datetime.fromisoformat(date).date()-datetime.fromisoformat(last_date).date()).days if date and last_date else None
  except ValueError: gap=None
  team_context[team]={'lastCompletedGameDate':last_date,'calendarDaysSinceLastGame':gap,'backToBack':gap==1 if gap is not None else None,'fullRestDays':max(0,gap-1) if gap is not None else None,'travelStatus':'NOT MEASURED — location sequence not verified'}
 for side,team in (('home',home),('away',away)):
  game_goalies=sm.get(side,{}).get('goalies',[]) or []
  game_goalie_ids={int(x.get('playerId') or x.get('id')) for x in game_goalies if x.get('playerId') or x.get('id')}
  marked_starter=sm.get(side,{}).get('starter') or {}
  marked_starter_id=marked_starter.get('playerId') or marked_starter.get('id')
  marked_starter_id=int(marked_starter_id) if marked_starter_id else None
  candidates=game_goalies or [{'playerId':p['playerId'],'name':p['name']} for p in ps if p['team']==team and p.get('section')=='goalies']
  for g in candidates:
   gid=g.get('playerId') or g.get('id')
   if not gid:continue
   gid=int(gid)
   if marked_starter_id == gid: starter_status='source explicitly marks starter'
   elif gid in game_goalie_ids: starter_status='game goalie listed; not marked starter'
   else: starter_status='current roster only; game starter not confirmed'
   ev=hist[team]['events']; goalie_rows.append({'team':team,'goalieId':gid,'goalie':g.get('name',{}).get('default','') if isinstance(g.get('name'),dict) else g.get('name',''),'starterStatus':starter_status,**goalie_hist(ev,gid)})
 byteam=defaultdict(list)
 for g in goalie_rows:byteam[g['team']].append(g)
 player_rows=[]
 for p in sk:
  ev=hist[p['team']]['events']; pr=player_hist(ev,p['playerId']); matches=[]
  for goalie in byteam[p['opponent']]:
   matches.append({**goalie,**direct(ev,p['playerId'],goalie['goalieId'])})
  role=('FINISHER + FACILITATOR' if pr['historicalGoals'] and pr['historicalAssists'] else ('FINISHER' if pr['historicalGoals'] else ('FACILITATOR' if pr['historicalAssists'] else 'NO RECORDED GOAL INVOLVEMENT')))
  player_rows.append({'playerId':p['playerId'],'player':p['name'],'team':p['team'],'opponent':p['opponent'],'position':p['position'],'recipientRole':role,**pr,'opposingGoalieMatches':matches,'recordId':sid(game.get('gameId'),p['playerId'],mode)})
 names={p['playerId']:p['name'] for p in ps}; direct_now=[]
 for e in current:
  if e.get('shooterId') and e.get('goalieId'):direct_now.append({'shooterId':e['shooterId'],'shooter':names.get(e['shooterId'],f"Player {e['shooterId']}"),'goalieId':e['goalieId'],'event':e.get('type'),'shotType':e.get('shotType','unknown'),'period':e.get('period'),'time':e.get('time'),'goal':isgoal(e)})
 hist_n=sum(len(x['bundles']) for x in hist.values()); hist_events=sum(len(x['events']) for x in hist.values())
 gates=[
 gate('G0','Game/slate lock',status(bool(game.get('gameId') and home and away)),[f"gameId={game.get('gameId')}",f'{away} @ {home}',f"state={game.get('gameState')}",f"gameType={game.get('gameType') or 'not supplied'}"]),
 gate('G1','Environment',status(any(team_context[t]['calendarDaysSinceLastGame'] is not None for t in (home,away))),[f"venue={game.get('venue') or 'not supplied'}",f'{home} rest context={team_context[home]}',f'{away} rest context={team_context[away]}'],'Rest interval is derived from retrieved completed-game dates; travel, weather, and arena conditions are not measured.'),
 gate('G2','Lineup/access',status(bool(hp and ap)),[f'home roster={len(hp)}',f'away roster={len(ap)}'],'Roster entries do not establish confirmed lines or PP units.'),
 gate('G3','Opponent attack map',status(any(g['shotsObserved']>0 for g in goalie_rows)),[f'goalie candidates={len(goalie_rows)}',f'goalies with observed shots={sum(g["shotsObserved"]>0 for g in goalie_rows)}',f'historical games={hist_n}'],'Weakness evidence is restricted to observed NHL event IDs in retrieved history.'),
 gate('G4','Damage mechanism',status(any(p['historicalShots'] for p in player_rows)),[f'skaters={len(sk)}',f'players with observed shots={sum(p["historicalShots"]>0 for p in player_rows)}'],'Shot-type history is descriptive, not proof of tactical mechanism.'),
 gate('G5','Exact matchup alignment',status(any(m['directEvents'] or (set(p['goalShotTypes'])-{'unknown'}) & (set(m.get('goalsAgainstByShotType',{}))-{'unknown'}) or (set(p.get('goalZones',{}))-{'unknown'}) & (set(m.get('goalsAgainstByZone',{}))-{'unknown'}) for p in player_rows for m in p['opposingGoalieMatches'])),[f'exact player-ID × opposing-goalie-ID pairs={sum(len(p["opposingGoalieMatches"]) for p in player_rows)}',f'direct historical goals={sum(m["directGoals"] for p in player_rows for m in p["opposingGoalieMatches"])}'],'Exact IDs define the player and goalie profiles; a historical head-to-head goal is supporting evidence, not mandatory when the player scoring lane matches the goalie weakness.'),
 gate('G6','Opportunity/access','PENDING / NO EVIDENCE',[f'full available skater pool={len(sk)}'],'Line/PP deployment not reliably provided.'),
 gate('G7','Recurrence/sequence',status(any(len(p['datesWithShots'])>=2 for p in player_rows)),[f'historical games per team requested={limit}'],'Bounded by available historical PBP; missing history is not negative evidence.'),
 gate('G8','Market fingerprint','PENDING / NO EVIDENCE',[],'No odds or market shortcut used.'),
 gate('G9','Player × environment','PARTIAL — REST / VENUE ONLY',[f"venue={game.get('venue') or 'not supplied'}",f'{home}={team_context[home]}',f'{away}={team_context[away]}'],'No fabricated home/road player split or travel effect; player-specific environment splits remain pending.'),
 gate('G10','Event route',status(any(p['historicalShots']>0 or p['historicalGoals']>0 for p in player_rows)),[f'unfiltered skater pool={len(player_rows)}',f'players with observed event routes={sum(p["historicalShots"]>0 or p["historicalGoals"]>0 for p in player_rows)}'],'No star/chalk/line filter is applied.'),
 gate('G10.5','Recipient separation',status(any(p['historicalGoals'] or p['historicalAssists'] for p in player_rows)),[f'goal recipients with historical goals={sum(p["historicalGoals"]>0 for p in player_rows)}',f'facilitators with historical assists={sum(p["historicalAssists"]>0 for p in player_rows)}',f'full skater pool preserved={len(player_rows)}'],'Finisher and facilitator are separated by recorded goal/assist event IDs; lineup/PP-role claims are not inferred.'),
 gate('G11','Continuation',status(hist_events>0),[f'recent completed games retrieved={hist_n}',f'players with goals in retrieved history={sum(p["historicalGoals"]>0 for p in player_rows)}'],'Continuity is limited to retrieved event history; no late-game deployment assumptions.'),
 gate('G12','Event ownership',status(any(isgoal(x) and x.get('shooterId') for x in current) or any(isgoal(x) and (x.get('shooterId') or x.get('assist1Id') or x.get('assist2Id')) for t in hist.values() for x in t['events'])),[f'current direct-ID events={len(direct_now)}',f'historical events={hist_events}',f'current goal events with scorer IDs={sum(bool(isgoal(x) and x.get("shooterId")) for x in current)}',f'historical goal/assist events with player IDs={sum(bool(isgoal(x) and (x.get("shooterId") or x.get("assist1Id") or x.get("assist2Id"))) for t in hist.values() for x in t["events"])}'],'Ownership is asserted only from event player IDs.'),
 gate('G14','WHO/anomaly',status(any(m['directGoals']>0 or (set(p['goalShotTypes'])-{'unknown'}) & (set(m.get('goalsAgainstByShotType',{}))-{'unknown'}) or (set(p.get('goalZones',{}))-{'unknown'}) & (set(m.get('goalsAgainstByZone',{}))-{'unknown'}) for p in player_rows for m in p['opposingGoalieMatches'])),[f'full candidate universe={len(player_rows)}',f'players with goal events={sum(p["historicalGoals"]>0 for p in player_rows)}',f'players with exact goalie goals={sum(any(m["directGoals"]>0 for m in p["opposingGoalieMatches"]) for p in player_rows)}'],'Roster presence alone is not anomaly evidence. Candidates are surfaced from direct-goal or exact shared-lane evidence and cannot override a stronger validated path.'),
 gate('G15','Finisher protection','COMPARISON REQUIRED',[f'players with recorded goals={sum(p["historicalGoals"]>0 for p in player_rows)}',f'players with recorded assists={sum(p["historicalAssists"]>0 for p in player_rows)}',f'candidate rows preserved={len(player_rows)}'],'Do not displace a finisher with a stronger validated goal path solely because another player has more assists. This gate remains unresolved until comparable candidate paths are reviewed.'),
 gate('G16','Final competition','CATEGORICAL — NO NUMERIC SCORE',[f'goal-scoring profiles={sum(p["historicalGoals"]>0 for p in player_rows)}',f'exact player-goalie goal paths={sum(1 for p in player_rows for m in p["opposingGoalieMatches"] if m["directGoals"]>0)}',f'candidate rows preserved={len(player_rows)}'],'No weighted score, arbitrary tie-breaker, or forced winner; candidate evidence stays visible for direct comparison.'),
 gate('G17','Contradiction audit','REVIEW REQUIRED' if errs else 'NO RETRIEVAL ERRORS — CONTRADICTIONS EXPOSED',[f'retrieval errors={len(errs)}',f'candidate records={len(player_rows)}',f'players with on-goal shots but no recorded goals={sum(p["historicalShots"]>0 and p["historicalGoals"]==0 for p in player_rows)}',f'players with assists but no recorded goals={sum(p["historicalAssists"]>0 and p["historicalGoals"]==0 for p in player_rows)}'],'This reports contradiction candidates and source failures; it does not claim every tactical contradiction has been resolved.'),
 gate('G18','Final audit','AUDIT TRACE COMPLETE — VALIDATION STATUS SHOWN',[f'mode={mode}',f'runUTC={now()}',f'gates={len(GATES)}',f'players={len(player_rows)}',f'full player pool retained={len(player_rows)}'],'Full gate trace is recorded; unresolved source data is not treated as a negative finding.')]
 # Candidate-level evidence rows are deliberately unranked; there is no weighted prediction score.
 route_rows=[]
 for p in player_rows:
  for m in p['opposingGoalieMatches']:
   player_goal_types=set(p['goalShotTypes'])-{'unknown'}
   goalie_allowed_types=set(m.get('goalsAgainstByShotType',{}))-{'unknown'}
   player_goal_zones=set(p.get('goalZones',{}))-{'unknown'}
   goalie_allowed_zones=set(m.get('goalsAgainstByZone',{}))-{'unknown'}
   type_overlap=sorted(player_goal_types & goalie_allowed_types)
   zone_overlap=sorted(player_goal_zones & goalie_allowed_zones)
   # Categorical path only. Report the evidence actually observed; never turn a tiny sample into a winner.
   direct_sample=m['directEvents']
   comparable_goal_lanes=bool(player_goal_types or player_goal_zones) and bool(goalie_allowed_types or goalie_allowed_zones)
   if m['directGoals']>0 and (type_overlap or zone_overlap):
    path='DIRECT GOAL + SHARED DAMAGE LANE'
   elif m['directGoals']>0:
    path='DIRECT GOAL HISTORY — SHARED LANE NOT ESTABLISHED'
   elif (type_overlap or zone_overlap) and comparable_goal_lanes:
    path='SHARED DAMAGE LANE — DIRECT GOAL NOT OBSERVED'
   elif p['historicalShots'] and m['shotsObserved']:
    path='CONTRADICTION CHECK — NO SHARED GOAL LANE FOUND'
   else:
    path='WHO — INSUFFICIENT COMPARABLE SAMPLE'
   route_rows.append({'playerId':p['playerId'],'player':p['player'],'team':p['team'],'opponent':p['opponent'],'position':p['position'],
    'playerHistoricalShotsOnGoal':p['historicalShots'],'playerHistoricalAttempts':p.get('historicalAttempts',0),'playerHistoricalGoals':p['historicalGoals'],'playerHistoricalAssists':p['historicalAssists'],'playerShotToGoalObserved':p['shotToGoalObserved'],'playerGoalGameCount':p['goalGameCount'],'playerShotTypes':p['shotTypes'],'playerGoalShotTypes':p['goalShotTypes'],
    'goalieId':m['goalieId'],'goalie':m['goalie'],'starterStatus':m['starterStatus'],'starterConfirmed':m['starterStatus']=='source explicitly marks starter','goalieShotsObserved':m['shotsObserved'],
    'goalieGoalsAllowedObserved':m['goalsAgainstObserved'],'goalieShotTypeOutcomes':m.get('shotTypeOutcomes',{}),'goalieZoneOutcomes':m.get('zoneOutcomes',{}),
    'shotTypeOverlap':type_overlap,'zoneOverlap':zone_overlap,'pathFinding':path,
    'directEvents':m['directEvents'],'directGoals':m['directGoals'],'directSampleNote':('Direct sample is limited; interpret descriptively.' if m['directEvents'] < 3 else 'Direct sample includes at least three recorded events.'),'directShotTypes':m['directShotTypes'],'directGoalShotTypes':m['directGoalShotTypes'],
    'directZones':m['directZones'],'directGoalZones':m['directGoalZones'],'directDates':m['directDates']})
 route_candidates=[p for p in player_rows if p['historicalShots']>0 or p['historicalGoals']>0]
 # Candidate-level, ordered gate trace: this is evidence progression, not a numeric ranking.
 for p in player_rows:
  pm=[r for r in route_rows if r['playerId']==p['playerId']]
  p['routeFindings']=[r['pathFinding'] for r in pm]
  p['confirmedStarterPath']=any(r['starterStatus']=='source explicitly marks starter' and bool(r['shotTypeOverlap'] or r['zoneOverlap']) for r in pm)
  p['opposingStarterDirectGoals']=sum(r['directGoals'] for r in pm if r['starterStatus']=='source explicitly marks starter')
  p['sharedDamageLaneCount']=sum(bool(r['shotTypeOverlap'] or r['zoneOverlap']) for r in pm)
  p['exactDirectGoalCount']=sum(r['directGoals'] for r in pm)
  if p['confirmedStarterPath']:
   p['pathDisposition']='MAIN — CONFIRMED STARTER + SHARED DAMAGE LANE'
  elif any(r['directGoals']>0 or r['shotTypeOverlap'] or r['zoneOverlap'] for r in pm):
   p['pathDisposition']='ALT — EXACT DIRECT GOAL OR SHARED DAMAGE LANE'
  elif p['historicalAttempts']>0 or p['historicalGoals']>0:
   p['pathDisposition']='SHADOW — PLAYER EVENT HISTORY, MATCHUP NOT ESTABLISHED'
  else:
   p['pathDisposition']='WHO — INSUFFICIENT EVENT EVIDENCE'
  p['gateTrace']=[
   gate('G0','Game identity',status(bool(game.get('gameId'))),[f"gameId={game.get('gameId')}",f"gameType={game.get('gameType') or 'not supplied'}",f"matchup={game.get('awayAbbrev')} @ {game.get('homeAbbrev')}"]),
   gate('G1','Environment','PARTIAL — REST / VENUE ONLY',[str(game.get('venue') or 'venue unavailable'),str(team_context.get(p['team'],{}))],'Travel and arena conditions are not measured by the current feed.'),
   gate('G2','Availability / access',status(bool(p.get('playerId'))),[f"roster source={next((q.get('source') for q in ps if q['playerId']==p['playerId']), 'unknown')}"]),
   gate('G3','Opponent goalie vulnerability',status(any(m['shotsObserved']>0 for m in p['opposingGoalieMatches'])),[f"goalie profiles={sum(m['shotsObserved']>0 for m in p['opposingGoalieMatches'])}"]),
   gate('G4','Damage mechanism',status(bool(p['shotTypes'])),[f"player shot types={p['shotTypes']}",f"goal shot types={p['goalShotTypes']}"]),
   gate('G5','Direct matchup',status(any(m['directEvents']>0 for m in p['opposingGoalieMatches']) or any(r['shotTypeOverlap'] or r['zoneOverlap'] for r in pm)),[f"direct goals={sum(m['directGoals'] for m in p['opposingGoalieMatches'])}",f"direct events={sum(m['directEvents'] for m in p['opposingGoalieMatches'])}",f"shared lanes={sum(bool(r['shotTypeOverlap'] or r['zoneOverlap']) for r in pm)}"]),
   gate('G6','Opportunity / access','PENDING — deployment data unavailable',[p['position']]),
   gate('G7','Recurrence',status(bool(p['datesWithShots'])),[f"shot dates={len(p['datesWithShots'])}",f"goal dates={len(p['datesWithGoals'])}"]),
   gate('G8','Market fingerprint','NOT USED — no market shortcut',[]),
   gate('G9','Player × environment','PARTIAL — REST / VENUE ONLY',[str(team_context.get(p['team'],{}))],'Player-specific venue splits and travel effects are not inferred.'),
   gate('G10','Event route',status(bool(p['historicalShots'])),[f"observed shots={p['historicalShots']}",f"observed goals={p['historicalGoals']}"]),
   gate('G10.5','Recipient separation',status(bool(p['historicalGoals'] or p['historicalAssists'])),[f"finisher goals={p['historicalGoals']}",f"facilitator assists={p['historicalAssists']}" ]),
   gate('G11','Continuation',status(bool(p['datesWithGoals'] or p['datesWithShots'])),[f"recent recorded goal dates={p['datesWithGoals'][:5]}"]),
   gate('G12','Event ownership',status(bool(p['historicalGoals'] or p['historicalAssists'])),[f"goal events={p['historicalGoals']}",f"assist events={p['historicalAssists']}"]),
   gate('G14','WHO/anomaly',status(any('SHARED DAMAGE LANE' in r['pathFinding'] or 'DIRECT GOAL' in r['pathFinding'] for r in pm)),[r['pathFinding'] for r in pm]),
   gate('G15','Finisher protection','COMPARISON REQUIRED',[f"recipient role={p['recipientRole']}",f"goals={p['historicalGoals']}",f"assists={p['historicalAssists']}",'candidate route findings='+str(p['routeFindings'])],'Compare every candidate route; do not discard a finisher solely because another player has more assists.'),
   gate('G16','Final competition','CATEGORICAL — DIRECT EVIDENCE / SHARED LANE / WHO',[r['pathFinding'] for r in pm]),
   gate('G17','Contradiction audit','REVIEW REQUIRED' if any('CONTRADICTION CHECK' in r['pathFinding'] for r in pm) else 'CANDIDATE REVIEW — NO AUTOMATIC OVERRIDE',[f"goals={p['historicalGoals']}",f"assists={p['historicalAssists']}",f"goalie path findings={len(pm)}",str(p['routeFindings'])],'This flags evidence requiring review; it does not auto-eliminate a player or claim every tactical contradiction is resolved.'),
   gate('G18','Final audit','EVIDENCE TRACE COMPLETE',[f"playerId={p['playerId']}",f"gate count={len(GATES)}" ])]
 return {'game':game,'mode':mode,'runUTC':now(),'auditStatus':'GATE TRACE BUILT; VALIDATION DEPENDS ON SOURCE COVERAGE','sourceCoverage':{'candidateSkaters':len(sk),'homeRoster':len(hp),'awayRoster':len(ap),'currentPbpEvents':len(current),'currentDirectMatchups':len(direct_now),'historicalBundles':hist_n,'historicalEvents':hist_events,'retrievalErrors':len(errs),'playersWithObservedAttempts':len(route_candidates),'exactDirectPairsWithEvents':sum(1 for x in route_rows if x['directEvents']>0)},'gates':gates,'teamContext':team_context,'players':player_rows,'goalies':goalie_rows,'directMatchupAudit':route_rows,'routeCandidates':route_candidates,'currentDirectMatchups':direct_now,'dataErrors':errs,'historicalByTeam':{t:{'games':[b['game'] for b in x['bundles']],'events':len(x['events'])} for t,x in hist.items()}}
def run_slate(bundles,mode,history_limit=8):
 games=[analyze(b,mode,history_limit) for b in bundles]
 return {'runId':sid(now(),mode,len(games)),'runUTC':now(),'mode':mode,'gameCount':len(games),'games':games,'statement':'Full-slate hockey event-path analysis. Every active gate is traced in order; direct player/goalie identity is exact-ID only; no unsupported player, evidence, or numeric score is invented.'}
