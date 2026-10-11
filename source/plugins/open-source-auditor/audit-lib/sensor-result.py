"""Build a traceable sensor envelope without interpreting missing coverage as PASS."""
import argparse
import hashlib
import json
from pathlib import Path


def result(sensor, raw, normalized, tools, decisions=()):
    artifacts = []
    for kind, folder in [('raw', raw), ('normalized', normalized)]:
        for path in sorted(Path(folder).glob('*.json')):
            json.loads(path.read_text(encoding='utf-8'))
            artifacts.append({'path': f'{kind}/{path.name}',
                              'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    known = {a['path'] for a in artifacts}
    for decision in decisions:
        if (not decision.get('finding_id') or decision.get('evidence_path') not in known
                or not decision['evidence_path'].startswith('raw/')):
            raise ValueError('every decision needs a finding_id and a recorded evidence_path')
    missing = [name for name, status in tools.items() if not status.get('available')]
    covered = bool(artifacts) and any(a['path'].startswith('raw/') for a in artifacts)
    covered = covered and any(a['path'].startswith('normalized/') for a in artifacts)
    return {'schema_version': 1, 'sensor': sensor,
            'status': 'complete' if covered and not missing else 'incomplete',
            'missing_tools': sorted(missing), 'tools': tools,
            'artifacts': artifacts, 'decisions': list(decisions)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sensor', required=True)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--normalized', type=Path, required=True)
    parser.add_argument('--tools', type=Path, required=True)
    parser.add_argument('--decisions', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = result(args.sensor, args.raw, args.normalized,
                  json.loads(args.tools.read_text(encoding='utf-8')),
                  json.loads(args.decisions.read_text(encoding='utf-8')) if args.decisions else [])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return 0 if data['status'] == 'complete' else 2


if __name__ == '__main__':
    raise SystemExit(main())
