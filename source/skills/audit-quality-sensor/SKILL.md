---
name: audit-quality-sensor
description: >-
  Native-linter sweep for the open-source pre-publication audit. Use when
  auditing a target repo for soft quality signals — dead code, commented-out
  blocks, unused imports, style drift, TODO/FIXME census, empty placeholder
  files — routed by the languages the repo actually contains. Read-only. Triggers:
  "audit quality", "lint the repo for the audit", "check for dead code before
  publish", pre-publish quality sweep.
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

## Contract

- **Read-only on the target repo.** Linters run in verify/report mode only — no
  `--fix`, no formatting writes. Output goes to the run's `raw/` folder.

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

## Additional deterministic checks (script in `scripts/`)

- Commented-out code-block detector (heuristic).
- TODO / FIXME / HACK census.
- Empty / placeholder file detector.

Write these to `raw/quality-extras.json`.

## Output

One `raw/<linter>.json` per linter run, plus `raw/quality-extras.json`, then
normalize. Handoff to the guardrail for severity.
