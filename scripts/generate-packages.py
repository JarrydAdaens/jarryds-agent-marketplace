"""Generate self-contained personal plugin payloads; manifests stay host-owned."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = ('open-source-auditor', 'repository-savior',
            'game-golden-screenshot-verifier', 'wpf-visual-quality-gate')
HOSTS = ('claude', 'codex', 'cursor')


def payload(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob('*')
            if p.is_file() and not any(part.startswith('.') or part == '__pycache__'
                                       for part in p.relative_to(root).parts)}


def adapted(relative, data, host):
    if relative.parts[0] == 'agents' and relative.suffix == '.md':
        text = data.decode('utf-8')
        if host != 'claude':
            text = '\n'.join(line for line in text.split('\n')
                             if not line.startswith(('tools:', 'model:')))
        return text.encode('utf-8')
    return data


def generate(check=False):
    errors = []
    for family in FAMILIES:
        source = ROOT / 'source' / 'plugins' / family
        files = payload(source)
        if not files:
            errors.append(f'empty authoring source: {family}')
            continue
        for host in HOSTS:
            target = ROOT / 'plugins' / host / family
            expected = {p: adapted(p, b, host) for p, b in files.items()}
            actual = payload(target)
            stale = set(actual) - set(expected)
            for relative in stale:
                errors.append(f'unowned payload: {host}/{family}/{relative}')
            for relative, data in expected.items():
                destination = target / relative
                if check:
                    if actual.get(relative) != data:
                        errors.append(f'parity: {host}/{family}/{relative}')
                else:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(data)
            digest = hashlib.sha256(b''.join(p.as_posix().encode() + b'\0' + b
                                             for p, b in sorted(expected.items()))).hexdigest()
            revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
            manifest = json.loads((target / f'.{host}-plugin/plugin.json').read_text(encoding='utf-8'))
            receipt = {'schema_version': 1, 'family': family, 'host': host,
                       'payload_sha256': digest, 'source': f'source/plugins/{family}',
                       'source_revision': revision, 'source_state': 'worktree',
                       'component_version': manifest.get('version', revision),
                       'activation': 'not_tested', 'host_version': None,
                       'note': 'Generation proves payload parity, not installed host activation.'}
            receipt_path = target / '.package-receipt.json'
            encoded = (json.dumps(receipt, indent=2) + '\n').encode()
            if check and (not receipt_path.exists() or receipt_path.read_bytes() != encoded):
                errors.append(f'receipt: {host}/{family}')
            elif not check:
                receipt_path.write_bytes(encoded)
    for error in errors:
        print(error, file=sys.stderr)
    return bool(errors)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    sys.exit(generate(parser.parse_args().check))
