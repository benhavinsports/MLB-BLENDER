from __future__ import annotations
from datetime import datetime, timezone
import requests
try:
    import streamlit as st
except ImportError:
    class _StreamlitFallback:
        @staticmethod
        def cache_data(*args, **kwargs):
            def decorate(fn): return fn
            return decorate
    st = _StreamlitFallback()
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
BASE='https://api-web.nhle.com/v1'
S=requests.Session(); S.headers.update({'User-Agent':'NHL-Blender-Audit/3.0','Accept':'application/json'})
_retry=Retry(total=3,connect=3,read=2,backoff_factor=0.6,status_forcelist=(429,500,502,503,504),allowed_methods=frozenset(['GET']))
_adapter=HTTPAdapter(max_retries=_retry,pool_connections=16,pool_maxsize=16)
S.mount('https://',_adapter); S.mount('http://',_adapter)
class NHLDataError(RuntimeError): pass
@st.cache_data(ttl=900,show_spinner=False)
def get_json(path):
    r=S.get(f'{BASE}/{path.lstrip("/")}',timeout=25); r.raise_for_status(); d=r.json()
    if not isinstance(d,dict): raise NHLDataError(f'Unexpected payload: {path}')
    return d
def safe(path):
    try:return get_json(path),None
    except Exception as e:return None,f'{path}: {type(e).__name__}: {e}'
def nm(x): return (x.get('default') or x.get('full') or '') if isinstance(x,dict) else (x or '')
def norm(g):
    h=g.get('homeTeam') or {}; a=g.get('awayTeam') or {}
    return {'gameId':int(g.get('id') or g.get('gameId') or 0),'gameDate':str(g.get('gameDate') or '')[:10],
      'startTimeUTC':g.get('startTimeUTC'),'gameState':g.get('gameState') or g.get('gameScheduleState') or 'UNKNOWN','gameType':g.get('gameType') or g.get('gameTypeId'),
      'homeAbbrev':h.get('abbrev') or h.get('teamAbbrev') or 'HOME','homeName':nm(h.get('name')),'homeTeamId':h.get('id'),
      'awayAbbrev':a.get('abbrev') or a.get('teamAbbrev') or 'AWAY','awayName':nm(a.get('name')),'awayTeamId':a.get('id'),
      'homeScore':h.get('score'),'awayScore':a.get('score'),'venue':nm(g.get('venue'))}
def get_schedule(day):
    """Retrieve a date's slate from multiple official NHL endpoints.

    A failure of the preferred schedule endpoint must not prevent attempts against
    the official score and schedule-calendar endpoints. If all endpoints fail,
    raise with each failure so the caller can mark the slate incomplete instead
    of treating an unavailable feed as an empty slate.
    """
    failures=[]
    # Preferred full schedule endpoint; retain exact date filtering because it
    # returns a multi-day gameWeek payload.
    d,e=safe(f'schedule/{day}')
    if d is not None:
        rows=[]
        for w in d.get('gameWeek',[]) or []:
            for g in w.get('games',[]) or []:
                if str(g.get('gameDate',''))[:10]==day:
                    rows.append(norm(g))
        if rows:
            return sorted(rows,key=lambda x:x.get('startTimeUTC') or '')
    else:
        failures.append(e)

    # Official date-scoped scoreboard is a separate retrieval route.
    score,e=safe(f'score/{day}')
    if score is not None:
        rows=[norm(g) for g in score.get('games',[]) or [] if str(g.get('gameDate',''))[:10] == day]
        if rows:
            return sorted(rows,key=lambda x:x.get('startTimeUTC') or '')
    else:
        failures.append(e)

    # Schedule calendar is a final independent fallback; its schema has varied,
    # so accept only explicit game records with a game ID and matching date.
    calendar,e=safe(f'schedule-calendar/{day}')
    if calendar is not None:
        rows=[]
        def walk(value):
            if isinstance(value,dict):
                if (value.get('id') or value.get('gameId')) and value.get('gameDate'):
                    if str(value.get('gameDate'))[:10]==day:
                        try: rows.append(norm(value))
                        except Exception: pass
                for child in value.values(): walk(child)
            elif isinstance(value,list):
                for child in value: walk(child)
        walk(calendar)
        # Deduplicate IDs in case the schema nests the same game in several places.
        rows=list({r['gameId']:r for r in rows if r.get('gameId')}.values())
        if rows:
            return sorted(rows,key=lambda x:x.get('startTimeUTC') or '')
    else:
        failures.append(e)

    if failures:
        raise NHLDataError('All official NHL slate endpoints failed: ' + ' | '.join(failures))
    # Successful, valid endpoints with no games means a genuinely empty slate.
    return []
def get_bundle(g):
    gid=g['gameId']; l,e1=safe(f'gamecenter/{gid}/landing'); b,e2=safe(f'gamecenter/{gid}/boxscore'); p,e3=safe(f'gamecenter/{gid}/play-by-play')
    return {'game':g,'landing':l,'boxscore':b,'plays':p,'errors':[x for x in (e1,e2,e3) if x]}
def get_recent(team,day,limit=8):
    d,e=safe(f'club-schedule-season/{team}/now')
    rows=[]
    for g in (d or {}).get('games',[]) or []:
        x=norm(g)
        if x['gameId'] and x['gameDate'] and x['gameDate']<day and x['gameState'] in ('OFF','FINAL','OVER','CRIT'):
            rows.append(x)
    # Keep only unique game IDs and recent completed games.
    return sorted({x['gameId']:x for x in rows}.values(),key=lambda x:x['gameDate'],reverse=True)[:limit]
def get_history(team,day,limit=8):
    bundles=[]; errors=[]
    for g in get_recent(team,day,limit):
        p,e=safe(f"gamecenter/{g['gameId']}/play-by-play"); l,e2=safe(f"gamecenter/{g['gameId']}/landing"); b,e3=safe(f"gamecenter/{g['gameId']}/boxscore")
        if e: errors.append(e)
        if e2: errors.append(e2)
        if e3: errors.append(e3)
        if p: bundles.append({'game':g,'plays':p,'landing':l,'boxscore':b})
    return bundles,errors
def players_from(obj,side,source):
    out=[]; t=(obj or {}).get(side+'Team') or {}
    for group,pos in [('forwards','F'),('defense','D'),('goalies','G')]:
        for p in t.get(group,[]) or []:
            pid=p.get('playerId') or p.get('id')
            if not pid:continue
            out.append({'playerId':int(pid),'name':nm(p.get('name')) or f"Player {pid}",'position':p.get('position') or p.get('positionCode') or pos,'section':group,'source':source})
    return out
def roster(box,landing,side,team=None):
    # Prefer the game-specific roster, then landing payload, then the current official team roster.
    pbg=(box or {}).get('playerByGameStats') or {}; t=pbg.get(side+'Team') or {}
    if t:
        fake={side+'Team':t}; rows=players_from(fake,side,'boxscore')
        if rows:return rows
    rows=players_from(landing,side,'landing')
    if rows:return rows
    if team:
        d,e=safe(f'roster/{team}/current')
        if d:
            rows=[]
            groups=[('forwards','F'),('defensemen','D'),('defense','D'),('goalies','G')]
            for key,pos in groups:
                for p in d.get(key,[]) or []:
                    pid=p.get('id') or p.get('playerId')
                    if not pid:continue
                    first=nm(p.get('firstName')); last=nm(p.get('lastName'))
                    name=nm(p.get('name')) or ' '.join(x for x in (first,last) if x) or f'Player {pid}'
                    rows.append({'playerId':int(pid),'name':name,'position':p.get('positionCode') or p.get('position') or pos,'section':'goalies' if pos=='G' else ('defense' if pos=='D' else 'forwards'),'source':'official current roster'})
            # Some payloads expose defensemen only; avoid duplicate IDs from alternate schema keys.
            return list({x['playerId']:x for x in rows}.values())
    return []
def events(payload):
    out=[]
    for p in (payload or {}).get('plays',[]) or []:
        typ=str(p.get('typeDescKey') or '').lower(); d=p.get('details') or {}
        if not any(x in typ for x in ('goal','shot','missed-shot','blocked-shot')):continue
        shooter=d.get('shootingPlayerId') or d.get('scoringPlayerId'); goalie=d.get('goalieInNetId') or d.get('goalieId')
        out.append({'eventId':p.get('eventId'),'type':typ,'period':(p.get('periodDescriptor') or {}).get('number'),'time':p.get('timeInPeriod'),'timeRemaining':p.get('timeRemaining'),
          'shooterId':int(shooter) if shooter else None,'goalieId':int(goalie) if goalie else None,'teamId':d.get('eventOwnerTeamId') or d.get('shootingPlayerTeamId'),
          'shotType':d.get('shotType') or 'unknown','zone':d.get('zoneCode'),'x':d.get('xCoord'),'y':d.get('yCoord'),
          'assist1Id':int(d['assist1PlayerId']) if d.get('assist1PlayerId') else None,
          'assist2Id':int(d['assist2PlayerId']) if d.get('assist2PlayerId') else None})
    return out
def starters(box):
    pbg=(box or {}).get('playerByGameStats') or {}; result={}
    for side in ('home','away'):
        goalies=(pbg.get(side+'Team') or {}).get('goalies') or []
        starter=next((x for x in goalies if x.get('starter') is True or x.get('isStarter') is True),None)
        result[side]={'goalies':goalies,'starter':starter,'status':'source explicitly marks starter' if starter else ('goalies listed; starter not confirmed' if goalies else 'no goalie data')}
    return result

# Multi-source deployment enrichment. Missing values trigger web-source fallbacks;
# source failures are retained in the run report instead of silently using roster membership.
def official_game_roster_evidence(box, side):
    """Extract only explicit NHL game-boxscore participation fields.

    This confirms a game-specific roster/participation record exists; it does not
    infer line combinations or power-play units from roster presence.
    """
    side_key = side + 'Team'
    stats = (box or {}).get('playerByGameStats') or {}
    team = stats.get(side_key) or {}
    if not team:
        return {
            'status': 'NOT AVAILABLE IN OFFICIAL BOXSCORE',
            'source': 'NHL Gamecenter boxscore',
            'players': [], 'scratches': [], 'goalieStarterIds': [],
            'lineAssignmentsConfirmed': False, 'powerPlayAssignmentsConfirmed': False,
        }

    players = []
    for group, default_pos in (('forwards', 'F'), ('defense', 'D'), ('goalies', 'G')):
        for item in team.get(group, []) or []:
            pid = item.get('playerId') or item.get('id')
            if not pid:
                continue
            players.append({
                'playerId': int(pid), 'name': nm(item.get('name')) or f'Player {pid}',
                'position': item.get('position') or item.get('positionCode') or default_pos,
                'group': group,
                'starterExplicitlyMarked': item.get('starter') is True or item.get('isStarter') is True,
            })
    scratches = []
    for item in team.get('scratches', []) or []:
        pid = item.get('playerId') or item.get('id')
        if pid:
            scratches.append({'playerId': int(pid), 'name': nm(item.get('name')) or f'Player {pid}'})
    starters = [p['playerId'] for p in players if p['group'] == 'goalies' and p['starterExplicitlyMarked']]
    return {
        'status': 'OFFICIAL GAME-SPECIFIC ROSTER PRESENT' if players else 'BOXSCORE PRESENT BUT NO PLAYER ROWS',
        'source': 'NHL Gamecenter boxscore',
        'players': players, 'scratches': scratches, 'goalieStarterIds': starters,
        'playerCount': len(players),
        'lineAssignmentsConfirmed': False,
        'powerPlayAssignmentsConfirmed': False,
        'limitation': 'Official game roster/participation only; no line or power-play unit is inferred.',
    }


def enrich_deployment(bundle, mode='projected'):
    from deployment_sources import fetch_deployment, norm_name
    game=bundle.get('game') or {}; box=bundle.get('boxscore') or {}; land=bundle.get('landing') or {}
    meta={}; assignments={}; official_participation={}
    for side in ('home','away'):
        team=game.get(side+'Abbrev') or ('HOME' if side=='home' else 'AWAY')
        team_name=game.get(side+'Name') or team
        rows,source_meta=fetch_deployment(team,team_name,mode=mode)
        # Name-to-ID join is exact after punctuation/diacritic normalization only.
        roster_rows=roster(box,land,side,team)
        official_participation[team]=official_game_roster_evidence(box, side)
        by_name={norm_name(p.get('name')):p for p in roster_rows if p.get('playerId') and norm_name(p.get('name'))}
        joined=[]; unmatched=[]
        for row in rows:
            p=by_name.get(norm_name(row.get('playerName')))
            if p:
                joined.append({**row,'playerId':p['playerId'],'officialPlayerName':p['name'],'joinMethod':'exact normalized full name to official roster ID','deploymentStatus':row.get('deploymentStatus','PROJECTED')})
            else: unmatched.append(row.get('playerName'))
        assignments[team]={'rows':joined,'source':source_meta.get('selectedSource'),'status':source_meta.get('status'),'sourceMeta':source_meta,'unmatchedNames':unmatched,'rosterJoinCount':len(joined)}
        meta[team]=source_meta
    bundle['deployment']={'mode':mode,'retrievedAt':datetime.now(timezone.utc).isoformat(),'teams':assignments,'sourceSearch':meta,'officialGameParticipation':official_participation}
    return bundle
