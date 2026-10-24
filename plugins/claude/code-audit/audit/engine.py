"""Frozen plans, provenance validation, review ingestion, and deterministic readiness."""
import copy
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import uuid

from . import SCHEMA, VERSION
from .adapters import VERSION as ADAPTER_VERSION, compare, parse
from .common import AuditError, atomic, digest, inside, now, read, relative, require, sha
from .processes import execute
from .rendering import render
from .scope import commit, git, integration, pin, policy, snapshot

ROLES = {'correctness', 'test-adequacy', 'security', 'duplication-reuse',
         'architecture', 'platform', 'cross-cutting', 'process-efficiency'}
TERMINAL = {'completed', 'not_applicable'}
STATES = {'queued', 'running', 'completed', 'partial', 'failed', 'unavailable', 'cancelled', 'not_applicable'}
SOURCE_EXTENSIONS = {'.cs', '.py', '.js', '.ts', '.tsx', '.jsx', '.cpp', '.h', '.c', '.rs',
                     '.go', '.java', '.kt', '.swift', '.xaml', '.xml', '.json', '.yml', '.yaml',
                     '.toml', '.props', '.targets', '.csproj', '.sln', '.sql', '.sh', '.ps1'}


def file_manifest(folder):
    return {p.relative_to(folder).as_posix(): sha(p) for p in sorted(Path(folder).rglob('*')) if p.is_file()}


def implementation_digest():
    root = Path(__file__).resolve().parents[1]
    return digest({p.relative_to(root).as_posix(): sha(p) for p in sorted(root.rglob('*'))
                   if p.is_file() and '__pycache__' not in p.parts and
                   p.relative_to(root).parts[0] in ('audit', 'scripts', 'agents', 'references', 'skills', 'config')})


def load(run):
    run = Path(run).resolve()
    state = read(run / 'run.json')
    if state['input_digest'] != digest(state['inputs']):
        raise AuditError('Frozen run inputs changed')
    if state['inputs']['component_version'] != VERSION:
        raise AuditError('Resume requires the original controller version')
    if state['inputs']['implementation_digest'] != implementation_digest():
        raise AuditError('Controller, expert prompts or contracts changed; create a new run')
    for name, manifest in state['inputs']['snapshot_manifests'].items():
        if file_manifest(run / 'snapshots' / name) != manifest:
            raise AuditError('Immutable snapshot changed: ' + name)
    return state


def save(run, state):
    atomic(Path(run) / 'run.json', state)


def task(task_id, kind, capability, paths, snapshot_id, required=True):
    return {'id': task_id, 'kind': kind, 'capability': capability, 'required': required,
            'paths': paths, 'snapshot': snapshot_id}


def initialize(repo, target, output, base=None, config=None, profile='full', intent=None,
               limited_roles=None, pr_metadata=None):
    if not output:
        raise AuditError('An explicit --output-root is required')
    base_ref = base
    pinned_base = None
    if not config:
        if not base_ref:
            raise AuditError('Supply --base or --config; target branch is never guessed')
        pinned_base = commit(repo, base_ref)
    config_data, policy_origin = policy(repo, pinned_base, config)
    base_ref = base_ref or config_data.get('target_branch')
    if not base_ref:
        raise AuditError('No PR target, explicit base, or trusted target_branch')
    pinned_base = pinned_base or commit(repo, base_ref)
    repo, scope = pin(repo, target, pinned_base)
    scope['base_ref'] = base_ref
    output = Path(output).resolve()
    package = Path(__file__).resolve().parents[1]
    if output.is_relative_to(repo) or output.is_relative_to(package):
        raise AuditError('Output must be outside the source checkout and plugin')
    destinations = config_data.get('output_destinations', [])
    if destinations and not any(output.is_relative_to(Path(x).resolve()) for x in destinations):
        raise AuditError('Output is outside trusted approved destinations')
    output.mkdir(parents=True, exist_ok=True)
    run = output / (dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:12])
    run.mkdir(mode=0o700)
    for folder in ['snapshots', 'tasks', 'evidence', 'hypotheses']:
        (run / folder).mkdir()
    try:
        omissions = []
        names = ['M', 'H', 'B'] + (['A'] if scope['A'] != scope['M'] else [])
        for name in names:
            omissions.extend(dict(x, snapshot=name) for x in snapshot(repo, scope[name], run / 'snapshots' / name))
        integration(repo, scope, run)
        omissions.extend(dict(x, snapshot='I') for x in scope.get('integration_omissions', []))
        if scope['I'] == scope['H']:
            shutil.copytree(run / 'snapshots' / 'H', run / 'snapshots' / 'I')
        changed = [x['path'] for x in scope['changes']]
        substantive = [p for p in changed if Path(p).suffix.lower() in SOURCE_EXTENSIONS or
                       Path(p).name in ('Dockerfile', 'Makefile') or not Path(p).suffix]
        # Cross-cutting review owns every path, including docs, resources and deletions.
        roles = {'cross-cutting'}
        if substantive:
            roles.update({'correctness', 'test-adequacy', 'security', 'duplication-reuse', 'architecture'})
        if any(p.lower().endswith(('.xaml', '.cs', '.csproj', '.vcxproj')) for p in changed):
            roles.add('platform')
        roles.update(config_data.get('required_roles', []))
        if roles - ROLES:
            raise AuditError('Unknown required role')
        tasks = [task('review-' + r, 'expert', r, changed, scope['H']) for r in sorted(roles)]
        required = set(config_data.get('required_capabilities', ['secrets', 'dependencies', 'tests']))
        required.update({'secrets', 'dependencies'})
        for cap in sorted(required | set(config_data.get('sensors', {}))):
            if not re.fullmatch(r'[a-z][a-z0-9-]{0,60}', cap):
                raise AuditError('Invalid capability identifier')
            snap = scope['I'] if cap in ('build', 'tests', 'runtime') else scope['H']
            tasks.append(task('check-' + cap, 'sensor', cap, changed, snap, cap in required))
        if limited_roles:
            if set(limited_roles) - ROLES:
                raise AuditError('Unknown selected role')
        policy_copy = copy.deepcopy(config_data)
        provisioned = {}
        for cap, sensor in policy_copy.get('sensors', {}).items():
            provisioned[cap] = {field: sha(Path(sensor[field])) for field in ('executable', 'rules_file')
                                if sensor.get(field) and Path(sensor[field]).is_absolute() and Path(sensor[field]).is_file()}
        intent_record = None
        if intent:
            intent_record = Path(intent).read_text(encoding='utf-8')
            atomic(run / 'evidence' / 'intent.txt', intent_record)
        inputs = {'schema_version': SCHEMA, 'component_version': VERSION, 'repo': str(repo),
                  'implementation_digest': implementation_digest(),
                  'scope': scope, 'policy': policy_copy, 'policy_origin': policy_origin,
                  'policy_digest': digest(policy_copy), 'profile': profile,
                  'limited_roles': limited_roles, 'intent_sha256': digest(intent_record),
                  'intent_available': intent is not None, 'pr_metadata': pr_metadata,
                  'tasks': tasks, 'omissions': omissions,
                  'provisioned_files': provisioned,
                  'snapshot_manifests': {p.name: file_manifest(p) for p in (run / 'snapshots').iterdir()},
                  'execution_host': 'session-only; attach commands to an existing durable job host for independent lifetime',
                  'cache': 'no cross-run reuse; validated completed attempts only within this frozen run'}
        state = {'schema_version': SCHEMA, 'run_id': run.name, 'created': now(),
                 'inputs': inputs, 'input_digest': digest(inputs), 'state': 'planned',
                 'results': {}, 'finding_batches': [], 'process_reviews': [], 'hypotheses': []}
        save(run, state)
        report(run)
        return run
    except Exception as exc:
        atomic(run / 'initialization-failure.json', {'state': 'failed', 'reason': str(exc), 'time': now()})
        raise


def definition(state, task_id):
    for item in state['inputs']['tasks']:
        if item['id'] == task_id:
            return item
    raise AuditError('Task is outside the frozen plan')


def evidence(run, source, name):
    source = Path(source)
    if source.is_symlink() or not source.is_file():
        raise AuditError('Evidence must be an existing regular file')
    destination = Path(run) / 'evidence' / (uuid.uuid4().hex + '-' + name)
    shutil.copyfile(source, destination)
    return {'path': destination.relative_to(run).as_posix(), 'sha256': sha(destination)}


def check_ref(run, reference):
    require(reference, ['path', 'sha256'])
    path = inside(run, reference['path'])
    if not path.is_file() or sha(path) != reference['sha256']:
        raise AuditError('Missing or modified evidence: ' + reference['path'])
    return path


def get_attempt(state, task_id):
    records = state['results'].get(task_id, [])
    return records[-1] if records else None


def attempt(state, definition, status, reason=None):
    if status not in STATES:
        raise AuditError('Unknown task state')
    count = len(state['results'].get(definition['id'], [])) + 1
    return {'schema_version': SCHEMA, 'run_id': state['run_id'], 'task_id': definition['id'],
            'attempt_id': f'{count:04d}-{uuid.uuid4().hex[:8]}', 'capability': definition['capability'],
            'required': definition['required'], 'state': status, 'snapshot': definition['snapshot'],
            'scope_digest': digest(definition['paths']), 'started': now(), 'ended': now(),
            'tool': None, 'tool_version': None, 'adapter_version': ADAPTER_VERSION,
            'config_digest': state['inputs']['policy_digest'], 'environment': None,
            'dependencies': None, 'advisory_database': None, 'resource_usage': None,
            'exit_code': None, 'parser_status': 'not_run', 'record_count': None,
            'omissions': [], 'outputs': [], 'reason': reason, 'observations': [],
            'product_failure': False, 'cached': False}


def record(run, state, result):
    folder = Path(run) / 'tasks' / result['task_id'] / result['attempt_id']
    folder.mkdir(parents=True, exist_ok=True)
    atomic(folder / 'result.json', result)
    state['results'].setdefault(result['task_id'], []).append(result)
    state['state'] = 'running'
    save(run, state)


def source_location(run, state, location):
    require(location, ['snapshot', 'path', 'start_line', 'end_line'])
    scope = state['inputs']['scope']
    labels = [name for name in ('H', 'M', 'B', 'I', 'A') if scope[name] == location['snapshot']]
    if not labels:
        if location['snapshot'] not in scope['history_commits']:
            raise AuditError('Source evidence belongs to another snapshot')
        relative(location['path'])
        content = git(state['inputs']['repo'], 'show', location['snapshot'] + ':' + location['path'], binary=True)
        import hashlib
        content_sha256 = hashlib.sha256(content).hexdigest()
        lines = content.decode('utf-8').splitlines()
    else:
        file = inside(Path(run) / 'snapshots' / labels[0], location['path'])
        if not file.is_file():
            raise AuditError('Source evidence file is unavailable')
        lines = file.read_text(encoding='utf-8').splitlines()
        content_sha256 = sha(file)
    start, end = location['start_line'], location['end_line']
    if type(start) is not int or type(end) is not int or not 1 <= start <= end <= len(lines):
        raise AuditError('Invalid source line range')
    return dict(location, content_sha256=content_sha256)


def validate_findings(run, state, findings, reviewer):
    if not isinstance(findings, list):
        raise AuditError('Findings must be an array')
    validated = []
    for f in findings:
        require(f, ['id', 'category', 'priority', 'evidence_status', 'attribution', 'locations',
                    'trigger', 'impact', 'evidence', 'reasoning', 'remediation', 'disposition'])
        if not re.fullmatch(r'[A-Za-z0-9-]{1,80}', f['id']):
            raise AuditError('Invalid finding ID')
        if f['priority'] not in ('P0', 'P1', 'P2', 'P3', 'Info') or f['evidence_status'] not in ('verified', 'supported', 'unverified'):
            raise AuditError('Invalid finding classification')
        if f['attribution'] not in ('introduced', 'worsened', 'pre-existing', 'unknown'):
            raise AuditError('Invalid attribution')
        if f['disposition'] not in ('open', 'rejected', 'duplicate', 'resolved', 'accepted risk'):
            raise AuditError('Invalid disposition')
        if f['disposition'] in ('resolved', 'accepted risk'):
            raise AuditError('1.0 does not accept reviewer-created resolution or risk waivers; rerun the corrected head')
        for name in ('trigger', 'impact', 'reasoning', 'remediation'):
            if not isinstance(f[name], str) or not f[name].strip():
                raise AuditError('Finding explanation is incomplete')
        if not f['locations'] or not f['evidence']:
            raise AuditError('Findings need source locations and evidence')
        locations = [source_location(run, state, x) for x in f['locations']]
        for ref in f['evidence']:
            check_ref(run, ref)
        f = copy.deepcopy(f)
        f.update(locations=locations, reviewer=reviewer)
        f['fingerprint'] = digest({'category': f['category'], 'root_cause': f.get('root_cause', f['trigger']),
                                   'remedy': f['remediation'], 'symbols': sorted(x.get('symbol', x['path']) for x in locations)})
        verification = f.get('verification')
        if verification:
            require(verification, ['reviewer', 'outcome', 'challenge', 'evidence'])
            if verification['reviewer'] == reviewer or verification['outcome'] not in ('upheld', 'refuted', 'unresolved'):
                raise AuditError('Verification needs a different reviewer and an explicit outcome')
            if not verification['challenge'] or not verification['evidence']:
                raise AuditError('Verification needs a counterexample search and evidence')
            for ref in verification['evidence']:
                check_ref(run, ref)
        if f['disposition'] in ('rejected', 'duplicate') and not f.get('disposition_reason'):
            raise AuditError('Retained dispositions need rationale')
        if f['disposition'] == 'rejected' and (not verification or verification['outcome'] != 'refuted'):
            raise AuditError('Rejecting a proposed finding requires independent refutation')
        if f['category'] == 'reuse' and f.get('consolidation'):
            require(f['consolidation'], ['definitions_and_callers', 'behavioral_comparison', 'domain_contract',
                                         'retained_implementation', 'affected_dependencies', 'validation', 'unresolved_differences'])
            if not verification or verification['outcome'] != 'upheld':
                f['evidence_status'] = 'unverified'
        validated.append(f)
    return validated


def ingest_review(run, input_path):
    state = load(run)
    data = read(input_path)
    require(data, ['schema_version', 'run_id', 'task_id', 'snapshot', 'reviewer', 'state',
                   'reviewed_paths', 'summary', 'model', 'findings', 'evidence'])
    spec = definition(state, data['task_id'])
    if spec['kind'] != 'expert' or data['schema_version'] != SCHEMA or data['run_id'] != state['run_id'] or data['snapshot'] != spec['snapshot']:
        raise AuditError('Review does not match this frozen task')
    if not data['reviewer'] or not data['summary'] or not data['model']:
        raise AuditError('Reviewer, model provenance and summary are required')
    require(data['model'], ['provider', 'model', 'version', 'reasoning'])
    if set(data['reviewed_paths']) - set(spec['paths']):
        raise AuditError('Review claims paths outside its assignment')
    result = attempt(state, spec, data['state'], data.get('reason'))
    if result['state'] != 'completed' and not result['reason']:
        raise AuditError('Non-complete reviews require an explicit reason')
    missing = set(spec['paths']) - set(data['reviewed_paths'])
    if result['state'] == 'completed' and (missing or not data['evidence']):
        raise AuditError('Completed review needs all assigned paths and evidence')
    if result['state'] == 'not_applicable':
        raise AuditError('Required roles cannot be waived after the plan is frozen')
    for ref in data['evidence']:
        check_ref(run, ref)
    findings = validate_findings(run, state, data['findings'], data['reviewer'])
    result.update(tool='agent', tool_version=data['model'], parser_status='valid',
                  record_count=len(findings), omissions=sorted(missing), reviewer=data['reviewer'],
                  outputs=data['evidence'], summary=data['summary'], reviewed_paths=data['reviewed_paths'])
    receipt = evidence(run, input_path, 'review.json')
    result['outputs'].append(receipt)
    # Later attempts supersede findings from the same task, preserving originals on disk.
    result['findings'] = findings
    record(run, state, result)
    report(run)
    return result


def ingest_check(run, input_path):
    state = load(run)
    data = read(input_path)
    require(data, ['schema_version', 'run_id', 'task_id', 'snapshot', 'state', 'tool', 'tool_version',
                   'environment', 'scope_paths', 'coverage_complete', 'omissions', 'adapter',
                   'report', 'expected_records', 'exit_code', 'completed_exit_codes', 'config_digest'])
    spec = definition(state, data['task_id'])
    if spec['kind'] != 'sensor' or data['schema_version'] != SCHEMA or data['run_id'] != state['run_id'] or data['snapshot'] != spec['snapshot']:
        raise AuditError('Evidence is for a different run, capability or build')
    result = attempt(state, spec, data['state'], data.get('reason'))
    if result['state'] != 'completed' and not result['reason']:
        raise AuditError('Non-complete checks require an explicit reason')
    if result['state'] == 'not_applicable':
        raise AuditError('Required capabilities cannot be waived by imported evidence')
    report_path = (Path(input_path).resolve().parent / data['report']).resolve()
    if not report_path.is_relative_to(Path(input_path).resolve().parent):
        raise AuditError('Imported report must be next to or beneath its envelope')
    # Parse before retaining sensor data; unredacted secrets are rejected before copying.
    observations = parse(report_path, data['adapter'])
    for item in observations:
        item['snapshot'] = item.get('snapshot') or spec['snapshot']
    if type(data['expected_records']) is not int or data['expected_records'] != len(observations):
        raise AuditError('Parser record count differs from declared source coverage')
    completed = result['state'] == 'completed'
    if completed:
        approved_codes = state['inputs']['policy'].get('sensors', {}).get(spec['capability'], {}).get(
            'completed_exit_codes', {'gitleaks-json': [0, 1], 'cpd-xml': [0, 4]}.get(data['adapter'], [0]))
        if data['completed_exit_codes'] != approved_codes:
            raise AuditError('Imported evidence cannot redefine permitted exit codes')
        if not data['coverage_complete'] or data['omissions'] or set(spec['paths']) - set(data['scope_paths']):
            raise AuditError('Completed evidence has missing scope or omissions')
        if data['exit_code'] not in data['completed_exit_codes']:
            raise AuditError('Exit status violates adapter completion contract')
        if not data['tool'] or not data['tool_version'] or not data['environment'] or not data['config_digest']:
            raise AuditError('Completed evidence needs pinned tool/config/environment identity')
        if spec['capability'] == 'secrets' and set(data.get('history_commits', [])) != set(state['inputs']['scope']['history_commits']):
            raise AuditError('Secrets evidence does not cover introduced history')
        if spec['capability'] == 'dependencies' and (not data.get('dependencies') or not data.get('advisory_database')):
            raise AuditError('Dependency evidence needs resolved graph and advisory database identities')
        if spec['capability'] in ('build', 'tests', 'runtime'):
            require(data, ['build'])
            require(data['build'], ['source', 'tree', 'configuration', 'toolchain'])
            if data['build']['source'] != spec['snapshot'] or data['build']['tree'] != state['inputs']['scope']['integration_tree']:
                raise AuditError('CI/runtime artifact belongs to another integration tree')
        if spec['capability'] == 'runtime':
            require(data, ['runtime'])
            require(data['runtime'], ['harness', 'device_fingerprint', 'scenario_version', 'assertions', 'initial_state',
                                      'final_state', 'ownership', 'failure_kind', 'application_hash'])
            runtime = data['runtime']
            if runtime['ownership'] != 'exclusive-granted' or runtime['failure_kind'] not in ('none', 'product'):
                raise AuditError('Runtime infrastructure/ownership failure is not complete product evidence')
            if runtime['failure_kind'] == 'product' and not data.get('product_failure'):
                raise AuditError('Demonstrated runtime product failure cannot be declared passing')
        if data.get('product_failure') and (not observations or not data.get('failure_reason')):
            raise AuditError('Product failure needs retained failing observations and a causal explanation')
    baseline_outputs = []
    if data.get('baseline'):
        baseline = data['baseline']
        require(baseline, ['snapshot', 'report', 'adapter', 'expected_records', 'state',
                           'tool_version', 'config_digest', 'environment', 'dependencies',
                           'advisory_database', 'scope_paths'])
        scope = state['inputs']['scope']
        allowed_base = scope['B'] if spec['snapshot'] == scope['I'] and scope['I'] != scope['H'] else scope['A']
        if baseline['snapshot'] != allowed_base:
            raise AuditError('Baseline does not identify the planned comparison pair')
        base_path = (Path(input_path).resolve().parent / baseline['report']).resolve()
        if not base_path.is_relative_to(Path(input_path).resolve().parent):
            raise AuditError('Baseline report escapes the import directory')
        before = parse(base_path, baseline['adapter'])
        if len(before) != baseline['expected_records']:
            raise AuditError('Baseline record count does not match parsed evidence')
        for item in before:
            item['snapshot'] = item.get('snapshot') or baseline['snapshot']
        keys = ['tool_version', 'config_digest', 'environment', 'dependencies', 'advisory_database']
        deltas = [key for key in keys if baseline.get(key) != data.get(key)]
        renames = {x['old_path']: x['path'] for x in scope['changes'] if x['old_path']}
        base_paths = {renames.get(x, x) for x in baseline['scope_paths']}
        equivalent = not deltas and baseline['adapter'] == data['adapter'] and baseline['state'] == 'completed' and base_paths == set(data['scope_paths'])
        observations = compare(before, observations, equivalent, completed and data['coverage_complete'], renames)
        result['comparison_inputs'] = {'baseline': baseline['snapshot'], 'head': spec['snapshot'],
                                       'equivalent': equivalent, 'environmental_deltas': deltas}
        baseline_outputs = [evidence(run, base_path, 'baseline' + base_path.suffix)]
    result.update(tool=data['tool'], tool_version=data['tool_version'], environment=data['environment'],
                  dependencies=data.get('dependencies'), advisory_database=data.get('advisory_database'),
                  config_digest=data['config_digest'], exit_code=data['exit_code'], parser_status='valid',
                  record_count=len(observations), observations=observations, omissions=data['omissions'],
                  outputs=baseline_outputs + [evidence(run, report_path, 'sensor-data' + report_path.suffix),
                           evidence(run, input_path, 'sensor-envelope.json')],
                  product_failure=bool(data.get('product_failure', False) and completed),
                  build=data.get('build'), runtime=data.get('runtime'))
    record(run, state, result)
    report(run)
    return result


def run_sensors(run, retry=False):
    state = load(run)
    if state['state'] in ('cancelled', 'paused'):
        raise AuditError('Use resume before executing a paused or cancelled run')
    policy_data = state['inputs']['policy']
    resources = policy_data.get('resources', {})
    timeout = resources.get('timeout_seconds', 7200)
    max_attempts = resources.get('max_attempts', 2)
    if not 1 <= timeout <= 86400 or not 1 <= max_attempts <= 20:
        raise AuditError('Resource timeout or attempt budget is invalid')
    for spec in state['inputs']['tasks']:
        if spec['kind'] != 'sensor':
            continue
        if (Path(run) / 'cancel.request.json').exists():
            state['state'] = 'cancelled'
            save(run, state)
            break
        previous = get_attempt(state, spec['id'])
        if previous and previous['state'] == 'completed':
            for ref in previous['outputs']:
                check_ref(run, ref)
            continue
        if previous and previous['state'] == 'running':
            # Process groups/jobs are owned by the prior controller; never kill a stale PID.
            previous.update(state='partial', reason='Controller interrupted; prior attempt not assumed complete', ended=now())
            atomic(Path(run) / 'tasks' / spec['id'] / previous['attempt_id'] / 'result.json', previous)
            save(run, state)
        if previous and not retry:
            continue
        if len(state['results'].get(spec['id'], [])) >= max_attempts:
            continue
        sensor = policy_data.get('sensors', {}).get(spec['capability'])
        result = attempt(state, spec, 'running')
        if not sensor:
            result.update(state='unavailable', reason='No pre-provisioned sensor or imported CI evidence configured')
            record(run, state, result)
            continue
        try:
            require(sensor, ['executable', 'version', 'version_args', 'adapter', 'isolation'])
            executable = Path(sensor['executable'])
            if not executable.is_absolute() or not executable.is_file():
                raise AuditError('Pinned executable must be an existing absolute local file')
            provisioned = state['inputs']['provisioned_files'].get(spec['capability'], {})
            if provisioned.get('executable') != sha(executable):
                raise AuditError('Executable changed or was not provisioned when this run was pinned')
            if sensor['isolation'] != 'approved-local-disposable':
                raise AuditError('Use an approved existing sandbox/CI host, or explicitly configure approved-local-disposable execution')
            if sensor.get('machine_lock') == 'scancode' or 'scancode' in executable.name.lower():
                raise AuditError('ScanCode requires a machine-wide owner integration; 1.0 does not run it locally')
            if spec['snapshot'] is None:
                raise AuditError('Integration snapshot unavailable')
            if spec['capability'] == 'secrets' and sensor['adapter'] != 'gitleaks-json':
                raise AuditError('Local secrets execution requires the native redacted Gitleaks adapter')
            folder = Path(run) / 'tasks' / spec['id'] / result['attempt_id']
            folder.mkdir(parents=True, exist_ok=True)
            version_info = execute([str(executable), *sensor['version_args']], Path(run), folder / 'version', 30,
                                   memory_mb=resources.get('max_memory_mb', 4096))
            version = (folder / 'version' / 'stdout.txt').read_text(encoding='utf-8').strip()
            if version_info.get('exit_code') != 0 or version != sensor['version']:
                raise AuditError('Tool version does not match the frozen provisioned pin')
            workspace = Path(run) / 'workspaces' / (spec['id'] + '-' + result['attempt_id'])
            if spec['capability'] == 'secrets':
                require(sensor, ['rules_file'])
                rules = Path(sensor['rules_file'])
                if not rules.is_absolute() or not rules.is_file() or rules.resolve().is_relative_to(Path(state['inputs']['repo'])):
                    raise AuditError('Gitleaks rules must be explicitly provisioned outside the proposed checkout')
                if provisioned.get('rules_file') != sha(rules):
                    raise AuditError('Gitleaks rules changed since run initialization')
                proc = git(state['inputs']['repo'], 'clone', '--local', '--no-hardlinks', '--no-checkout',
                           Path(state['inputs']['repo']).as_posix(), workspace.as_posix(), okay=True)
                if proc.returncode:
                    raise AuditError('Could not prepare isolated history clone')
                git(workspace, 'checkout', '--detach', state['inputs']['scope']['H'])
                atomic(folder / 'empty.ignore', '')
                args = ['git', '--no-banner', '--redact=100', '--report-format=json',
                        '--config=' + str(rules), '--ignore-gitleaks-allow',
                        '--gitleaks-ignore-path=' + str(folder / 'empty.ignore'),
                        '--report-path=' + str(folder / 'raw.json'),
                        '--log-opts=' + state['inputs']['scope']['H'] + ' ^' + state['inputs']['scope']['B'],
                        str(workspace)]
                report_path = folder / 'raw.json'
            else:
                label = 'I' if spec['capability'] in ('tests', 'build', 'runtime') else 'H'
                shutil.copytree(Path(run) / 'snapshots' / label, workspace)
                require(sensor, ['args', 'report'])
                report_path = inside(folder, sensor['report'])
                replacements = {'{workspace}': str(workspace), '{report}': str(report_path),
                                '{head}': state['inputs']['scope']['H'], '{snapshot}': spec['snapshot']}
                args = []
                for arg in sensor['args']:
                    for token, value in replacements.items():
                        arg = arg.replace(token, value)
                    args.append(arg)
            result.update(tool=str(executable), tool_version=version,
                          config_digest=digest(sensor), environment={'platform': sys_platform(), 'python': os.sys.version},
                          executable_sha256=sha(executable))
            record(run, state, result)
            info = execute([str(executable), *args], workspace, folder, timeout,
                           memory_mb=resources.get('max_memory_mb', 4096),
                           min_disk_mb=resources.get('min_disk_mb', 256),
                           cancel_file=Path(run) / 'cancel.request.json')
            result.update(resource_usage=info, exit_code=info.get('exit_code'), ended=now())
            if info.get('timed_out'):
                raise AuditError('Scanner timeout; retained partial artifacts')
            if info.get('cancelled'):
                raise AuditError('Cancellation requested; retained partial artifacts')
            codes = sensor.get('completed_exit_codes', [0, 1] if spec['capability'] == 'secrets' else [0])
            if info['exit_code'] not in codes:
                raise AuditError('Scanner failed its adapter exit contract')
            observations = parse(report_path, sensor['adapter'], source_root=workspace)
            for item in observations:
                item['snapshot'] = item.get('snapshot') or spec['snapshot']
            outputs = [evidence(run, report_path, 'sensor-data' + report_path.suffix)]
            if spec['capability'] == 'secrets':
                # History alone misses unchanged secrets already present at the merge base.
                current = Path(run) / 'workspaces' / ('current-' + result['attempt_id'])
                shutil.copytree(Path(run) / 'snapshots' / 'H', current)
                current_report = folder / 'current.json'
                current_args = [str(executable), 'dir', '--no-banner', '--redact=100',
                                '--config=' + str(rules), '--ignore-gitleaks-allow',
                                '--gitleaks-ignore-path=' + str(folder / 'empty.ignore'),
                                '--report-format=json', '--report-path=' + str(current_report), str(current)]
                current_info = execute(current_args, current, folder / 'current', timeout,
                                       memory_mb=resources.get('max_memory_mb', 4096),
                                       cancel_file=Path(run) / 'cancel.request.json')
                if current_info.get('exit_code') not in codes or current_info.get('timed_out') or current_info.get('cancelled'):
                    raise AuditError('Current-tree secrets scan incomplete')
                current_observations = parse(current_report, sensor['adapter'], source_root=current)
                for item in current_observations:
                    item['snapshot'] = spec['snapshot']
                observations += current_observations
                outputs.append(evidence(run, current_report, 'current-secrets.json'))
                result['resource_usage']['current_tree'] = current_info
                result['rules_sha256'] = sha(rules)
            result.update(state='completed', parser_status='valid', record_count=len(observations),
                          observations=observations, outputs=outputs)
            if spec['capability'] == 'dependencies':
                # A source-only scan cannot substitute for a resolved graph/advisory receipt.
                raise AuditError('Import dependency results with resolved graph and advisory provenance')
            if spec['capability'] in ('build', 'tests', 'runtime'):
                raise AuditError('Import exact-build CI/harness envelopes to complete this capability')
        except KeyboardInterrupt:
            result.update(state='cancelled', reason='Controller interrupted; partial artifacts retained', ended=now())
            records = state['results'].get(spec['id'], [])
            if records and records[-1]['attempt_id'] == result['attempt_id']:
                records[-1] = result
            else:
                state['results'].setdefault(spec['id'], []).append(result)
            atomic(Path(run) / 'tasks' / spec['id'] / result['attempt_id'] / 'result.json', result)
            state['state'] = 'cancelled'
            save(run, state)
            report(run)
            raise
        except (AuditError, OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
            result.update(state='partial' if result.get('resource_usage') else 'unavailable',
                          reason=str(exc), ended=now())
            if (Path(run) / 'cancel.request.json').exists():
                result.update(state='cancelled')
                state['state'] = 'cancelled'
        # Publish one final record; running checkpoints are updated, never duplicate attempts.
        records = state['results'].get(spec['id'], [])
        if records and records[-1]['attempt_id'] == result['attempt_id']:
            records[-1] = result
            atomic(Path(run) / 'tasks' / spec['id'] / result['attempt_id'] / 'result.json', result)
            save(run, state)
        else:
            record(run, state, result)
        report(run)
    report(run)


def sys_platform():
    import platform
    return platform.platform()


def triage(run, input_path):
    state = load(run)
    data = read(input_path)
    require(data, ['run_id', 'reviewer', 'observations'])
    if data['run_id'] != state['run_id'] or not data['reviewer']:
        raise AuditError('Triage identity mismatch')
    available = {x['fingerprint'] for spec in state['inputs']['tasks']
                 for x in (get_attempt(state, spec['id']) or {}).get('observations', [])}
    finding_ids = {f['id'] for spec in state['inputs']['tasks']
                   for f in (get_attempt(state, spec['id']) or {}).get('findings', [])}
    for x in data['observations']:
        require(x, ['fingerprint', 'disposition', 'reason', 'evidence'])
        if x['fingerprint'] not in available or x['disposition'] not in ('finding', 'rejected', 'advisory', 'pre-existing'):
            raise AuditError('Invalid observation disposition')
        if not x['reason'] or not x['evidence']:
            raise AuditError('Triage needs rationale and retained evidence')
        if x['disposition'] == 'finding' and x.get('finding_id') not in finding_ids:
            raise AuditError('Triage must link an existing validated finding')
        for ref in x['evidence']:
            check_ref(run, ref)
    state['triage'] = {'data': data, 'receipt': evidence(run, input_path, 'triage.json')}
    save(run, state)
    report(run)


def freshness(state):
    scope = state['inputs']['scope']
    try:
        if state['inputs'].get('pr_metadata'):
            metadata = state['inputs']['pr_metadata']
            p = subprocess.run(metadata['api_command'], cwd=state['inputs']['repo'],
                               capture_output=True, text=True, timeout=60)
            if p.returncode:
                return 'unknown'
            data = json.loads(p.stdout)
            return 'current' if data['head']['sha'] == scope['H'] and data['base']['sha'] == scope['B'] else 'stale'
        head = commit(state['inputs']['repo'], scope['head_ref'])
        base = commit(state['inputs']['repo'], scope['base_ref'])
        return 'current' if head == scope['H'] and base == scope['B'] else 'stale'
    except (AuditError, OSError, KeyError, ValueError, subprocess.TimeoutExpired):
        return 'unknown'


def evaluate(run, state):
    missing, blockers, investigations, findings = [], [], [], []
    coverage = []
    for spec in state['inputs']['tasks']:
        result = get_attempt(state, spec['id'])
        status = result['state'] if result else 'queued'
        valid = status == 'completed'
        reason = result.get('reason') if result else 'Not executed'
        if result:
            try:
                for ref in result['outputs']:
                    check_ref(run, ref)
            except AuditError as exc:
                valid, reason = False, str(exc)
            findings.extend(result.get('findings', []))
            if valid and result.get('product_failure') and spec['required']:
                blockers.append(spec['id'])
        coverage.append(dict(spec, state=status, valid=valid, reason=reason,
                             reviewed_paths=(result or {}).get('reviewed_paths', [])))
        if spec['required'] and not valid:
            missing.append(spec['id'] + ': ' + (reason or status))
    # Preserve contributing records; group only explicit semantic fingerprints.
    unique = {}
    for f in findings:
        if f['fingerprint'] in unique:
            prior = unique[f['fingerprint']]
            prior['contributing_ids'].append(f['id'])
            prior['contributing_evidence'].extend(f['evidence'])
        else:
            unique[f['fingerprint']] = dict(f, contributing_ids=[f['id']], contributing_evidence=list(f['evidence']))
    ids = {f['id'] for f in findings}
    lookup = {f['id']: f for f in findings}
    for f in findings:
        if f['disposition'] == 'duplicate' and f.get('duplicate_of') not in ids:
            missing.append('Duplicate finding has no retained root cause: ' + f['id'])
        elif f['disposition'] == 'duplicate':
            canonical = lookup[f['duplicate_of']]
            if canonical['disposition'] != 'open' or canonical['id'] == f['id']:
                missing.append('Duplicate root cause is not an open canonical finding: ' + f['id'])
            if f['priority'] in ('P0', 'P1') and canonical['priority'] not in ('P0', 'P1'):
                missing.append('Duplicate priority conflict requires verification: ' + f['id'])
        priority_block = f['priority'] in state['inputs']['policy'].get('blocking_priorities', ['P0', 'P1'])
        if f['attribution'] == 'pre-existing' and f['priority'] != 'P0':
            priority_block = False  # historical debt is separate; no self-authorized waiver of critical exposure
        verification = f.get('verification', {})
        if f['disposition'] != 'open':
            continue
        refs_valid = True
        try:
            for ref in f['evidence'] + verification.get('evidence', []):
                check_ref(run, ref)
        except AuditError:
            refs_valid = False
            missing.append('Finding evidence integrity: ' + f['id'])
        if priority_block:
            if f['evidence_status'] in ('verified', 'supported') and verification.get('outcome') == 'upheld' and refs_valid:
                blockers.append(f['id'])
            else:
                investigations.append(f['id'])
    scope = state['inputs']['scope']
    if scope['integration'] == 'conflict':
        blockers.append('integration-conflict')
    elif scope['integration'] not in ('head-includes-target', 'merge-candidate'):
        missing.append('Integration validation unavailable')
    missing.extend('Unavailable source: ' + x['path'] + ' (' + x['reason'] + ')' for x in state['inputs']['omissions'])
    observed = {x['fingerprint'] for spec in state['inputs']['tasks']
                for x in (get_attempt(state, spec['id']) or {}).get('observations', [])}
    triaged = {x['fingerprint'] for x in state.get('triage', {}).get('data', {}).get('observations', [])}
    if observed - triaged:
        missing.append(f'{len(observed - triaged)} sensor observations await contextual triage')
    if state.get('triage'):
        try:
            check_ref(run, state['triage']['receipt'])
        except AuditError as exc:
            missing.append(str(exc))
    if state['inputs']['profile'] == 'scan':
        missing.append('Scan-only profile cannot establish merge readiness')
    if state['inputs']['limited_roles']:
        missing.append('Deliberately limited expert selection')
    if state['state'] in ('cancelled', 'paused'):
        missing.append('Run is ' + state['state'])
    elif (Path(run) / 'cancel.request.json').exists():
        missing.append('Run cancellation requested')
    fresh = freshness(state)
    if fresh != 'current':
        missing.append('Source/target freshness is ' + fresh)
    missing.extend('Blocking investigation unresolved: ' + x for x in investigations)
    verdict = 'CHANGES_REQUIRED' if blockers else 'INCOMPLETE' if missing else 'READY'
    return {'schema_version': SCHEMA, 'run_id': state['run_id'], 'verdict': verdict,
            'blocking_ids': sorted(set(blockers)), 'completion': 'incomplete' if missing else 'completed',
            'freshness': fresh, 'scope': {k: scope[k] for k in ('H', 'B', 'M', 'A', 'I', 'integration_tree')},
            'missing': missing, 'generated': now()}, coverage, list(unique.values())


def report(run):
    state = load(run)
    verdict, coverage, findings = evaluate(run, state)
    # Preserve every historical conclusion, particularly a previously ready report.
    revision = uuid.uuid4().hex
    history = Path(run) / 'reports' / revision
    history.mkdir(parents=True)
    scope = state['inputs']['scope']
    lines = ['# Code Audit', '', f"**{verdict['verdict']}** | coverage: {verdict['completion']} | freshness: {verdict['freshness']}", '',
             f"Run: {state['run_id']} | Code Audit {VERSION}", '',
             f"Head H: `{scope['H']}`", f"Target B: `{scope['B']}`", f"Merge base M: `{scope['M']}`",
             f"Integration I: `{scope['I']}`", '',
             f"Comparison base A: `{scope['A']}` ({scope['range_mode']})", '',
             'Review covers the committed net tree and introduced history. Local edits are excluded.',
             'Intent: ' + ('supplied' if state['inputs']['intent_available'] else 'not supplied; requirements must not be invented'),
             'Cache: no cross-run reuse. Job lifetime: session-bound unless an existing durable host owns execution.', '',
             '## Decision and coverage', '']
    lines += ['- ' + x for x in verdict['missing']] or ['All required checks and reviews completed.']
    if verdict['blocking_ids']:
        lines += ['', 'Blocking items: ' + ', '.join(verdict['blocking_ids'])]
    lines += ['', '| Task | Required | State | Evidence |', '| --- | --- | --- | --- |']
    for entry in coverage:
        result = get_attempt(state, entry['id']) or {}
        refs = ', '.join(f"[{x['sha256'][:10]}]({x['path']})" for x in result.get('outputs', []))
        lines.append(f"| {entry['id']} | {entry['required']} | {entry['state']} | {refs} |")
    lines += ['', '## Findings', '']
    for f in findings:
        lines += [f"### {f['id']} — {f['priority']} {f['category']}", '',
                  f"{f['evidence_status']}; {f['attribution']}; {f['disposition']}", '',
                  'Trigger: ' + f['trigger'], '', 'Impact: ' + f['impact'], '',
                  'Evidence and inference: ' + f['reasoning'], '', 'Remediation: ' + f['remediation'], '']
        for loc in f['locations']:
            lines.append(f"- `{loc['snapshot']}:{loc['path']}:{loc['start_line']}-{loc['end_line']}`")
        for ref in f['contributing_evidence']:
            lines.append(f"- [{ref['path']}]({ref['path']}) (`{ref['sha256']}`)")
        if f.get('verification'):
            lines += ['', 'Verification: ' + f['verification']['challenge']]
    if not findings:
        lines.append('No validated review findings recorded. This does not imply completed coverage.')
    process = 'not available' if not state['process_reviews'] else 'partial/complete as recorded in process receipts'
    lines += ['', '## Process review and hypotheses', '', 'Process completeness: ' + process + '.',
              'Missing process logs do not satisfy or block product coverage.',
              '[Hypothesis index](hypotheses/index.json)', '',
              '## Limitations', '',
              'A clean review is not proof of defect absence. Runtime evidence establishes only inspected scenarios.',
              'Historical debt, rejected findings, explicit exclusions and retained evidence remain in machine records.',
              'Reports and source/log excerpts are private evidence. Publishing or changing product code requires its own instruction.']
    md = '\n'.join(lines) + '\n'
    # Render every source/log string inert. No raw Markdown HTML, script, or external resource loading.
    rendered = render(state, verdict, coverage, findings)
    artifacts = {'verdict.json': verdict, 'coverage.json': {'schema_version': SCHEMA, 'work_units': coverage,
                  'changes': scope['changes'], 'exclusions': state['inputs']['omissions']},
                 'findings.json': findings, 'report.md': md, 'report.html': rendered}
    for name, content in artifacts.items():
        historical = content
        if name == 'report.md':
            historical = content.replace('](evidence/', '](../../evidence/').replace('](hypotheses/', '](../../hypotheses/')
        elif name == 'report.html':
            historical = content.replace('href="evidence/', 'href="../../evidence/').replace('href="hypotheses/', 'href="../../hypotheses/')
        atomic(history / name, historical)
        atomic(Path(run) / name, content)
    atomic(Path(run) / 'hypotheses' / 'index.json', {'schema_version': SCHEMA, 'items': state['hypotheses'],
           'reason': None if state['hypotheses'] else 'No defensible experiment has been supplied with sufficient attributed evidence.'})
    state['latest_report'] = 'reports/' + revision
    if state['state'] not in ('cancelled', 'paused'):
        state['state'] = verdict['completion']
    save(run, state)
    return verdict
