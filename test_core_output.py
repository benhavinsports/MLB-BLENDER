import unittest
from unittest.mock import patch
from engine import run_slate

def locked_game(game_id, player_id):
    return {
        'game': {'gameId': game_id, 'homeAbbrev': f'H{game_id}', 'awayAbbrev': f'A{game_id}', 'gameState': 'FUT'},
        'players': [{
            'playerId': player_id, 'player': f'Player {player_id}', 'team': f'A{game_id}', 'opponent': f'H{game_id}',
            'pathDisposition': 'LOCKED — verified path',
            'gateTrace': [{'gate': 'G18', 'status': 'LOCKED — VERIFIED'}]
        }],
        'dataErrors': [], 'sourceCoverage': {'candidateSkaters': 1}
    }

class CoreOutputTests(unittest.TestCase):
    def test_no_games_never_fabricates_core(self):
        report = run_slate([], 'projected')
        self.assertEqual(report['coreOutput']['status'], 'NO VALID CORE — ZERO G18-LOCKED SURVIVORS')
        self.assertEqual(report['coreOutput']['core'], [])
        self.assertFalse(report['validationSummary']['finalPlayerPathsCertified'])

    @patch('engine.analyze')
    def test_core_three_uses_only_three_distinct_g18_locked_games(self, analyze):
        analyze.side_effect = [locked_game(1, 11), locked_game(2, 22), locked_game(3, 33)]
        bundles = [{'game': {'gameId': i, 'gameState': 'FUT'}} for i in (1, 2, 3)]
        report = run_slate(bundles, 'projected')
        self.assertEqual(report['coreOutput']['status'], 'CORE 3 LOCKED')
        self.assertEqual([p['playerId'] for p in report['coreOutput']['core']], [11, 22, 33])
        self.assertEqual(len({p['gameId'] for p in report['coreOutput']['core']}), 3)

    @patch('engine.analyze')
    def test_unlocked_player_never_fills_core_slot(self, analyze):
        game = locked_game(1, 11)
        game['players'][0]['pathDisposition'] = 'UNRESOLVED — required gates missing'
        game['players'][0]['gateTrace'][-1]['status'] = 'NOT VALIDATED'
        analyze.return_value = game
        report = run_slate([{'game': {'gameId': 1, 'gameState': 'FUT'}}], 'projected')
        self.assertEqual(report['coreOutput']['core'], [])
        self.assertEqual(report['coreOutput']['status'], 'NO VALID CORE — ZERO G18-LOCKED SURVIVORS')


    @patch('engine.analyze')
    def test_two_game_slate_returns_core_two_only_from_two_locked_games(self, analyze):
        analyze.side_effect = [locked_game(1, 11), locked_game(2, 22)]
        bundles = [{'game': {'gameId': i, 'gameState': 'FUT'}} for i in (1, 2)]
        report = run_slate(bundles, 'confirmed')
        self.assertEqual(report['coreOutput']['status'], 'CORE 2 LOCKED')
        self.assertEqual([p['playerId'] for p in report['coreOutput']['core']], [11, 22])

    @patch('engine.analyze')
    def test_more_than_three_locks_are_not_arbitrarily_truncated(self, analyze):
        analyze.side_effect = [locked_game(i, i * 10) for i in (1, 2, 3, 4)]
        bundles = [{'game': {'gameId': i, 'gameState': 'FUT'}} for i in (1, 2, 3, 4)]
        report = run_slate(bundles, 'projected')
        self.assertEqual(report['coreOutput']['status'], 'CORE SELECTION UNRESOLVED — CROSS-GAME COMPETITION REQUIRED')
        self.assertEqual(report['coreOutput']['core'], [])

if __name__ == '__main__':
    unittest.main()
