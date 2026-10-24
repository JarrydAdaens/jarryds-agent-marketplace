"""Consume Oracle-compatible receipts; never infer invoices or invent missing counters."""
from pathlib import Path
import zipfile

from .common import AuditError, atomic, digest, inside, read, require, sha
from .engine import check_ref, evidence, load, report, save

FIELDS = ('input_tokens', 'cache_creation_input_tokens', 'cached_input_tokens',
          'output_tokens', 'reasoning_output_tokens')


def ingest_process(run, input_path):
    state = load(run)
    data = read(input_path)
    require(data, ['schema_version', 'run_id', 'attribution', 'receipts', 'observations'])
    if data['schema_version'] != 1:
        raise AuditError('Unsupported process envelope schema')
    require(data['attribution'], ['repository_identity', 'sessions', 'status', 'evidence'])
    attribution = data['attribution']
    if data['run_id'] != state['run_id'] or attribution['repository_identity'] != state['inputs']['scope']['repository_identity']:
        raise AuditError('Process attribution does not match repository/run')
    if attribution['status'] not in ('exact', 'partial', 'unknown'):
        raise AuditError('Invalid process attribution')
    for ref in attribution['evidence']:
        check_ref(run, ref)
    totals = {field: 0 for field in FIELDS}
    unknown, responses = set(), {}
    source_partial = False
    selected = {}
    for receipt in data['receipts']:
        require(receipt, ['provider', 'session_id', 'responses', 'coverage'])
        if receipt['session_id'] not in attribution['sessions']:
            raise AuditError('Unattributed session receipt')
        if receipt['provider'] != 'claude' or not isinstance(receipt['responses'], list):
            unknown.update(FIELDS)
            continue
        if receipt['coverage'].get('status') not in ('complete', 'completed'):
            source_partial = True
        key = (receipt['provider'], receipt['session_id'])
        old = selected.get(key)
        if not old or (receipt.get('schema_version', 1), receipt.get('updated_at', '')) > (old.get('schema_version', 1), old.get('updated_at', '')):
            selected[key] = receipt
    for receipt in selected.values():
        for r in receipt['responses']:
            if not r.get('message_id') or not r.get('request_id'):
                unknown.update(FIELDS)
                continue
            identity = (receipt['provider'], r['message_id'], r['request_id'])
            prior = responses.setdefault(identity, {field: None for field in FIELDS})
            for field in FIELDS:
                value = r.get(field)
                if value is None:
                    continue
                if type(value) is not int or value < 0:
                    raise AuditError('Invalid provider token counter')
                # Streaming/cumulative updates of a single response count maxima once.
                prior[field] = max(prior[field] or 0, value)
    for r in responses.values():
        for field in FIELDS:
            if r[field] is None:
                unknown.add(field)
            else:
                totals[field] += r[field]
    if not responses or attribution['status'] != 'exact':
        unknown.update(FIELDS)
    for field in unknown:
        totals[field] = None
    for observation in data['observations']:
        require(observation, ['id', 'claim', 'events', 'evidence', 'limitations'])
        if not observation['events'] or not observation['evidence']:
            raise AuditError('Process observations require actual attributed events')
        for ref in observation['evidence']:
            check_ref(run, ref)
    status = 'partial' if unknown or source_partial or not attribution['evidence'] else 'completed'
    result = {'status': status, 'attribution': attribution, 'totals': totals,
              'total_tokens': None if any(totals[f] is None for f in FIELDS[:4]) else sum(totals[f] for f in FIELDS[:4]),
              'estimated_cost': None, 'cost_reason': 'No audited pricing source supplied; token usage is not an invoice',
              'observations': data['observations'], 'source': evidence(run, input_path, 'process.json')}
    state['process_reviews'].append(result)
    atomic(Path(run) / 'process-review.json', result)
    save(run, state)
    report(run)
    return result


def package_hypothesis(run, input_path):
    state = load(run)
    data = read(input_path)
    require(data, ['schema_version', 'id', 'origin_evidence', 'claim', 'population', 'intervention', 'baseline',
                   'metrics', 'success_criteria', 'failure_criteria', 'readiness', 'missing', 'package_root'])
    if data['schema_version'] != 1:
        raise AuditError('Unsupported hypothesis schema')
    from .engine import re
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,60}', data['id']):
        raise AuditError('Invalid hypothesis identifier')
    if any(item['id'] == data['id'] for item in state['hypotheses']):
        raise AuditError('Hypotheses are immutable; use a new ID')
    if data['readiness'] not in ('ready', 'not_ready') or (data['readiness'] == 'not_ready' and not data['missing']):
        raise AuditError('Not-ready experiments must list missing prerequisites')
    if not data['origin_evidence']:
        raise AuditError('Hypotheses require retained motivating evidence')
    for ref in data['origin_evidence']:
        check_ref(run, ref)
    root = (Path(input_path).resolve().parent / data['package_root']).resolve()
    if not root.is_relative_to(Path(input_path).resolve().parent):
        raise AuditError('Hypothesis payload must be beneath its explicit input directory')
    required = ['README.md', 'prompt.md', 'sample', 'environment', 'evaluation', 'reference']
    missing = [name for name in required if not inside(root, name).exists()]
    if data['readiness'] == 'ready' and (missing or data['missing']):
        raise AuditError('Ready experiment lacks required reproduction/evaluation inputs')
    files = []
    for path in root.rglob('*'):
        if path.is_symlink():
            raise AuditError('Hypothesis symlinks are not portable')
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            inside(root, rel)
            if rel != 'prompt.md' and rel != 'README.md' and rel.split('/')[0] not in ('sample', 'environment', 'evaluation', 'reference'):
                raise AuditError('Unexpected hypothesis payload path')
            files.append((path, rel))
    # Only these files enter the candidate package. README may discuss results; withhold it too.
    candidate = [(path, rel) for path, rel in files if rel == 'prompt.md' or rel.split('/')[0] in ('sample', 'environment')]
    for path, rel in candidate:
        if rel == 'prompt.md' and any(marker in path.read_text(encoding='utf-8').lower() for marker in
                                      ('../reference', '../evaluation', 'reference/', 'evaluation/')):
            raise AuditError('Candidate prompt reaches withheld evaluator/reference material')
    candidate_hashes = {sha(path) for path, _ in candidate}
    if any(sha(path) in candidate_hashes for path, rel in files if rel.startswith(('reference/', 'evaluation/'))):
        raise AuditError('Candidate includes a copy of withheld evaluator/reference content')
    metadata = {k: v for k, v in data.items() if k != 'package_root'}
    metadata['missing'] = sorted(set(metadata['missing'] + missing))
    metadata['candidate_access'] = 'candidate ZIP only; full ZIP is evaluator-private; inspect candidate content before trials'
    folder = Path(run) / 'hypotheses'
    full = folder / ('hypothesis-' + data['id'] + '.zip')
    candidate_zip = folder / ('candidate-' + data['id'] + '.zip')
    # Exclusive creation avoids replacing an earlier package after a crash.
    with zipfile.ZipFile(full, 'x', zipfile.ZIP_DEFLATED) as archive:
        import json
        archive.writestr('hypothesis.yml', json.dumps(metadata, indent=2))  # JSON is valid YAML.
        for path, rel in files:
            archive.write(path, rel)
    with zipfile.ZipFile(candidate_zip, 'x', zipfile.ZIP_DEFLATED) as archive:
        for path, rel in candidate:
            archive.write(path, rel)
    item = {'id': data['id'], 'readiness': data['readiness'], 'missing': metadata['missing'],
            'evaluator_package': full.name, 'evaluator_sha256': sha(full),
            'candidate_package': candidate_zip.name, 'candidate_sha256': sha(candidate_zip),
            'input_digest': digest(metadata)}
    state['hypotheses'].append(item)
    save(run, state)
    report(run)
    return item
