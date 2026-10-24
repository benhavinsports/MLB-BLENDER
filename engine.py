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
def _seconds(value):
 if value is None:return None
 if isinstance(value,(int,float)):return int(value)
 parts=str(value).strip().split(':')
 try:
  if len(parts)==2:return int(parts[0])*60+int(parts[1])
  if len(parts)==3:return int(parts[0])*3600+int(parts[1])*60+int(parts[2])
 except ValueError:return None
 return None
def historical_usage(history, player_id):
 """Summarize historical official-boxscore TOI/PP usage without inferring tonight's deployment."""
 toi=[]; pp=[]; gp=0
 for team_hist in history.values():
  for b in team_hist.get('bundles',[]):
   pbg=((b.get('boxscore') or {}).get('playerByGameStats') or {}); found=False
   for side in ('home','away'):
    t=pbg.get(side+'Team') or {}
    for group in ('forwards','defense'):
     for player in t.get(group,[]) or []:
      pid=player.get('playerId') or player.get('id')
      if pid is None or int(pid)!=int(player_id):continue
      found=True
      for key in ('toi','timeOnIce','timeOnIcePerGame'):
       val=_seconds(player.get(key))
       if val is not None:toi.append(val);break
      for key in ('powerPlayToi','powerPlayTimeOnIce','ppToi'):
       val=_seconds(player.get(key))
       if val is not None:pp.append(val);break
   if found:gp+=1
 return {'gamesWithBoxscoreUsage':gp,'toiSecondsByGame':toi,'meanToiSeconds':round(sum(toi)/len(toi)) if toi else None,'powerPlayToiSecondsByGame':pp,'meanPowerPlayToiSeconds':round(sum(pp)/len(pp)) if pp else None,'evidenceSource':'official historical game boxscores' if gp else 'no matching historical boxscore usage found'}
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
 deployment=bundle.get('deployment') or {}; deployment_teams=deployment.get('teams') or {}
 deployment_by_id={}
 for tdata in deployment_teams.values():
  for assignment in tdata.get('rows',[]) or []:
   if assignment.get('playerId') is not None: deployment_by_id[int(assignment['playerId'])]=assignment
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
  usage=historical_usage(hist,p['playerId'])
  player_rows.append({'playerId':p['playerId'],'player':p['name'],'team':p['team'],'opponent':p['opponent'],'position':p['position'],'recipientRole':role,'historicalUsage':usage,'deploymentEvidence':deployment_by_id.get(int(p['playerId']),{}),'deploymentSourceStatus':(deployment_teams.get(p['team']) or {}).get('status','NOT SEARCHED'),'deploymentSource':(deployment_teams.get(p['team']) or {}).get('source'),'deploymentUnmatchedNames':(deployment_teams.get(p['team']) or {}).get('unmatchedNames',[]),**pr,'opposingGoalieMatches':matches,'recordId':sid(game.get('gameId'),p['playerId'],mode)})
 names={p['playerId']:p['name'] for p in ps}; direct_now=[]
 for e in current:
  if e.get('shooterId') and e.get('goalieId'):direct_now.append({'shooterId':e['shooterId'],'shooter':names.get(e['shooterId'],f"Player {e['shooterId']}"),'goalieId':e['goalieId'],'event':e.get('type'),'shotType':e.get('shotType','unknown'),'period':e.get('period'),'time':e.get('time'),'goal':isgoal(e)})
 hist_n=sum(len(x['bundles']) for x in hist.values()); hist_events=sum(len(x['events']) for x in hist.values())
 contradictions=[]
 ids=[p.get('playerId') for p in ps if p.get('playerId') is not None]
 duplicates=sorted(pid for pid,n in Counter(ids).items() if n>1)
 if duplicates: contradictions.append({'type':'duplicate_current_roster_player_id','playerIds':duplicates})
 if not hp or not ap: contradictions.append({'type':'incomplete_current_roster','homeRosterCount':len(hp),'awayRosterCount':len(ap)})
 if not sm.get('home',{}).get('starter') and not sm.get('away',{}).get('starter'): contradictions.append({'type':'starting_goalies_unconfirmed','detail':'Neither side has an explicitly identified starter.'})
 if not current: contradictions.append({'type':'current_game_event_feed_empty','detail':'May be expected pregame; not negative scoring evidence.'})
 if errs: contradictions.append({'type':'source_retrieval_errors','count':len(errs),'details':errs[:20]})
 for team in (home,away):
  if not hist[team]['bundles']: contradictions.append({'type':'historical_sample_missing','team':team})
 gates=[
 gate('G0','Game/slate lock',status(bool(game.get('gameId') and home and away)),[f"gameId={game.get('gameId')}",f'{away} @ {home}',f"state={game.get('gameState')}",f"gameType={game.get('gameType') or 'not supplied'}"]),
 gate('G1','Environment',status(any(team_context[t]['calendarDaysSinceLastGame'] is not None for t in (home,away))),[f"venue={game.get('venue') or 'not supplied'}",f'{home} rest context={team_context[home]}',f'{away} rest context={team_context[away]}'],'Rest interval is derived from retrieved completed-game dates; travel, weather, and arena conditions are not measured.'),
 gate('G2','Lineup/access', 'DEPLOYMENT FOUND — SOURCE/UNIT LABELLED' if any(x.get('rosterJoinCount',0) for x in deployment_teams.values()) else 'SEARCHED MULTIPLE WEB SOURCES — DEPLOYMENT NOT FOUND',[f'home roster={len(hp)}',f'away roster={len(ap)}',*[f'{t}: source={(deployment_teams.get(t) or {}).get("source")}; status={(deployment_teams.get(t) or {}).get("status")}; joined={(deployment_teams.get(t) or {}).get("rosterJoinCount",0)}' for t in (home,away)]], 'Only exact normalized full-name joins to official roster IDs are accepted. A published projected line is not represented as confirmed; PP assignment is recorded only when explicitly present.'),
 gate('G3','Opponent attack map',status(any(g['shotsObserved']>0 for g in goalie_rows)),[f'goalie candidates={len(goalie_rows)}',f'goalies with observed shots={sum(g["shotsObserved"]>0 for g in goalie_rows)}',f'historical games={hist_n}'],'Weakness evidence is restricted to observed NHL event IDs in retrieved history.'),
 gate('G4','Damage mechanism',status(any(p['historicalShots'] for p in player_rows)),[f'skaters={len(sk)}',f'players with observed shots={sum(p["historicalShots"]>0 for p in player_rows)}'],'Shot-type history is descriptive, not proof of tactical mechanism.'),
 gate('G5','Exact matchup alignment',status(any(m['directEvents'] or (set(p['goalShotTypes'])-{'unknown'}) & (set(m.get('goalsAgainstByShotType',{}))-{'unknown'}) or (set(p.get('goalZones',{}))-{'unknown'}) & (set(m.get('goalsAgainstByZone',{}))-{'unknown'}) for p in player_rows for m in p['opposingGoalieMatches'])),[f'exact player-ID × opposing-goalie-ID pairs={sum(len(p["opposingGoalieMatches"]) for p in player_rows)}',f'direct historical goals={sum(m["directGoals"] for p in player_rows for m in p["opposingGoalieMatches"])}'],'Exact IDs define the player and goalie profiles; a historical head-to-head goal is supporting evidence, not mandatory when the player scoring lane matches the goalie weakness.'),
 gate('G6','Opportunity/access','DEPLOYMENT PARTIALLY FOUND' if deployment_by_id else 'SEARCHED MULTIPLE WEB SOURCES — CURRENT DEPLOYMENT UNRESOLVED',[f'full available skater pool={len(sk)}',f'players joined to deployment source={len(deployment_by_id)}',f'players with explicit PP unit={sum(bool(x.get("powerPlayUnit")) for x in deployment_by_id.values())}',f'players with explicit even-strength line={sum(bool(x.get("line")) for x in deployment_by_id.values())}'],'Historical TOI remains context only. Source freshness and whether a row is projected versus confirmed remain explicit; absence is not a negative finding.'),
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
 gate('G17','Contradiction audit','CONTRADICTIONS FOUND' if contradictions else 'NO STRUCTURAL CONTRADICTIONS FOUND — TACTICAL AUDIT STILL REQUIRED',[f'retrieval errors={len(errs)}',f'candidate records={len(player_rows)}',* [str(c) for c in contradictions]],'Structural source/data problems are exposed explicitly; tactical contradictions still require evidence review.'),
 gate('G18','Final audit','NOT VALIDATED — REQUIRED GATES UNRESOLVED',[f'mode={mode}',f'runUTC={now()}',f'gates={len(GATES)}',f'players={len(player_rows)}',f'full player pool retained={len(player_rows)}','G6 deployment unresolved','G15 comparative finisher protection unresolved','G16 final competition unresolved','G17 tactical contradiction audit remains required'],'A complete trace is not a successful validation. No final path is certified while required evidence remains unresolved.')]
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
   # Compare the shooter's observed goal-producing lanes against this goalie's
   # observed conversion rates. A lane is called elevated only relative to this
   # goalie's own all-shot observed rate; no invented threshold or weights.
   overall_rate=m.get('saveRateObserved')
   overall_goal_rate=(m.get('goalsAgainstObserved',0)/m.get('shotsObserved',1)) if m.get('shotsObserved',0) else None
   elevated_types=[]; elevated_zones=[]
   for lane, stats in (m.get('shotTypeOutcomes') or {}).items():
    rate=stats.get('observedGoalRate')
    if lane in player_goal_types and lane!='unknown' and rate is not None and overall_goal_rate is not None and rate>overall_goal_rate:
     elevated_types.append({'lane':lane,'shotsFaced':stats.get('shotsFaced',0),'goalsAllowed':stats.get('goalsAllowed',0),'observedGoalRate':rate,'goalieOverallObservedGoalRate':round(overall_goal_rate,3)})
   for lane, stats in (m.get('zoneOutcomes') or {}).items():
    rate=stats.get('observedGoalRate')
    if lane in player_goal_zones and lane!='unknown' and rate is not None and overall_goal_rate is not None and rate>overall_goal_rate:
     elevated_zones.append({'lane':lane,'shotsFaced':stats.get('shotsFaced',0),'goalsAllowed':stats.get('goalsAllowed',0),'observedGoalRate':rate,'goalieOverallObservedGoalRate':round(overall_goal_rate,3)})
   elevated_type_names=[x['lane'] for x in elevated_types]
   elevated_zone_names=[x['lane'] for x in elevated_zones]
   # A direct goal and a population-level lane vulnerability are different
   # evidence types; preserve both and the denominator behind each rate.
   if m['directGoals']>0 and (elevated_type_names or elevated_zone_names):
    path='DIRECT GOAL + GOALIE-ELEVATED SHARED LANE'
   elif m['directGoals']>0:
    path='DIRECT GOAL HISTORY — ELEVATED LANE NOT ESTABLISHED'
   elif elevated_type_names or elevated_zone_names:
    path='GOALIE-ELEVATED SHARED LANE — DIRECT GOAL NOT OBSERVED'
   elif type_overlap or zone_overlap:
    path='SHARED LANE OBSERVED — NOT ELEVATED AGAINST GOALIE BASELINE'
   elif p['historicalShots'] and m['shotsObserved']:
    path='NO SHARED GOAL-PRODUCING LANE IN AVAILABLE SAMPLE'
   else:
    path='INSUFFICIENT COMPARABLE SAMPLE'
   route_rows.append({'playerId':p['playerId'],'player':p['player'],'team':p['team'],'opponent':p['opponent'],'position':p['position'],
    'playerHistoricalShotsOnGoal':p['historicalShots'],'playerHistoricalAttempts':p.get('historicalAttempts',0),'playerHistoricalGoals':p['historicalGoals'],'playerHistoricalAssists':p['historicalAssists'],'playerShotToGoalObserved':p['shotToGoalObserved'],'playerGoalGameCount':p['goalGameCount'],'playerShotTypes':p['shotTypes'],'playerGoalShotTypes':p['goalShotTypes'],
    'goalieId':m['goalieId'],'goalie':m['goalie'],'starterStatus':m['starterStatus'],'starterConfirmed':m['starterStatus']=='source explicitly marks starter','goalieShotsObserved':m['shotsObserved'],
    'goalieGoalsAllowedObserved':m['goalsAgainstObserved'],'goalieShotTypeOutcomes':m.get('shotTypeOutcomes',{}),'goalieZoneOutcomes':m.get('zoneOutcomes',{}),
    'shotTypeOverlap':type_overlap,'zoneOverlap':zone_overlap,
    'goalieElevatedSharedShotTypes':elevated_types,'goalieElevatedSharedZones':elevated_zones,
    'goalieOverallObservedGoalRate':round(overall_goal_rate,3) if overall_goal_rate is not None else None,
    'pathFinding':path,
    'directEvents':m['directEvents'],'directGoals':m['directGoals'],'directSampleNote':('Direct sample is limited; interpret descriptively.' if m['directEvents'] < 3 else 'Direct sample includes at least three recorded events.'),'directShotTypes':m['directShotTypes'],'directGoalShotTypes':m['directGoalShotTypes'],
    'directZones':m['directZones'],'directGoalZones':m['directGoalZones'],'directDates':m['directDates']})
 route_candidates=[p for p in player_rows if p['historicalShots']>0 or p['historicalGoals']>0]
 # Establish evidence classes for the entire pool before any candidate-to-candidate comparison.
 for p in player_rows:
  pm0=[r for r in route_rows if r['playerId']==p['playerId']]
  p['evidencePathClass'] = (
   'STARTER + SHARED LANE EVIDENCE' if any(r['starterConfirmed'] and (r['shotTypeOverlap'] or r['zoneOverlap']) for r in pm0) else
   'DIRECT GOAL OR SHARED LANE EVIDENCE' if any(r['directGoals']>0 or r['shotTypeOverlap'] or r['zoneOverlap'] for r in pm0) else
   'PLAYER HISTORY ONLY' if p['historicalAttempts']>0 or p['historicalGoals']>0 else
   'INSUFFICIENT EVENT EVIDENCE')
 # Candidate-level, ordered gate trace: this is evidence progression, not a numeric ranking.
 for p in player_rows:
  pm=[r for r in route_rows if r['playerId']==p['playerId']]
  p['routeFindings']=[r['pathFinding'] for r in pm]
  p['confirmedStarterPath']=any(r['starterStatus']=='source explicitly marks starter' and bool(r['shotTypeOverlap'] or r['zoneOverlap']) for r in pm)
  p['opposingStarterDirectGoals']=sum(r['directGoals'] for r in pm if r['starterStatus']=='source explicitly marks starter')
  p['sharedDamageLaneCount']=sum(bool(r['shotTypeOverlap'] or r['zoneOverlap']) for r in pm)
  p['exactDirectGoalCount']=sum(r['directGoals'] for r in pm)
  # A matchup overlap is evidence, not a completed route. G6 deployment is not
  # currently sourced by this adapter, so do not promote anyone to a final path.
  p['evidencePathClass'] = (
   'STARTER + SHARED LANE EVIDENCE' if p['confirmedStarterPath'] else
   'DIRECT GOAL OR SHARED LANE EVIDENCE' if any(r['directGoals']>0 or r['shotTypeOverlap'] or r['zoneOverlap'] for r in pm) else
   'PLAYER HISTORY ONLY' if p['historicalAttempts']>0 or p['historicalGoals']>0 else
   'INSUFFICIENT EVENT EVIDENCE')
  p['pathDisposition'] = 'UNRESOLVED — DEPLOYMENT / FULL-GATE VALIDATION REQUIRED'
  p['finisherProtectionAudit'] = {
   'role': p['recipientRole'],
   'goals': p['historicalGoals'],
   'assists': p['historicalAssists'],
   'evidencePathClass': p['evidencePathClass'],
   'comparedAgainstPlayerIds': [q['playerId'] for q in player_rows if q['team'] == p['team'] and q['playerId'] != p['playerId']],
   'decision': 'NO DISPLACEMENT — comparative paths are not fully validated'
  }
  p['finalCompetition'] = {
   'competingPathClasses': sorted({q['evidencePathClass'] for q in player_rows if q['opponent'] == p['opponent']}),
   'decision': 'UNRESOLVED — G6 deployment and complete contradiction review are missing',
   'numericScoreUsed': False
  }
  p['gateTrace']=[
   gate('G0','Game identity',status(bool(game.get('gameId'))),[f"gameId={game.get('gameId')}",f"gameType={game.get('gameType') or 'not supplied'}",f"matchup={game.get('awayAbbrev')} @ {game.get('homeAbbrev')}"]),
   gate('G1','Environment','PARTIAL — REST / VENUE ONLY',[str(game.get('venue') or 'venue unavailable'),str(team_context.get(p['team'],{}))],'Travel and arena conditions are not measured by the current feed.'),
   gate('G2','Availability / access',status(bool(p.get('playerId'))),[f"roster source={next((q.get('source') for q in ps if q['playerId']==p['playerId']), 'unknown')}"]),
   gate('G3','Opponent goalie vulnerability',status(any(m['shotsObserved']>0 for m in p['opposingGoalieMatches'])),[f"goalie profiles={sum(m['shotsObserved']>0 for m in p['opposingGoalieMatches'])}"]),
   gate('G4','Damage mechanism',status(bool(p['shotTypes'])),[f"player shot types={p['shotTypes']}",f"goal shot types={p['goalShotTypes']}"]),
   gate('G5','Direct matchup',status(any(m['directEvents']>0 for m in p['opposingGoalieMatches']) or any(r['shotTypeOverlap'] or r['zoneOverlap'] for r in pm)),[f"direct goals={sum(m['directGoals'] for m in p['opposingGoalieMatches'])}",f"direct events={sum(m['directEvents'] for m in p['opposingGoalieMatches'])}",f"shared lanes={sum(bool(r['shotTypeOverlap'] or r['zoneOverlap']) for r in pm)}"]),
   gate('G6','Opportunity / access','EXPLICIT LINE/PP DEPLOYMENT FOUND' if p.get('deploymentEvidence') and (p['deploymentEvidence'].get('line') or p['deploymentEvidence'].get('powerPlayUnit')) else ('SEARCHED SOURCES — PLAYER DEPLOYMENT NOT FOUND' if p.get('deploymentSourceStatus') else 'UNRESOLVED — deployment data unavailable'),[f"position={p['position']}",f"deployment source={p.get('deploymentSource')}",f"line={((p.get('deploymentEvidence') or {}).get('line'))}",f"PP unit={((p.get('deploymentEvidence') or {}).get('powerPlayUnit'))}",f"historical boxscore games={p.get('historicalUsage',{}).get('gamesWithBoxscoreUsage',0)}",f"mean historical TOI seconds={p.get('historicalUsage',{}).get('meanToiSeconds')}"],'Historical TOI is context only. Projected source data remains projected; absence is not a negative finding.'),
   gate('G7','Recurrence',status(bool(p['datesWithShots'])),[f"shot dates={len(p['datesWithShots'])}",f"goal dates={len(p['datesWithGoals'])}"]),
   gate('G8','Market fingerprint','NOT USED — no market shortcut',[]),
   gate('G9','Player × environment','PARTIAL — REST / VENUE ONLY',[str(team_context.get(p['team'],{}))],'Player-specific venue splits and travel effects are not inferred.'),
   gate('G10','Event route',status(bool(p['historicalShots'])),[f"observed shots={p['historicalShots']}",f"observed goals={p['historicalGoals']}"]),
   gate('G10.5','Recipient separation',status(bool(p['historicalGoals'] or p['historicalAssists'])),[f"finisher goals={p['historicalGoals']}",f"facilitator assists={p['historicalAssists']}" ]),
   gate('G11','Continuation',status(bool(p['datesWithGoals'] or p['datesWithShots'])),[f"recent recorded goal dates={p['datesWithGoals'][:5]}"]),
   gate('G12','Event ownership',status(bool(p['historicalGoals'] or p['historicalAssists'])),[f"goal events={p['historicalGoals']}",f"assist events={p['historicalAssists']}"]),
   gate('G14','WHO/anomaly',status(any('SHARED DAMAGE LANE' in r['pathFinding'] or 'DIRECT GOAL' in r['pathFinding'] for r in pm)),[r['pathFinding'] for r in pm]),
   gate('G15','Finisher protection','UNRESOLVED — COMPARATIVE PATHS INCOMPLETE',[f"recipient role={p['recipientRole']}",f"goals={p['historicalGoals']}",f"assists={p['historicalAssists']}",f"evidence path={p['evidencePathClass']}",f"same-team competitors={p['finisherProtectionAudit']['comparedAgainstPlayerIds']}",p['finisherProtectionAudit']['decision']],'The engine records all same-team competitors and protects against automatic displacement, but cannot finish comparison without verified deployment and complete gate evidence.'),
   gate('G16','Final competition','UNRESOLVED — NO FORCED WINNER',[f"candidate evidence class={p['evidencePathClass']}",f"competing classes={p['finalCompetition']['competingPathClasses']}",p['finalCompetition']['decision']],'Competition is recorded categorically; a final disposition is withheld while required gates are unresolved.'),
   gate('G17','Contradiction audit','REVIEW REQUIRED' if any('CONTRADICTION CHECK' in r['pathFinding'] for r in pm) else 'CANDIDATE REVIEW — NO AUTOMATIC OVERRIDE',[f"goals={p['historicalGoals']}",f"assists={p['historicalAssists']}",f"goalie path findings={len(pm)}",str(p['routeFindings'])],'This flags evidence requiring review; it does not auto-eliminate a player or claim every tactical contradiction is resolved.'),
   gate('G18','Final audit','NOT VALIDATED — REQUIRED GATES UNRESOLVED',[f"playerId={p['playerId']}",f"gate count={len(GATES)}",f"path class={p['evidencePathClass']}",'G6 current deployment unresolved','G15 comparison incomplete','G16 competition unresolved'],'A trace is not a pass. This record is not eligible for a final player-path designation until required evidence and contradictions are resolved.')]
 # Real comparative output: compare every same-game candidate's observed
 # route dimensions without assigning a synthetic score or forcing a winner.
 route_comparisons=[]
 for team in (home,away):
  team_players=[p for p in player_rows if p['team']==team]
  for idx,a in enumerate(team_players):
   for b in team_players[idx+1:]:
    ar=[r for r in route_rows if r['playerId']==a['playerId']]
    br=[r for r in route_rows if r['playerId']==b['playerId']]
    def dims(rows):
     return {
      'directGoalsAgainstListedOpposingGoalies':sum(r['directGoals'] for r in rows),
      'goalieElevatedShotTypeLanes':sorted({x['lane'] for r in rows for x in r.get('goalieElevatedSharedShotTypes',[])}),
      'goalieElevatedScoringZones':sorted({x['lane'] for r in rows for x in r.get('goalieElevatedSharedZones',[])}),
      'confirmedStarterSharedLane':any(r.get('starterConfirmed') and (r.get('goalieElevatedSharedShotTypes') or r.get('goalieElevatedSharedZones')) for r in rows),
      'historicalGoalGames':a['goalGameCount'] if rows is ar else b['goalGameCount'],
      'historicalAttempts':a['historicalAttempts'] if rows is ar else b['historicalAttempts'],
      'historicalGoals':a['historicalGoals'] if rows is ar else b['historicalGoals'],
      'historicalAssists':a['historicalAssists'] if rows is ar else b['historicalAssists']}
    ad,bd=dims(ar),dims(br)
    advantages_a=[]; advantages_b=[]
    for key in ('directGoalsAgainstListedOpposingGoalies','historicalGoalGames','historicalGoals'):
     if ad[key]>bd[key]: advantages_a.append(key)
     elif bd[key]>ad[key]: advantages_b.append(key)
    for key in ('confirmedStarterSharedLane',):
     if ad[key] and not bd[key]: advantages_a.append(key)
     elif bd[key] and not ad[key]: advantages_b.append(key)
    # This is a comparison of observed dimensions, not an aggregate rank.
    decision='A HAS DISTINCT OBSERVED ADVANTAGES' if advantages_a and not advantages_b else ('B HAS DISTINCT OBSERVED ADVANTAGES' if advantages_b and not advantages_a else ('MIXED EVIDENCE — CARRY BOTH' if advantages_a and advantages_b else 'NO EVIDENCE-BASED SEPARATION'))
    route_comparisons.append({'team':team,'playerA':{'playerId':a['playerId'],'player':a['player'],'dimensions':ad,'distinctAdvantages':advantages_a},'playerB':{'playerId':b['playerId'],'player':b['player'],'dimensions':bd,'distinctAdvantages':advantages_b},'comparison':decision,'numericScoreUsed':False,'note':"Comparisons are descriptive and bounded by available historical event samples; they do not establish tonight's deployment."})
 return {'game':game,'mode':mode,'runUTC':now(),'auditStatus':'ANALYSIS COMPLETE — EVIDENCE PATHS AND PAIRWISE COMPARISONS GENERATED; LIVE DEPLOYMENT STILL SOURCE-DEPENDENT','sourceCoverage':{'candidateSkaters':len(sk),'homeRoster':len(hp),'awayRoster':len(ap),'currentPbpEvents':len(current),'currentDirectMatchups':len(direct_now),'historicalBundles':hist_n,'historicalEvents':hist_events,'retrievalErrors':len(errs),'playersWithObservedAttempts':len(route_candidates),'exactDirectPairsWithEvents':sum(1 for x in route_rows if x['directEvents']>0)},'gates':gates,'teamContext':team_context,'players':player_rows,'goalies':goalie_rows,'directMatchupAudit':route_rows,'routeComparisons':route_comparisons,'routeCandidates':route_candidates,'currentDirectMatchups':direct_now,'deploymentSourceSearch':{team:{'source':x.get('source'),'status':x.get('status'),'joined':x.get('rosterJoinCount',0),'sourceDate':(x.get('sourceMeta') or {}).get('sourceDate'),'lineEvidenceFound':(x.get('sourceMeta') or {}).get('lineEvidenceFound'),'powerPlayEvidenceFound':(x.get('sourceMeta') or {}).get('powerPlayEvidenceFound'),'unmatchedNames':x.get('unmatchedNames',[]),'attempts':x.get('sourceMeta',{}).get('attempts',[])} for team,x in deployment_teams.items()},'dataErrors':errs,'contradictions':contradictions,'historicalByTeam':{t:{'games':[b['game'] for b in x['bundles']],'events':len(x['events'])} for t,x in hist.items()}}
def _blocking_contradictions(report):
    """Only source/data contradictions that invalidate identity or evidence block a lock.

    An empty live play feed is normal before puck drop and is intentionally not a blocker.
    """
    blocking = {
        'duplicate_current_roster_player_id',
        'incomplete_current_roster',
        'starting_goalies_unconfirmed',
        'source_retrieval_errors',
        'historical_sample_missing',
    }
    return [c for c in (report.get('contradictions') or []) if c.get('type') in blocking]


def _candidate_lock_reasons(player, report):
    reasons = []
    dep = player.get('deploymentEvidence') or {}
    if not (dep.get('line') or dep.get('powerPlayUnit')):
        reasons.append('current line/PP deployment not explicitly sourced')
    if not player.get('confirmedStarterPath'):
        reasons.append('no shared damage lane against an explicitly confirmed opposing starter')
    if not (player.get('opposingStarterDirectGoals', 0) > 0 or player.get('confirmedStarterPath')):
        reasons.append('no direct-goal or confirmed-starter shared-lane path')
    fp = player.get('finisherProtectionAudit') or {}
    if str(fp.get('decision', '')).startswith('REVIEW'):
        reasons.append('finisher protection has an unresolved stronger-path comparator')
    if _blocking_contradictions(report):
        reasons.append('blocking source/data contradiction exists')
    return reasons


def run_slate(bundles, mode, history_limit=8):
    """Run the full pregame slate, evaluate G18 candidates, then derive Core output.

    No candidate is locked just for having a path. A game produces a lock only when
    exactly one candidate satisfies the explicit deployment, confirmed-starter lane,
    finisher-protection, and source-integrity checks. Multiple eligible candidates
    remain unresolved; the engine never picks one by name, odds, or numeric score.
    """
    pregame_states = {'FUT', 'PRE', 'SCHEDULED', 'PREGAME', 'FUTURE'}
    analyzed, excluded = [], []
    for bundle in bundles:
        game = bundle.get('game') or {}
        state = str(game.get('gameState') or game.get('gameScheduleState') or 'UNKNOWN').upper()
        if state not in pregame_states:
            excluded.append({
                'gameId': game.get('gameId'),
                'matchup': f"{game.get('awayAbbrev', 'AWAY')} @ {game.get('homeAbbrev', 'HOME')}",
                'gameState': state,
                'reason': 'Excluded from pregame Blender: game is not explicitly in a scheduled/pregame state.'
            })
            continue
        analyzed.append(bundle)

    games = [analyze(bundle, mode, history_limit) for bundle in analyzed]
    locked = []
    unresolved_candidates = []
    for report in games:
        game = report.get('game') or {}
        game_id = game.get('gameId')
        players = report.get('players', [])
        eligible = []
        for player in players:
            reasons = _candidate_lock_reasons(player, report)
            if not reasons:
                eligible.append(player)
            else:
                unresolved_candidates.append({
                    'gameId': game_id, 'playerId': player.get('playerId'),
                    'player': player.get('player'), 'reasons': reasons
                })
        # Ambiguity means no lock for this game. Never select a convenient name.
        if len(eligible) == 1:
            player = eligible[0]
            trace = player.get('gateTrace') or []
            if trace and trace[-1].get('gate') == 'G18':
                trace[-1]['status'] = 'LOCKED — G18 FINAL AUDIT PASSED'
                trace[-1]['evidence'] = list(trace[-1].get('evidence') or []) + [
                    'Unique eligible candidate in this game after deployment, starter-lane, finisher-protection, and source-integrity checks.'
                ]
                trace[-1]['limitation'] = 'Lock is conditional on the retrieved pregame sources; it is not a guarantee of a goal.'
            player['pathDisposition'] = 'LOCKED — G18 FINAL AUDIT PASSED'
            locked.append({
                'gameId': game_id,
                'matchup': f"{game.get('awayAbbrev', 'AWAY')} @ {game.get('homeAbbrev', 'HOME')}",
                'playerId': player.get('playerId'), 'player': player.get('player'),
                'team': player.get('team'), 'opponent': player.get('opponent'),
                'pathDisposition': player['pathDisposition'], 'gateTrace': trace,
            })
        elif len(eligible) > 1:
            report.setdefault('finalSlateAudit', {})['status'] = 'UNRESOLVED — MULTIPLE CANDIDATES PASSED INDIVIDUAL CHECKS'
            report['finalSlateAudit']['eligiblePlayerIds'] = [p.get('playerId') for p in eligible]
            report['finalSlateAudit']['reason'] = 'No arbitrary tie-breaker or numeric score is allowed.'
        else:
            report.setdefault('finalSlateAudit', {})['status'] = 'NO G18 LOCK — NO CANDIDATE PASSED ALL REQUIRED CHECKS'

    # Core output uses only actual G18 locks, one per distinct game. If more than
    # three games qualify, preserve all locks and mark Core selection unresolved
    # rather than silently selecting by source order or inventing a ranking.
    by_game = defaultdict(list)
    for player in locked:
        by_game[player.get('gameId')].append(player)
    unique_locks = [v[0] for v in by_game.values() if len(v) == 1]
    ambiguous_game_ids = [gid for gid, v in by_game.items() if len(v) != 1]
    if len(unique_locks) == 3 and not ambiguous_game_ids:
        core = unique_locks
        core_status = 'CORE 3 — THREE DISTINCT G18-LOCKED GAMES'
    elif len(unique_locks) == 2 and not ambiguous_game_ids:
        core = unique_locks
        core_status = 'CORE 2 — TWO DISTINCT G18-LOCKED GAMES'
    elif len(unique_locks) > 3:
        core = []
        core_status = 'CORE SELECTION UNRESOLVED — MORE THAN THREE VALID GAME LOCKS; NO ARBITRARY TRUNCATION'
    elif len(unique_locks) == 1:
        core = unique_locks
        core_status = 'NO VALID CORE — ONLY ONE G18-LOCKED SURVIVOR'
    else:
        core = unique_locks
        core_status = 'NO VALID CORE — ZERO G18-LOCKED SURVIVORS'

    certified = len(core) in (2, 3) and not ambiguous_game_ids
    unresolved = sum(1 for r in games for p in r.get('players', [])
                     if not str(p.get('pathDisposition', '')).upper().startswith('LOCKED'))
    return {
        'runId': sid(now(), mode, len(games)), 'runUTC': now(), 'mode': mode,
        'gameCount': len(games), 'games': games, 'excludedGames': excluded,
        'coreOutput': {
            'status': core_status, 'core': core,
            'lockedSurvivorCount': len(locked), 'ambiguousGameIds': ambiguous_game_ids,
            'unresolvedCandidates': unresolved_candidates,
            'rule': 'Only explicit G18 locks qualify; at most one player per distinct game; no forced slots, numeric ranking, or arbitrary truncation.'
        },
        'validationSummary': {
            'status': 'VALIDATED — EXPLICIT G18 LOCKS ONLY' if certified else (
                'NO PRE-GAME GAMES ELIGIBLE — SLATE NOT VALIDATED' if excluded and not games else
                'NO GAMES RETURNED — SLATE NOT VALIDATED' if not games else
                'NOT VALIDATED — REQUIRED PLAYER PATHS OR CORE SELECTION UNRESOLVED'),
            'gamesWithErrors': sum(bool(g.get('dataErrors')) for g in games),
            'playersRetained': sum(len(g.get('players', [])) for g in games),
            'playersWithUnresolvedFinalAudit': unresolved,
            'excludedNonPregameGames': len(excluded),
            'requiredUnresolvedAreas': [] if certified else [
                'G2 projected/confirmed line and PP deployment freshness/status',
                'G6 current deployment / line access', 'G15 finisher protection comparison',
                'G16 final competition', 'G17 full tactical contradiction review',
                'unambiguous game-level candidate and Core selection'],
            'finalPlayerPathsCertified': certified,
        },
        'statement': 'Full-slate pregame hockey event-path audit. Live/completed games are excluded. Core is derived only from explicit G18 locks; no unsupported player, evidence, or numeric score is invented.'
    }
