"""Strict typed observation adapters; unknown data remains in hashed raw evidence."""
import json
import re
from pathlib import Path
import xml.etree.ElementTree as ET

from .common import AuditError, digest, relative, require


VERSION = '1.0.0'


def observation(rule, path, message, *, symbol=None, identity=None, severity=None,
                line=None, raw=None, secret=False):
    relative(path)
    if not isinstance(rule, str) or not rule or not isinstance(message, str):
        raise AuditError('Invalid rule/message')
    # A producer-provided stable symbol/content identity is necessary for rename matching.
    key = {'rule': rule, 'location': symbol or path, 'identity': identity or message}
    return {'rule': rule, 'path': path, 'symbol': symbol, 'line': line,
            'message': '[redacted secret observation]' if secret else message,
            'severity_hint': severity, 'fingerprint': digest(key), 'comparison': 'unknown',
            'identity_digest': digest(identity or message), 'raw_pointer': raw}


def normalized(record, index):
    require(record, ['rule', 'path', 'message'])
    return observation(record['rule'], record['path'], record['message'],
                       symbol=record.get('symbol'), identity=record.get('identity'),
                       severity=record.get('severity'), line=record.get('line'), raw=index)


def parse(path, adapter, source_root=None):
    text = Path(path).read_text(encoding='utf-8-sig')
    try:
        if adapter == 'observations-json':
            data = json.loads(text)
            if not isinstance(data, list):
                raise AuditError('Expected an observations array')
            return [normalized(x, i) for i, x in enumerate(data)]
        if adapter == 'observations-jsonl':
            return [normalized(json.loads(line), i) for i, line in enumerate(text.splitlines()) if line.strip()]
        if adapter == 'gitleaks-json':
            data = json.loads(text)
            if not isinstance(data, list):
                raise AuditError('Expected a Gitleaks array')
            result = []
            for i, x in enumerate(data):
                require(x, ['RuleID', 'File', 'StartLine', 'Secret', 'Match'])
                for field in ('Secret', 'Match'):
                    value = x[field]
                    redacted = value in ('REDACTED', '[REDACTED]') or (value and set(value) == {'*'})
                    if field == 'Match' and re.search(r'(?<![A-Za-z])REDACTED(?![A-Za-z])', value):
                        redacted = True
                    if value and not redacted:
                        raise AuditError('Gitleaks output was not natively redacted')
                source_path = x['File']
                if source_root and Path(source_path).is_absolute():
                    actual, root = Path(source_path).resolve(), Path(source_root).resolve()
                    if not actual.is_relative_to(root):
                        raise AuditError('Secret scanner path is outside its assigned snapshot')
                    source_path = actual.relative_to(root).as_posix()
                item = observation(x['RuleID'], source_path, 'Historical or snapshot secret exposure',
                                   identity=x.get('Fingerprint', str(i)), line=x['StartLine'], raw=i, secret=True)
                item['snapshot'] = x.get('Commit') or None
                result.append(item)
            return result
        if adapter == 'sarif':
            data = json.loads(text)
            if data.get('version') != '2.1.0' or not isinstance(data.get('runs'), list):
                raise AuditError('Expected SARIF 2.1.0 runs')
            result = []
            for ri, run in enumerate(data['runs']):
                if 'results' not in run:
                    raise AuditError('SARIF results omitted')
                if any(not invocation.get('executionSuccessful', False) for invocation in run.get('invocations', [])):
                    raise AuditError('SARIF reports failed or incomplete invocation')
                for i, x in enumerate(run['results']):
                    require(x, ['ruleId', 'message', 'locations'])
                    if not x['locations']:
                        raise AuditError('SARIF location missing')
                    loc = x['locations'][0]['physicalLocation']
                    uri = loc['artifactLocation']['uri']
                    # URI/path conversion must be supplied by the producing tool when absolute.
                    result.append(observation(x['ruleId'], uri, x['message']['text'],
                                              identity=x.get('partialFingerprints') or None,
                                              line=loc.get('region', {}).get('startLine'),
                                              severity=x.get('level'), raw=f'/runs/{ri}/results/{i}'))
            return result
        if adapter == 'cpd-xml':
            if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
                raise AuditError('XML entities/DTDs are not accepted')
            root = ET.fromstring(text)
            if root.tag != 'pmd-cpd' or root.findall('error') or root.findall('file/error'):
                raise AuditError('Invalid or incomplete CPD report')
            result = []
            for i, cluster in enumerate(root.findall('duplication')):
                files = cluster.findall('file')
                if len(files) < 2 or cluster.find('codefragment') is None:
                    raise AuditError('Incomplete duplicate cluster')
                content = cluster.findtext('codefragment')
                members = sorted((x.attrib['path'], x.attrib.get('line')) for x in files)
                result.append(observation('cpd', members[0][0], 'Structural duplication candidate',
                                          identity={'content': content, 'members': [x[0] for x in members]},
                                          raw=i))
            return result
        raise AuditError('Unsupported adapter: ' + str(adapter))
    except (KeyError, TypeError, json.JSONDecodeError, ET.ParseError) as exc:
        raise AuditError('Malformed or unsupported sensor record') from exc


def compare(base, head, equivalent, head_complete, renames=None):
    """No resolution claim from absent or failed coverage; no advisory/code conflation."""
    renames = renames or {}
    def key(x):
        return digest({'rule': x['rule'], 'path': x.get('symbol') or renames.get(x['path'], x['path']),
                       'identity': x['identity_digest']})
    before = {key(x): x for x in base}
    after = {key(x): x for x in head}
    results = []
    for k, x in after.items():
        state = 'unknown' if not equivalent else ('unchanged' if k in before else 'introduced')
        results.append(dict(x, comparison=state))
    if equivalent and head_complete:
        results.extend(dict(x, comparison='resolved') for k, x in before.items() if k not in after)
    return results
