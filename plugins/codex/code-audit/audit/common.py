"""Atomic artifacts, containment, canonical digests, and single-writer ownership."""
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile


class AuditError(ValueError):
    pass


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True).encode()).hexdigest()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=True) + '\n'
    fd, temp = tempfile.mkstemp(prefix='.writing-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def relative(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise AuditError('Expected a repository-relative POSIX path')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('..', '.') for x in value.split('/')):
        raise AuditError('Path traversal or absolute path rejected')
    return p


def inside(root, value):
    root = Path(root).resolve()
    result = root.joinpath(*relative(value).parts)
    if not result.resolve().is_relative_to(root):
        raise AuditError('Path escapes artifact root')
    # Do not consume symlinked evidence or source paths.
    for parent in [result, *result.parents]:
        if parent == root:
            break
        if parent.is_symlink():
            raise AuditError('Symlinked evidence rejected')
    return result


def require(obj, fields):
    if not isinstance(obj, dict) or any(k not in obj for k in fields):
        raise AuditError('Missing required fields: ' + ', '.join(fields))


@contextlib.contextmanager
def writer(root):
    """Only abandon a dead controller lock; never signal an arbitrary saved PID."""
    path = Path(root) / '.controller.lock'
    for attempt in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            break
        except FileExistsError:
            lock = read(path)
            try:
                os.kill(int(lock['pid']), 0)
            except ProcessLookupError:
                path.unlink()
                continue
            except PermissionError:
                pass
            raise AuditError('Another controller owns this run')
    else:
        raise AuditError('Unable to acquire run ownership')
    with os.fdopen(fd, 'w') as stream:
        json.dump({'pid': os.getpid(), 'started': now()}, stream)
    try:
        yield
    finally:
        path.unlink(missing_ok=True)
