#!/usr/bin/env python3
"""Code Audit 1.0: standalone, checkpointed changeset review controller."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.common import AuditError, atomic, read, writer
from audit import engine
from audit.process_review import ingest_process, package_hypothesis


def pull_request(repo, value):
    """Read only; never fetch/checkout unreviewed remote content automatically."""
    p = subprocess.run(['gh', 'pr', 'view', value, '--json', 'url'], cwd=repo,
                       capture_output=True, text=True, timeout=60)
    if p.returncode:
        raise AuditError('Unable to resolve PR via pre-provisioned authenticated gh')
    url = json.loads(p.stdout)['url']
    from urllib.parse import urlparse
    parsed = urlparse(url)
    parts = parsed.path.strip('/').split('/')
    if len(parts) != 4 or parts[2] != 'pull' or not parts[3].isdigit():
        raise AuditError('Unsupported PR URL')
    api = f'repos/{parts[0]}/{parts[1]}/pulls/{parts[3]}'
    command = ['gh', 'api', '--hostname', parsed.hostname, api]
    response = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=60)
    if response.returncode:
        raise AuditError('Unable to pin PR head/target from provider')
    data = json.loads(response.stdout)
    return {'url': url, 'api_command': command, 'H': data['head']['sha'], 'B': data['base']['sha']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='Freeze policy, scope, snapshots and required tasks')
    init.add_argument('--repo', required=True)
    group = init.add_mutually_exclusive_group(required=True)
    group.add_argument('--target')
    group.add_argument('--pr')
    init.add_argument('--base')
    init.add_argument('--config', help='Explicit trusted machine/project policy; never load policy from proposed head')
    init.add_argument('--output-root', required=True)
    init.add_argument('--profile', choices=['full', 'scan'], default='full')
    init.add_argument('--intent')
    init.add_argument('--roles', nargs='+', help='Limited focus; required coverage remains visible')
    for name in ['status', 'report', 'freshness', 'resume', 'cancel', 'pause']:
        p = commands.add_parser(name)
        p.add_argument('--run', required=True)
    sensors = commands.add_parser('run-sensors', help='Run serial pinned sensors within this controller lifetime')
    sensors.add_argument('--run', required=True)
    sensors.add_argument('--retry', action='store_true')
    for name in ['import-check', 'import-review', 'triage', 'import-process', 'hypothesis', 'add-evidence']:
        p = commands.add_parser(name)
        p.add_argument('--run', required=True)
        p.add_argument('--input', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'init':
            pr = pull_request(args.repo, args.pr) if args.pr else None
            if pr and args.base:
                raise AuditError('--base cannot override an actual PR target; use --target for another comparison')
            run = engine.initialize(args.repo, pr['H'] if pr else args.target, args.output_root,
                                    base=pr['B'] if pr else args.base, config=args.config,
                                    profile=args.profile, intent=args.intent, limited_roles=args.roles, pr_metadata=pr)
            print(json.dumps({'run_id': run.name, 'run': str(run), 'state': 'planned',
                              'lifetime': 'controller/session; existing durable host required for unattended lifetime'}))
            return 0
        run = Path(args.run).resolve()
        if args.command == 'cancel':
            engine.load(run)
            atomic(run / 'cancel.request.json', {'requested': engine.now(), 'run_id': run.name})
            if (run / '.controller.lock').exists():
                print(json.dumps({'run_id': run.name, 'state': 'cancellation-requested',
                                  'note': 'Active controller will close its owned scanner containment.'}))
                return 0
        with writer(run):
            if args.command in ('report', 'freshness', 'status'):
                output = engine.report(run)
            elif args.command == 'run-sensors':
                engine.run_sensors(run, retry=args.retry)
                output = read(run / 'verdict.json')
            elif args.command == 'resume':
                state = engine.load(run)
                (run / 'cancel.request.json').unlink(missing_ok=True)
                state['state'] = 'running'
                engine.save(run, state)
                engine.run_sensors(run, retry=True)
                output = engine.report(run)
            elif args.command in ('cancel', 'pause'):
                state = engine.load(run)
                state['state'] = 'cancelled' if args.command == 'cancel' else 'paused'
                engine.save(run, state)
                output = engine.report(run)
            elif args.command == 'add-evidence':
                engine.load(run)
                output = engine.evidence(run, args.input, 'source.txt')
            else:
                fn = {'import-check': engine.ingest_check, 'import-review': engine.ingest_review,
                      'triage': engine.triage, 'import-process': ingest_process,
                      'hypothesis': package_hypothesis}[args.command]
                output = fn(run, args.input)
            print(json.dumps(output, indent=2))
        return 0
    except KeyboardInterrupt:
        print('Interrupted; owned process containment closed. Resume the retained run.', file=sys.stderr)
        return 130
    except (AuditError, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print('Code Audit: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
