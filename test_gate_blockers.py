import unittest
from engine import final_gate_blockers

class GateBlockerTests(unittest.TestCase):
    def test_missing_deployment_and_comparison_are_explicit_blockers(self):
        player = {
            'deploymentEvidence': {}, 'confirmedStarterPath': False,
            'historicalGoals': 0, 'datesWithGoals': [],
            'finisherProtectionAudit': {'decision': 'NO DISPLACEMENT — comparative paths are not fully validated'},
            'finalCompetition': {'decision': 'UNRESOLVED — G6 deployment missing'},
            'routeFindings': []
        }
        blockers = final_gate_blockers(player, [], [player], [], 'projected')
        gates = {x['gate'] for x in blockers}
        self.assertTrue({'G6','G3/G5','G10.5/G12','G7/G11','G15','G16','G17','G8','G9'}.issubset(gates))

    def test_missing_history_is_not_misreported_as_zero_goal_sample(self):
        player = {
            'deploymentEvidence': {}, 'confirmedStarterPath': False,
            'historicalGoals': 0, 'datesWithGoals': [],
            'historicalSampleAvailable': False,
            'finisherProtectionAudit': {'decision': 'MISSING'},
            'finalCompetition': {'decision': 'MISSING'}, 'routeFindings': []
        }
        blockers = final_gate_blockers(player, [], [player], [], 'projected')
        history = next(x for x in blockers if 'sample unavailable' in x['reason'])
        self.assertIn('zero counts cannot be interpreted as observed zero production', history['reason'])
        self.assertFalse(any('no recorded historical goal as finisher' in x['reason'] for x in blockers))

    def test_observed_zero_goals_only_after_history_sample_exists(self):
        player = {
            'deploymentEvidence': {}, 'confirmedStarterPath': False,
            'historicalGoals': 0, 'datesWithGoals': [],
            'historicalSampleAvailable': True,
            'finisherProtectionAudit': {'decision': 'MISSING'},
            'finalCompetition': {'decision': 'MISSING'}, 'routeFindings': []
        }
        blockers = final_gate_blockers(player, [], [player], [], 'projected')
        self.assertTrue(any('sample retrieved, but no recorded goal' in x['reason'] for x in blockers))
        self.assertFalse(any('sample unavailable' in x['reason'] for x in blockers))

    def test_confirmed_mode_requires_explicit_confirmed_deployment(self):
        player = {
            'deploymentEvidence': {'line': 1, 'deploymentStatus': 'PROJECTED'},
            'confirmedStarterPath': True, 'historicalGoals': 1,
            'datesWithGoals': ['2026-10-01'],
            'finisherProtectionAudit': {'decision': 'COMPARISON COMPLETE'},
            'finalCompetition': {'decision': 'COMPETITION COMPLETE'},
            'routeFindings': []
        }
        blockers = final_gate_blockers(player, [], [player], [], 'confirmed')
        self.assertTrue(any(x['gate']=='G2/G6' for x in blockers))
        self.assertTrue(any(x['gate']=='G17' for x in blockers))
        self.assertTrue(any(x['gate']=='G8' for x in blockers))
        self.assertTrue(any(x['gate']=='G9' for x in blockers))


    def test_market_record_without_timestamp_pair_does_not_clear_g8(self):
        player = {
            'deploymentEvidence': {'line': 1, 'deploymentStatus': 'PROJECTED'},
            'confirmedStarterPath': True, 'historicalGoals': 1,
            'datesWithGoals': ['2026-10-01'],
            'marketFingerprint': [{'priceAmerican': 130, 'marketUpdatedAt': None}],
            'homeAwayEnvironmentSplit': {'comparativeSampleAvailable': True},
            'finisherProtectionAudit': {'decision': 'COMPARISON COMPLETE'},
            'finalCompetition': {'decision': 'COMPETITION COMPLETE'},
            'routeFindings': []
        }
        blockers = final_gate_blockers(player, [], [player], [], 'projected')
        self.assertTrue(any(x['gate'] == 'G8' and 'timestamp' in x['reason'] for x in blockers))

    def test_deployment_conflicts_and_retrieval_errors_block_g17(self):
        player = {
            'deploymentEvidence': {'line': 1, 'deploymentStatus': 'PROJECTED'},
            'confirmedStarterPath': True, 'historicalGoals': 2,
            'datesWithGoals': ['2026-10-01'],
            'finisherProtectionAudit': {'decision': 'COMPARISON COMPLETE'},
            'finalCompetition': {'decision': 'COMPETITION COMPLETE'},
            'routeFindings': []
        }
        contradictions = [
            {'type': 'conflicting_deployment_assignments', 'team': 'BOS'},
            {'type': 'source_retrieval_errors', 'count': 1},
        ]
        blockers = final_gate_blockers(player, [], [player], contradictions, 'projected')
        g17 = [x for x in blockers if x['gate'] == 'G17']
        self.assertTrue(g17)
        self.assertTrue({'conflicting_deployment_assignments', 'source_retrieval_errors'}.issubset(set(g17[0].get('findingTypes', []))))


    def test_g15_g16_only_clear_on_exact_distinct_advantage_decisions(self):
        player = {
            'deploymentEvidence': {'line': 1, 'deploymentStatus': 'CONFIRMED'},
            'confirmedStarterPath': True, 'historicalGoals': 2,
            'datesWithGoals': ['2026-10-01'],
            'marketFingerprint': [],
            'homeAwayEnvironmentSplit': {'comparativeSampleAvailable': True},
            'finisherProtectionAudit': {'decision': 'COMPARISON COMPLETE — NO DISTINCT ADVANTAGE'},
            'finalCompetition': {'decision': 'COMPETITION COMPLETE — DOMINATED ON OBSERVED DIMENSIONS'},
            'routeFindings': []
        }
        blockers = final_gate_blockers(player, [], [player], [], 'confirmed')
        g15 = next(x for x in blockers if x['gate'] == 'G15')
        g16 = next(x for x in blockers if x['gate'] == 'G16')
        self.assertIn('distinct evidence advantage', g15['reason'])
        self.assertIn('distinct evidence advantage', g16['reason'])

    def test_g15_g16_clear_only_when_both_have_distinct_advantage(self):
        player = {
            'deploymentEvidence': {'line': 1, 'deploymentStatus': 'CONFIRMED'},
            'confirmedStarterPath': True, 'historicalGoals': 2,
            'datesWithGoals': ['2026-10-01'],
            'marketFingerprint': [],
            'homeAwayEnvironmentSplit': {'comparativeSampleAvailable': True},
            'finisherProtectionAudit': {'decision': 'COMPARISON COMPLETE — DISTINCT EVIDENCE ADVANTAGE'},
            'finalCompetition': {'decision': 'COMPETITION COMPLETE — DISTINCT EVIDENCE ADVANTAGE'},
            'routeFindings': []
        }
        blockers = final_gate_blockers(player, [], [player], [], 'confirmed')
        self.assertFalse(any(x['gate'] in ('G15', 'G16') for x in blockers))

if __name__ == '__main__': unittest.main()
