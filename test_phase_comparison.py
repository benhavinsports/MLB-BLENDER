import unittest
from run_daily import compare_phases


def report(run_id, mode, players):
    return {
        'runId': run_id,
        'games': [{
            'game': {'gameId': 2026020001, 'awayAbbrev': 'AAA', 'homeAbbrev': 'BBB'},
            'players': players,
        }],
    }


class PhaseComparisonTests(unittest.TestCase):
    def test_detects_assignment_change_by_exact_player_id(self):
        projected = report('p1', 'projected', [
            {'playerId': 10, 'player': 'Player A', 'team': 'AAA',
             'deploymentEvidence': {'line': 1, 'powerPlayUnit': 1, 'lineEvidence': [], 'powerPlayEvidence': []}},
        ])
        confirmed = report('c1', 'confirmed', [
            {'playerId': 10, 'player': 'Player A', 'team': 'AAA',
             'deploymentEvidence': {'line': 2, 'powerPlayUnit': 1, 'lineEvidence': [], 'powerPlayEvidence': [], 'deploymentStatus': 'PROJECTED / NOT CONFIRMED'}},
        ])
        result = compare_phases(projected, confirmed)
        self.assertEqual(result['changedAssignments'], 1)
        self.assertEqual(result['rows'][0]['state'], 'DEPLOYMENT_CHANGED_BETWEEN_PHASES')
        self.assertIn('NOT ESTABLISHED', result['status'])

    def test_missing_confirmed_phase_player_is_not_silently_preserved(self):
        projected = report('p1', 'projected', [
            {'playerId': 10, 'player': 'Player A', 'team': 'AAA',
             'deploymentEvidence': {'line': 1, 'powerPlayUnit': None}},
        ])
        confirmed = report('c1', 'confirmed', [])
        result = compare_phases(projected, confirmed)
        self.assertEqual(result['missingFromConfirmedPhase'], 1)
        self.assertEqual(result['rows'][0]['state'], 'MISSING_FROM_CONFIRMED_PHASE')

    def test_does_not_count_projected_status_as_confirmed(self):
        projected = report('p1', 'projected', [])
        confirmed = report('c1', 'confirmed', [
            {'playerId': 10, 'player': 'Player A', 'team': 'AAA',
             'deploymentEvidence': {'line': 1, 'powerPlayUnit': 1, 'deploymentStatus': 'PROJECTED / NOT CONFIRMED'}},
        ])
        result = compare_phases(projected, confirmed)
        self.assertEqual(result['unsupportedConfirmedLabels'], 0)
        self.assertEqual(result['onlyInConfirmedPhase'], 1)

    def test_flags_explicit_confirmed_label_as_contract_violation(self):
        result = compare_phases(report('p', 'projected', []), report('c', 'confirmed', [
            {'playerId': 7, 'player': 'Player B', 'team': 'BBB',
             'deploymentEvidence': {'deploymentStatus': 'CONFIRMED'}},
        ]))
        self.assertEqual(result['unsupportedConfirmedLabels'], 1)


if __name__ == '__main__':
    unittest.main()
