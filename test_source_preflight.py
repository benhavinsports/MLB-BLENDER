import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import run_daily


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')
    def json(self):
        return self.payload


class SourcePreflightTests(unittest.TestCase):
    def test_preflight_reports_reachable_schemas_and_date_matched_rows(self):
        payloads = [
            {'gameWeek': [{'games': [{'id': 1, 'gameDate': '2026-10-19'}]}]},
            {'games': [{'id': 1, 'gameDate': '2026-10-19'}]},
            {'gameWeek': [{'games': [{'id': 1, 'gameDate': '2026-10-19'}]}]},
        ]
        with tempfile.TemporaryDirectory() as temp, patch.object(
            run_daily.requests, 'get', side_effect=[FakeResponse(p) for p in payloads]
        ):
            report = run_daily.run_source_preflight('2026-10-19', Path(temp))
            saved = json.loads((Path(temp) / 'nhl_blender_2026-10-19_source_preflight.json').read_text())
        self.assertEqual(report['status'], 'ENDPOINTS_REACHABLE_DATE_ROWS_FOUND')
        self.assertEqual(report['successfulEndpoints'], 3)
        self.assertEqual(report['dateMatchedGamesBySource']['schedule'], 1)
        self.assertEqual(saved['reportType'], 'NHL_BLENDER_SOURCE_PREFLIGHT')
        self.assertIn('does not', report['guardrail'])

    def test_preflight_distinguishes_network_failure_from_empty_date(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(
            run_daily.requests, 'get', side_effect=OSError('DNS resolution failed')
        ):
            report = run_daily.run_source_preflight('2026-10-19', Path(temp))
        self.assertEqual(report['status'], 'NO_ENDPOINT_REACHABLE')
        self.assertEqual(report['successfulEndpoints'], 0)
        self.assertTrue(all(row['status'] == 'FAILED' for row in report['probes']))

    def test_preflight_does_not_treat_other_date_as_requested_slate(self):
        payloads = [
            {'gameWeek': [{'games': [{'id': 1, 'gameDate': '2026-10-20'}]}]},
            {'games': [{'id': 2, 'gameDate': '2026-10-20'}]},
            {'gameWeek': [{'games': [{'id': 3, 'gameDate': '2026-10-20'}]}]},
        ]
        with tempfile.TemporaryDirectory() as temp, patch.object(
            run_daily.requests, 'get', side_effect=[FakeResponse(p) for p in payloads]
        ):
            report = run_daily.run_source_preflight('2026-10-19', Path(temp))
        self.assertEqual(report['status'], 'ENDPOINTS_REACHABLE_NO_DATE_ROWS')
        self.assertEqual(sum(report['dateMatchedGamesBySource'].values()), 0)


if __name__ == '__main__':
    unittest.main()
