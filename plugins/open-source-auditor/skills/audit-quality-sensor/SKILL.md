---
name: audit-quality-sensor
description: >-
  Native-linter sweep for the open-source pre-publication audit. Use when
  auditing a target repo for soft quality signals — dead code, commented-out
  blocks, unused imports, style drift, TODO/FIXME census, empty placeholder
  files — routed by the languages the repo actually contains. Read-only on the
  target repo: writes only into the user-specified report folder, and refuses to
  run without one. Triggers: "audit quality", "lint the repo for the audit",
  "check for dead code before publish", pre-publish quality sweep.
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: audit-mode-sensor
---

# Audit — Quality Sensor

Runs the native linter per language, routed by a file-extension census of the
target repo. Records which linters ran and which were skipped and why. Catches
the soft signals a reviewer notices: dead code, commented-out blocks, unused
imports, style drift.

## Required arguments & paths

Invocation: `<target-repo> <report-folder> [run-timestamp]`

- `REPO` — absolute path of the ONE repo being audited.
- `report-folder` — absolute path where `open-source-audit-report/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- `run-timestamp` — the shared `YYYY-MM-DD_HHMM` stamp when part of a
  persona-led run; mint a fresh one standalone. Never overwrite an earlier run.

Derived: `RUN = <report-folder>/open-source-audit-report/<run-timestamp>`,
`OUT = RUN/audit-quality-sensor`, `RAW = OUT/raw`. Config lives in
`<report-folder>/open-source-audit-report/audit-config/`. `LIB` = the
`audit-lib/` folder at this plugin's root (`../../audit-lib` relative to this
SKILL.md).

## Contract

- **Read-only on the target repo.** Linters run in verify/report mode only — no
  `--fix`, no formatting writes. Output goes only inside `OUT`.

## Language detection

Census file extensions in the target repo, then run only the applicable
linters. Record skipped languages and the reason in `raw/quality-extras.json`.

## Tools by language

- **C# / WPF:**
  ```bash
  dotnet format --verify-no-changes --report "$RAW/dotnet-format.json" "$REPO"
  # Roslyn analyzers: capture warnings from a warnaserror build report.
  ```
- **Python (via uvx):**
  ```bash
  uvx ruff check --output-format json "$REPO" > "$RAW/ruff.json"
  ```
- **TypeScript / JS:**
  ```bash
  npx eslint -f json "$REPO" > "$RAW/eslint.json"   # only if repo has a config
  ```
- **PowerShell:** `PSScriptAnalyzer` if present.

## Additional deterministic checks (implement as throwaway greps/scripts per run)

- Commented-out code-block detector (heuristic).
- TODO / FIXME / HACK census.
- Empty / placeholder file detector.

Write these to `raw/quality-extras.json`.

## Output

One `raw/<linter>.json` per linter run, plus `raw/quality-extras.json`, then
normalize (`uv run "$LIB/normalize.py" "$REPO" "$RAW" "$OUT/normalized"`).
Handoff to the guardrail for severity.
