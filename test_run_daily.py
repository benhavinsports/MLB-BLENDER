import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_daily


class RunDailyFaultIsolationTests(unittest.TestCase):
    def test_schedule_failure_writes_explicit_incomplete_report(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(run_daily, 'get_schedule', side_effect=TimeoutError('NHL API timeout')):
                report = run_daily.run_mode('2026-10-16', 'projected', 8, Path(temp))
            self.assertEqual(report['retrievalAudit']['failedGamesOrStages'], 1)
            self.assertFalse(report['retrievalAudit']['completeSlateRetrieval'])
            self.assertEqual(report['validationSummary']['status'], 'NOT VALIDATED — SOURCE RETRIEVAL INCOMPLETE')
            self.assertEqual(report['coreOutput']['core'], [])
            saved = json.loads((Path(temp) / 'nhl_blender_2026-10-16_projected.json').read_text())
            self.assertEqual(saved['retrievalAudit']['failures'][0]['stage'], 'schedule')


    def test_empty_schedule_is_not_reported_as_complete_success(self):
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(run_daily, 'get_schedule', return_value=[]):
            report = run_daily.run_mode('2026-10-18', 'projected', 8, Path(temp))
        self.assertFalse(report['retrievalAudit']['completeSlateRetrieval'])
        self.assertEqual(report['retrievalAudit']['failures'][0]['stage'], 'schedule_empty')
        self.assertEqual(report['validationSummary']['status'], 'NOT VALIDATED — SOURCE RETRIEVAL INCOMPLETE')
        self.assertEqual(report['coreOutput']['core'], [])

    def test_one_game_failure_does_not_discard_other_game_bundle(self):
        games = [
            {'gameId': 1, 'gameDate': '2026-10-16', 'awayAbbrev': 'A', 'homeAbbrev': 'B'},
            {'gameId': 2, 'gameDate': '2026-10-16', 'awayAbbrev': 'C', 'homeAbbrev': 'D'},
        ]
        good_report = {
            'validationSummary': {'status': 'NOT VALIDATED', 'finalPlayerPathsCertified': False, 'requiredUnresolvedAreas': []},
            'coreOutput': {'status': 'NO VALID CORE', 'core': []},
        }
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(run_daily, 'get_schedule', return_value=games), \
             patch.object(run_daily, 'get_bundle', side_effect=[TimeoutError('game feed down'), {'game': games[1]}]), \
             patch.object(run_daily, 'enrich_deployment', side_effect=lambda bundle, mode: bundle), \
             patch.object(run_daily, 'run_slate', return_value=good_report) as runner:
            report = run_daily.run_mode('2026-10-16', 'projected', 8, Path(temp))
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(len(runner.call_args.args[0]), 1)
        self.assertEqual(report['retrievalAudit']['scheduledGamesFound'], 2)
        self.assertEqual(report['retrievalAudit']['gameBundlesAnalyzed'], 1)
        self.assertFalse(report['retrievalAudit']['completeSlateRetrieval'])
        self.assertEqual(report['coreOutput']['core'], [])


    def test_partial_gamecenter_feed_suppresses_core_even_when_bundle_exists(self):
        games = [{'gameId': 1, 'gameDate': '2026-10-16', 'awayAbbrev': 'A', 'homeAbbrev': 'B'}]
        good_report = {
            'validationSummary': {'status': 'VALIDATED', 'finalPlayerPathsCertified': True, 'requiredUnresolvedAreas': []},
            'coreOutput': {'status': 'CORE 3 LOCKED', 'core': [{'player': 'Example'}]},
        }
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(run_daily, 'get_schedule', return_value=games), \
             patch.object(run_daily, 'get_bundle', return_value={'game': games[0], 'errors': ['play-by-play timeout']}), \
             patch.object(run_daily, 'enrich_deployment', side_effect=lambda bundle, mode: bundle), \
             patch.object(run_daily, 'run_slate', return_value=good_report):
            report = run_daily.run_mode('2026-10-16', 'projected', 8, Path(temp))
        self.assertFalse(report['retrievalAudit']['completeSlateRetrieval'])
        self.assertEqual(report['retrievalAudit']['failures'][0]['stage'], 'game_feed_partial')
        self.assertEqual(report['coreOutput']['core'], [])
        self.assertFalse(report['validationSummary']['finalPlayerPathsCertified'])


if __name__ == '__main__':
    unittest.main()

class ScheduleRecordValidationTests(unittest.TestCase):
    def test_rejects_cross_date_and_malformed_records(self):
        valid = {'gameId': 1, 'gameDate': '2026-10-19', 'awayAbbrev': 'ANA', 'homeAbbrev': 'NYR'}
        wrong_date = {'gameId': 2, 'gameDate': '2026-10-20', 'awayAbbrev': 'SJS', 'homeAbbrev': 'TOR'}
        missing_team = {'gameId': 3, 'gameDate': '2026-10-19', 'awayAbbrev': 'AWAY', 'homeAbbrev': 'PHI'}
        rows, failures = run_daily.validate_schedule_records('2026-10-19', [valid, wrong_date, missing_team])
        self.assertEqual(rows, [valid])
        self.assertEqual(len(failures), 2)
        self.assertIn('does not match requested date', failures[0]['error'])
        self.assertIn('missing away team abbreviation', failures[1]['error'])

    def test_duplicate_game_id_blocks_slate_validation(self):
        row = {'gameId': 1, 'gameDate': '2026-10-19', 'awayAbbrev': 'ANA', 'homeAbbrev': 'NYR'}
        rows, failures = run_daily.validate_schedule_records('2026-10-19', [row, dict(row)])
        self.assertEqual(rows, [row])
        self.assertEqual(len(failures), 1)
        self.assertIn('duplicate gameId=1', failures[0]['error'])

    def test_invalid_schedule_row_suppresses_core_even_if_remaining_game_analyzes(self):
        games = [
            {'gameId': 1, 'gameDate': '2026-10-19', 'awayAbbrev': 'ANA', 'homeAbbrev': 'NYR'},
            {'gameId': 2, 'gameDate': '2026-10-20', 'awayAbbrev': 'SJS', 'homeAbbrev': 'TOR'},
        ]
        base_report = {
            'validationSummary': {'status': 'VALIDATED', 'finalPlayerPathsCertified': True, 'requiredUnresolvedAreas': []},
            'coreOutput': {'status': 'CORE 3 LOCKED', 'core': [{'player': 'Example'}]},
        }
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(run_daily, 'get_schedule', return_value=games), \
             patch.object(run_daily, 'get_bundle', return_value={'game': games[0], 'errors': []}), \
             patch.object(run_daily, 'enrich_deployment', side_effect=lambda bundle, mode: bundle), \
             patch.object(run_daily, 'run_slate', return_value=base_report):
            report = run_daily.run_mode('2026-10-19', 'projected', 8, Path(temp))
        self.assertEqual(report['retrievalAudit']['failedGamesOrStages'], 1)
        self.assertFalse(report['retrievalAudit']['completeSlateRetrieval'])
        self.assertEqual(report['coreOutput']['core'], [])
