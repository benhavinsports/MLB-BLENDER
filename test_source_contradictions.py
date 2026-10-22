import unittest
from engine import audit_source_contradictions

class SourceContradictionTests(unittest.TestCase):
    def test_conflicting_deployment_assignments_are_not_silently_resolved(self):
        findings = audit_source_contradictions(
            [{'playerId': 10}],
            {'AAA': {'rows': [
                {'playerId': 10, 'line': 1, 'powerPlayUnit': 1, 'sources': ['Source A']},
                {'playerId': 10, 'line': 2, 'powerPlayUnit': 1, 'sources': ['Source B']},
            ]}}, [], [])
        conflict = next(x for x in findings if x['type'] == 'conflicting_deployment_assignments')
        self.assertEqual(conflict['playerId'], 10)
        self.assertEqual(len(conflict['assignments']), 2)

    def test_multiple_goalies_marked_as_starter_is_a_conflict(self):
        findings = audit_source_contradictions([], {}, [
            {'team': 'AAA', 'goalieId': 1, 'starterStatus': 'source explicitly marks starter'},
            {'team': 'AAA', 'goalieId': 2, 'starterStatus': 'source explicitly marks starter'},
        ], [])
        self.assertIn('multiple_goalies_marked_starter', {x['type'] for x in findings})

    def test_duplicate_player_id_and_fetch_errors_are_visible(self):
        findings = audit_source_contradictions(
            [{'playerId': 5}, {'playerId': 5}], {}, [], ['boxscore timeout'])
        types = {x['type'] for x in findings}
        self.assertIn('duplicate_current_roster_player_id', types)
        self.assertIn('source_retrieval_errors', types)

    def test_no_findings_for_clean_empty_inputs(self):
        self.assertEqual(audit_source_contradictions([], {}, [], []), [])

if __name__ == '__main__':
    unittest.main()
