"""Historical NHL shift-chart retrieval and descriptive usage summaries.

Shift charts are evidence of deployment in completed games only. They never
confirm tonight's line, PP unit, or starting lineup.
"""
from __future__ import annotations
from datetime import datetime, timezone
import requests

URL = 'https://api.nhle.com/stats/rest/en/shiftcharts?cayenneExp=gameId={game_id}'
TIMEOUT = 15
HEADERS = {'User-Agent': 'NHL-Blender-Audit/3.0', 'Accept': 'application/json'}


def clock_seconds(value):
    """Parse a shift-chart MM:SS value without assuming clock direction."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    parts = str(value).strip().split(':')
    try:
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except ValueError:
        return None
    return None


def parse_shiftchart(payload, game_id=None):
    """Return normalized shift rows; malformed/empty feeds remain unavailable."""
    if not isinstance(payload, dict):
        raise ValueError('Shift-chart payload is not a JSON object')
    rows = payload.get('data')
    if rows is None:
        rows = payload.get('shifts')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Shift-chart payload contains no shift rows')
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        pid = row.get('playerId') or row.get('player_id') or row.get('id')
        start = clock_seconds(row.get('startTime') or row.get('start_time'))
        end = clock_seconds(row.get('endTime') or row.get('end_time'))
        if pid is None or start is None or end is None:
            continue
        period = row.get('period')
        try:
            pid = int(pid)
            period = int(period) if period is not None else None
        except (TypeError, ValueError):
            continue
        duration = abs(end - start)
        if duration <= 0 or duration > 1800:
            continue
        out.append({
            'gameId': int(game_id or row.get('gameId') or row.get('game_id') or 0),
            'playerId': pid,
            'period': period,
            'startClockSeconds': start,
            'endClockSeconds': end,
            'durationSeconds': duration,
            'teamId': row.get('teamId') or row.get('team_id'),
            'teamAbbrev': row.get('teamAbbrev') or row.get('team_abbrev'),
            'shiftNumber': row.get('shiftNumber') or row.get('shift_number'),
            'source': 'NHL Stats API shiftcharts',
        })
    if not out:
        raise ValueError('Shift-chart feed returned no parseable player shifts')
    return out


def fetch_shiftchart(game_id, session=None):
    """Fetch one completed game's shift chart with explicit source provenance."""
    client = session or requests
    url = URL.format(game_id=int(game_id))
    retrieved = datetime.now(timezone.utc).isoformat()
    try:
        response = client.get(url, headers=HEADERS, timeout=TIMEOUT)
        response.raise_for_status()
        rows = parse_shiftchart(response.json(), game_id=game_id)
        return rows, {'status': 'RETRIEVED', 'url': url, 'gameId': int(game_id),
                      'retrievedAt': retrieved, 'rowCount': len(rows),
                      'source': 'NHL Stats API shiftcharts', 'limitation': 'historical shifts only; does not confirm upcoming lines or PP units'}
    except Exception as exc:
        return [], {'status': 'UNAVAILABLE', 'url': url, 'gameId': int(game_id),
                    'retrievedAt': retrieved, 'rowCount': 0,
                    'source': 'NHL Stats API shiftcharts',
                    'error': f'{type(exc).__name__}: {exc}',
                    'limitation': 'historical shifts only; does not confirm upcoming lines or PP units'}


def summarize_player_shifts(shift_rows, player_id):
    """Summarize a player's observed historical shift duration by game."""
    rows = [r for r in (shift_rows or []) if int(r.get('playerId') or 0) == int(player_id)]
    by_game = {}
    for row in rows:
        gid = int(row.get('gameId') or 0)
        if not gid:
            continue
        bucket = by_game.setdefault(gid, {'gameId': gid, 'shiftCount': 0, 'shiftSeconds': 0,
                                          'periodsObserved': set()})
        bucket['shiftCount'] += 1
        bucket['shiftSeconds'] += int(row.get('durationSeconds') or 0)
        if row.get('period') is not None:
            bucket['periodsObserved'].add(int(row['period']))
    games = []
    for gid, item in sorted(by_game.items()):
        games.append({**item, 'periodsObserved': sorted(item['periodsObserved'])})
    return {'gamesWithShiftChartData': len(games), 'shiftCount': sum(x['shiftCount'] for x in games),
            'shiftSeconds': sum(x['shiftSeconds'] for x in games), 'perGame': games,
            'evidenceSource': 'NHL Stats API shiftcharts' if games else 'no matching player shift-chart rows',
            'scope': 'historical completed-game deployment only; not tonight line/PP confirmation'}


def summarize_shift_overlap(shift_rows, player_id=None):
    """Summarize historical pairwise on-ice overlap from same-game shift intervals.

    Shift-chart clocks are compared only within the same game and period. This is
    descriptive historical evidence; it does not certify future line assignment.
    """
    rows = []
    for row in (shift_rows or []):
        try:
            pid = int(row.get('playerId') or 0)
            gid = int(row.get('gameId') or 0)
            period = int(row.get('period') or 0)
            start = int(row.get('startClockSeconds'))
            end = int(row.get('endClockSeconds'))
        except (TypeError, ValueError):
            continue
        if not pid or not gid or not period or start == end:
            continue
        lo, hi = sorted((start, end))
        rows.append({'playerId': pid, 'gameId': gid, 'period': period,
                     'lo': lo, 'hi': hi, 'teamId': row.get('teamId')})
    by_scope = {}
    for row in rows:
        by_scope.setdefault((row['gameId'], row['period'], row.get('teamId')), []).append(row)
    pairs = {}
    for (gid, period, team_id), shifts in by_scope.items():
        # Pairwise overlap of shifts; intervals are not merged because separate
        # shifts can legitimately overlap only at the boundary (zero seconds).
        for i, a in enumerate(shifts):
            for b in shifts[i + 1:]:
                if a['playerId'] == b['playerId']:
                    continue
                if player_id is not None and int(player_id) not in (a['playerId'], b['playerId']):
                    continue
                overlap = min(a['hi'], b['hi']) - max(a['lo'], b['lo'])
                if overlap <= 0:
                    continue
                one, two = sorted((a['playerId'], b['playerId']))
                key = (gid, one, two)
                item = pairs.setdefault(key, {'gameId': gid, 'playerIdA': one,
                    'playerIdB': two, 'overlapSeconds': 0, 'periods': set(),
                    'teamId': team_id})
                item['overlapSeconds'] += overlap
                item['periods'].add(period)
    by_pair = {}
    for item in pairs.values():
        key = (item['playerIdA'], item['playerIdB'])
        agg = by_pair.setdefault(key, {'playerIdA': key[0], 'playerIdB': key[1],
            'games': set(), 'overlapSeconds': 0, 'gameDetails': []})
        agg['games'].add(item['gameId'])
        agg['overlapSeconds'] += item['overlapSeconds']
        agg['gameDetails'].append({'gameId': item['gameId'],
            'overlapSeconds': item['overlapSeconds'], 'periods': sorted(item['periods'])})
    result = []
    for item in by_pair.values():
        result.append({'playerIdA': item['playerIdA'], 'playerIdB': item['playerIdB'],
            'gamesObservedTogether': len(item['games']), 'overlapSeconds': item['overlapSeconds'],
            'gameDetails': sorted(item['gameDetails'], key=lambda x: x['gameId'])})
    result.sort(key=lambda x: (-x['gamesObservedTogether'], -x['overlapSeconds'],
                               x['playerIdA'], x['playerIdB']))
    return {'pairCount': len(result), 'pairs': result,
            'evidenceSource': 'NHL Stats API shiftcharts' if rows else 'no parseable shift intervals',
            'scope': 'historical same-team interval overlap only; not a current or confirmed line assignment'}


def summarize_goal_shift_context(shift_rows, goal_events):
    """Join historical goal events to skaters whose shift intervals cover the goal clock.

    NHL shift-chart clocks are countdown clocks; play-by-play ``timeRemaining`` is
    used for the join. Events without a parseable remaining clock or team identity
    are retained as unjoined, never guessed from elapsed time.
    """
    shifts_by_scope = {}
    for row in (shift_rows or []):
        try:
            pid = int(row.get('playerId') or 0)
            gid = int(row.get('gameId') or 0)
            period = int(row.get('period') or 0)
            start = int(row.get('startClockSeconds'))
            end = int(row.get('endClockSeconds'))
        except (TypeError, ValueError):
            continue
        if not pid or not gid or not period or start == end:
            continue
        lo, hi = sorted((start, end))
        shifts_by_scope.setdefault((gid, period), []).append({
            'playerId': pid, 'teamId': row.get('teamId'), 'lo': lo, 'hi': hi
        })
    joined, unjoined = [], []
    for event in (goal_events or []):
        typ = str(event.get('type') or '').lower().replace('_', '-')
        if 'goal' not in typ or 'shot-on-goal' in typ:
            continue
        try:
            gid = int(event.get('gameId') or 0)
            period = int(event.get('period') or 0)
            remaining = clock_seconds(event.get('timeRemaining'))
            scorer = int(event.get('shooterId') or 0)
        except (TypeError, ValueError):
            remaining, scorer = None, 0
        if not gid or not period or remaining is None or not scorer or event.get('teamId') is None:
            unjoined.append({'gameId': event.get('gameId'), 'eventId': event.get('eventId'),
                             'reason': 'missing game/period/remaining-clock/scorer/team identity'})
            continue
        scope = shifts_by_scope.get((gid, period), [])
        team_rows = [r for r in scope if str(r.get('teamId')) == str(event.get('teamId'))]
        on_ice = sorted({r['playerId'] for r in team_rows if r['lo'] <= remaining <= r['hi']})
        if scorer not in on_ice:
            unjoined.append({'gameId': gid, 'eventId': event.get('eventId'),
                             'reason': 'scorer not covered by same-team shift intervals at event clock',
                             'scorerId': scorer, 'remainingClockSeconds': remaining})
            continue
        joined.append({'gameId': gid, 'eventId': event.get('eventId'), 'period': period,
                       'remainingClockSeconds': remaining, 'scorerId': scorer,
                       'teamId': event.get('teamId'), 'onIcePlayerIds': on_ice,
                       'teammatePlayerIds': [pid for pid in on_ice if pid != scorer],
                       'assistPlayerIds': [int(event[k]) for k in ('assist1Id', 'assist2Id') if event.get(k)]})
    teammate_counts = {}
    for goal in joined:
        for pid in goal['teammatePlayerIds']:
            bucket = teammate_counts.setdefault(pid, {'playerId': pid, 'onIceAtGoals': 0,
                'goalsByTeammates': 0, 'scorerGoalsWithPlayerOnIce': []})
            bucket['onIceAtGoals'] += 1
            bucket['goalsByTeammates'] += int(pid != goal['scorerId'])
            bucket['scorerGoalsWithPlayerOnIce'].append({'gameId': goal['gameId'],
                'eventId': goal['eventId'], 'scorerId': goal['scorerId']})
    return {'goalsJoinedToShiftIntervals': len(joined), 'goalsNotJoined': len(unjoined),
            'goalEvents': joined, 'unjoinedEvents': unjoined,
            'teammateGoalContext': sorted(teammate_counts.values(),
                key=lambda x: (-x['onIceAtGoals'], x['playerId'])),
            'evidenceSource': 'NHL Stats API shiftcharts + NHL play-by-play',
            'scope': 'historical only; interval joins require exact game, period, team and remaining clock; not a future deployment claim'}


def compare_deployment_to_goal_context(goal_context, deployment_rows, player_id):
    """Compare an explicit current deployment label with historical goal-shift evidence.

    This is a descriptive join only: it does not infer an assignment, claim causality,
    or turn historical co-occurrence into a gate pass. Only exact shared line/PP labels
    and exact player IDs are considered.
    """
    try:
        candidate_id = int(player_id)
    except (TypeError, ValueError):
        return {'status': 'UNRESOLVED', 'reason': 'candidate player ID unavailable',
                'matchedHistoricalGoalEvents': [], 'scope': 'descriptive only'}
    rows = [r for r in (deployment_rows or []) if isinstance(r, dict) and r.get('playerId') is not None]
    candidate = next((r for r in rows if _same_player_id(r.get('playerId'), candidate_id)), None)
    if not candidate:
        return {'status': 'UNRESOLVED', 'reason': 'no explicit deployment row for candidate',
                'matchedHistoricalGoalEvents': [], 'scope': 'descriptive only'}
    labels = []
    for field in ('line', 'powerPlayUnit'):
        value = candidate.get(field)
        if value is not None and str(value).strip():
            labels.append((field, str(value).strip().casefold()))
    if not labels:
        return {'status': 'UNRESOLVED', 'reason': 'candidate has no explicit line or PP unit label',
                'deploymentStatus': candidate.get('status') or candidate.get('deploymentStatus'),
                'matchedHistoricalGoalEvents': [], 'scope': 'descriptive only'}
    by_id = {_to_int(r.get('playerId')): r for r in rows if _to_int(r.get('playerId')) is not None}
    event_list = (goal_context or {}).get('goalEvents') or []
    matches = []
    for event in event_list:
        ids = set()
        try:
            scorer = int(event.get('scorerId') or 0)
            ids.add(scorer)
            ids.update(int(x) for x in event.get('onIcePlayerIds', []) if x is not None)
        except (TypeError, ValueError):
            continue
        if candidate_id not in ids:
            continue
        for other_id in sorted(ids - {candidate_id}):
            other = by_id.get(other_id)
            if not other:
                continue
            shared = [field for field, label in labels
                      if other.get(field) is not None and str(other.get(field)).strip().casefold() == label]
            if shared:
                matches.append({'gameId': event.get('gameId'), 'eventId': event.get('eventId'),
                    'scorerId': event.get('scorerId'), 'teammateId': other_id,
                    'sharedExplicitAssignments': shared})
    return {'status': 'MATCHED HISTORICAL CONTEXT' if matches else 'NO MATCH FOUND IN RETRIEVED SAMPLE',
            'deploymentStatus': candidate.get('status') or candidate.get('deploymentStatus'),
            'explicitAssignments': {field: candidate.get(field) for field, _ in labels},
            'matchedHistoricalGoalEventCount': len({(x.get('gameId'), x.get('eventId')) for x in matches}),
            'matchedHistoricalGoalEvents': matches,
            'historicalGoalEventsAvailable': len(event_list),
            'scope': 'descriptive only; historical on-ice context does not confirm current deployment or prove scoring causality'}


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _same_player_id(value, expected):
    parsed = _to_int(value)
    return parsed is not None and parsed == int(expected)
