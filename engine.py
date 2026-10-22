from __future__ import annotations
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
from nhl_data import events,roster,starters,get_history,players_from
from shiftchart_sources import fetch_shiftchart, summarize_player_shifts, summarize_shift_overlap, summarize_goal_shift_context, compare_deployment_to_goal_context
from market_sources import fetch_market_fingerprint, market_record_integrity
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
def audit_source_contradictions(players, deployment_teams, goalie_rows, retrieval_errors=None):
 """Detect objective identity/deployment/starter conflicts without guessing a resolution."""
 findings=[]
 ids=[int(p['playerId']) for p in players if p.get('playerId') is not None]
 duplicates=sorted(pid for pid,n in Counter(ids).items() if n>1)
 if duplicates:
  findings.append({'type':'duplicate_current_roster_player_id','playerIds':duplicates})
 for team, data in (deployment_teams or {}).items():
  rows=(data or {}).get('rows') or []
  by_id=defaultdict(list)
  for row in rows:
   if row.get('playerId') is not None:
    by_id[int(row['playerId'])].append(row)
  for pid, assignments in by_id.items():
   signatures={(r.get('line'),r.get('powerPlayUnit')) for r in assignments}
   if len(signatures)>1:
    findings.append({'type':'conflicting_deployment_assignments','team':team,'playerId':pid,
      'assignments':[{'line':r.get('line'),'powerPlayUnit':r.get('powerPlayUnit'),'sources':r.get('sources',[]),'conflicts':r.get('conflicts',[])} for r in assignments]})
   elif len(assignments)>1:
    # Duplicate rows are reported even if they agree; the consumer can inspect provenance.
    findings.append({'type':'duplicate_deployment_records','team':team,'playerId':pid,'recordCount':len(assignments)})
 for team in sorted({g.get('team') for g in (goalie_rows or []) if g.get('team')}):
  marked=[g for g in goalie_rows if g.get('team')==team and g.get('starterStatus')=='source explicitly marks starter']
  if len(marked)>1:
   findings.append({'type':'multiple_goalies_marked_starter','team':team,'goalieIds':[g.get('goalieId') for g in marked]})
 if retrieval_errors:
  findings.append({'type':'source_retrieval_errors','count':len(retrieval_errors),'details':list(retrieval_errors)[:20]})
 return findings

def final_gate_blockers(player, route_rows, player_rows, contradictions, mode):
 """Return explicit evidence blockers; never infer a lock from a populated trace."""
 blockers=[]
 deployment=player.get('deploymentEvidence') or {}
 # Every active gate that remains explicitly incomplete must block G18. This is
 # intentionally not a scoring system: unavailable evidence is a blocker, not a zero.
 if not (deployment.get('line') or deployment.get('powerPlayUnit')):
  blockers.append({'gate':'G6','reason':'No exact-ID-joined current line or PP deployment evidence'})
 if mode=='confirmed' and deployment.get('deploymentStatus')!='CONFIRMED':
  blockers.append({'gate':'G2/G6','reason':'Current deployment is not explicitly confirmed'})
 if not player.get('confirmedStarterPath'):
  blockers.append({'gate':'G3/G5','reason':'No confirmed-starter plus shared scoring-lane path'})
 if not player.get('historicalSampleAvailable'):
  blockers.append({'gate':'G4/G10','reason':'Historical play-by-play sample unavailable; zero counts cannot be interpreted as observed zero production'}); blockers.append({'gate':'G7/G11','reason':'Goal-date recurrence cannot be evaluated without a historical play-by-play sample'}); blockers.append({'gate':'G10.5/G12','reason':'Finisher/event-ownership evidence cannot be evaluated without a historical play-by-play sample'})
 elif not player.get('historicalGoals'):
  blockers.append({'gate':'G10.5/G12','reason':'Historical sample retrieved, but no recorded goal as finisher in that sample'})
 if player.get('historicalSampleAvailable') and not player.get('datesWithGoals'):
  blockers.append({'gate':'G7/G11','reason':'Historical sample retrieved, but no recorded historical goal-date recurrence'})
 g15_decision=(player.get('finisherProtectionAudit') or {}).get('decision','')
 if g15_decision != 'COMPARISON COMPLETE — DISTINCT EVIDENCE ADVANTAGE':
  blockers.append({'gate':'G15','reason':'Same-team finisher comparison has not established a distinct evidence advantage','decision':g15_decision or 'MISSING DECISION'})
 g16_decision=(player.get('finalCompetition') or {}).get('decision','')
 if g16_decision != 'COMPETITION COMPLETE — DISTINCT EVIDENCE ADVANTAGE':
  blockers.append({'gate':'G16','reason':'Cross-candidate competition has not established a distinct evidence advantage','decision':g16_decision or 'MISSING DECISION'})
 # G8 accepts only exact player-level anytime-goal market records. Market odds
 # remain contextual evidence and never rank candidates or become a score.
 market = player.get('marketFingerprint') or []
 market_integrity = market_record_integrity(market)
 player['marketFingerprintIntegrity'] = market_integrity
 if not market:
  blockers.append({'gate':'G8','reason':'No exact player-level anytime-goal market record retrieved; gate remains pending'})
 elif not market_integrity.get('usableRecordCount'):
  blockers.append({'gate':'G8','reason':'Player market rows lack a valid American price plus parseable provider update timestamp'})
 env_split = player.get('homeAwayEnvironmentSplit') or {}
 if not env_split.get('comparativeSampleAvailable'):
  blockers.append({'gate':'G9','reason':'Player-specific home/away environment comparison lacks samples on both sides'})
 structural_types={
  'duplicate_current_roster_player_id','incomplete_current_roster',
  'starting_goalies_unconfirmed','multiple_goalies_marked_starter',
  'conflicting_deployment_assignments','duplicate_deployment_records',
  'source_retrieval_errors'
 }
 structural=[c for c in contradictions if c.get('type') in structural_types]
 if structural:
  blockers.append({'gate':'G17','reason':'Game-level structural/source contradiction remains','findingTypes':sorted({c.get('type') for c in structural})})
 if any('CONTRADICTION CHECK' in str(x) for x in player.get('routeFindings',[])):
  blockers.append({'gate':'G17','reason':'Player route has a contradiction-review flag'})
 if not any(b['gate']=='G17' for b in blockers):
  blockers.append({'gate':'G17','reason':'Manual/structured tactical contradiction audit has not been certified'})
 return blockers
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
 market_audit=fetch_market_fingerprint(game, sk)
 market_by_id=market_audit.get('records') or {}
 current=events(bundle.get('plays')); sm=starters(box); hist={}; goalie_rows=[]
 for team in (home,away):
  hb,he=get_history(team,date,limit); errs.extend(he); ev=[]; names={}
  for b in hb:
   for x in events(b.get('plays')):x['date']=b['game'].get('gameDate');x['gameId']=b['game'].get('gameId');ev.append(x)
   for side in ('home','away'):
    for p in players_from(b.get('landing'),side,'history'):names[p['playerId']]=p['name']
  # Retrieve the last three completed shift charts as historical deployment evidence.
  # This supports opportunity/usage context but must never be relabelled as tonight's lineup.
  shift_rows=[]; shift_audit=[]
  recent_bundles=sorted(hb,key=lambda b:(b.get('game') or {}).get('gameDate',''),reverse=True)[:3]
  for historical_bundle in recent_bundles:
   historical_game=historical_bundle.get('game') or {}; historical_id=historical_game.get('gameId')
   if not historical_id: continue
   rows_shift, audit_shift=fetch_shiftchart(historical_id)
   shift_rows.extend(rows_shift); shift_audit.append(audit_shift)
  hist[team]={'bundles':hb,'events':ev,'names':names,'shiftRows':shift_rows,'shiftChartAudit':shift_audit,'shiftOverlap':summarize_shift_overlap(shift_rows),'goalShiftContext':summarize_goal_shift_context(shift_rows, ev)}
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
  ev=hist[p['team']]['events']; pr=player_hist(ev,p['playerId']); pr['historicalSampleAvailable']=bool(hist[p['team']]['bundles'] and ev); pr['historicalGamesRetrieved']=len(hist[p['team']]['bundles']); pr['historicalPlayByPlayEventsRetrieved']=len(ev); matches=[]
  for goalie in byteam[p['opponent']]:
   matches.append({**goalie,**direct(ev,p['playerId'],goalie['goalieId'])})
  role=('FINISHER + FACILITATOR' if pr['historicalGoals'] and pr['historicalAssists'] else ('FINISHER' if pr['historicalGoals'] else ('FACILITATOR' if pr['historicalAssists'] else 'NO RECORDED GOAL INVOLVEMENT')))
  usage=historical_usage(hist,p['playerId'])
  shift_usage=summarize_player_shifts(hist[p['team']].get('shiftRows',[]),p['playerId'])
  overlap_summary=summarize_shift_overlap(hist[p['team']].get('shiftRows',[]),p['playerId'])
  goal_shift_context=hist[p['team']].get('goalShiftContext') or {}
  goal_shift_player_context=next((x for x in goal_shift_context.get('teammateGoalContext',[]) if int(x.get('playerId') or 0)==int(p['playerId'])),None)
  deployment_goal_context=compare_deployment_to_goal_context(goal_shift_context, list(deployment_by_id.values()), p['playerId'])
  # Player-specific venue split from official historical game/event records.
  venue_games={'home':set(),'away':set()}; venue_shots={'home':0,'away':0}; venue_goals={'home':0,'away':0}
  team_hist_bundles={int((b.get('game') or {}).get('gameId') or 0):b for b in hist[p['team']]['bundles'] if (b.get('game') or {}).get('gameId')}
  # Denominator is games the player actually appeared in, not games with a shot;
  # this avoids inflating per-game rates by dropping zero-shot appearances.
  for gid, hist_bundle in team_hist_bundles.items():
   hist_game=hist_bundle.get('game') or {}
   venue='home' if hist_game.get('homeAbbrev')==p['team'] else ('away' if hist_game.get('awayAbbrev')==p['team'] else None)
   if not venue: continue
   pbg=((hist_bundle.get('boxscore') or {}).get('playerByGameStats') or {})
   appeared=False
   for hist_side in ('home','away'):
    team_box=pbg.get(hist_side+'Team') or {}
    for group in ('forwards','defense'):
     for hist_player in team_box.get(group,[]) or []:
      pid=hist_player.get('playerId') or hist_player.get('id')
      if pid is not None and int(pid)==int(p['playerId']): appeared=True; break
     if appeared: break
    if appeared: break
   if appeared: venue_games[venue].add(gid)
  for h_event in ev:
   gid=int(h_event.get('gameId') or 0); hist_bundle=team_hist_bundles.get(gid); hist_game=(hist_bundle or {}).get('game') or {}
   venue='home' if hist_game.get('homeAbbrev')==p['team'] else ('away' if hist_game.get('awayAbbrev')==p['team'] else None)
   if not venue or gid not in venue_games[venue] or h_event.get('shooterId')!=p['playerId']: continue
   if is_on_goal(h_event): venue_shots[venue]+=1
   if isgoal(h_event): venue_goals[venue]+=1
  venue_split={'upcomingVenue':'home' if p['team']==home else 'away','games':{side:len(venue_games[side]) for side in ('home','away')},'shotsOnGoal':dict(venue_shots),'goals':dict(venue_goals),'shotsOnGoalPerGame':{side:round(venue_shots[side]/len(venue_games[side]),3) if venue_games[side] else None for side in ('home','away')},'goalsPerGame':{side:round(venue_goals[side]/len(venue_games[side]),3) if venue_games[side] else None for side in ('home','away')},'comparativeSampleAvailable':bool(venue_games['home'] and venue_games['away']),'source':'official historical NHL play-by-play joined to game IDs'}
  player_rows.append({'playerId':p['playerId'],'player':p['name'],'team':p['team'],'opponent':p['opponent'],'position':p['position'],'recipientRole':role,'historicalUsage':usage,'historicalShiftUsage':shift_usage,'historicalShiftOverlap':overlap_summary,'historicalGoalShiftContext':goal_shift_player_context,'deploymentHistoricalGoalContext':deployment_goal_context,'homeAwayEnvironmentSplit':venue_split,'marketFingerprint':(market_by_id.get(str(p['playerId'])) or {}).get('outcomes',[]),'marketFingerprintIntegrity':market_record_integrity((market_by_id.get(str(p['playerId'])) or {}).get('outcomes',[])),'deploymentEvidence':deployment_by_id.get(int(p['playerId']),{}),'deploymentSourceStatus':(deployment_teams.get(p['team']) or {}).get('status','NOT SEARCHED'),'deploymentSource':(deployment_teams.get(p['team']) or {}).get('source'),'deploymentUnmatchedNames':(deployment_teams.get(p['team']) or {}).get('unmatchedNames',[]),**pr,'opposingGoalieMatches':matches,'recordId':sid(game.get('gameId'),p['playerId'],mode)})
 names={p['playerId']:p['name'] for p in ps}; direct_now=[]
 for e in current:
  if e.get('shooterId') and e.get('goalieId'):direct_now.append({'shooterId':e['shooterId'],'shooter':names.get(e['shooterId'],f"Player {e['shooterId']}"),'goalieId':e['goalieId'],'event':e.get('type'),'shotType':e.get('shotType','unknown'),'period':e.get('period'),'time':e.get('time'),'goal':isgoal(e)})
 hist_n=sum(len(x['bundles']) for x in hist.values()); hist_events=sum(len(x['events']) for x in hist.values())
 contradictions=audit_source_contradictions(ps, deployment_teams, goalie_rows, errs)
 if not hp or not ap: contradictions.append({'type':'incomplete_current_roster','homeRosterCount':len(hp),'awayRosterCount':len(ap)})
 if not sm.get('home',{}).get('starter') and not sm.get('away',{}).get('starter'): contradictions.append({'type':'starting_goalies_unconfirmed','detail':'Neither side has an explicitly identified starter.'})
 if not current: contradictions.append({'type':'current_game_event_feed_empty','detail':'May be expected pregame; not negative scoring evidence.'})
 for team in (home,away):
  if not hist[team]['bundles']: contradictions.append({'type':'historical_sample_missing','team':team})
 gates=[
 gate('G0','Game/slate lock',status(bool(game.get('gameId') and home and away)),[f"gameId={game.get('gameId')}",f'{away} @ {home}',f"state={game.get('gameState')}",f"gameType={game.get('gameType') or 'not supplied'}"]),
 gate('G1','Environment',status(any(team_context[t]['calendarDaysSinceLastGame'] is not None for t in (home,away))),[f"venue={game.get('venue') or 'not supplied'}",f'{home} rest context={team_context[home]}',f'{away} rest context={team_context[away]}'],'Rest interval is derived from retrieved completed-game dates; travel, weather, and arena conditions are not measured.'),
 gate('G2','Lineup/access', 'DEPLOYMENT FOUND — SOURCE/UNIT LABELLED' if any(x.get('rosterJoinCount',0) for x in deployment_teams.values()) else 'SEARCHED MULTIPLE WEB SOURCES — DEPLOYMENT NOT FOUND',[f'home roster={len(hp)}',f'away roster={len(ap)}',*[f'{t}: source={(deployment_teams.get(t) or {}).get("source")}; status={(deployment_teams.get(t) or {}).get("status")}; joined={(deployment_teams.get(t) or {}).get("rosterJoinCount",0)}' for t in (home,away)]], 'Only exact normalized full-name joins to official roster IDs are accepted. A published projected line is not represented as confirmed; PP assignment is recorded only when explicitly present.'),
 gate('G3','Opponent attack map',status(any(g['shotsObserved']>0 for g in goalie_rows)),[f'goalie candidates={len(goalie_rows)}',f'goalies with observed shots={sum(g["shotsObserved"]>0 for g in goalie_rows)}',f'historical games={hist_n}'],'Weakness evidence is restricted to observed NHL event IDs in retrieved history.'),
 gate('G4','Damage mechanism',status(any(p['historicalShots'] for p in player_rows)),[f'skaters={len(sk)}',f'players with observed shots={sum(p["historicalShots"]>0 for p in player_rows)}'],'Shot-type history is descriptive, not proof of tactical mechanism.'),
 gate('G5','Exact matchup alignment',status(any(m['directEvents'] or (set(p['goalShotTypes'])-{'unknown'}) & (set(m.get('goalsAgainstByShotType',{}))-{'unknown'}) or (set(p.get('goalZones',{}))-{'unknown'}) & (set(m.get('goalsAgainstByZone',{}))-{'unknown'}) for p in player_rows for m in p['opposingGoalieMatches'])),[f'exact player-ID × opposing-goalie-ID pairs={sum(len(p["opposingGoalieMatches"]) for p in player_rows)}',f'direct historical goals={sum(m["directGoals"] for p in player_rows for m in p["opposingGoalieMatches"])}'],'Exact IDs define the player and goalie profiles; a historical head-to-head goal is supporting evidence, not mandatory when the player scoring lane matches the goalie weakness.'),
 gate('G6','Opportunity/access','DEPLOYMENT PARTIALLY FOUND' if deployment_by_id else 'SEARCHED MULTIPLE WEB SOURCES — CURRENT DEPLOYMENT UNRESOLVED',[f'full available skater pool={len(sk)}',f'players joined to deployment source={len(deployment_by_id)}',f'players with explicit PP unit={sum(bool(x.get("powerPlayUnit")) for x in deployment_by_id.values())}',f'players with explicit even-strength line={sum(bool(x.get("line")) for x in deployment_by_id.values())}',f'historical shift-chart player records={sum(p.get("historicalShiftUsage",{}).get("gamesWithShiftChartData",0)>0 for p in player_rows)}'],'Historical TOI remains context only. Source freshness and whether a row is projected versus confirmed remain explicit; absence is not a negative finding.'),
 gate('G7','Recurrence/sequence',status(any(len(p['datesWithShots'])>=2 for p in player_rows)),[f'historical games per team requested={limit}'],'Bounded by available historical PBP; missing history is not negative evidence.'),
 gate('G8','Market fingerprint',market_audit.get('status','PENDING / NO EVIDENCE'),[f"provider={market_audit.get('provider')}",f"market={market_audit.get('market')}",f"exact player records={market_audit.get('matchedPlayerCount',0)}",f"bookmakers={market_audit.get('bookmakerCount',0)}",*market_audit.get('errors',[])],'Market evidence is descriptive only; it is not used to rank or score candidates.'),
 gate('G9','Player × environment','PLAYER HOME/AWAY SPLITS MEASURED' if any(p.get('homeAwayEnvironmentSplit',{}).get('comparativeSampleAvailable') for p in player_rows) else 'PARTIAL — REST / VENUE ONLY',[f"venue={game.get('venue') or 'not supplied'}",f'{home}={team_context[home]}',f'{away}={team_context[away]}',f'players with both home/away samples={sum(bool(p.get("homeAwayEnvironmentSplit",{}).get("comparativeSampleAvailable")) for p in player_rows)}'],'Uses retrieved historical NHL game IDs and event feeds to compare player home/away shot and goal production; does not infer travel, weather, or causal effects.'),
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
 # Evidence-only Pareto comparisons for G15/G16. No weights, synthetic score,
 # sportsbook/chalk prior, or arbitrary tie-break is used. A candidate has a
 # distinct advantage only if it is at least as strong on every observed
 # dimension and strictly stronger on one; mixed evidence remains unresolved.
 def comparison_dimensions(p):
  pm = [r for r in route_rows if r['playerId'] == p['playerId']]
  return {
   'historicalGoals': int(p.get('historicalGoals') or 0),
    'historicalSampleAvailable': bool(p.get('historicalSampleAvailable')),
    'historicalGamesRetrieved': int(p.get('historicalGamesRetrieved') or 0),
    'historicalPlayByPlayEventsRetrieved': int(p.get('historicalPlayByPlayEventsRetrieved') or 0),
   'goalGameCount': int(p.get('goalGameCount') or 0),
   'directGoals': sum(int(r.get('directGoals') or 0) for r in pm),
   'confirmedStarterSharedLane': int(any(r.get('starterConfirmed') and (r.get('shotTypeOverlap') or r.get('zoneOverlap')) for r in pm)),
   'elevatedSharedLaneCount': len({x['lane'] for r in pm for x in (r.get('goalieElevatedSharedShotTypes', []) + r.get('goalieElevatedSharedZones', []))}),
  }
 def pareto_relation(a, b):
  keys = tuple(a)
  ge = all(a[k] >= b[k] for k in keys)
  le = all(a[k] <= b[k] for k in keys)
  gt = any(a[k] > b[k] for k in keys)
  lt = any(a[k] < b[k] for k in keys)
  if ge and gt: return 'A_DOMINATES'
  if le and lt: return 'B_DOMINATES'
  if not gt and not lt: return 'EQUIVALENT_OBSERVED_EVIDENCE'
  return 'MIXED_EVIDENCE'
 for p in player_rows:
  p['comparisonDimensions'] = comparison_dimensions(p)
  same_team = [q for q in player_rows if q['team'] == p['team'] and q['playerId'] != p['playerId']]
  same_game = [q for q in player_rows if q['playerId'] != p['playerId']]
  p['finisherProtectionAudit'] = {
   'role': p['recipientRole'], 'goals': p['historicalGoals'], 'assists': p['historicalAssists'],
   'evidencePathClass': p['evidencePathClass'],
   'comparedAgainstPlayerIds': [q['playerId'] for q in same_team],
   'pairwiseResults': [{'playerId': q['playerId'], 'relation': pareto_relation(p['comparisonDimensions'], comparison_dimensions(q)), 'dimensions': comparison_dimensions(q)} for q in same_team],
   'decision': 'COMPARISON COMPLETE — DISTINCT EVIDENCE ADVANTAGE' if same_team and all(pareto_relation(p['comparisonDimensions'], comparison_dimensions(q)) == 'A_DOMINATES' for q in same_team) else ('COMPARISON COMPLETE — DOMINATED ON OBSERVED DIMENSIONS' if any(pareto_relation(p['comparisonDimensions'], comparison_dimensions(q)) == 'B_DOMINATES' for q in same_team) else ('COMPARISON COMPLETE — NO DISTINCT ADVANTAGE' if same_team and all(pareto_relation(p['comparisonDimensions'], comparison_dimensions(q)) == 'EQUIVALENT_OBSERVED_EVIDENCE' for q in same_team) else 'UNRESOLVED — MIXED OR INSUFFICIENT COMPARABLE EVIDENCE')),
  }
  p['finalCompetition'] = {
   'competingPathClasses': sorted({q['evidencePathClass'] for q in same_game}),
   'pairwiseResults': [{'playerId': q['playerId'], 'relation': pareto_relation(p['comparisonDimensions'], comparison_dimensions(q)), 'dimensions': comparison_dimensions(q)} for q in same_game],
   'decision': 'COMPETITION COMPLETE — DISTINCT EVIDENCE ADVANTAGE' if same_game and all(pareto_relation(p['comparisonDimensions'], comparison_dimensions(q)) == 'A_DOMINATES' for q in same_game) else ('COMPETITION COMPLETE — DOMINATED ON OBSERVED DIMENSIONS' if any(pareto_relation(p['comparisonDimensions'], comparison_dimensions(q)) == 'B_DOMINATES' for q in same_game) else ('COMPETITION COMPLETE — NO DISTINCT ADVANTAGE' if same_game and all(pareto_relation(p['comparisonDimensions'], comparison_dimensions(q)) == 'EQUIVALENT_OBSERVED_EVIDENCE' for q in same_game) else 'UNRESOLVED — MIXED OR INSUFFICIENT COMPARABLE EVIDENCE')),
   'numericScoreUsed': False,
   'dimensions': p['comparisonDimensions'],
  }
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
  p['gateTrace']=[
   gate('G0','Game identity',status(bool(game.get('gameId'))),[f"gameId={game.get('gameId')}",f"gameType={game.get('gameType') or 'not supplied'}",f"matchup={game.get('awayAbbrev')} @ {game.get('homeAbbrev')}"]),
   gate('G1','Environment','PARTIAL — REST / VENUE ONLY',[str(game.get('venue') or 'venue unavailable'),str(team_context.get(p['team'],{}))],'Travel and arena conditions are not measured by the current feed.'),
   gate('G2','Availability / access',status(bool(p.get('playerId'))),[f"roster source={next((q.get('source') for q in ps if q['playerId']==p['playerId']), 'unknown')}"]),
   gate('G3','Opponent goalie vulnerability',status(any(m['shotsObserved']>0 for m in p['opposingGoalieMatches'])),[f"goalie profiles={sum(m['shotsObserved']>0 for m in p['opposingGoalieMatches'])}"]),
   gate('G4','Damage mechanism',('PENDING — NO HISTORICAL PLAY-BY-PLAY SAMPLE' if not p.get('historicalSampleAvailable') else status(bool(p['shotTypes']))),[f"historical games retrieved={p.get('historicalGamesRetrieved',0)}",f"historical PBP events retrieved={p.get('historicalPlayByPlayEventsRetrieved',0)}",f"player shot types={p['shotTypes']}",f"goal shot types={p['goalShotTypes']}"]),
   gate('G5','Direct matchup',status(any(m['directEvents']>0 for m in p['opposingGoalieMatches']) or any(r['shotTypeOverlap'] or r['zoneOverlap'] for r in pm)),[f"direct goals={sum(m['directGoals'] for m in p['opposingGoalieMatches'])}",f"direct events={sum(m['directEvents'] for m in p['opposingGoalieMatches'])}",f"shared lanes={sum(bool(r['shotTypeOverlap'] or r['zoneOverlap']) for r in pm)}"]),
   gate('G6','Opportunity / access','EXPLICIT LINE/PP DEPLOYMENT FOUND' if p.get('deploymentEvidence') and (p['deploymentEvidence'].get('line') or p['deploymentEvidence'].get('powerPlayUnit')) else ('SEARCHED SOURCES — PLAYER DEPLOYMENT NOT FOUND' if p.get('deploymentSourceStatus') else 'UNRESOLVED — deployment data unavailable'),[f"position={p['position']}",f"deployment source={p.get('deploymentSource')}",f"line={((p.get('deploymentEvidence') or {}).get('line'))}",f"PP unit={((p.get('deploymentEvidence') or {}).get('powerPlayUnit'))}",f"historical boxscore games={p.get('historicalUsage',{}).get('gamesWithBoxscoreUsage',0)}",f"mean historical TOI seconds={p.get('historicalUsage',{}).get('meanToiSeconds')}"],'Historical TOI is context only. Projected source data remains projected; absence is not a negative finding.'),
   gate('G7','Recurrence',status(bool(p['datesWithShots'])),[f"shot dates={len(p['datesWithShots'])}",f"goal dates={len(p['datesWithGoals'])}"]),
   gate('G8','Market fingerprint','PLAYER MARKET RECORD WITH SOURCE TIMESTAMP' if (p.get('marketFingerprintIntegrity') or {}).get('usableRecordCount',0)>0 else market_audit.get('status','PENDING — NO VALID PLAYER MARKET RECORD'),[str(p.get('marketFingerprint',[])),str(p.get('marketFingerprintIntegrity',{})),f"provider={market_audit.get('provider')}",f"market={market_audit.get('market')}"],'Odds are recorded as market context only; no ranking, probability conversion, or arbitrary freshness cutoff.'),
   gate('G9','Player × environment','COMPARATIVE HOME/AWAY SAMPLE AVAILABLE' if p.get('homeAwayEnvironmentSplit',{}).get('comparativeSampleAvailable') else 'PENDING — INSUFFICIENT HOME/AWAY SAMPLE',[str(p.get('homeAwayEnvironmentSplit',{})),str(team_context.get(p['team'],{}))],'Observed home/away production is descriptive, not a causal estimate; travel and weather are not inferred.'),
   gate('G10','Event route',('PENDING — NO HISTORICAL PLAY-BY-PLAY SAMPLE' if not p.get('historicalSampleAvailable') else status(bool(p['historicalShots']))),[f"sample available={p.get('historicalSampleAvailable')}",f"observed shots={p['historicalShots']}",f"observed goals={p['historicalGoals']}"]),
   gate('G10.5','Recipient separation',status(bool(p['historicalGoals'] or p['historicalAssists'])),[f"finisher goals={p['historicalGoals']}",f"facilitator assists={p['historicalAssists']}" ]),
   gate('G11','Continuation',status(bool(p['datesWithGoals'] or p['datesWithShots'])),[f"recent recorded goal dates={p['datesWithGoals'][:5]}"]),
   gate('G12','Event ownership',status(bool(p['historicalGoals'] or p['historicalAssists'])),[f"goal events={p['historicalGoals']}",f"assist events={p['historicalAssists']}"]),
   gate('G14','WHO/anomaly',status(any('SHARED DAMAGE LANE' in r['pathFinding'] or 'DIRECT GOAL' in r['pathFinding'] for r in pm)),[r['pathFinding'] for r in pm]),
   gate('G15','Finisher protection',p['finisherProtectionAudit']['decision'],[f"recipient role={p['recipientRole']}",f"goals={p['historicalGoals']}",f"assists={p['historicalAssists']}",f"evidence path={p['evidencePathClass']}",f"same-team competitors={p['finisherProtectionAudit']['comparedAgainstPlayerIds']}",str(p['finisherProtectionAudit'].get('pairwiseResults', []))],'Pareto comparison uses observed goals, goal-game recurrence, exact goalie goals, confirmed-starter shared-lane evidence, and elevated shared-lane count. Mixed evidence is not forced into a winner.'),
   gate('G16','Final competition',p['finalCompetition']['decision'],[f"candidate evidence class={p['evidencePathClass']}",f"competing classes={p['finalCompetition']['competingPathClasses']}",str(p['finalCompetition'].get('pairwiseResults', []))],'Game-wide Pareto comparison uses observed evidence only. Mixed evidence or ties do not create a forced winner.'),
   gate('G17','Contradiction audit','REVIEW REQUIRED' if any('CONTRADICTION CHECK' in r['pathFinding'] for r in pm) else 'CANDIDATE REVIEW — NO AUTOMATIC OVERRIDE',[f"goals={p['historicalGoals']}",f"assists={p['historicalAssists']}",f"goalie path findings={len(pm)}",str(p['routeFindings'])],'This flags evidence requiring review; it does not auto-eliminate a player or claim every tactical contradiction is resolved.'),
   gate('G18','Final audit','NOT VALIDATED — REQUIRED GATES UNRESOLVED',[f"playerId={p['playerId']}",f"gate count={len(GATES)}",f"path class={p['evidencePathClass']}",'G6 current deployment unresolved','G15 comparison incomplete','G16 competition unresolved'],'A trace is not a pass. This record is not eligible for a final player-path designation until required evidence and contradictions are resolved.')]
 # Publish exact per-player blockers so a missing gate can be fixed directly;
 # a complete trace is never treated as a pass by itself.
 for p in player_rows:
  p['gateBlockers'] = final_gate_blockers(p, route_rows, player_rows, contradictions, mode)
  p['gateBlockerCount'] = len(p['gateBlockers'])
  p['g18Eligible'] = False
  p['g18Decision'] = 'NOT LOCKED — REQUIRED EVIDENCE BLOCKERS REMAIN'
  for tr in p.get('gateTrace', []):
   if tr.get('gate') == 'G18':
    tr['evidence'] = [f"playerId={p['playerId']}", f"blockerCount={len(p['gateBlockers'])}", *(['G6 current deployment unresolved'] if any(b['gate'] == 'G6' for b in p['gateBlockers']) else []), *[f"{b['gate']}: {b['reason']}" for b in p['gateBlockers']]]
    tr['limitation'] = 'No final lock is issued until each listed blocker is supported and the competing candidate audit is resolved.'
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
 return {'game':game,'mode':mode,'runUTC':now(),'auditStatus':'ANALYSIS COMPLETE — EVIDENCE PATHS AND PAIRWISE COMPARISONS GENERATED; LIVE DEPLOYMENT STILL SOURCE-DEPENDENT','sourceCoverage':{'candidateSkaters':len(sk),'homeRoster':len(hp),'awayRoster':len(ap),'currentPbpEvents':len(current),'currentDirectMatchups':len(direct_now),'historicalBundles':hist_n,'historicalEvents':hist_events,'retrievalErrors':len(errs),'playersWithObservedAttempts':len(route_candidates),'exactDirectPairsWithEvents':sum(1 for x in route_rows if x['directEvents']>0)},'gates':gates,'teamContext':team_context,'players':player_rows,'gateBlockerSummary':{'playersWithBlockers':sum(bool(p.get('gateBlockers')) for p in player_rows),'totalBlockers':sum(p.get('gateBlockerCount',0) for p in player_rows),'byGate':dict(Counter(b['gate'] for p in player_rows for b in p.get('gateBlockers',[])))},'goalies':goalie_rows,'directMatchupAudit':route_rows,'routeComparisons':route_comparisons,'routeCandidates':route_candidates,'currentDirectMatchups':direct_now,'officialGameParticipation':deployment.get('officialGameParticipation',{}),'marketFingerprintAudit':market_audit,'deploymentSourceSearch':{team:{'source':x.get('source'),'status':x.get('status'),'joined':x.get('rosterJoinCount',0),'sourceDate':(x.get('sourceMeta') or {}).get('sourceDate'),'lineEvidenceFound':(x.get('sourceMeta') or {}).get('lineEvidenceFound'),'powerPlayEvidenceFound':(x.get('sourceMeta') or {}).get('powerPlayEvidenceFound'),'unmatchedNames':x.get('unmatchedNames',[]),'attempts':x.get('sourceMeta',{}).get('attempts',[])} for team,x in deployment_teams.items()},'dataErrors':errs,'contradictions':contradictions,'historicalByTeam':{t:{'games':[b['game'] for b in x['bundles']],'events':len(x['events']),'shiftChartAudit':x.get('shiftChartAudit',[]),'shiftChartRowsRetrieved':len(x.get('shiftRows',[])),'historicalShiftOverlap':x.get('shiftOverlap',{}),'historicalGoalShiftContext':x.get('goalShiftContext',{})} for t,x in hist.items()}}
def run_slate(bundles,mode,history_limit=8):
 # Pregame analysis must never silently back-solve from a live or completed game.
 # Keep excluded game IDs and states visible in the report rather than analyzing them.
 pregame_states={'FUT','PRE','SCHEDULED','PREGAME','FUTURE'}
 analyzed=[]; excluded=[]
 for bundle in bundles:
  game=bundle.get('game') or {}
  state=str(game.get('gameState') or game.get('gameScheduleState') or 'UNKNOWN').upper()
  if state not in pregame_states:
   excluded.append({'gameId':game.get('gameId'),'matchup':f"{game.get('awayAbbrev','AWAY')} @ {game.get('homeAbbrev','HOME')}",'gameState':state,'reason':'Excluded from pregame Blender: game is not explicitly in a scheduled/pregame state.'})
   continue
  analyzed.append(bundle)
 games=[analyze(b,mode,history_limit) for b in analyzed]
 unresolved=sum(1 for g in games for p in g.get('players',[]) if str(p.get('pathDisposition','')).startswith('UNRESOLVED') or str((p.get('gateTrace') or [{}])[-1].get('status','')).startswith('NOT VALIDATED'))
 # Core output is derived only from explicit G18 locks. Never rank or promote an unresolved
 # candidate to fill a slot; each game can contribute at most one locked survivor.
 locked=[]
 for g in games:
  game_locked=[]
  for p in g.get('players',[]):
   trace=p.get('gateTrace') or []
   final=trace[-1] if trace else {}
   if str(p.get('pathDisposition','')).startswith('LOCKED —') and str(final.get('status','')).startswith('LOCKED'):
    game_locked.append({'gameId':g.get('game',{}).get('gameId'),'matchup':f"{g.get('game',{}).get('awayAbbrev')} @ {g.get('game',{}).get('homeAbbrev')}",'playerId':p.get('playerId'),'player':p.get('player'),'team':p.get('team'),'opponent':p.get('opponent'),'pathDisposition':p.get('pathDisposition'),'gate18':final})
  if len(game_locked)==1: locked.extend(game_locked)
  elif len(game_locked)>1:
   # Multiple purported locks in one game violate the one-survivor-per-game contract.
   for item in game_locked: item['coreEligibility']='REJECTED — MULTIPLE G18 LOCKS IN ONE GAME'
 core3=locked if len(locked)==3 and len({x['gameId'] for x in locked})==3 else []
 core2=locked if len(games)==2 and len(locked)==2 and len({x['gameId'] for x in locked})==2 else []
 selected_core=core3 or core2
 core_status='CORE 3 LOCKED' if len(core3)==3 else ('CORE 2 LOCKED' if len(core2)==2 else ('CORE SELECTION UNRESOLVED — CROSS-GAME COMPETITION REQUIRED' if len(locked)>3 else ('NO VALID CORE — G18 LOCKS NOT EARNED' if locked else 'NO VALID CORE — ZERO G18-LOCKED SURVIVORS')))
 return {'runId':sid(now(),mode,len(games)),'runUTC':now(),'mode':mode,'gameCount':len(games),'games':games,'excludedGames':excluded,'coreOutput':{'status':core_status,'lockedSurvivorCount':len(locked),'core':selected_core,'rule':'Only explicit G18 locks; one survivor per game; no substitutions or ranking; Core 3 requires three distinct games; two-game slate may return Core 2.'},'validationSummary':{'status':'NOT VALIDATED — REQUIRED GATES UNRESOLVED' if games else ('NO PRE-GAME GAMES ELIGIBLE — SLATE NOT VALIDATED' if excluded else 'NO GAMES RETURNED — SLATE NOT VALIDATED'),'gamesWithErrors':sum(bool(g.get('dataErrors')) for g in games),'playersRetained':sum(len(g.get('players',[])) for g in games),'playersWithUnresolvedFinalAudit':unresolved,'excludedNonPregameGames':len(excluded),'requiredUnresolvedAreas':['G2 projected/confirmed line and PP deployment freshness/status','G6 current deployment / line access','G15 finisher protection comparison','G16 final competition','G17 full tactical contradiction review','live source retrieval must be confirmed in deployment environment'],'finalPlayerPathsCertified':bool(core3 or core2)},'statement':'Full-slate pregame hockey event-path audit. Live/completed games are excluded. Every active gate is traced in order; direct player/goalie identity is exact-ID only; no unsupported player, evidence, or numeric score is invented. A completed trace is not a certified final path.'}
