"""Multi-source lineup/PP deployment retrieval with explicit provenance.

Source order: Hockey Insights' public lineup snapshot (which credits PuckPedia,
Daily Faceoff, and NHL.com); NHL.com projected-lineup article; Daily Faceoff
line combinations. Names are only joined to official NHL IDs after exact normalized
name matching or an official NHL search response. Missing data remains missing.
"""
from __future__ import annotations
import json, re, unicodedata
from datetime import datetime, timezone
from urllib.parse import quote
import requests

TIMEOUT = 12
_HTTP_CACHE = {}
_CACHE_TTL = 600
HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; NHLBlender/4.0; +https://www.nhl.com)', 'Accept':'application/json,text/html,*/*'}
HI_BASE = 'https://hockeyinsights.ca/data/lineups'
NHL_LINEUP_URL = 'https://www.nhl.com/news/nhl-lineup-projections-2026-27-season'
DFO_URL = 'https://www.dailyfaceoff.com/teams/{team}/line-combinations'


def norm_name(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii','ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+',' ',s).strip()


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    return r


def _strings(obj):
    """Yield (path, dict) pairs from arbitrary JSON source schemas."""
    def walk(x, path=''):
        if isinstance(x, dict):
            yield path, x
            for k,v in x.items(): yield from walk(v, f'{path}.{k}' if path else str(k))
        elif isinstance(x, list):
            for i,v in enumerate(x): yield from walk(v, f'{path}[{i}]')
    yield from walk(obj)


def _player_name(d):
    for key in ('fullName','name','playerName','displayName','skater','player'):
        v=d.get(key)
        if isinstance(v,str) and len(v.strip())>2: return v.strip()
        if isinstance(v,dict):
            for nk in ('default','full','name'):
                if isinstance(v.get(nk),str): return v[nk].strip()
            first=v.get('firstName'); last=v.get('lastName')
            if first and last: return f'{first} {last}'.strip()
    first=d.get('firstName'); last=d.get('lastName')
    if isinstance(first,dict): first=first.get('default')
    if isinstance(last,dict): last=last.get('default')
    if first and last: return f'{first} {last}'.strip()
    return None


def parse_lineup_json(data, team, source, retrieved_at=None):
    """Normalize common public lineup JSON shapes without guessing missing units."""
    target=team.upper(); rows=[]
    for path,d in _strings(data):
        name=_player_name(d)
        if not name: continue
        # Unit labels are kept only when explicit in source fields/path.
        raw=' '.join([path]+[str(d.get(k,'')) for k in ('line','lineNumber','lineType','unit','unitName','position','role','type','specialTeamsUnit')]).lower()
        pp=None
        for key in ('powerPlayUnit','ppUnit','specialTeamsUnit','unit','unitName','lineType','type'):
            v=d.get(key)
            if isinstance(v,str) and re.search(r'\b(pp|power.?play)\s*[-#:]?\s*([12])\b',v.lower()):
                pp=int(re.search(r'([12])\b',v).group(1)); break
        if pp is None:
            m=re.search(r'(?:power.?play|\bpp)\s*[-#:]?\s*([12])\b',raw)
            if m: pp=int(m.group(1))
        line=None
        for key in ('lineNumber','line','forwardLine','lineNo','line_number'):
            v=d.get(key)
            if isinstance(v,(int,float)) and 1<=int(v)<=4: line=int(v); break
            if isinstance(v,str):
                m=re.fullmatch(r'\s*(?:line\s*)?([1-4])\s*',v.lower())
                if m: line=int(m.group(1)); break
        if line is None:
            m=re.search(r'(?:forward.?line|line)\s*[-#:]?\s*([1-4])\b',raw)
            if m: line=int(m.group(1))
        if pp is None and line is None: continue
        team_fields=' '.join(str(d.get(k,'')) for k in ('team','teamAbbrev','teamCode','abbrev','teamName')).upper().strip()
        if team_fields and target not in team_fields and target not in path.upper(): continue
        rows.append({'playerName':name,'line':line,'powerPlayUnit':pp,'source':source,'sourcePath':path,'retrievedAt':retrieved_at or datetime.now(timezone.utc).isoformat(),'sourceTeam':target})
    # Avoid duplicates by player + deployment dimension; retain separate line/PP records.
    uniq={ (norm_name(x['playerName']),x['line'],x['powerPlayUnit']):x for x in rows }
    return list(uniq.values())


def fetch_hockeyinsights(team):
    """Try the published index and then the team's club file; source is dated in payload."""
    errors=[]
    for url in (f'{HI_BASE}/index.json', f'{HI_BASE}/{team.lower()}.json', f'{HI_BASE}/{team.upper()}.json'):
        try:
            d=get(url).json()
            # Index often maps abbreviations to a path/file. Follow exact team entries.
            if 'index.json' in url and isinstance(d,dict):
                candidate=None
                for k,v in d.items():
                    if team.upper() in str(k).upper() and isinstance(v,(str,dict)):
                        candidate=v.get('url') or v.get('file') or v.get('path') if isinstance(v,dict) else v
                        if candidate: break
                if candidate:
                    target=candidate if str(candidate).startswith('http') else 'https://hockeyinsights.ca/'+str(candidate).lstrip('/')
                    try: d=get(target).json(); url=target
                    except Exception as e: errors.append(f'{target}: {e}')
            rows=parse_lineup_json(d,team,'Hockey Insights snapshot')
            if rows: return rows, {'source':'Hockey Insights snapshot','url':url,'sourceDate':_date_in(d),'errors':errors}
            errors.append(f'{url}: no explicit line/PP assignments parsed')
        except Exception as e: errors.append(f'{url}: {type(e).__name__}: {e}')
    return [], {'source':None,'errors':errors}


def _date_in(obj):
    for _,d in _strings(obj):
        for k in ('updatedAt','builtAt','generatedAt','sourceDate','date','timestamp'):
            if isinstance(d.get(k),str) and re.search(r'20\d\d-\d\d-\d\d',d[k]): return d[k]
    return None


def fetch_nhl_article(team, team_name=None):
    """Fallback to NHL.com's current-season projected-lineup article, if readable."""
    try:
        html=get(NHL_LINEUP_URL).text
        txt=re.sub(r'<(script|style)\b[^>]*>.*?</\1>',' ',html,flags=re.I|re.S)
        txt=re.sub(r'<[^>]+>','\n',txt)
        for old,new in (('&nbsp;',' '),('&#x27;',"'"),('&amp;','&'),('&ndash;','--'),('&mdash;','--')): txt=txt.replace(old,new)
        txt=re.sub(r'\s+',' ',txt).strip()
        # Article labels use city/nickname headings, not always full club names.
        aliases=[]
        if team_name:
            parts=team_name.strip().split()
            aliases.extend([team_name.strip(), parts[-1] if parts else team_name.strip()])
        aliases.append(team)
        lower=txt.lower(); start=-1; matched=None
        for alias in aliases:
            if not alias: continue
            # Anchor on the explicit projected lineup heading to avoid accidentally
            # collecting a nearby opponent's line based on a loose substring match.
            pattern=re.compile(re.escape(alias.lower())+r'\s+projected lineup',re.I)
            m=pattern.search(lower)
            if m: start=m.start(); matched=alias; break
        if start < 0:
            return [], {'source':None,'errors':[f'{team_name or team} not found as a projected-lineup heading in NHL.com article']}
        tail=txt[start:]
        next_heading=re.search(r'\b[A-Z][A-Za-z .-]+\s+projected lineup\b',tail[len(matched)+18:],re.I)
        if next_heading: tail=tail[:len(matched)+18+next_heading.start()]
        # Forward line rows are the only units reliably published in this article.
        rows=[]; line_no=0
        for raw in re.findall(r'([A-ZÀ-ÿ][A-Za-zÀ-ÿ .\'-]+?\s+--\s+[A-ZÀ-ÿ][A-Za-zÀ-ÿ .\'-]+?(?:\s+--\s+[A-ZÀ-ÿ][A-Za-zÀ-ÿ .\'-]+)?)',tail):
            parts=[x.strip() for x in raw.split('--')]
            if len(parts)==3 and all(len(x)>2 for x in parts):
                line_no+=1
                for n in parts:
                    rows.append({'playerName':n,'line':line_no if line_no<=4 else None,'powerPlayUnit':None,'source':'NHL.com projected lineup article','sourcePath':f'forward line {line_no}','retrievedAt':datetime.now(timezone.utc).isoformat(),'sourceTeam':team.upper()})
        if rows:return rows, {'source':'NHL.com projected lineup article','url':NHL_LINEUP_URL,'sourceDate':datetime.now(timezone.utc).date().isoformat(),'errors':[]}
        return [], {'source':None,'errors':['NHL.com team section found but no reliable forward-line rows parsed']}
    except Exception as e:return [], {'source':None,'errors':[f'NHL.com article: {type(e).__name__}: {e}']}


def fetch_dailyfaceoff(team, team_name=None):
    """Last public-web fallback. If embedded schema cannot be parsed, report that honestly."""
    slug=(team_name or team).lower().replace(' ','-')
    url=DFO_URL.format(team=quote(slug))
    try:
        html=get(url).text
        matches=re.findall(r'"(?:fullName|playerName|name)"\s*:\s*"([^"]+)"[^{}]{0,300}?(?:"(?:line|lineNumber|ppUnit|powerPlayUnit)"\s*:\s*"?([1-4])"?)',html,re.I)
        rows=[]
        for name,unit in matches:
            near=html[max(0,html.find(name)-250):html.find(name)+350].lower()
            is_pp=('pp' in near or 'powerplay' in near or 'power-play' in near)
            is_line=('line' in near and not is_pp)
            if not (is_pp or is_line): continue
            rows.append({'playerName':name,'line':int(unit) if is_line else None,'powerPlayUnit':int(unit) if is_pp else None,'source':'Daily Faceoff page','sourcePath':'embedded page data','retrievedAt':datetime.now(timezone.utc).isoformat(),'sourceTeam':team.upper()})
        return rows, {'source':'Daily Faceoff page' if rows else None,'url':url,'errors':[] if rows else ['page loaded but no reliable line/PP schema parsed']}
    except Exception as e:
        return [], {'source':None,'url':url,'errors':[f'Daily Faceoff page: {type(e).__name__}: {e}']}


def fetch_web_search(team, team_name=None):
    """Search multiple public web indexes, then inspect discovered pages.

    Search titles/snippets are discovery only. Assignments are accepted only from
    explicit structured page data and remain subject to exact official-roster ID
    joins and cross-source conflict handling downstream.
    """
    from html import unescape
    import json as _json
    from urllib.parse import unquote
    team_label = team_name or team
    query = quote(f'"{team_label}" NHL projected line combinations power play PP1 PP2')
    providers = [
        ('DuckDuckGo HTML', f'https://html.duckduckgo.com/html/?q={query}', r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>'),
        ('Bing HTML', f'https://www.bing.com/search?q={query}', r'<li class="b_algo"[^>]*>.*?<h2><a[^>]+href="([^"]+)"[^>]*>(.*?)</a>'),
    ]
    attempts=[]; rows=[]; seen=set(); discovered=[]
    for provider, search_url, pattern in providers:
        try:
            html=get(search_url).text
            matches=re.findall(pattern,html,re.I|re.S)
            provider_count=0
            for href,title_html in matches:
                url=unescape(re.sub(r'<[^>]+>','',href)).strip()
                title=unescape(re.sub(r'<[^>]+>','',title_html)).strip()
                if 'uddg=' in url:
                    m=re.search(r'[?&]uddg=([^&]+)',url)
                    if m: url=unquote(m.group(1))
                if not url.startswith('http') or url in seen: continue
                if any(host in url.lower() for host in ('duckduckgo.com','bing.com/search')): continue
                seen.add(url); discovered.append((url,title,provider)); provider_count+=1
                if len(discovered)>=12: break
            attempts.append({'provider':provider,'url':search_url,'resultLinksFound':provider_count,
                             'result':'search results parsed' if provider_count else 'no parseable result links'})
        except Exception as e:
            attempts.append({'provider':provider,'url':search_url,'result':f'search failed: {type(e).__name__}: {e}'})
        # Search the second index if the first produced no candidates, or too few
        # pages to provide meaningful fallback coverage.
        if len(discovered)>=8: break
    for url,title,provider in discovered[:12]:
        page_meta={'provider':provider,'url':url,'title':title,'parsedRows':0}
        try:
            page=get(url).text
            blobs=re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',page,re.I|re.S)
            blobs += re.findall(r'<script[^>]+type=["\']application/json["\'][^>]*>(.*?)</script>',page,re.I|re.S)
            page_rows=[]
            for blob in blobs:
                try: data=_json.loads(unescape(blob.strip()))
                except Exception: continue
                parsed=parse_lineup_json(data,team,'Web-search discovered page: '+title)
                for row in parsed: row['sourcePath']=url+' :: '+row.get('sourcePath','structured data')
                page_rows.extend(parsed)
            rows.extend(page_rows); page_meta['parsedRows']=len(page_rows)
            page_meta['result']='explicit structured assignments found' if page_rows else 'page checked; no explicit structured line/PP assignments'
        except Exception as e:
            page_meta['result']=f'page fetch/parse failed: {type(e).__name__}: {e}'
        attempts.append(page_meta)
    if not discovered:
        attempts.append({'result':'all configured search indexes returned no parseable result links'})
    return rows, {'source':'General web search' if rows else None,
                  'url':providers[0][1],'attempts':attempts,
                  'errors':[] if rows else ['Multiple web indexes searched; no explicit structured line/PP assignments found']}


def fetch_deployment(team, team_name=None, mode='projected'):
    """Search all configured web sources; never silently choose between conflicts.

    In confirmed mode, projected-only sources are still searched for context but are
    not promoted to confirmed deployment. A source must explicitly identify its
    information as confirmed/actual before the resulting row can be labelled so.
    """
    attempts=[]; collected=[]
    for fn in (fetch_hockeyinsights, fetch_nhl_article, fetch_dailyfaceoff):
        rows,meta=fn(team) if fn is fetch_hockeyinsights else fn(team,team_name)
        attempts.append(meta)
        collected.extend(rows)

    # Broaden to a general web search only when the known sources have not
    # supplied both dimensions. The search result is discovery; only explicit
    # structured assignments on opened pages can become evidence rows.
    known_line=any(r.get('line') is not None for r in collected)
    known_pp=any(r.get('powerPlayUnit') is not None for r in collected)
    if not (known_line and known_pp):
        rows,meta=fetch_web_search(team,team_name)
        attempts.append(meta)
        collected.extend(rows)

    # Aggregate by exact normalized full name. If two sources disagree about a
    # deployment dimension, keep the conflict visible and leave that dimension
    # unresolved rather than using arbitrary source order as a tie-break.
    by_player={}
    for row in collected:
        key=norm_name(row.get('playerName'))
        if not key: continue
        item=by_player.setdefault(key, {
            'playerName':row.get('playerName'), 'line':None, 'powerPlayUnit':None,
            'sources':[], 'lineEvidence':[], 'powerPlayEvidence':[], 'conflicts':[],
            'retrievedAt':row.get('retrievedAt'), 'sourceTeam':team.upper()
        })
        src=row.get('source') or 'Unknown source'
        if src not in item['sources']: item['sources'].append(src)
        for field, evidence_key in (('line','lineEvidence'),('powerPlayUnit','powerPlayEvidence')):
            value=row.get(field)
            if value is None: continue
            evidence={'value':value,'source':src,'sourcePath':row.get('sourcePath'),'retrievedAt':row.get('retrievedAt')}
            if evidence not in item[evidence_key]: item[evidence_key].append(evidence)

    for item in by_player.values():
        for field,evidence_key in (('line','lineEvidence'),('powerPlayUnit','powerPlayEvidence')):
            values=sorted({e['value'] for e in item[evidence_key]})
            if len(values)==1:
                item[field]=values[0]
                item[field+'Source']=item[evidence_key][0]['source']
                item[field+'SourcePath']=item[evidence_key][0].get('sourcePath')
            elif len(values)>1:
                item['conflicts'].append({'field':field,'values':values,'evidence':item[evidence_key]})
                item[field]=None
        item['evidenceStatus']='CONFLICT — DIMENSION LEFT UNRESOLVED' if item['conflicts'] else 'CONSISTENT SOURCE EVIDENCE'

    rows=list(by_player.values())
    has_line=any(r.get('line') is not None for r in rows)
    has_pp=any(r.get('powerPlayUnit') is not None for r in rows)
    conflicts=sum(len(r.get('conflicts',[])) for r in rows)
    if mode=='confirmed':
        # None of the configured generic sources proves a confirmed in-game unit
        # merely by listing a line. Do not re-label projected information.
        for row in rows:
            row['deploymentStatus']='PROJECTED / NOT CONFIRMED'
        status='CONFIRMED DEPLOYMENT NOT ESTABLISHED — PROJECTED SOURCES SEARCHED'
    else:
        for row in rows: row['deploymentStatus']='PROJECTED'
        status=('CONFLICTS FOUND — REVIEW REQUIRED' if conflicts else
                'FOUND LINE + PP EVIDENCE' if has_line and has_pp else
                'PARTIAL — LINE + PP SOURCE SEARCH COMPLETED' if has_line or has_pp else
                'NOT FOUND — ALL SOURCES SEARCHED')
    return rows, {
        'status':status,
        'selectedSource':' + '.join(dict.fromkeys(s for r in rows for s in r.get('sources',[]))) or None,
        'sourceDate':next((x.get('sourceDate') for x in attempts if x.get('sourceDate')),None),
        'attempts':attempts, 'lineEvidenceFound':has_line, 'powerPlayEvidenceFound':has_pp,
        'conflictCount':conflicts, 'modeRequested':mode,
        'confirmedDeploymentEstablished':False,
        'sourceSearchComplete':True
    }
