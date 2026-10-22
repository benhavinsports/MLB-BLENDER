import unittest
from unittest.mock import Mock
from shiftchart_sources import clock_seconds, parse_shiftchart, summarize_player_shifts, fetch_shiftchart

class ShiftChartTests(unittest.TestCase):
    def test_clock_parser_handles_supported_formats(self):
        self.assertEqual(clock_seconds('12:34'), 754)
        self.assertEqual(clock_seconds('1:02:03'), 3723)
        self.assertIsNone(clock_seconds('nope'))

    def test_parser_normalizes_rows_and_rejects_invalid_durations(self):
        payload = {'data': [
            {'playerId': 10, 'period': 1, 'startTime': '18:00', 'endTime': '17:22', 'teamId': 1},
            {'playerId': 11, 'period': 1, 'startTime': '17:00', 'endTime': '17:00'},
            {'playerId': 12, 'period': 1, 'startTime': '00:00', 'endTime': '40:00'},
        ]}
        rows = parse_shiftchart(payload, 2026020001)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['gameId'], 2026020001)
        self.assertEqual(rows[0]['playerId'], 10)
        self.assertEqual(rows[0]['durationSeconds'], 38)

    def test_missing_or_unparseable_feed_is_not_zero_usage(self):
        with self.assertRaises(ValueError):
            parse_shiftchart({'data': []}, 123)
        summary = summarize_player_shifts([], 10)
        self.assertEqual(summary['gamesWithShiftChartData'], 0)
        self.assertEqual(summary['shiftSeconds'], 0)
        self.assertIn('no matching', summary['evidenceSource'])

    def test_summary_keeps_per_game_historical_usage(self):
        rows = [
            {'gameId': 2, 'playerId': 10, 'durationSeconds': 40, 'period': 1},
            {'gameId': 2, 'playerId': 10, 'durationSeconds': 35, 'period': 2},
            {'gameId': 3, 'playerId': 10, 'durationSeconds': 30, 'period': 1},
            {'gameId': 3, 'playerId': 99, 'durationSeconds': 100, 'period': 1},
        ]
        summary = summarize_player_shifts(rows, 10)
        self.assertEqual(summary['gamesWithShiftChartData'], 2)
        self.assertEqual(summary['shiftCount'], 3)
        self.assertEqual(summary['shiftSeconds'], 105)
        self.assertIn('not tonight', summary['scope'])

    def test_fetch_failure_is_audited_not_silently_empty(self):
        client = Mock()
        client.get.side_effect = RuntimeError('offline')
        rows, audit = fetch_shiftchart(123, session=client)
        self.assertEqual(rows, [])
        self.assertEqual(audit['status'], 'UNAVAILABLE')
        self.assertIn('offline', audit['error'])

if __name__ == '__main__':
    unittest.main()

class ShiftOverlapTests(unittest.TestCase):
    def test_pairwise_overlap_aggregates_games_and_periods(self):
        from shiftchart_sources import summarize_shift_overlap
        rows = [
            {'gameId': 10, 'playerId': 1, 'period': 1, 'startClockSeconds': 100, 'endClockSeconds': 80, 'teamId': 7},
            {'gameId': 10, 'playerId': 2, 'period': 1, 'startClockSeconds': 95, 'endClockSeconds': 75, 'teamId': 7},
            {'gameId': 10, 'playerId': 3, 'period': 1, 'startClockSeconds': 70, 'endClockSeconds': 60, 'teamId': 7},
            {'gameId': 11, 'playerId': 1, 'period': 2, 'startClockSeconds': 50, 'endClockSeconds': 30, 'teamId': 7},
            {'gameId': 11, 'playerId': 2, 'period': 2, 'startClockSeconds': 45, 'endClockSeconds': 25, 'teamId': 7},
        ]
        result = summarize_shift_overlap(rows)
        pair = next(x for x in result['pairs'] if (x['playerIdA'], x['playerIdB']) == (1, 2))
        self.assertEqual(pair['gamesObservedTogether'], 2)
        self.assertEqual(pair['overlapSeconds'], 30)
        self.assertIn('not a current', result['scope'])

    def test_player_filter_only_returns_pairs_involving_player(self):
        from shiftchart_sources import summarize_shift_overlap
        rows = [
            {'gameId': 10, 'playerId': 1, 'period': 1, 'startClockSeconds': 100, 'endClockSeconds': 80, 'teamId': 7},
            {'gameId': 10, 'playerId': 2, 'period': 1, 'startClockSeconds': 95, 'endClockSeconds': 75, 'teamId': 7},
            {'gameId': 10, 'playerId': 3, 'period': 1, 'startClockSeconds': 95, 'endClockSeconds': 75, 'teamId': 7},
        ]
        result = summarize_shift_overlap(rows, player_id=1)
        self.assertTrue(result['pairs'])
        self.assertTrue(all(1 in (x['playerIdA'], x['playerIdB']) for x in result['pairs']))

    def test_different_teams_and_periods_do_not_overlap(self):
        from shiftchart_sources import summarize_shift_overlap
        rows = [
            {'gameId': 10, 'playerId': 1, 'period': 1, 'startClockSeconds': 100, 'endClockSeconds': 80, 'teamId': 7},
            {'gameId': 10, 'playerId': 2, 'period': 1, 'startClockSeconds': 100, 'endClockSeconds': 80, 'teamId': 8},
            {'gameId': 10, 'playerId': 3, 'period': 2, 'startClockSeconds': 100, 'endClockSeconds': 80, 'teamId': 7},
        ]
        self.assertEqual(summarize_shift_overlap(rows)['pairCount'], 0)

class GoalShiftContextTests(unittest.TestCase):
    def test_goal_joins_only_same_game_period_team_and_remaining_clock(self):
        from shiftchart_sources import summarize_goal_shift_context
        shifts = [
            {'gameId': 100, 'playerId': 1, 'period': 1, 'startClockSeconds': 700, 'endClockSeconds': 650, 'teamId': 7},
            {'gameId': 100, 'playerId': 2, 'period': 1, 'startClockSeconds': 710, 'endClockSeconds': 640, 'teamId': 7},
            {'gameId': 100, 'playerId': 3, 'period': 1, 'startClockSeconds': 700, 'endClockSeconds': 650, 'teamId': 8},
            {'gameId': 100, 'playerId': 4, 'period': 2, 'startClockSeconds': 700, 'endClockSeconds': 650, 'teamId': 7},
        ]
        goals = [{'gameId': 100, 'eventId': 9, 'type': 'goal', 'period': 1,
                  'timeRemaining': '11:10', 'shooterId': 1, 'teamId': 7,
                  'assist1Id': 2}]
        result = summarize_goal_shift_context(shifts, goals)
        self.assertEqual(result['goalsJoinedToShiftIntervals'], 1)
        self.assertEqual(result['goalEvents'][0]['onIcePlayerIds'], [1, 2])
        self.assertEqual(result['goalEvents'][0]['teammatePlayerIds'], [2])

    def test_missing_clock_or_scorer_shift_does_not_guess_join(self):
        from shiftchart_sources import summarize_goal_shift_context
        shifts = [{'gameId': 100, 'playerId': 1, 'period': 1,
                   'startClockSeconds': 700, 'endClockSeconds': 650, 'teamId': 7}]
        goals = [
            {'gameId': 100, 'eventId': 1, 'type': 'goal', 'period': 1,
             'shooterId': 1, 'teamId': 7},
            {'gameId': 100, 'eventId': 2, 'type': 'goal', 'period': 1,
             'timeRemaining': '10:50', 'shooterId': 99, 'teamId': 7},
        ]
        result = summarize_goal_shift_context(shifts, goals)
        self.assertEqual(result['goalsJoinedToShiftIntervals'], 0)
        self.assertEqual(result['goalsNotJoined'], 2)

class DeploymentGoalContextTests(unittest.TestCase):
    def test_matches_only_exact_shared_explicit_line_or_pp_assignment(self):
        from shiftchart_sources import compare_deployment_to_goal_context
        context = {'goalEvents': [{'gameId': 9, 'eventId': 3, 'scorerId': 10,
                                  'onIcePlayerIds': [10, 11, 12]}]}
        assignments = [
            {'playerId': 10, 'line': 'L1', 'powerPlayUnit': 'PP1', 'status': 'PROJECTED'},
            {'playerId': 11, 'line': 'L1', 'powerPlayUnit': 'PP2', 'status': 'PROJECTED'},
            {'playerId': 12, 'line': 'L2', 'powerPlayUnit': 'PP2', 'status': 'PROJECTED'},
        ]
        result = compare_deployment_to_goal_context(context, assignments, 10)
        self.assertEqual(result['status'], 'MATCHED HISTORICAL CONTEXT')
        self.assertEqual(result['matchedHistoricalGoalEventCount'], 1)
        self.assertEqual(result['matchedHistoricalGoalEvents'][0]['teammateId'], 11)
        self.assertEqual(result['matchedHistoricalGoalEvents'][0]['sharedExplicitAssignments'], ['line'])
        self.assertIn('does not confirm current deployment', result['scope'])

    def test_missing_assignment_and_empty_sample_remain_unresolved_or_no_match(self):
        from shiftchart_sources import compare_deployment_to_goal_context
        no_assignment = compare_deployment_to_goal_context({'goalEvents': []}, [], 10)
        self.assertEqual(no_assignment['status'], 'UNRESOLVED')
        assignments = [{'playerId': 10, 'line': 'L1'}, {'playerId': 11, 'line': 'L2'}]
        no_match = compare_deployment_to_goal_context({'goalEvents': []}, assignments, 10)
        self.assertEqual(no_match['status'], 'NO MATCH FOUND IN RETRIEVED SAMPLE')
        self.assertEqual(no_match['matchedHistoricalGoalEventCount'], 0)
