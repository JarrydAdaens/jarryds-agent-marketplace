#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""The only permitted path for creating the GitHub repository.

Publication policy is PRIVATE_ONLY. It is a constant, not a parameter:
there is no argument, environment variable, or config value that can make
this script create anything other than a private repository. Commands that
mention public/internal visibility are rejected before anything runs.

Usage:
    uv run create_private_repo.py <owner> <name>
        [--description TEXT] [--allow-issues] [--allow-wiki]

Exit codes:
    0  created and verified private
    2  gh not authenticated / cannot act for owner
    3  name collision - repository already exists (never overwritten)
    4  CRITICAL - created repository failed the privacy check; do not push,
       mark the migration BLOCKED, escalate to the human immediately
    5  forbidden visibility token detected in the invocation
    6  creation command failed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

PUBLICATION_POLICY = "PRIVATE_ONLY"

# Rejected anywhere in the invocation, case-insensitively. "--private" is
# not listed because the gateway itself supplies it - callers never pass
# visibility in any form.
FORBIDDEN_TOKENS = (
    "--public",
    "--internal",
    "--visibility",
    "repo edit",
)


class ForbiddenVisibilityError(ValueError):
    """Raised when an invocation smells like a visibility override."""


def reject_forbidden(argv: list[str]) -> None:
    """Reject any invocation containing a visibility-related token."""
    joined = " ".join(argv).lower()
    for token in FORBIDDEN_TOKENS:
        if token in joined:
            raise ForbiddenVisibilityError(
                f"forbidden token {token!r} in invocation; "
                f"publication policy is {PUBLICATION_POLICY}"
            )


def build_create_command(
    owner: str,
    name: str,
    description: str = "",
    allow_issues: bool = False,
    allow_wiki: bool = False,
) -> list[str]:
    """Build the gh invocation. --private is unconditional by construction."""
    command = ["gh", "repo", "create", f"{owner}/{name}", "--private"]
    if description:
        command += ["--description", description]
    if not allow_issues:
        command.append("--disable-issues")
    if not allow_wiki:
        command.append("--disable-wiki")
    return command


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a PRIVATE GitHub repository (the only option)."
    )
    parser.add_argument("owner")
    parser.add_argument("name")
    parser.add_argument("--description", default="")
    parser.add_argument("--allow-issues", action="store_true")
    parser.add_argument("--allow-wiki", action="store_true")
    args = parser.parse_args()

    try:
        reject_forbidden(sys.argv)
    except ForbiddenVisibilityError as error:
        print(f"REJECTED: {error}", file=sys.stderr)
        return 5

    full_name = f"{args.owner}/{args.name}"

    auth = run(["gh", "auth", "status"])
    if auth.returncode != 0:
        print("gh is not authenticated; run 'gh auth login' first.", file=sys.stderr)
        return 2

    existing = run(["gh", "repo", "view", full_name, "--json", "name"])
    if existing.returncode == 0:
        print(
            f"COLLISION: {full_name} already exists on GitHub. "
            "This gateway never overwrites; resolve the name and rerun.",
            file=sys.stderr,
        )
        return 3

    create = run(
        build_create_command(
            args.owner,
            args.name,
            args.description,
            args.allow_issues,
            args.allow_wiki,
        )
    )
    if create.returncode != 0:
        print(f"gh repo create failed:\n{create.stderr}", file=sys.stderr)
        return 6

    view = run(
        ["gh", "repo", "view", full_name, "--json", "isPrivate,visibility,owner,name"]
    )
    payload = json.loads(view.stdout) if view.returncode == 0 else {}
    is_private = payload.get("isPrivate") is True
    visibility = str(payload.get("visibility", "")).upper()

    result = {
        "policy": PUBLICATION_POLICY,
        "repository": full_name,
        "created": True,
        "isPrivate": payload.get("isPrivate"),
        "visibility": visibility,
        "verified_private": is_private and visibility == "PRIVATE",
    }
    print(json.dumps(result, indent=2))

    if not result["verified_private"]:
        print(
            "CRITICAL: repository was created but is NOT verifiably private. "
            "Do not add the remote, do not push. Mark the migration BLOCKED "
            "and escalate to the human immediately.",
            file=sys.stderr,
        )
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
