import unittest
from unittest.mock import patch
from deployment_sources import parse_lineup_json, norm_name, fetch_deployment
import nhl_data

class DeploymentTests(unittest.TestCase):
    def test_json_parser_extracts_only_explicit_line_and_pp_units(self):
        data={'teamAbbrev':'NYR','players':[
            {'fullName':'Example Forward','lineNumber':2},
            {'fullName':'Example PP Forward','powerPlayUnit':'PP1'},
            {'fullName':'No Unit Player'}]}
        rows=parse_lineup_json(data,'NYR','fixture')
        self.assertEqual(len(rows),2)
        self.assertEqual(next(x for x in rows if x['playerName']=='Example Forward')['line'],2)
        self.assertEqual(next(x for x in rows if x['playerName']=='Example PP Forward')['powerPlayUnit'],1)

    def test_name_normalization_is_diacritic_safe(self):
        self.assertEqual(norm_name('Alexis Lafrenière'),norm_name('Alexis Lafreniere'))

    def test_source_fallback_continues_after_first_source_missing(self):
        with patch('deployment_sources.fetch_hockeyinsights',return_value=([],{'source':None,'errors':['not found']})), \
             patch('deployment_sources.fetch_nhl_article',return_value=([{'playerName':'Test Player','line':1,'powerPlayUnit':None,'source':'NHL.com projected lineup article'}],{'source':'NHL.com projected lineup article','errors':[]})), \
             patch('deployment_sources.fetch_dailyfaceoff',return_value=([],{'source':None,'errors':['not found']})):
            rows,meta=fetch_deployment('NYR','New York Rangers')
        self.assertEqual(rows[0]['playerName'],'Test Player')
        self.assertEqual(meta['selectedSource'],'NHL.com projected lineup article')
        self.assertGreaterEqual(len(meta['attempts']),3)
        self.assertTrue(meta['sourceSearchComplete'])

    def test_enrichment_requires_exact_roster_name_join_and_keeps_projected_status(self):
        bundle={'game':{'homeAbbrev':'NYR','awayAbbrev':'BOS','homeName':'New York Rangers','awayName':'Boston Bruins'},'boxscore':{},'landing':{}}
        roster_rows=[{'playerId':123,'name':'Alexis Lafreniere','position':'LW','section':'forwards'}]
        def fake_roster(box,land,side,team): return roster_rows if side=='home' else []
        def fake_fetch(team,team_name=None,mode="projected"):
            if team=='NYR': return ([{'playerName':'Alexis Lafrenière','line':1,'powerPlayUnit':1,'source':'NHL.com projected lineup article'}],{'status':'FOUND','selectedSource':'NHL.com projected lineup article','attempts':[]})
            return [],{'status':'NOT FOUND — ALL SOURCES SEARCHED','selectedSource':None,'attempts':[{'errors':['not found']}]}
        with patch('nhl_data.roster',side_effect=fake_roster),patch('deployment_sources.fetch_deployment',side_effect=fake_fetch):
            out=nhl_data.enrich_deployment(bundle,'confirmed')
        assignment=out['deployment']['teams']['NYR']['rows'][0]
        self.assertEqual(assignment['playerId'],123)
        self.assertEqual(assignment['deploymentStatus'],'PROJECTED')
        self.assertEqual(out['deployment']['teams']['BOS']['status'],'NOT FOUND — ALL SOURCES SEARCHED')



    def test_official_boxscore_roster_does_not_invent_line_or_pp_confirmation(self):
        box = {'playerByGameStats': {'homeTeam': {
            'forwards': [{'playerId': 10, 'name': {'default': 'Example Forward'}}],
            'defense': [],
            'goalies': [{'playerId': 20, 'name': {'default': 'Example Goalie'}, 'starter': True}],
            'scratches': [{'playerId': 30, 'name': {'default': 'Scratched Player'}}],
        }}}
        evidence = nhl_data.official_game_roster_evidence(box, 'home')
        self.assertEqual(evidence['status'], 'OFFICIAL GAME-SPECIFIC ROSTER PRESENT')
        self.assertEqual(evidence['playerCount'], 2)
        self.assertEqual(evidence['goalieStarterIds'], [20])
        self.assertEqual(evidence['scratches'][0]['playerId'], 30)
        self.assertFalse(evidence['lineAssignmentsConfirmed'])
        self.assertFalse(evidence['powerPlayAssignmentsConfirmed'])

    def test_missing_official_game_roster_is_not_treated_as_negative_roster_evidence(self):
        evidence = nhl_data.official_game_roster_evidence({}, 'away')
        self.assertEqual(evidence['status'], 'NOT AVAILABLE IN OFFICIAL BOXSCORE')
        self.assertEqual(evidence['players'], [])
        self.assertFalse(evidence['lineAssignmentsConfirmed'])

    def test_conflicting_sources_do_not_silently_choose_a_line_or_pp_unit(self):
        hi=[{'playerName':'Test Player','line':1,'powerPlayUnit':1,'source':'Hockey Insights snapshot','sourcePath':'team file'}]
        nhl=[{'playerName':'Test Player','line':2,'powerPlayUnit':1,'source':'NHL.com projected lineup article','sourcePath':'forward line 2'}]
        with patch('deployment_sources.fetch_hockeyinsights',return_value=(hi,{'source':'Hockey Insights snapshot','errors':[]})), \
             patch('deployment_sources.fetch_nhl_article',return_value=(nhl,{'source':'NHL.com projected lineup article','errors':[]})), \
             patch('deployment_sources.fetch_dailyfaceoff',return_value=([],{'source':None,'errors':[]})):
            rows,meta=fetch_deployment('NYR','New York Rangers')
        player=rows[0]
        self.assertIsNone(player['line'])
        self.assertEqual(player['powerPlayUnit'],1)
        self.assertEqual(player['evidenceStatus'],'CONFLICT — DIMENSION LEFT UNRESOLVED')
        self.assertEqual(meta['conflictCount'],1)

    def test_confirmed_mode_never_promotes_projected_web_lines_to_confirmed(self):
        rows_fixture=[{'playerName':'Test Player','line':1,'powerPlayUnit':1,'source':'NHL.com projected lineup article','sourcePath':'forward line 1'}]
        with patch('deployment_sources.fetch_hockeyinsights',return_value=([],{'source':None,'errors':[]})), \
             patch('deployment_sources.fetch_nhl_article',return_value=(rows_fixture,{'source':'NHL.com projected lineup article','errors':[]})), \
             patch('deployment_sources.fetch_dailyfaceoff',return_value=([],{'source':None,'errors':[]})):
            rows,meta=fetch_deployment('NYR','New York Rangers',mode='confirmed')
        self.assertEqual(rows[0]['deploymentStatus'],'PROJECTED / NOT CONFIRMED')
        self.assertFalse(meta['confirmedDeploymentEstablished'])
        self.assertIn('NOT ESTABLISHED',meta['status'])

    def test_general_web_search_runs_when_known_sources_miss_a_deployment_dimension(self):
        line_rows=[{'playerName':'Test Player','line':1,'powerPlayUnit':None,'source':'NHL.com projected lineup article'}]
        with patch('deployment_sources.fetch_hockeyinsights',return_value=([],{'source':None,'errors':['not found']})), \
             patch('deployment_sources.fetch_nhl_article',return_value=(line_rows,{'source':'NHL.com projected lineup article','errors':[]})), \
             patch('deployment_sources.fetch_dailyfaceoff',return_value=([],{'source':None,'errors':['not found']})), \
             patch('deployment_sources.fetch_web_search',return_value=([],{'source':None,'attempts':[{'result':'searched'}],'errors':[]})) as web_search:
            rows,meta=fetch_deployment('NYR','New York Rangers')
        web_search.assert_called_once()
        self.assertEqual(len(meta['attempts']),4)
        self.assertTrue(meta['sourceSearchComplete'])

if __name__=='__main__': unittest.main()
