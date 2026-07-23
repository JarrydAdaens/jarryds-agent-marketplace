---
name: push-git-repository
description: >-
  Use when pushing an approved converted repository to its
  privacy-verified GitHub remote. Pushes exactly the verified ref
  inventory — approved branches, tags, and separately approved LFS objects
  — never a broad wildcard, never converter/audit/temporary/backup refs,
  and never a force push. Writes only into the user-specified migration
  root and refuses to run without one. Triggers: "push the migrated repo",
  "upload the approved refs".
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Push Git Repository

Adds the verified GitHub remote to `WS/converted.git/` and pushes the
approved refs — and only those.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`REMOTE_PRIVACY_VERIFIED`; the approved ref inventory comes from
`WS/manifests/ref-map.json` and `local-verification.json`.

## Building the push set

Generate the explicit ref list from the verified inventory — **never**
`push --all`, `push --mirror`, or `refs/*` wildcards.

Include the approved:

- branches;
- tags;
- Git LFS objects, only when LFS was separately approved by the human.

Exclude:

- converter scratch refs;
- audit refs;
- temporary migration refs;
- local backup refs.

## Rules

- Transport uses the gh credential integration or existing SSH config; no
  credentials ever appear in the remote URL, scripts, logs, or reports.
- **No force push** during initial publication, ever. A rejected push is a
  stop-and-diagnose, not a `--force`.
- On rerun after interruption, re-verify remote privacy state first, then
  push the same explicit set — pushing identical refs is idempotent; never
  create a second repository.

## Steps

1. `git -C "$WS/converted.git" remote add origin <verified-url>` (or reuse
   the recorded remote on resume).
2. Push the explicit ref list, capturing full output to `WS/logs/push.log`.
3. Confirm every pushed ref is reported up to date; any rejected or skipped
   ref is a failure, never silently dropped.

## State

All approved refs accepted → transition to `PUSHED`, recording the exact
ref list fingerprint. Any rejection → `FAILED` with the push log.

## Handoff

`clone-and-verify` proves the published result next.
