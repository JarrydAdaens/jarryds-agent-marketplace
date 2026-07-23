---
name: write-migration-report
description: >-
  Use when writing the final migration report for one repository — both the
  human-readable Markdown and the machine-readable JSON — covering source
  fingerprint, converter and exact version, author/branch/tag mappings,
  counts, large-file findings, audit result, GitHub destination, privacy
  and fresh-clone verification, warnings, accepted deviations, and final
  status. Also verifies the completion criteria before recording COMPLETE.
  Writes only into the user-specified migration root and refuses to run
  without one. Triggers: "write the migration report", "close out the
  migration".
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Write Migration Report

Produces the durable record of the migration and performs the final
completion check. A migration without its report is not finished.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; inputs are the manifests
and state accumulated by every prior skill. Template:
`../../templates/migration-report.md`; JSON must validate against
`../../schemas/migration-report.schema.json` (paths relative to this
SKILL.md).

## Outputs

- `<migration-root>/reports/<repository-name>.migration.md` — from the
  template;
- `<migration-root>/reports/<repository-name>.migration.json` — schema-
  valid.

Both include: source type, location, and fingerprint; converter and exact
version (pinned commit for hg-fast-export); author mapping; branch and tag
mapping; revision and commit counts with any explained deviation;
large-file findings; audit result and report path; GitHub destination;
privacy verification result; fresh-clone verification result; warnings and
accepted deviations; final status. **No secrets, tokens, or credential
material ever appear in a report.**

## Completion criteria (verify, do not assume)

Record `COMPLETE` only when ALL are true:

- the original source remains intact (re-run the source-read-only gateway's
  `verify` against the **original** source path);
- the source inventory exists;
- the local Git repository passed integrity verification;
- branch, tag, author, and tip-content mappings are documented;
- GitHub publishability checks passed;
- the auditor returned `pass`;
- the GitHub repository exists under the configured owner;
- independent remote verification proved it private;
- all approved refs were pushed;
- the fresh clone succeeded and matches the approved local repository;
- both report files exist.

Anything less is an incomplete migration — report the actual status
(`BLOCKED`, `FAILED`, `REQUIRES_HUMAN_DECISION`) faithfully instead. On
`COMPLETE`, the workspace may be moved to
`<migration-root>/completed/` per config; failed workspaces are retained
when `retain_failed_workspaces` is true.

## State

Final transition to `COMPLETE` (or the truthful terminal state), with both
report paths recorded.
