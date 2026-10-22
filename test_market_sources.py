import unittest
from unittest.mock import Mock
from market_sources import fetch_market_fingerprint, _find_event, norm_name, market_record_integrity

class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): pass
    def json(self): return self.payload

class FakeSession:
    def __init__(self, responses): self.responses = list(responses); self.calls = []
    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params, timeout))
        value = self.responses.pop(0)
        if isinstance(value, Exception): raise value
        return FakeResponse(value)

class MarketSourceTests(unittest.TestCase):
    def setUp(self):
        self.game = {'homeName':'Boston Bruins','awayName':'New York Rangers','gameId':202601}
        self.players = [{'playerId':8478402,'name':'David Pastrnak'}, {'playerId':8479323,'name':'Artemi Panarin'}]

    def test_missing_key_is_pending_without_network(self):
        result = fetch_market_fingerprint(self.game, self.players, api_key='')
        self.assertEqual(result['status'], 'PENDING — API KEY NOT CONFIGURED')
        self.assertEqual(result['records'], {})

    def test_exact_event_and_player_market_join_preserves_bookmaker_prices(self):
        events = [{'id':'event-1','home_team':'Boston Bruins','away_team':'New York Rangers','commence_time':'2026-10-17T23:00:00Z'}]
        odds = {'id':'event-1','bookmakers':[{'key':'book-a','title':'Book A','last_update':'2026-10-17T20:00:00Z','markets':[{'key':'player_goal_scorer_anytime','last_update':'2026-10-17T20:01:00Z','outcomes':[{'name':'Yes','description':'David Pastrnak','price':130},{'name':'No','description':'David Pastrnak','price':-160},{'name':'Yes','description':'Unknown Player','price':500}]}]}]}
        session = FakeSession([events, odds])
        result = fetch_market_fingerprint(self.game, self.players, api_key='test-key', session=session)
        self.assertEqual(result['status'], 'PLAYER MARKET EVIDENCE RETRIEVED')
        self.assertEqual(result['matchedPlayerCount'], 1)
        self.assertEqual(result['records']['8478402']['outcomes'][0]['priceAmerican'], 130)
        self.assertEqual(result['records']['8478402']['outcomes'][0]['bookmaker'], 'Book A')
        self.assertEqual(len(session.calls), 2)

    def test_ambiguous_event_does_not_pick_first(self):
        events = [
            {'id':'event-1','home_team':'Boston Bruins','away_team':'New York Rangers'},
            {'id':'event-2','home_team':'Boston Bruins','away_team':'New York Rangers'},
        ]
        result = fetch_market_fingerprint(self.game, self.players, api_key='test-key', session=FakeSession([events]))
        self.assertEqual(result['status'], 'PENDING — EVENT NOT UNIQUELY MATCHED')

    def test_market_error_remains_pending_and_is_reported(self):
        result = fetch_market_fingerprint(self.game, self.players, api_key='test-key', session=FakeSession([RuntimeError('offline')]))
        self.assertEqual(result['status'], 'PENDING — MARKET RETRIEVAL FAILED')
        self.assertIn('offline', result['errors'][0])

    def test_name_normalization_is_exact_after_diacritic_cleanup(self):
        self.assertEqual(norm_name('Artemí Panarin'), norm_name('Artemi Panarin'))
        self.assertNotEqual(norm_name('Artemi Panarin'), norm_name('Artemi Panarin Jr'))

    def test_market_integrity_requires_price_and_provider_timestamp(self):
        valid = market_record_integrity([{'priceAmerican': 130, 'marketUpdatedAt': '2026-10-17T20:01:00Z'}])
        self.assertEqual(valid['usableRecordCount'], 1)
        self.assertEqual(valid['status'], 'SOURCE FIELDS VALID')
        self.assertIsNotNone(valid['latestRecordAgeSeconds'])
        self.assertIn('no arbitrary freshness threshold', valid['timestampAgePolicy'].lower())

    def test_market_integrity_rejects_missing_timestamp_and_invalid_price(self):
        result = market_record_integrity([
            {'priceAmerican': 130, 'marketUpdatedAt': None},
            {'priceAmerican': 0, 'marketUpdatedAt': '2026-10-17T20:01:00Z'},
            {'priceAmerican': -110, 'marketUpdatedAt': 'not-a-date'},
        ])
        self.assertEqual(result['usableRecordCount'], 0)
        self.assertEqual(result['invalidPriceCount'], 1)
        self.assertEqual(result['missingOrInvalidTimestampCount'], 2)

if __name__ == '__main__': unittest.main()
