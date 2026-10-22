"""Optional direct player anytime-goal market evidence from The Odds API.

Market records are evidence only. They are never converted to a prediction score,
used to rank players, or treated as proof that a player will score.
Requires ODDS_API_KEY and an account tier that includes NHL player props.
"""
from __future__ import annotations
import os
import re
import unicodedata
from datetime import datetime, timezone
import requests

BASE = 'https://api.the-odds-api.com/v4'
SPORT = 'icehockey_nhl'
MARKET = 'player_goal_scorer_anytime'


def norm_name(value):
    value = unicodedata.normalize('NFKD', str(value or ''))
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r'[^a-z0-9]+', '', value.lower())


def _team_name(game, side):
    return (game.get(f'{side}Name') or '').strip()


def _find_event(events, game):
    home, away = norm_name(_team_name(game, 'home')), norm_name(_team_name(game, 'away'))
    if not home or not away:
        return None
    matches = [e for e in events if norm_name(e.get('home_team')) == home and norm_name(e.get('away_team')) == away]
    return matches[0] if len(matches) == 1 else None



def market_record_integrity(outcomes):
    """Validate source-level market fields without inventing a freshness cutoff.

    A record is usable only when its American price is numeric and its source
    update timestamp parses as ISO-8601. Age is reported, never converted into
    a pass/fail threshold that the user did not define.
    """
    checked_at = datetime.now(timezone.utc)
    valid = 0
    missing_timestamp = 0
    invalid_price = 0
    timestamps = []
    for row in outcomes or []:
        price = row.get('priceAmerican')
        try:
            if isinstance(price, bool) or price is None or float(price) == 0:
                raise ValueError('invalid American price')
            float(price)
        except (TypeError, ValueError):
            invalid_price += 1
            continue
        raw = row.get('marketUpdatedAt')
        try:
            stamp = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            missing_timestamp += 1
            continue
        valid += 1
        timestamps.append(stamp.astimezone(timezone.utc))
    latest = max(timestamps) if timestamps else None
    return {
        'usableRecordCount': valid,
        'invalidPriceCount': invalid_price,
        'missingOrInvalidTimestampCount': missing_timestamp,
        'latestMarketUpdatedAtUTC': latest.isoformat() if latest else None,
        'latestRecordAgeSeconds': max(0, int((checked_at - latest).total_seconds())) if latest else None,
        'timestampAgePolicy': 'Age reported for transparency; no arbitrary freshness threshold applied.',
        'status': 'SOURCE FIELDS VALID' if valid else 'PENDING — NO VALID PRICE + SOURCE TIMESTAMP PAIR',
    }

def fetch_market_fingerprint(game, player_rows, api_key=None, session=None):
    """Return exact-name-joined anytime-goal odds evidence, preserving provenance.

    A missing key, unsupported plan, absent event, absent market, or unmatched
    name remains pending. No player is inferred from team odds or name similarity.
    """
    key = api_key or os.getenv('ODDS_API_KEY')
    result = {
        'provider': 'The Odds API', 'market': MARKET,
        'status': 'PENDING — API KEY NOT CONFIGURED' if not key else 'PENDING — NOT RETRIEVED',
        'retrievedAtUTC': datetime.now(timezone.utc).isoformat(),
        'matchedPlayerCount': 0, 'bookmakerCount': 0, 'records': {}, 'errors': [],
        'limitations': ['Market listing is contextual evidence only; no odds-based ranking or probability conversion.',
                        'Exact normalized player-name join only; ambiguous event or player matches remain unresolved.'],
    }
    if not key:
        return result
    http = session or requests.Session()
    try:
        resp = http.get(f'{BASE}/sports/{SPORT}/events', params={'apiKey': key}, timeout=18)
        resp.raise_for_status()
        events = resp.json()
        if not isinstance(events, list):
            raise ValueError('Unexpected event-list payload type')
        event = _find_event(events, game)
        if not event:
            result['status'] = 'PENDING — EVENT NOT UNIQUELY MATCHED'
            result['errors'].append('No unique exact home/away team-name match in odds event list')
            return result
        resp = http.get(f"{BASE}/sports/{SPORT}/events/{event['id']}/odds", params={
            'apiKey': key, 'regions': 'us', 'markets': MARKET, 'oddsFormat': 'american'
        }, timeout=18)
        resp.raise_for_status()
        payload = resp.json()
        books = payload.get('bookmakers', []) if isinstance(payload, dict) else []
        player_index = {}
        for player in player_rows:
            nk = norm_name(player.get('name') or player.get('player'))
            if nk:
                player_index.setdefault(nk, []).append(player)
        records = {}
        for book in books:
            book_name = book.get('title') or book.get('key') or 'unknown bookmaker'
            for market in book.get('markets', []) or []:
                if market.get('key') != MARKET:
                    continue
                updated = market.get('last_update') or book.get('last_update')
                for outcome in market.get('outcomes', []) or []:
                    if str(outcome.get('name', '')).strip().lower() not in ('yes', 'over'):
                        continue
                    description = outcome.get('description') or outcome.get('participant') or ''
                    nk = norm_name(description)
                    matched = player_index.get(nk, [])
                    if len(matched) != 1:
                        continue
                    pid = str(matched[0].get('playerId'))
                    records.setdefault(pid, {'playerId': matched[0].get('playerId'), 'player': matched[0].get('name') or matched[0].get('player'), 'market': MARKET, 'outcomes': []})
                    records[pid]['outcomes'].append({'bookmaker': book_name, 'priceAmerican': outcome.get('price'), 'marketUpdatedAt': updated, 'outcome': outcome.get('name'), 'description': description})
        for record in records.values():
            record['integrity'] = market_record_integrity(record.get('outcomes', []))
        result.update({'eventId': event.get('id'), 'eventCommenceTime': event.get('commence_time'), 'records': records,
                       'matchedPlayerCount': len(records), 'bookmakerCount': len({o['bookmaker'] for v in records.values() for o in v['outcomes']}),
                       'status': 'PLAYER MARKET EVIDENCE RETRIEVED' if records else 'PENDING — NO EXACT PLAYER MARKET MATCH',
                       'integritySummary': market_record_integrity([o for v in records.values() for o in v['outcomes']])})
        return result
    except Exception as exc:
        result['status'] = 'PENDING — MARKET RETRIEVAL FAILED'
        result['errors'].append(f'{type(exc).__name__}: {exc}')
        return result
