import unittest
from unittest.mock import patch
import nhl_data


class ScheduleFallbackTests(unittest.TestCase):
    def test_scoreboard_fallback_when_schedule_endpoint_fails(self):
        game = {'id': 2026020001, 'gameDate': '2026-10-17', 'gameState': 'FUT',
                'homeTeam': {'id': 1, 'abbrev': 'BOS', 'name': {'default': 'Boston Bruins'}},
                'awayTeam': {'id': 2, 'abbrev': 'NYR', 'name': {'default': 'New York Rangers'}},
                'startTimeUTC': '2026-10-17T23:00:00Z'}
        with patch.object(nhl_data, 'safe', side_effect=[(None, 'schedule timeout'), ({'games': [game]}, None)]):
            rows = nhl_data.get_schedule('2026-10-17')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['gameId'], 2026020001)
        self.assertEqual(rows[0]['homeAbbrev'], 'BOS')

    def test_calendar_fallback_after_schedule_and_scoreboard_empty(self):
        game = {'id': 2026020002, 'gameDate': '2026-10-18', 'gameState': 'FUT',
                'homeTeam': {'id': 3, 'abbrev': 'MTL'}, 'awayTeam': {'id': 4, 'abbrev': 'TOR'}}
        with patch.object(nhl_data, 'safe', side_effect=[({'gameWeek': []}, None), ({'games': []}, None), ({'gamesByDate': [game]}, None)]):
            rows = nhl_data.get_schedule('2026-10-18')
        self.assertEqual([r['gameId'] for r in rows], [2026020002])

    def test_scoreboard_fallback_rejects_missing_or_wrong_game_date(self):
        wrong_date = {'id': 2026020003, 'gameDate': '2026-10-17', 'gameState': 'FUT',
                      'homeTeam': {'id': 1, 'abbrev': 'BOS'},
                      'awayTeam': {'id': 2, 'abbrev': 'NYR'}}
        missing_date = {'id': 2026020004, 'gameState': 'FUT',
                        'homeTeam': {'id': 3, 'abbrev': 'MTL'},
                        'awayTeam': {'id': 4, 'abbrev': 'TOR'}}
        correct_date = {'id': 2026020005, 'gameDate': '2026-10-18', 'gameState': 'FUT',
                        'homeTeam': {'id': 5, 'abbrev': 'SEA'},
                        'awayTeam': {'id': 6, 'abbrev': 'VAN'}}
        with patch.object(nhl_data, 'safe', side_effect=[
            ({'gameWeek': []}, None),
            ({'games': [wrong_date, missing_date]}, None),
            ({'gamesByDate': [wrong_date, correct_date]}, None),
        ]):
            rows = nhl_data.get_schedule('2026-10-18')
        self.assertEqual([r['gameId'] for r in rows], [2026020005])
        self.assertEqual(rows[0]['gameDate'], '2026-10-18')

    def test_all_failed_endpoints_raise_not_empty_slate(self):
        with patch.object(nhl_data, 'safe', side_effect=[(None, 'schedule timeout'), (None, 'score 503'), (None, 'calendar DNS')]):
            with self.assertRaises(nhl_data.NHLDataError) as ctx:
                nhl_data.get_schedule('2026-10-18')
        self.assertIn('All official NHL slate endpoints failed', str(ctx.exception))
        self.assertIn('calendar DNS', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
