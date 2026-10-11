---
name: assess-github-publishability
description: Use when an authorized legacy repository migration reaches the assess github publishability stage. Requires an explicit migration root.
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Assess GitHub Publishability

Checks the **full Git object history** — not just the tip — before
publication. Legacy game repositories especially need the full-history
large-object scan; a 100 MiB+ blob anywhere in history blocks the push.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`CONVERTED`.

## Checks

Against `WS/converted.git/`:

- **Object size sweep** across all history (e.g.
  `git cat-file --batch-all-objects --batch-check`) — flag every blob at or
  near GitHub's 100 MiB hard limit, and totals against GitHub's
  keep-repositories-small guidance;
- repository size and object count;
- Git LFS candidates (large binary classes: assets, archives, builds);
- generated binaries and build outputs committed into history;
- path or filename incompatibilities (case collisions, reserved Windows
  names, invalid characters, over-long paths);
- submodules or SVN externals requiring separate migration;
- damaged Git objects (`git fsck` object errors).

## Gate behavior

- All clear → record findings and proceed.
- **Needs Git LFS or history rewriting** → `REQUIRES_HUMAN_DECISION`. The
  human chooses the remediation; historical storage is never silently
  altered, and any approved rewrite flows back through conversion +
  re-verification + re-audit.
- Damaged objects → `FAILED`.

## Outputs

`WS/manifests/publishability.json`: findings per check, every flagged path
with byte size, and the overall verdict. Nothing is silently discarded —
every large file is listed even when under the limit but notable.

## State

Append a transition recording the verdict; state remains `CONVERTED` (this
is an input to local verification), or moves to the holding state above.

## Handoff

`verify-local-conversion` runs next when the gate passes.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
