---
name: audit-license-apply
description: >-
  Action-mode skill that applies Apache 2.0 to a target repo for open-source
  release. Use ONLY after the guardrail returns PASS (or all blocking findings
  are cleared/waived) and the human has approved licensing this repo. Adds LICENSE,
  NOTICE, per-file headers (source only, per config), and a README License section
  as ONE tip commit — never a history rewrite. Idempotent. Never pushes. Requires
  the user-specified report folder (to verify the verdict and read config);
  refuses to run without one. Triggers: "apply the license", "add Apache 2.0 to
  this repo", "license the repo for publish".
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.2"
  owner: Jarryd Adaens
  stage: action-mode
---

# Audit — License Apply (Apache 2.0)

Applies Apache 2.0 to one target repo. **Action mode** — it writes to the target
repo, so it runs only on an approved, PASS-verdict repo, and only when the human
has said "license this one."

## Required arguments & paths

Invocation: `<target-repo> <report-folder> [run-timestamp]`

- `report-folder` — absolute path where `open-source-audit-report-<repo-name>/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- The PASS verdict is read from
  `<report-folder>/open-source-audit-report-<repo-name>/<run-timestamp>/audit-publish-guardrail/audit-report.md`
  (newest run if no timestamp given); config from
  `<report-folder>/open-source-audit-report-<repo-name>/audit-config/`.

## Settled policy (encode verbatim — do not relitigate)

- **Never rewrite history to inject a license.** The license is a normal commit
  **at the tip, present day**. Retro-injecting rewrites every SHA for zero
  benefit and reads as manicuring the origin.
- **Files created / edited:**
  - `LICENSE` — verbatim Apache License 2.0 text.
  - `NOTICE` — project name, `Copyright <year> <copyrightHolder>`, and any
    required third-party attributions surfaced by the dependency sensor's SBOM.
  - **Per-file headers** — the short Apache header (`references/apache-header.txt`)
    in **source-code files only**, gated by `audit-config/global.json` →
    `license.applyPerFileHeaders`. Markdown-heavy repos get the LICENSE + NOTICE
    pair and no per-file headers — headers in markdown are noise.
  - A **License section** in the README stating Apache 2.0 and linking `LICENSE`.
- **One commit per repo**, message via the `commit-log` skill format when that
  skill is installed, otherwise a plain conventional message.
- **Never push.** Push stays human-only.

## Idempotency

Re-running on an already-licensed repo **verifies, does not duplicate**: if
`LICENSE` matches the canonical text, NOTICE carries the right copyright line,
headers are present in the configured file types, and the README has a License
section, report "already licensed, verified" and make no commit.

## Procedure

1. Confirm PASS verdict (or cleared/waived blockers) and human approval for this
   specific repo.
2. Resolve `year` and `copyrightHolder` from `audit-config/global.json`.
3. Write `LICENSE` (canonical text), `NOTICE` (with SBOM attributions).
4. Stamp per-file headers into the configured source file types only.
5. Add/refresh the README License section.
6. Stage and commit as one commit via `commit-log`. Stop. Report. Do not push.
