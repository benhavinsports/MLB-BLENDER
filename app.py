from __future__ import annotations
import datetime as dt,json
import pandas as pd
import streamlit as st
from nhl_data import get_schedule,get_bundle
from engine import run_slate
st.set_page_config(page_title='NHL Blender',page_icon='🏒',layout='wide')
st.title('NHL Blender')
st.caption('Full-slate automated data analysis · projected pass → confirmed update · ordered gate audit')
st.info('This is the Blender analysis/audit workflow, not a prediction engine. The full available player pool is retained; exact player IDs are matched to goalie IDs; missing evidence is never treated as a negative finding.')
with st.sidebar:
    day=st.date_input('Slate date',dt.date.today())
    mode=st.radio('Pass',['Projected','Confirmed'])
    history=st.slider('Historical completed games per team',4,15,8)
    run=st.button('Run entire slate',type='primary',use_container_width=True)
    st.caption('Source: NHL public Web API. A goalie is not called confirmed unless the source explicitly marks a starter.')
if 'runs' not in st.session_state:st.session_state.runs={}
if run:
    with st.spinner('Fetching every scheduled game, boxscore, play-by-play, and recent team event history…'):
        try:
            games=get_schedule(day.isoformat()); bundles=[]; bar=st.progress(0)
            for i,g in enumerate(games):bundles.append(get_bundle(g));bar.progress((i+1)/max(1,len(games)))
            report=run_slate(bundles,mode.lower(),history);report['slateDate']=day.isoformat()
            key=f'{day.isoformat()}::{mode.lower()}::{report["runId"]}';st.session_state.runs[key]=report;st.session_state.active=key
            if not games:st.warning('The NHL API returned no games for this date.')
        except Exception as e:st.error(f'{type(e).__name__}: {e}')
report=st.session_state.runs.get(st.session_state.get('active')) if st.session_state.get('active') else None
if report:
    st.subheader(f'{report["slateDate"]} · {report["mode"].title()} pass')
    totals=report['games']; cov=[g['sourceCoverage'] for g in totals];c=st.columns(5)
    c[0].metric('Games',report['gameCount']);c[1].metric('Candidate skaters',sum(x['candidateSkaters'] for x in cov));c[2].metric('History games',sum(x['historicalBundles'] for x in cov));c[3].metric('Historical events',sum(x['historicalEvents'] for x in cov));c[4].metric('Retrieval errors',sum(x['retrievalErrors'] for x in cov))
    st.caption(f'Run {report["runId"]} · {report["runUTC"]}')
    st.warning('Projected and Confirmed are separate passes. Re-run Confirmed as official gamecenter data populates; if lineups or the starter are not published in the feed, those gates remain unresolved. Earlier passes stay saved.')
    tabs=st.tabs(['Full slate','Gate audit','Path board','Full player pool','Route evidence','Goalie weakness','Direct matchup audit','Player gate trace','Export / history'])
    with tabs[0]:
        st.dataframe(pd.DataFrame([{'Matchup':f'{g["game"].get("awayAbbrev")} @ {g["game"].get("homeAbbrev")}','Game ID':g['game'].get('gameId'),'Start UTC':g['game'].get('startTimeUTC'),'State':g['game'].get('gameState'),'Audit status':g['auditStatus'],'Players':g['sourceCoverage']['candidateSkaters'],'Historical games':g['sourceCoverage']['historicalBundles'],'Historical events':g['sourceCoverage']['historicalEvents'],'Errors':g['sourceCoverage']['retrievalErrors']} for g in totals]),use_container_width=True,hide_index=True)
        for g in totals:
            if g['dataErrors']:
                with st.expander(f'{g["game"].get("awayAbbrev")} @ {g["game"].get("homeAbbrev")} · retrieval errors'):st.write('\n'.join(g['dataErrors']))
    labels=[f'{g["game"].get("awayAbbrev")} @ {g["game"].get("homeAbbrev")} · {g["game"].get("gameId")}' for g in totals]
    with tabs[1]:
        if labels:
            choice=st.selectbox('Game',labels);g=totals[labels.index(choice)]
            st.dataframe(pd.DataFrame([{'Gate':x['gate'],'Rule':x['name'],'Status':x['status'],'Evidence':' | '.join(x['evidence']),'Limitation':x['limitation']} for x in g['gates']]),use_container_width=True,hide_index=True)
    with tabs[2]:
        st.caption('Categorical event-path board. A Main path requires a source-confirmed starter plus an exact shared scoring-lane match; historical head-to-head goals strengthen the path but are not mandatory. Unconfirmed goalie paths stay separate; no numeric score, forced winner, odds shortcut, or star-based filtering.')
        path_rows=[]
        for g in totals:
            label=f'{g["game"].get("awayAbbrev")}@{g["game"].get("homeAbbrev")}'
            for p in g['players']:
                group=p.get('pathDisposition','WHO — INSUFFICIENT EVENT EVIDENCE')
                path_rows.append({'game':label,'pathGroup':group,'playerId':p['playerId'],'player':p['player'],'team':p['team'],'position':p['position'],
                    'recipientRole':p.get('recipientRole'),'historicalShotsOnGoal':p['historicalShots'],'historicalAttempts':p.get('historicalAttempts',0),'historicalGoals':p['historicalGoals'],'historicalAssists':p['historicalAssists'],
                    'exactDirectGoals':p.get('exactDirectGoalCount',0),'starterDirectGoals':p.get('opposingStarterDirectGoals',0),'sharedDamageLaneCount':p.get('sharedDamageLaneCount',0),
                    'goalDates':p['datesWithGoals'],'routeFindings':' | '.join(p.get('routeFindings',[]))})
        if path_rows:
            pdf=pd.DataFrame(path_rows)
            for group in ['MAIN — CONFIRMED STARTER + SHARED DAMAGE LANE','ALT — EXACT DIRECT GOAL OR SHARED DAMAGE LANE','SHADOW — PLAYER EVENT HISTORY, MATCHUP NOT ESTABLISHED','WHO — INSUFFICIENT EVENT EVIDENCE']:
                with st.expander(f'{group} · {int((pdf.pathGroup==group).sum())}',expanded=(group.startswith('MAIN'))):
                    st.dataframe(pdf[pdf.pathGroup==group],use_container_width=True,hide_index=True)
        else: st.info('No player rows returned for this slate.')

    with tabs[3]:
        rows=[{'game':f'{g["game"].get("awayAbbrev")}@{g["game"].get("homeAbbrev")}',**{k:v for k,v in p.items() if k!='opposingGoalieMatches'}} for g in totals for p in g['players']]
        if rows:
            df=pd.DataFrame(rows);teams=st.multiselect('Filter teams',sorted(df.team.dropna().unique()));st.dataframe(df[df.team.isin(teams)] if teams else df,use_container_width=True,hide_index=True)
        else:st.info('No player candidates were returned by the available official game payloads.')
    with tabs[4]:
        st.caption('Unranked route evidence: player shot/goal history beside the opposing goalie’s observed shot-type and zone outcomes. These are source counts, not a weighted prediction score.')
        route_rows=[]
        for g in totals:
            label=f'{g["game"].get("awayAbbrev")}@{g["game"].get("homeAbbrev")}'
            for p in g.get('routeCandidates',[]):
                route_rows.append({'game':label,'playerId':p['playerId'],'player':p['player'],'team':p['team'],'opponent':p['opponent'],'position':p['position'],'historicalAttempts':p.get('historicalAttempts',p['historicalShots']),'historicalGoals':p['historicalGoals'],'shotTypes':p['shotTypes'],'goalShotTypes':p['goalShotTypes'],'datesWithShots':p['datesWithShots'],'opposingGoalies':len(p['opposingGoalieMatches']),'exactDirectEvents':sum(m['directEvents'] for m in p['opposingGoalieMatches']),'exactDirectGoals':sum(m['directGoals'] for m in p['opposingGoalieMatches']),'pathFindings':' | '.join(p.get('routeFindings',[]))})
        if route_rows: st.dataframe(pd.DataFrame(route_rows),use_container_width=True,hide_index=True)
        else: st.info('No player historical event routes could be built from returned data.')
    with tabs[5]:
        rows=[{'game':f'{g["game"].get("awayAbbrev")}@{g["game"].get("homeAbbrev")}',**p} for g in totals for p in g['goalies']]
        if rows:st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        else:st.info('No goalie event profiles available.')
        st.caption('Observed shot/save rates and shot-type goals are sample descriptions, not invented probabilities. Starter status is explicitly recorded.')
    with tabs[6]:
        rows=[]
        for g in totals:
            label=f'{g["game"].get("awayAbbrev")}@{g["game"].get("homeAbbrev")}'
            for p in g['players']:
                for m in p['opposingGoalieMatches']:rows.append({'game':label,'player':p['player'],'team':p['team'],'opponent':p['opponent'],**m})
        if rows:st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        else:st.info('No historical direct player-ID × goalie-ID pairs were found in the retrieved event history.')
        curr=[{'game':f'{g["game"].get("awayAbbrev")}@{g["game"].get("homeAbbrev")}',**m} for g in totals for m in g['currentDirectMatchups']]
        st.subheader('Current-game direct-ID events')
        if curr:st.dataframe(pd.DataFrame(curr),use_container_width=True,hide_index=True)
    with tabs[7]:
        st.caption('Every candidate keeps its own ordered gate trace. Pending evidence remains visible and does not become a failed-path claim.')
        opts=[]
        for g in totals:
            glabel=f'{g["game"].get("awayAbbrev")}@{g["game"].get("homeAbbrev")}'
            opts.extend([(f'{glabel} · {p["player"]} · {p["playerId"]}',p) for p in g['players']])
        if opts:
            selected=st.selectbox('Candidate',list(range(len(opts))),format_func=lambda i:opts[i][0])
            candidate=opts[selected][1]
            st.dataframe(pd.DataFrame([{'Gate':x['gate'],'Rule':x['name'],'Status':x['status'],'Evidence':' | '.join(map(str,x['evidence'])),'Limitation':x['limitation']} for x in candidate.get('gateTrace',[])]),use_container_width=True,hide_index=True)
        else: st.info('No candidates available for gate tracing.')

    with tabs[8]:
        st.download_button('Download complete JSON audit',json.dumps(report,indent=2,ensure_ascii=False),f'nhl_blender_{report["slateDate"]}_{report["mode"]}.json','application/json')
        gates=[];players=[];matches=[];routes=[]
        for g in totals:
            label=f'{g["game"].get("awayAbbrev")}@{g["game"].get("homeAbbrev")}'
            for x in g['gates']:gates.append({'game':label,**x,'evidence':' | '.join(x['evidence'])})
            for p in g['players']:
                players.append({'game':label,**{k:v for k,v in p.items() if k!='opposingGoalieMatches'}})
                for m in p['opposingGoalieMatches']:matches.append({'game':label,'player':p['player'],**m})
            for r in g.get('directMatchupAudit',[]): routes.append({'game':label,**r})
        if gates:st.download_button('Gate audit CSV',pd.DataFrame(gates).to_csv(index=False),'nhl_blender_gates.csv','text/csv')
        if players:st.download_button('Player pool CSV',pd.DataFrame(players).to_csv(index=False),'nhl_blender_players.csv','text/csv')
        if matches:st.download_button('Direct historical matchups CSV',pd.DataFrame(matches).to_csv(index=False),'nhl_blender_matchups.csv','text/csv')
        if routes:st.download_button('Player × goalie weakness audit CSV',pd.DataFrame(routes).to_csv(index=False),'nhl_blender_route_evidence.csv','text/csv')
        st.subheader('Saved passes this session')
        st.dataframe(pd.DataFrame([{'key':k,'runId':v['runId'],'date':v.get('slateDate'),'mode':v['mode'],'games':v['gameCount']} for k,v in st.session_state.runs.items()]),use_container_width=True,hide_index=True)
else:
    st.subheader('Ready to run')
    st.write('Choose the slate date and pass. The app fetches the full slate and recent game history for both clubs, then builds player histories, goalie event profiles, exact player-ID × goalie-ID matchup records, and the ordered audit.')
    st.write('No forced picks, no odds-based ranking, no manual evidence entry, and no fabricated missing values.')
st.divider();st.caption('Integrity boundary: evidence is separated from inference. Missing lineup, deployment, goalie, or matchup evidence stays visible; the app does not fabricate a path or force a winner.')
