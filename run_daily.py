"""Run the NHL Blender with per-game fault isolation and an auditable report.

A single failed NHL API or deployment-source request must not erase successful
runs for other games, and a partial retrieval must never be described as a
complete slate validation.
"""
import argparse
import datetime
from zoneinfo import ZoneInfo
import json
import time
import requests
from pathlib import Path
from nhl_data import get_schedule, get_bundle, enrich_deployment, BASE, S
from engine import run_slate


def error_record(stage, exc, game=None):
    return {
        'stage': stage,
        'errorType': type(exc).__name__,
        'error': str(exc),
        'gameId': (game or {}).get('gameId'),
        'matchup': (
            f"{(game or {}).get('awayAbbrev', 'AWAY')} @ "
            f"{(game or {}).get('homeAbbrev', 'HOME')}"
        ) if game else None,
    }



def validate_schedule_records(day, games):
    """Reject malformed, duplicate, or cross-date games before any player analysis.

    Invalid rows are returned as audit failures and never enter the engine. A
    single invalid row still makes the slate incomplete, so a partial valid
    subset cannot be presented as the full slate.
    """
    valid = []
    failures = []
    seen_ids = set()
    for index, game in enumerate(games or []):
        game_id = game.get('gameId')
        game_date = str(game.get('gameDate') or '')[:10]
        away = game.get('awayAbbrev')
        home = game.get('homeAbbrev')
        issues = []
        if not game_id:
            issues.append('missing gameId')
        if game_date != day:
            issues.append(f'gameDate={game_date or "MISSING"} does not match requested date {day}')
        if not away or away == 'AWAY':
            issues.append('missing away team abbreviation')
        if not home or home == 'HOME':
            issues.append('missing home team abbreviation')
        if game_id and str(game_id) in seen_ids:
            issues.append(f'duplicate gameId={game_id}')
        if game_id:
            seen_ids.add(str(game_id))
        if issues:
            failures.append({
                'stage': 'schedule_record_validation',
                'errorType': 'InvalidScheduleRecord',
                'error': '; '.join(issues),
                'gameId': game_id,
                'matchup': f'{away or "AWAY"} @ {home or "HOME"}',
                'recordIndex': index,
            })
            continue
        valid.append(game)
    return valid, failures


def apply_retrieval_audit(report, games, bundles, failures):
    """Attach completeness provenance and suppress picks after any partial fetch."""
    report['retrievalAudit'] = {
        'scheduledGamesFound': len(games),
        'gameBundlesAnalyzed': len(bundles),
        'failedGamesOrStages': len(failures),
        'failures': failures,
        'completeSlateRetrieval': not failures and len(bundles) == len(games),
    }
    if failures or len(bundles) != len(games):
        report['validationSummary']['status'] = 'NOT VALIDATED — SOURCE RETRIEVAL INCOMPLETE'
        report['validationSummary']['finalPlayerPathsCertified'] = False
        report['validationSummary'].setdefault('requiredUnresolvedAreas', []).append(
            'schedule/game/deployment retrieval had one or more failures; inspect retrievalAudit'
        )
        report['coreOutput']['status'] = 'NO VALID CORE — SOURCE RETRIEVAL INCOMPLETE'
        report['coreOutput']['core'] = []
    return report

def run_mode(day, mode, history, out):
    failures = []
    try:
        games = get_schedule(day)
    except Exception as exc:
        games = []
        failures.append(error_record('schedule', exc))

    # Validate the schedule boundary before fetching any game data. A malformed
    # or cross-date row is excluded from analysis but still blocks a complete-slate
    # claim, because the retrieved slate may be incomplete or contaminated.
    if games:
        games, schedule_record_failures = validate_schedule_records(day, games)
        failures.extend(schedule_record_failures)

    # An empty response is not proof that the slate is complete: it may be an
    # off-day, a date-boundary mistake, or a schema/feed regression. Preserve it
    # as an explicit no-slate validation state instead of reporting success.
    if not games and not failures:
        failures.append(error_record('schedule_empty', RuntimeError(
            'No games returned for requested date; verify local slate date and schedule feed'
        )))

    bundles = []
    for game in games:
        try:
            bundle = get_bundle(game)
            # Preserve a partial bundle for audit visibility, but never call the
            # slate complete when any required gamecenter feed failed.
            feed_errors = list(bundle.get('errors') or [])
            bundle = enrich_deployment(bundle, mode)
            bundles.append(bundle)
            if feed_errors:
                failures.append({**error_record('game_feed_partial', RuntimeError('One or more required gamecenter feeds failed'), game), 'details': feed_errors})
        except Exception as exc:
            failures.append(error_record('game_bundle_or_deployment', exc, game))

    report = run_slate(bundles, mode, history)
    report['slateDate'] = day
    report['phaseSequence'] = {
        'requestedModes': [mode], 'phaseIndex': 1, 'phaseCount': 1,
        'freshRetrieval': True,
    }
    # A failed fetch is not a zero-evidence observation and cannot support a lock.
    report = apply_retrieval_audit(report, games, bundles, failures)
    path = out / f'nhl_blender_{day}_{mode}.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'{path} | scheduled={len(games)} | analyzed={len(bundles)} | failures={len(failures)} | mode={mode}')
    return report



def _deployment_snapshot(report):
    """Build exact-ID deployment snapshots from reports without promoting status."""
    snapshot = {}
    for game_row in report.get('games', []):
        game = game_row.get('game') or {}
        game_id = str(game.get('gameId') or '')
        matchup = f"{game.get('awayAbbrev', 'AWAY')} @ {game.get('homeAbbrev', 'HOME')}"
        for player in game_row.get('players', []):
            pid = player.get('playerId')
            if pid is None:
                continue
            dep = player.get('deploymentEvidence') or {}
            key = (game_id, str(pid))
            snapshot[key] = {
                'gameId': game_id, 'matchup': matchup,
                'playerId': pid, 'player': player.get('player'),
                'team': player.get('team'), 'line': dep.get('line'),
                'powerPlayUnit': dep.get('powerPlayUnit'),
                'evidenceStatus': dep.get('evidenceStatus'),
                'deploymentStatus': dep.get('deploymentStatus'),
                'lineEvidence': dep.get('lineEvidence', []),
                'powerPlayEvidence': dep.get('powerPlayEvidence', []),
                'sourceStatus': player.get('deploymentSourceStatus'),
            }
    return snapshot


def compare_phases(projected_report, confirmed_report):
    """Audit projected-vs-confirmed retrieval without treating projected data as confirmed."""
    projected = _deployment_snapshot(projected_report)
    confirmed = _deployment_snapshot(confirmed_report)
    keys = sorted(set(projected) | set(confirmed))
    rows = []
    for key in keys:
        before, after = projected.get(key), confirmed.get(key)
        if before is None:
            state = 'ONLY_IN_CONFIRMED_PHASE'
        elif after is None:
            state = 'MISSING_FROM_CONFIRMED_PHASE'
        elif before['line'] != after['line'] or before['powerPlayUnit'] != after['powerPlayUnit']:
            state = 'DEPLOYMENT_CHANGED_BETWEEN_PHASES'
        elif before['lineEvidence'] != after['lineEvidence'] or before['powerPlayEvidence'] != after['powerPlayEvidence']:
            state = 'ASSIGNMENT_SAME_SOURCE_EVIDENCE_CHANGED'
        else:
            state = 'NO_ASSIGNMENT_CHANGE_OBSERVED'
        rows.append({'gameId': key[0], 'playerId': key[1], 'state': state,
                     'projected': before, 'confirmedPhase': after})
    # The configured sources do not establish confirmed line/PP deployment today.
    confirmed_claims = [r for r in confirmed.values()
                        if str(r.get('deploymentStatus') or '').upper() == 'CONFIRMED']
    return {
        'status': 'AUDIT COMPLETE — CONFIRMED DEPLOYMENT NOT ESTABLISHED BY CONFIGURED SOURCES',
        'projectedRunId': projected_report.get('runId'),
        'confirmedPhaseRunId': confirmed_report.get('runId'),
        'projectedPlayers': len(projected), 'confirmedPhasePlayers': len(confirmed),
        'changedAssignments': sum(r['state'] == 'DEPLOYMENT_CHANGED_BETWEEN_PHASES' for r in rows),
        'missingFromConfirmedPhase': sum(r['state'] == 'MISSING_FROM_CONFIRMED_PHASE' for r in rows),
        'onlyInConfirmedPhase': sum(r['state'] == 'ONLY_IN_CONFIRMED_PHASE' for r in rows),
        'unsupportedConfirmedLabels': len(confirmed_claims),
        'rows': rows,
        'guardrail': 'A second retrieval pass is not confirmation. Only a source explicitly establishing confirmed game-day line/PP deployment may be labelled confirmed.'
    }

def run_source_preflight(day, out):
    """Probe official schedule endpoints and write a diagnostic-only report.

    This deliberately does not run the Blender or certify any picks. It makes
    DNS, HTTP, JSON, and endpoint-schema failures distinguishable in the user's
    actual runtime environment.
    """
    probes = [
        ('schedule', f'{BASE}/schedule/{day}'),
        ('score', f'{BASE}/score/{day}'),
        ('schedule-calendar', f'{BASE}/schedule-calendar/{day}'),
    ]
    results = []
    for name, url in probes:
        started = time.monotonic()
        row = {'source': name, 'url': url, 'requestedDate': day}
        try:
            response = requests.get(url, timeout=4, headers={'User-Agent': 'NHL-Blender-Preflight/1.29', 'Accept': 'application/json'})
            row['httpStatus'] = response.status_code
            row['elapsedMs'] = round((time.monotonic() - started) * 1000)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError('JSON root is not an object')
            row['jsonValid'] = True
            row['topLevelKeys'] = sorted(payload.keys())[:40]
            if name == 'schedule':
                games = [g for week in (payload.get('gameWeek') or [])
                         for g in (week.get('games') or [])
                         if str(g.get('gameDate') or '')[:10] == day]
                row['dateMatchedGames'] = len(games)
                row['schemaValid'] = isinstance(payload.get('gameWeek', []), list)
            elif name == 'score':
                games = [g for g in (payload.get('games') or [])
                         if str(g.get('gameDate') or '')[:10] == day]
                row['dateMatchedGames'] = len(games)
                row['schemaValid'] = isinstance(payload.get('games', []), list)
            else:
                found = []
                def walk(value):
                    if isinstance(value, dict):
                        if (value.get('id') or value.get('gameId')) and str(value.get('gameDate') or '')[:10] == day:
                            found.append(value)
                        for child in value.values(): walk(child)
                    elif isinstance(value, list):
                        for child in value: walk(child)
                walk(payload)
                row['dateMatchedGames'] = len({str(g.get('id') or g.get('gameId')) for g in found})
                row['schemaValid'] = bool(payload)
            row['status'] = 'HTTP_OK_SCHEMA_OK' if row['schemaValid'] else 'HTTP_OK_SCHEMA_UNEXPECTED'
        except Exception as exc:
            row['elapsedMs'] = round((time.monotonic() - started) * 1000)
            row['status'] = 'FAILED'
            row['errorType'] = type(exc).__name__
            row['error'] = str(exc)
            row['jsonValid'] = False
            row['schemaValid'] = False
        results.append(row)
    successful = [r for r in results if r.get('status') == 'HTTP_OK_SCHEMA_OK']
    date_rows = [r for r in successful if r.get('dateMatchedGames', 0) > 0]
    report = {
        'reportType': 'NHL_BLENDER_SOURCE_PREFLIGHT',
        'requestedDate': day,
        'status': 'ENDPOINTS_REACHABLE_DATE_ROWS_FOUND' if date_rows else ('ENDPOINTS_REACHABLE_NO_DATE_ROWS' if successful else 'NO_ENDPOINT_REACHABLE'),
        'successfulEndpoints': len(successful),
        'endpointCount': len(probes),
        'dateMatchedGamesBySource': {r['source']: r.get('dateMatchedGames', 0) for r in results},
        'probes': results,
        'guardrail': 'Diagnostic only. This does not fetch gamecenter bundles, validate deployment, execute gates, or certify a Core.'
    }
    out.mkdir(parents=True, exist_ok=True)
    path = out / f'nhl_blender_{day}_source_preflight.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'{path} | preflight={report["status"]} | reachable={len(successful)}/{len(probes)}')
    return report


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--date', default=datetime.datetime.now(ZoneInfo('America/New_York')).date().isoformat(),
                   help='Slate date in America/New_York local calendar (default: today in New York)')
    p.add_argument('--mode', choices=['projected', 'confirmed', 'both'], default='projected')
    p.add_argument('--preflight', action='store_true', help='Probe official NHL schedule endpoint reachability/schema only; do not run player analysis')
    p.add_argument('--history', type=int, default=8)
    p.add_argument('--out', default='runs')
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    if a.preflight:
        run_source_preflight(a.date, out)
        return
    modes = ['projected', 'confirmed'] if a.mode == 'both' else [a.mode]
    reports = {}
    for mode in modes:
        reports[mode] = run_mode(a.date, mode, a.history, out)
    if a.mode == 'both':
        comparison = compare_phases(reports['projected'], reports['confirmed'])
        comparison_path = out / f'nhl_blender_{a.date}_phase_comparison.json'
        comparison_path.write_text(json.dumps(comparison, indent=2, ensure_ascii=False), encoding='utf-8')
        print(f"{comparison_path} | changed={comparison['changedAssignments']} | missing_confirmed={comparison['missingFromConfirmedPhase']} | unsupported_confirmed_labels={comparison['unsupportedConfirmedLabels']}")


if __name__ == '__main__':
    main()
