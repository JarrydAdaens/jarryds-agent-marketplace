"""Pin scope without changing the developer checkout or consulting head policy."""
import json
import os
from pathlib import Path
import re
import subprocess

from .common import AuditError, digest, inside, relative


def git(repo, *args, binary=False, okay=False, input_bytes=None):
    env = dict(os.environ, GIT_TERMINAL_PROMPT='0', GIT_CONFIG_NOSYSTEM='1',
               GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS='0')
    p = subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
                        '-c', 'diff.external=', '-C', str(repo), *args],
                       capture_output=True, env=env, timeout=180, input=input_bytes)
    if p.returncode and not okay:
        raise AuditError('Git scope operation failed: ' + p.stderr.decode(errors='replace')[:1000])
    if okay:
        return p
    return p.stdout if binary else p.stdout.decode('utf-8', errors='strict').strip()


def commit(repo, ref):
    if not ref or ref.startswith('-'):
        raise AuditError('An explicit resolvable ref is required')
    return git(repo, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}')


def load_config(text):
    try:
        config = json.loads(text)
    except json.JSONDecodeError:
        try:
            import yaml
        except ImportError as exc:
            raise AuditError('Full YAML needs pre-provisioned PyYAML; JSON-compatible YAML needs no dependency') from exc
        config = yaml.safe_load(text)
    if not isinstance(config, dict) or config.get('schema_version') != 1:
        raise AuditError('Configuration schema_version must be 1')
    allowed = {'schema_version', 'target_branch', 'required_capabilities', 'sensors',
               'required_roles', 'blocking_priorities', 'resources', 'models',
               'intentional_duplication', 'accepted_risks', 'output_destinations',
               'integration_strategy', 'external_operations', 'retention_days'}
    if set(config) - allowed:
        raise AuditError('Unknown policy fields: ' + ', '.join(sorted(set(config) - allowed)))
    if config.get('integration_strategy', 'merge') != 'merge':
        raise AuditError('1.0 constructs merge candidates only; provide exact CI evidence for other strategies in a future adapter')
    # Unimplemented exception authority must never silently waive a blocker.
    if config.get('accepted_risks'):
        raise AuditError('1.0 records proposed risks but does not apply policy waivers; resolve findings explicitly')
    return config


def policy(repo, base, config_path=None):
    if config_path:
        return load_config(Path(config_path).read_text(encoding='utf-8-sig')), 'explicit-local-config'
    if not base:
        raise AuditError('Supply --base or --config; target branch is never guessed')
    pinned = commit(repo, base)
    p = git(repo, 'show', pinned + ':.code-audit.yml', okay=True)
    if p.returncode:
        return {'schema_version': 1}, 'built-in-conservative-policy'
    return load_config(p.stdout.decode('utf-8-sig')), 'target:' + pinned


def inventory(repo, start, end):
    raw = git(repo, 'diff', '--no-ext-diff', '--no-textconv', '--name-status', '-z',
              '--find-renames', start, end, binary=True).decode('utf-8').split('\0')
    changes = []
    i = 0
    while i < len(raw) and raw[i]:
        status, path = raw[i], raw[i + 1]
        i += 2
        old = None
        if status.startswith(('R', 'C')):
            old, path = path, raw[i]
            i += 1
        relative(path)
        changes.append({'status': status, 'path': path, 'old_path': old})
    nums = git(repo, 'diff', '--no-ext-diff', '--no-textconv', '--numstat', '-z', start, end, binary=True)
    # Binary content remains in scope; unsupported reviewer content stays a gap.
    binary_present = b'-\t-\t' in nums
    return changes, binary_present


def snapshot(repo, ref, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    omitted = []
    files = []
    materialized = set()
    for entry in git(repo, 'ls-tree', '-r', '-z', ref, binary=True).split(b'\0'):
        if not entry:
            continue
        fields, name = entry.split(b'\t', 1)
        mode, kind, oid = fields.decode('ascii').split(' ')
        path = name.decode('utf-8')
        relative(path)
        if mode == '160000':
            omitted.append({'path': path, 'reason': 'submodule content unavailable'})
        elif mode not in ('100644', '100755') or kind != 'blob':
            omitted.append({'path': path, 'reason': 'symlink or special file not materialized'})
        else:
            destination_key = os.path.normcase(str(inside(destination, path)))
            if destination_key in materialized:
                raise AuditError('Snapshot paths collide on this filesystem: ' + path)
            materialized.add(destination_key)
            files.append((path, oid, mode))
    # Read committed blobs directly: git archive would obey branch export-ignore/export-subst.
    # Batch bounds peak memory by one group instead of the entire repository.
    for offset in range(0, len(files), 128):
        batch = files[offset:offset + 128]
        raw = git(repo, 'cat-file', '--batch', binary=True,
                  input_bytes=('\n'.join(oid for _, oid, _ in batch) + '\n').encode('ascii'))
        position = 0
        for name, oid, mode in batch:
            end = raw.index(b'\n', position)
            returned, kind, size = raw[position:end].decode('ascii').split(' ')
            size = int(size)
            if returned != oid or kind != 'blob':
                raise AuditError('Git blob snapshot was incomplete')
            content = raw[end + 1:end + 1 + size]
            if len(content) != size:
                raise AuditError('Truncated Git blob snapshot')
            target = inside(destination, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            if mode == '100755':
                target.chmod(0o755)
            position = end + size + 2
    for path in destination.rglob('*'):
        if path.is_file() and path.stat().st_size < 1024:
            if path.read_bytes().startswith(b'version https://git-lfs.github.com/spec/v1'):
                omitted.append({'path': path.relative_to(destination).as_posix(), 'reason': 'LFS pointer only'})
    return omitted


def pin(repo, target, base):
    repo = Path(git(repo, 'rev-parse', '--show-toplevel')).resolve()
    if git(repo, 'rev-parse', '--is-shallow-repository') == 'true':
        raise AuditError('Shallow history is incomplete; provision full history before review')
    if '...' in target:
        raise AuditError('Use an explicit A..H net range, not an ambiguous three-dot range')
    range_start = None
    if '..' in target:
        range_start, target = target.split('..', 1)
        if not range_start or not target:
            raise AuditError('Both explicit range endpoints are required')
    h, b = commit(repo, target), commit(repo, base)
    merges = git(repo, 'merge-base', '--all', b, h).splitlines()
    if len(merges) != 1:
        raise AuditError('A unique merge base is required')
    m = merges[0]
    start = commit(repo, range_start) if range_start else m
    changes, binary = inventory(repo, start, h)
    history = git(repo, 'rev-list', '--reverse', h, '--not', b).splitlines()
    return repo, {'H': h, 'B': b, 'M': m, 'A': start, 'I': None, 'integration_tree': None,
                  'head_ref': target, 'base_ref': base, 'range_start': start,
                  'range_mode': 'net-tree' if range_start else 'branch',
                  'history_commits': history, 'changes': changes, 'binary_present': binary,
                  'local_edits_excluded': bool(git(repo, 'status', '--porcelain')),
                  'repository_identity': digest(str(repo)), 'integration': 'pending'}


def integration(repo, scope, run):
    if git(repo, 'merge-base', '--is-ancestor', scope['B'], scope['H'], okay=True).returncode == 0:
        scope.update(I=scope['H'], integration_tree=git(repo, 'rev-parse', scope['H'] + '^{tree}'),
                     integration='head-includes-target')
        return
    # An unconfigured custom driver silently falls back to text in a fresh clone.
    # Refuse that substitution rather than asserting the wrong candidate is valid.
    for label in ('B', 'H'):
        for attributes in (Path(run) / 'snapshots' / label).rglob('.gitattributes'):
            for line in attributes.read_text(encoding='utf-8').splitlines():
                if line.lstrip().startswith('#'):
                    continue
                drivers = re.findall(r'(?:^|\s)merge=([^\s#]+)', line)
                if any(driver not in ('text', 'binary', 'union') for driver in drivers):
                    scope.update(integration='unavailable', integration_reason='Custom merge driver requires a validated integration adapter')
                    return
    candidate = Path(run) / 'workspaces' / 'integration'
    candidate.parent.mkdir(parents=True, exist_ok=True)
    p = git(repo, 'clone', '--local', '--no-hardlinks', '--no-checkout',
            Path(repo).as_posix(), candidate.as_posix(), okay=True)
    if p.returncode:
        raise AuditError('Could not create isolated integration workspace: ' + p.stderr.decode(errors='replace')[:1000])
    git(candidate, 'checkout', '--detach', scope['B'])
    result = git(candidate, '-c', 'user.name=Audit Candidate', '-c', 'user.email=audit@example.invalid',
                 '-c', 'commit.gpgSign=false', '-c', 'merge.autoStash=false',
                 'merge', '--no-commit', '--no-ff', scope['H'], okay=True)
    if result.returncode:
        conflicts = git(candidate, 'diff', '--name-only', '--diff-filter=U').splitlines()
        scope['integration'] = 'conflict' if conflicts else 'unavailable'
        scope['integration_reason'] = 'Merge conflict: ' + ', '.join(conflicts) if conflicts else 'Merge candidate construction failed'
        return
    tree = git(candidate, 'write-tree')
    # A tree hash is the build identity for an uncommitted candidate, never a fictitious commit SHA.
    scope.update(I='tree:' + tree, integration_tree=tree, integration='merge-candidate')
    omissions = snapshot(candidate, tree, Path(run) / 'snapshots' / 'I')
    scope['integration_omissions'] = omissions
