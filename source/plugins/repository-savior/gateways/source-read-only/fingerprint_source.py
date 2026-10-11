#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Source archive fingerprinting - the read-only guarantee, made checkable.

Records a deterministic manifest (per-file SHA-256, size, and an aggregate
fingerprint) of a source repository before conversion, and later verifies
the source against that manifest to prove the migration never modified it.

Usage:
    uv run fingerprint_source.py record <source-path> <manifest.json>
    uv run fingerprint_source.py verify <source-path> <manifest.json>

Exit codes:
    0  recorded, or verified unchanged
    1  verification FAILED - the source differs from its recorded
       fingerprint; stop and escalate to the human
    2  usage or IO error
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

CHUNK_SIZE = 1 << 20


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(root: Path) -> dict:
    """Walk every file under root in deterministic order and hash it."""
    files = []
    aggregate = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative = path.relative_to(root).as_posix()
        file_hash = hash_file(path)
        files.append({"path": relative, "size": path.stat().st_size, "sha256": file_hash})
        aggregate.update(f"{relative}\0{file_hash}\n".encode())
    return {
        "schema_version": 1,
        "root": str(root),
        "file_count": len(files),
        "total_bytes": sum(entry["size"] for entry in files),
        "aggregate_sha256": aggregate.hexdigest(),
        "files": files,
    }


def main() -> int:
    if len(sys.argv) != 4 or sys.argv[1] not in ("record", "verify"):
        print(__doc__, file=sys.stderr)
        return 2
    mode, source, manifest_path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])

    if not source.is_dir():
        print(f"source path is not a directory: {source}", file=sys.stderr)
        return 2

    if mode == 'record' and manifest_path.resolve().is_relative_to(source.resolve()):
        print('refusing to write a manifest inside the read-only source', file=sys.stderr)
        return 2
    if mode == 'record' and manifest_path.exists():
        print('refusing to overwrite an existing source fingerprint', file=sys.stderr)
        return 2

    current = build_manifest(source)

    if mode == "record":
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        print(
            f"recorded {current['file_count']} files, "
            f"aggregate {current['aggregate_sha256']}"
        )
        return 0

    recorded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if recorded["aggregate_sha256"] == current["aggregate_sha256"]:
        print(f"source unchanged: aggregate {current['aggregate_sha256']}")
        return 0

    recorded_by_path = {entry["path"]: entry["sha256"] for entry in recorded["files"]}
    current_by_path = {entry["path"]: entry["sha256"] for entry in current["files"]}
    added = sorted(set(current_by_path) - set(recorded_by_path))
    removed = sorted(set(recorded_by_path) - set(current_by_path))
    changed = sorted(
        path
        for path in set(recorded_by_path) & set(current_by_path)
        if recorded_by_path[path] != current_by_path[path]
    )
    print(
        json.dumps(
            {"verified": False, "added": added, "removed": removed, "changed": changed},
            indent=2,
        )
    )
    print(
        "SOURCE MODIFIED since fingerprint was recorded. Stop the migration "
        "and escalate to the human.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
