#!/usr/bin/env python3
"""Preflight for the open-source audit sensors.

Resolves which audit tools are actually available on this machine, records the
resolved version against the pin in global.json, and emits a skip record for
every tool that is missing. A sensor NEVER fails because a tool is absent; it
records the skip and moves on. That skip record is itself audit evidence.

Run standalone to see the current toolchain state:
    uv run <plugin-root>/audit-lib/preflight.py

Import from a sensor runner:
    from preflight import resolve_tools, ToolStatus
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path

# tool name -> how to invoke a version probe. Native binaries are looked up on
# PATH; uv-fronted tools are probed through uvx so the python-uv-guardrail is
# honored (never bare python/pip).
NATIVE_TOOLS = {
    "gitleaks": ["gitleaks", "version"],
    "trufflehog": ["trufflehog", "--version"],
    "syft": ["syft", "version"],
    "grype": ["grype", "version"],
    "trivy": ["trivy", "--version"],
    "lychee": ["lychee", "--version"],
    "scancode": ["scancode", "--version"],
}
UVX_TOOLS = {
    "detect-secrets": ["uvx", "detect-secrets", "--version"],
    "codespell": ["uvx", "codespell", "--version"],
    "ruff": ["uvx", "ruff", "--version"],
    "git-filter-repo": ["uvx", "git-filter-repo", "--version"],
}
NODE_TOOLS = {
    "eslint": ["npx", "--no-install", "eslint", "--version"],
}
DOTNET_TOOLS = {
    "dotnet-format": ["dotnet", "format", "--version"],
}


@dataclass
class ToolStatus:
    name: str
    available: bool
    resolved_version: str | None
    invocation: list[str]
    note: str = ""

    def skip_record(self, reason: str) -> dict:
        return {
            "tool": self.name,
            "skipped": True,
            "reason": reason,
            "resolved_version": self.resolved_version,
        }


def _probe(name: str, cmd: list[str], needs_launcher: str | None) -> ToolStatus:
    launcher = cmd[0]
    if needs_launcher and shutil.which(needs_launcher) is None:
        return ToolStatus(name, False, None, cmd,
                          note=f"launcher '{needs_launcher}' not on PATH")
    if needs_launcher is None and shutil.which(launcher) is None:
        return ToolStatus(name, False, None, cmd, note=f"'{launcher}' not on PATH")
    # On Windows a launcher may be a .cmd/.bat shim that subprocess cannot spawn
    # by bare name; resolve to the full path shutil.which found.
    resolved = shutil.which(launcher)
    run_cmd = [resolved, *cmd[1:]] if resolved else cmd
    try:
        out = subprocess.run(run_cmd, capture_output=True, text=True, timeout=90)
        version = (out.stdout or out.stderr).strip().splitlines()
        return ToolStatus(name, out.returncode == 0,
                          version[0].strip() if version else "unknown", cmd)
    except Exception as exc:  # noqa: BLE001 - preflight must never throw
        return ToolStatus(name, False, None, cmd, note=f"probe failed: {exc}")


def resolve_tools(required: list[str]) -> dict[str, ToolStatus]:
    """Resolve status for the named tools. Unknown names are reported missing."""
    statuses: dict[str, ToolStatus] = {}
    for name in required:
        if name in NATIVE_TOOLS:
            statuses[name] = _probe(name, NATIVE_TOOLS[name], None)
        elif name in UVX_TOOLS:
            statuses[name] = _probe(name, UVX_TOOLS[name], "uvx")
        elif name in NODE_TOOLS:
            statuses[name] = _probe(name, NODE_TOOLS[name], "npx")
        elif name in DOTNET_TOOLS:
            statuses[name] = _probe(name, DOTNET_TOOLS[name], "dotnet")
        else:
            statuses[name] = ToolStatus(name, False, None, [],
                                        note="unknown tool name")
    return statuses


def all_tool_names() -> list[str]:
    return [*NATIVE_TOOLS, *UVX_TOOLS, *NODE_TOOLS, *DOTNET_TOOLS]


def main() -> None:
    statuses = resolve_tools(all_tool_names())
    report = {name: asdict(s) for name, s in statuses.items()}
    print(json.dumps(report, indent=2))
    missing = [n for n, s in statuses.items() if not s.available]
    if missing:
        print(f"\nMISSING ({len(missing)}): {', '.join(missing)}")
    else:
        print("\nAll probed tools available.")


if __name__ == "__main__":
    main()
