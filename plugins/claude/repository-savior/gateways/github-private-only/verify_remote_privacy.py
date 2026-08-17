#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Independent post-creation privacy verification (Gate 4).

Queries GitHub for the just-created repository and verifies, before any
push is permitted:

    isPrivate  == true
    visibility == PRIVATE
    owner      == configured target owner
    name       == approved repository name

Usage:
    uv run verify_remote_privacy.py <owner> <name>

Exit codes:
    0  verified private, owner and name match - push may proceed
    1  verification FAILED - do not add or use the remote, do not push,
       mark the migration BLOCKED, produce a high-severity report
    2  could not query GitHub (gh error) - treat as failed, do not push
"""

from __future__ import annotations

import json
import subprocess
import sys


def evaluate(payload: dict, expected_owner: str, expected_name: str) -> list[str]:
    """Return the list of privacy-check failures (empty means verified)."""
    failures: list[str] = []
    if payload.get("isPrivate") is not True:
        failures.append(f"isPrivate is {payload.get('isPrivate')!r}, expected True")
    visibility = str(payload.get("visibility", "")).upper()
    if visibility != "PRIVATE":
        failures.append(f"visibility is {visibility!r}, expected 'PRIVATE'")
    owner = (payload.get("owner") or {}).get("login", "")
    if owner.lower() != expected_owner.lower():
        failures.append(f"owner is {owner!r}, expected {expected_owner!r}")
    name = payload.get("name", "")
    if name.lower() != expected_name.lower():
        failures.append(f"name is {name!r}, expected {expected_name!r}")
    return failures


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: verify_remote_privacy.py <owner> <name>", file=sys.stderr)
        return 2
    owner, name = sys.argv[1], sys.argv[2]

    view = subprocess.run(
        [
            "gh", "repo", "view", f"{owner}/{name}",
            "--json", "isPrivate,visibility,owner,name",
        ],
        capture_output=True,
        text=True,
    )
    if view.returncode != 0:
        print(f"could not query {owner}/{name}:\n{view.stderr}", file=sys.stderr)
        return 2

    payload = json.loads(view.stdout)
    failures = evaluate(payload, owner, name)
    print(
        json.dumps(
            {
                "repository": f"{owner}/{name}",
                "verified_private": not failures,
                "failures": failures,
            },
            indent=2,
        )
    )
    if failures:
        print(
            "PRIVACY VERIFICATION FAILED. Do not push. Mark the migration "
            "BLOCKED and escalate to the human. Never attempt to 'fix' the "
            "remote's visibility - even brief exposure is unacceptable.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
