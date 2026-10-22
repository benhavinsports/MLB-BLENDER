import unittest
from unittest.mock import patch
from engine import GATES, analyze, direct, goalie_hist, isgoal, historical_usage, run_slate
import nhl_data

class BlenderTests(unittest.TestCase):
    def test_slate_summary_never_claims_validation_from_trace_alone(self):
        report = run_slate([], 'projected', 8)
        self.assertEqual(report['validationSummary']['status'], 'NO GAMES RETURNED — SLATE NOT VALIDATED')
        self.assertFalse(report['validationSummary']['finalPlayerPathsCertified'])
        self.assertIn('G15 finisher protection comparison', report['validationSummary']['requiredUnresolvedAreas'])

    def test_gate_order_is_complete_and_sequential(self):
        self.assertEqual([x[0] for x in GATES], ['G0','G1','G2','G3','G4','G5','G6','G7','G8','G9','G10','G10.5','G11','G12','G14','G15','G16','G17','G18'])

    def test_direct_match_uses_both_exact_ids(self):
        rows = [
            {'shooterId': 1, 'goalieId': 9, 'type': 'shot', 'shotType': 'wrist', 'zone': 'O', 'date': '2026-10-01'},
            {'shooterId': 1, 'goalieId': 9, 'type': 'goal', 'shotType': 'wrist', 'zone': 'O', 'date': '2026-10-02'},
            {'shooterId': 2, 'goalieId': 9, 'type': 'goal', 'shotType': 'slap', 'zone': 'N'},
            {'shooterId': 1, 'goalieId': 8, 'type': 'goal', 'shotType': 'snap', 'zone': 'O'},
        ]
        result = direct(rows, 1, 9)
        self.assertEqual(result['directEvents'], 2)
        self.assertEqual(result['directGoals'], 1)
        self.assertEqual(result['directGoalShotTypes'], {'wrist': 1})

    def test_goalie_weakness_map_keeps_sample_sizes(self):
        rows = [
            {'goalieId': 9, 'type': 'shot', 'shotType': 'wrist', 'zone': 'O'},
            {'goalieId': 9, 'type': 'goal', 'shotType': 'wrist', 'zone': 'O'},
            {'goalieId': 9, 'type': 'shot', 'shotType': 'slap', 'zone': 'N'},
        ]
        result = goalie_hist(rows, 9)
        self.assertEqual(result['shotTypeOutcomes']['wrist']['shotsFaced'], 2)
        self.assertEqual(result['shotTypeOutcomes']['wrist']['goalsAllowed'], 1)
        self.assertEqual(result['shotTypeOutcomes']['slap']['observedGoalRate'], 0.0)


    def test_only_explicitly_marked_goalie_can_confirm_a_main_path(self):
        game = {'gameId': 1, 'gameDate': '2026-10-12', 'homeAbbrev': 'HOM', 'awayAbbrev': 'AWY', 'gameState': 'FUT'}
        box = {'playerByGameStats': {
            'homeTeam': {'forwards': [{'playerId': 1, 'name': {'default': 'Home Forward'}, 'position': 'C'}], 'defense': [], 'goalies': [{'playerId': 9, 'name': {'default': 'Home Starter'}, 'starter': True}, {'playerId': 10, 'name': {'default': 'Home Backup'}}]},
            'awayTeam': {'forwards': [{'playerId': 2, 'name': {'default': 'Away Forward'}, 'position': 'C'}], 'defense': [], 'goalies': [{'playerId': 8, 'name': {'default': 'Away Goalie'}}]},
        }}
        with patch('engine.get_history', return_value=([], [])):
            report = analyze({'game': game, 'boxscore': box, 'landing': {}, 'plays': {}, 'errors': []}, 'confirmed', 8)
        home_goalies = [g for g in report['goalies'] if g['team'] == 'HOM']
        statuses = {g['goalieId']: g['starterStatus'] for g in home_goalies}
        self.assertEqual(statuses[9], 'source explicitly marks starter')
        self.assertEqual(statuses[10], 'game goalie listed; not marked starter')


    def test_main_path_can_use_shared_lane_without_head_to_head_goal(self):
        game = {'gameId': 99, 'gameDate': '2026-10-12', 'homeAbbrev': 'HOM', 'awayAbbrev': 'AWY', 'gameState': 'FUT'}
        box = {'playerByGameStats': {
            'homeTeam': {'forwards': [{'playerId': 1, 'name': {'default': 'Direct Finisher'}, 'position': 'C'}], 'defense': [], 'goalies': [{'playerId': 9, 'name': {'default': 'Home Goalie'}}]},
            'awayTeam': {'forwards': [{'playerId': 3, 'name': {'default': 'Away Skater'}, 'position': 'C'}], 'defense': [], 'goalies': [{'playerId': 8, 'name': {'default': 'Away Starter'}, 'starter': True}]},
        }}
        home_events = [
            {'shooterId': 1, 'goalieId': 77, 'type': 'goal', 'shotType': 'wrist', 'zone': 'O', 'date': '2026-10-01'},
            {'shooterId': 1, 'goalieId': 77, 'type': 'shot-on-goal', 'shotType': 'wrist', 'zone': 'O', 'date': '2026-10-02'},
        ]
        away_events = [
            {'shooterId': 20, 'goalieId': 8, 'type': 'goal', 'shotType': 'wrist', 'zone': 'O', 'date': '2026-10-01'},
            {'shooterId': 21, 'goalieId': 8, 'type': 'shot-on-goal', 'shotType': 'wrist', 'zone': 'O', 'date': '2026-10-02'},
        ]
        home_payload = {'plays': []}; away_payload = {'plays': []}
        def history(team, day, limit):
            payload = home_payload if team == 'HOM' else away_payload
            return ([{'game': {'gameDate': '2026-10-03', 'gameId': 7}, 'plays': payload, 'landing': {}}], [])
        def parsed_events(payload):
            if payload is home_payload: return home_events
            if payload is away_payload: return away_events
            return []
        with patch('engine.get_history', side_effect=history), patch('engine.events', side_effect=parsed_events):
            report = analyze({'game': game, 'boxscore': box, 'landing': {}, 'plays': {}, 'errors': []}, 'confirmed', 8)
        player = next(p for p in report['players'] if p['playerId'] == 1)
        self.assertEqual(player['pathDisposition'], 'UNRESOLVED — DEPLOYMENT / FULL-GATE VALIDATION REQUIRED')
        self.assertEqual(player['evidencePathClass'], 'STARTER + SHARED LANE EVIDENCE')
        self.assertIn('G6 current deployment unresolved', player['gateTrace'][-1]['evidence'])
        self.assertEqual(player['recipientRole'], 'FINISHER')
        self.assertEqual(player['exactDirectGoalCount'], 0)  # H2H goal is not mandatory when scoring lane matches starter weakness.

    def test_historical_usage_uses_official_boxscore_toi_without_claiming_current_deployment(self):
        history = {'HOM': {'bundles': [
            {'boxscore': {'playerByGameStats': {'homeTeam': {
                'forwards': [{'playerId': 101, 'toi': '18:30', 'powerPlayToi': '03:15'}],
                'defense': []}, 'awayTeam': {}}}},
            {'boxscore': {'playerByGameStats': {'awayTeam': {
                'forwards': [{'playerId': 101, 'toi': '20:30', 'powerPlayToi': '04:15'}],
                'defense': []}, 'homeTeam': {}}}},
        ]}}
        result = historical_usage(history, 101)
        self.assertEqual(result['gamesWithBoxscoreUsage'], 2)
        self.assertEqual(result['meanToiSeconds'], 1170)
        self.assertEqual(result['meanPowerPlayToiSeconds'], 225)
        self.assertEqual(historical_usage(history, 999)['meanToiSeconds'], None)

    def test_projected_roster_falls_back_to_official_team_roster(self):
        payload = {
            'forwards': [{'id': 101, 'firstName': {'default': 'Test'}, 'lastName': {'default': 'Forward'}, 'positionCode': 'C'}],
            'defensemen': [{'id': 102, 'firstName': {'default': 'Test'}, 'lastName': {'default': 'Defense'}, 'positionCode': 'D'}],
            'goalies': [{'id': 109, 'firstName': {'default': 'Test'}, 'lastName': {'default': 'Goalie'}, 'positionCode': 'G'}],
        }
        with patch('nhl_data.safe', return_value=(payload, None)):
            rows = nhl_data.roster({}, {}, 'home', 'TST')
        self.assertEqual({x['playerId'] for x in rows}, {101, 102, 109})
        self.assertEqual(next(x for x in rows if x['playerId'] == 109)['section'], 'goalies')


    def test_official_play_by_play_event_normalization_keeps_exact_ids(self):
        payload = {'plays': [
            {'eventId': 11, 'typeDescKey': 'goal', 'periodDescriptor': {'number': 1}, 'timeInPeriod': '04:21',
             'details': {'scoringPlayerId': 101, 'goalieInNetId': 202, 'assist1PlayerId': 103, 'shotType': 'wrist', 'zoneCode': 'O', 'xCoord': 70, 'yCoord': 5}},
            {'eventId': 12, 'typeDescKey': 'blocked-shot', 'periodDescriptor': {'number': 1}, 'timeInPeriod': '05:00',
             'details': {'shootingPlayerId': 104, 'blockingPlayerId': 105, 'shotType': 'slap', 'zoneCode': 'O'}},
        ]}
        rows = nhl_data.events(payload)
        self.assertEqual(rows[0]['shooterId'], 101)
        self.assertEqual(rows[0]['goalieId'], 202)
        self.assertEqual(rows[0]['assist1Id'], 103)
        self.assertEqual(rows[1]['type'], 'blocked-shot')
        self.assertIsNone(rows[1]['goalieId'])

    def test_shot_on_goal_event_is_not_misclassified_as_a_goal(self):
        self.assertFalse(isgoal({'type': 'shot-on-goal'}))
        self.assertFalse(isgoal({'type': 'missed-shot'}))
        self.assertTrue(isgoal({'type': 'goal'}))

    def test_goalie_denominator_excludes_missed_and_blocked_attempts(self):
        rows = [
            {'goalieId': 9, 'type': 'shot-on-goal', 'shotType': 'wrist', 'zone': 'O'},
            {'goalieId': 9, 'type': 'goal', 'shotType': 'wrist', 'zone': 'O'},
            {'goalieId': 9, 'type': 'missed-shot', 'shotType': 'slap', 'zone': 'O'},
            {'goalieId': 9, 'type': 'blocked-shot', 'shotType': 'snap', 'zone': 'O'},
        ]
        result = goalie_hist(rows, 9)
        self.assertEqual(result['shotsObserved'], 2)
        self.assertEqual(result['goalsAgainstObserved'], 1)
        self.assertEqual(result['saveRateObserved'], 0.5)

    def test_empty_goalie_sample_is_unknown_not_zero_rate(self):
        result = goalie_hist([], 9)
        self.assertIsNone(result['saveRateObserved'])
        self.assertEqual(result['shotsObserved'], 0)

    def test_structural_contradictions_are_exposed_in_report(self):
        game = {'gameId': 1, 'gameDate': '2026-10-12', 'homeAbbrev': 'HOM', 'awayAbbrev': 'AWY', 'gameState': 'FUT'}
        box = {'playerByGameStats': {
            'homeTeam': {'forwards': [{'playerId': 1, 'name': {'default': 'Home Forward'}, 'position': 'C'}], 'defense': [], 'goalies': []},
            'awayTeam': {'forwards': [{'playerId': 2, 'name': {'default': 'Away Forward'}, 'position': 'C'}], 'defense': [], 'goalies': []},
        }}
        with patch('engine.get_history', return_value=([], [])):
            report = analyze({'game': game, 'boxscore': box, 'landing': {}, 'plays': {}, 'errors': ['history timeout']}, 'projected', 8)
        kinds = {c['type'] for c in report['contradictions']}
        self.assertIn('starting_goalies_unconfirmed', kinds)
        self.assertIn('source_retrieval_errors', kinds)
        g17 = next(g for g in report['gates'] if g['gate'] == 'G17')
        self.assertEqual(g17['status'], 'CONTRADICTIONS FOUND')

    def test_full_player_pool_and_gate_trace_survive_empty_history(self):
        game = {'gameId': 1, 'gameDate': '2026-10-12', 'homeAbbrev': 'HOM', 'awayAbbrev': 'AWY', 'gameState': 'FUT'}
        box = {'playerByGameStats': {
            'homeTeam': {'forwards': [{'playerId': 1, 'name': {'default': 'Home Forward'}, 'position': 'C'}], 'defense': [{'playerId': 3, 'name': {'default': 'Home D'}, 'position': 'D'}], 'goalies': [{'playerId': 9, 'name': {'default': 'Home Goalie'}}]},
            'awayTeam': {'forwards': [{'playerId': 2, 'name': {'default': 'Away Forward'}, 'position': 'C'}], 'defense': [], 'goalies': [{'playerId': 8, 'name': {'default': 'Away Goalie'}}]},
        }}
        with patch('engine.get_history', return_value=([], [])):
            report = analyze({'game': game, 'boxscore': box, 'landing': {}, 'plays': {}, 'errors': []}, 'projected', 8)
        self.assertEqual(len(report['players']), 3)
        self.assertEqual([x['gate'] for x in report['gates']], [x[0] for x in GATES])
        self.assertEqual(report['sourceCoverage']['candidateSkaters'], 3)
        self.assertTrue(all(len(p['gateTrace']) == len(GATES) for p in report['players']))
        self.assertTrue(all('routeFindings' in p for p in report['players']))
        self.assertTrue(all(p['confirmedStarterPath'] is False for p in report['players']))
        self.assertEqual(len(report['gates']), len(GATES))


    def test_run_slate_excludes_live_and_completed_games_from_pregame_pass(self):
        from engine import run_slate
        bundles = [
            {'game': {'gameId': 1, 'gameState': 'FUT', 'homeAbbrev': 'HOM', 'awayAbbrev': 'AWY', 'gameDate': '2026-10-13'}, 'boxscore': {}, 'landing': {}, 'plays': {}, 'errors': []},
            {'game': {'gameId': 2, 'gameState': 'LIVE', 'homeAbbrev': 'AAA', 'awayAbbrev': 'BBB', 'gameDate': '2026-10-13'}, 'boxscore': {}, 'landing': {}, 'plays': {}, 'errors': []},
            {'game': {'gameId': 3, 'gameState': 'FINAL', 'homeAbbrev': 'CCC', 'awayAbbrev': 'DDD', 'gameDate': '2026-10-13'}, 'boxscore': {}, 'landing': {}, 'plays': {}, 'errors': []},
        ]
        with patch('engine.analyze', return_value={'game': bundles[0]['game'], 'players': [], 'dataErrors': [], 'gates': [], 'sourceCoverage': {}}) as mocked:
            report = run_slate(bundles, 'projected', 8)
        self.assertEqual(report['gameCount'], 1)
        self.assertEqual([x['gameId'] for x in report['excludedGames']], [2, 3])
        self.assertEqual(mocked.call_count, 1)
        self.assertEqual(report['validationSummary']['excludedNonPregameGames'], 2)

    def test_unknown_game_state_is_not_admitted_to_pregame_pass(self):
        from engine import run_slate
        report = run_slate([{'game': {'gameId': 4, 'gameState': 'UNKNOWN'}, 'boxscore': {}, 'landing': {}, 'plays': {}, 'errors': []}], 'confirmed', 8)
        self.assertEqual(report['gameCount'], 0)
        self.assertEqual(report['excludedGames'][0]['gameState'], 'UNKNOWN')
        self.assertFalse(report['validationSummary']['finalPlayerPathsCertified'])

if __name__ == '__main__':
    unittest.main()
