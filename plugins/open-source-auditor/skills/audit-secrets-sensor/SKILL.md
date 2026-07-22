---
name: audit-secrets-sensor
description: >-
  Deterministic secret scanner for the open-source pre-publication audit. Use
  when auditing a target repo for leaked API keys, tokens, credentials, private
  keys, internal URLs, or company identity — in current files AND full git
  history. Read-only on the target repo: writes only into the user-specified
  report folder, and refuses to run without one. Highest-stakes sensor; run it
  first. Triggers: "audit secrets", "scan for leaked keys", "check history for
  credentials", pre-publish secret sweep.
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: audit-mode-sensor
---

# Audit — Secrets Sensor

The highest-stakes sensor. A leaked live credential is the one finding that
BLOCKs publish unconditionally. It scans the working tree **and the entire git
history of every branch that will be pushed**, because history is exactly where
secrets hide and where a reviewer's own scanner will find them.

## Required arguments & paths

Invocation: `<target-repo> <report-folder> [run-timestamp]`

- `REPO` — absolute path of the ONE repo being audited.
- `report-folder` — absolute path where `open-source-audit-report/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- `run-timestamp` — the shared `YYYY-MM-DD_HHMM` stamp when part of a
  persona-led run; mint a fresh one standalone. Never overwrite an earlier run.

Derived: `RUN = <report-folder>/open-source-audit-report/<run-timestamp>`,
`OUT = RUN/audit-secrets-sensor`, `RAW = OUT/raw`. Config lives in
`<report-folder>/open-source-audit-report/audit-config/` (bootstrap from this
plugin's `config/` templates if missing). `LIB` = the `audit-lib/` folder at
this plugin's root (`../../audit-lib` relative to this SKILL.md).

## Contract

- **Read-only on the target repo.** Every artifact goes inside `OUT`; nothing in
  the target repo is created, modified, or deleted.
- **Deterministic first, judgment never.** This sensor reports; it does not
  decide. Allowlisted fixtures are still reported here — the guardrail downgrades
  them with the config as evidence.

## Preflight

```bash
uv run "$LIB/preflight.py"
```

Record the resolved versions into `OUT/metadata.json` and compare against
`audit-config/global.json` `toolVersions`. Any tool marked
`PENDING-INSTALL` or reported missing is a recorded **skip**, not a failure.

## Tools & invocations

1. **gitleaks** (primary — fast, full-history, regex + entropy). Emit JSON for
   triage and SARIF as a second format (cheap; ready for GitHub code-scanning):
   ```bash
   gitleaks git "$REPO" --log-opts "--all --full-history" \
     --report-format json --report-path "$RAW/gitleaks.json" \
     --redact=100 --no-banner
   gitleaks git "$REPO" --log-opts "--all --full-history" \
     --report-format sarif --report-path "$RAW/gitleaks.sarif" \
     --redact=100 --no-banner
   ```
2. **trufflehog** (optional second pass — verified/live-credential detection):
   ```bash
   trufflehog git "file://$REPO" --json > "$RAW/trufflehog.json"
   ```
3. **detect-secrets** (optional third opinion / baseline workflow, via uvx):
   ```bash
   uvx detect-secrets scan "$REPO" > "$RAW/detect-secrets.json"
   ```
4. **Company-identity grep** (always runs — insurance, even when repos are
   believed clean). Scan history metadata for author/committer names, emails,
   and hostnames matching the watchlist in `global.json`:
   ```bash
   git -C "$REPO" log --all --format='%an|%ae|%cn|%ce' | sort -u > "$RAW/identity-authors.txt"
   ```
   Then match against `tone.properNounWatchlist` + any company-identity patterns
   and write structured results to `$RAW/identity-grep.json`.

## Scope

Working tree + full history of all branches that exist on the public remote or
will be pushed. Do not limit to `HEAD`.

## Normalize

```bash
uv run "$LIB/normalize.py" "$REPO" "$RAW" "$OUT/normalized"
```

## Outputs

`raw/gitleaks.json`, `raw/gitleaks.sarif`, `raw/trufflehog.json`,
`raw/detect-secrets.json`, `raw/identity-grep.json`, plus normalized copies. Per-repo fixture allowlists
live in `audit-config/<repo-name>.json` and are consumed by the guardrail, not
here.

## Handoff

Do not triage. Leave severity, true-vs-false-positive, and the PASS/BLOCK
verdict to `audit-publish-guardrail`.
