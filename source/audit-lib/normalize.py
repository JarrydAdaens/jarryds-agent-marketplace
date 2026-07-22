#!/usr/bin/env python3
"""Deterministic normalization for audit sensor output.

The raw/ tree is untouched tool output. The normalized/ tree is the same
findings with volatile fields stripped and a stable sort applied, so two runs
from the same starting commit produce byte-identical normalized output. That is
what makes the baseline-branch validation (manual vs. automated) a real diff and
not a vibe.

Rules (from the design spec):
  - Strip volatile fields: timestamps, durations, run IDs, hostnames.
  - Rewrite absolute path prefixes to repo-relative.
  - Sort findings by (file, line, rule) so ordering is never a diff artifact.

Usage:
    uv run .claude/audit-lib/normalize.py <repo_root> <raw_dir> <normalized_dir>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Field names that carry run-to-run noise. Matched case-insensitively against
# JSON keys at any depth and removed before diffing.
VOLATILE_KEYS = {
    "timestamp", "date", "scandate", "starttime", "endtime", "duration",
    "elapsed", "runid", "run_id", "scanid", "hostname", "host", "machine",
    "user", "username", "createdat", "updatedat", "_meta_generated",
}

# JSON keys whose string values are file paths we want repo-relative.
PATH_KEYS = {"file", "path", "filename", "sourcefile", "location", "target"}


def _to_relative(value: str, repo_root: Path) -> str:
    try:
        p = Path(value)
        if p.is_absolute():
            return p.relative_to(repo_root).as_posix()
    except (ValueError, OSError):
        pass
    # Also strip an embedded absolute prefix inside a longer string.
    root_str = repo_root.as_posix()
    return value.replace(root_str + "/", "").replace(str(repo_root) + "\\", "")


def _scrub(obj, repo_root: Path):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k.lower() in VOLATILE_KEYS:
                continue
            if k.lower() in PATH_KEYS and isinstance(v, str):
                out[k] = _to_relative(v, repo_root)
            else:
                out[k] = _scrub(v, repo_root)
        return out
    if isinstance(obj, list):
        return [_scrub(v, repo_root) for v in obj]
    return obj


def _sort_key(finding: dict) -> tuple:
    def first(*keys):
        for k in keys:
            for actual in finding:
                if actual.lower() == k:
                    return str(finding[actual])
        return ""
    return (first("file", "path", "filename"),
            first("line", "startline", "linenumber"),
            first("ruleid", "rule", "check", "id"))


def normalize_file(src: Path, repo_root: Path) -> object:
    data = json.loads(src.read_text(encoding="utf-8"))
    scrubbed = _scrub(data, repo_root)
    if isinstance(scrubbed, list) and all(isinstance(x, dict) for x in scrubbed):
        scrubbed.sort(key=_sort_key)
    return scrubbed


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    repo_root = Path(sys.argv[1]).resolve()
    raw_dir = Path(sys.argv[2])
    norm_dir = Path(sys.argv[3])
    norm_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    for src in sorted(raw_dir.glob("*.json")):
        try:
            result = normalize_file(src, repo_root)
        except json.JSONDecodeError as exc:
            print(f"skip {src.name}: not valid JSON ({exc})")
            continue
        dst = norm_dir / src.name
        dst.write_text(json.dumps(result, indent=2, sort_keys=True,
                                  ensure_ascii=False) + "\n", encoding="utf-8")
        count += 1
    print(f"normalized {count} file(s) into {norm_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
