# open-source-auditor

Pre-publication audit for open-sourcing a repository, installed as one bundle: a specialist auditor persona, six deterministic read-only sensors (secrets, tone, quality, dependency, provenance, hygiene), a triaging guardrail that ends in a machine-readable PASS/BLOCK verdict, an Apache 2.0 license applier, and a post-abort cleanup janitor.

**Design principle:** deterministic scanners find, AI triages and explains, the human gates action. Every finding traces to machine output with file, line, and evidence.

## Install

**Claude Code / Codex:** add the `jarryds-agents` marketplace, then `/plugin install open-source-auditor@jarryds-agents` — globally if you audit often, or enabled per project.

**Cursor:** copy this plugin folder to `%USERPROFILE%\.cursor\plugins\local\open-source-auditor\` (must contain `.cursor-plugin/plugin.json` at that root), then **Developer: Reload Window**. On Teams/Enterprise, import the marketplace repo from Dashboard → Plugins instead. See the marketplace root `README.md` for details.

One install brings the persona, all nine skills, the shared `audit-lib/` scripts, and sanitized config templates.

## Usage

Everything takes explicit arguments: `<target-repo> <report-folder>`. The report folder is **required** — the persona and every skill refuse to run without it, and never write anywhere you did not name.

All output lands under `<report-folder>/open-source-audit-report-<repo-name>/`:

```text
open-source-audit-report-<repo-name>/
  audit-config/            # your filled-in config (personal - never publish it)
  <YYYY-MM-DD_HHMM>/       # one folder per run/attempt
    audit-report.html      # durable single-file report: Summary tab + one tab
                           #   per sensor, every claim linked to raw evidence
    <skill-name>/          # one folder per skill that produced artifacts
      raw/  normalized/
    audit-publish-guardrail/
      audit-report.md      # the PASS/BLOCK verdict
```

Each run's `audit-report.html` is self-contained (inline CSS/JS, relative evidence links), so successive passes over a repo can be opened side by side to compare progress.

Re-runs create sibling timestamp folders; nothing is overwritten. The guardrail raises a **Critical** finding if any of the report tree is tracked by the target repo's git — it holds the very findings the audit exists to catch and must never be published.

## What the consuming machine must provide

External scanner binaries, installed and pinned in your `audit-config/global.json` → `toolVersions`: gitleaks, trufflehog, detect-secrets, syft, grype, trivy, lychee, codespell, ScanCode Toolkit, plus per-language linters. Python tools run through `uv`/`uvx`. Missing tools are recorded as skips, never silent gaps.

## Known limitations

- Works on Claude Code, Cursor, and Codex (skills + persona markdown). Persona frontmatter still carries Claude-oriented `tools` / `model` hints; Cursor/Codex discover the agent by `name` + `description` and may ignore those fields.
- One repo per run, sequentially — the sensors are memory-heavy (ScanCode especially); never fan audits out concurrently.
- Audit mode is read-only on the target repo except for the report tree when you point the report folder inside it.
- It never pushes; publishing remains a human action.
