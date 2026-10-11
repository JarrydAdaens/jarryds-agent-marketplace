---
name: audit-quality-sensor
description: Use when asked to run the quality sensor in an explicitly requested publication audit. Requires an explicit target repository and report folder.
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.2"
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
- `report-folder` — absolute path where `open-source-audit-report-<repo-name>/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- `run-timestamp` — the shared `YYYY-MM-DD_HHMM` stamp when part of a
  persona-led run; mint a fresh one standalone. Never overwrite an earlier run.

Derived: `RUN = <report-folder>/open-source-audit-report-<repo-name>/<run-timestamp>`,
`OUT = RUN/audit-quality-sensor`, `RAW = OUT/raw`. Config lives in
`<report-folder>/open-source-audit-report-<repo-name>/audit-config/`. `LIB` = the
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

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.

## Evidence envelope

After preserving raw tool output and successful normalization, write
`sensor-result.json` with the packaged `audit-lib/sensor-result.py`. Record the
required tool statuses, raw and normalized artifact hashes, and coverage status.
Missing tools or malformed results remain incomplete, never a clean result.
