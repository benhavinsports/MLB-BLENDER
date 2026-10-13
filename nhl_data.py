from __future__ import annotations
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
    d=get_json(f'schedule/{day}'); rows=[]
    for w in d.get('gameWeek',[]) or []:
        for g in w.get('games',[]) or []:
            if str(g.get('gameDate',''))[:10]==day: rows.append(norm(g))
    if not rows:
        s,e=safe(f'score/{day}')
        if s: rows=[norm(g) for g in s.get('games',[]) or []]
    return sorted(rows,key=lambda x:x.get('startTimeUTC') or '')
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
        p,e=safe(f"gamecenter/{g['gameId']}/play-by-play"); l,e2=safe(f"gamecenter/{g['gameId']}/landing")
        if e: errors.append(e)
        if e2: errors.append(e2)
        if p: bundles.append({'game':g,'plays':p,'landing':l})
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
        out.append({'eventId':p.get('eventId'),'type':typ,'period':(p.get('periodDescriptor') or {}).get('number'),'time':p.get('timeInPeriod'),
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
