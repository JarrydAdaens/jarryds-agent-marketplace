---
name: snapshot-source
description: Use when an authorized legacy repository migration reaches the snapshot source stage. Requires an explicit migration root.
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Snapshot Source

Creates the working copy conversion will actually read, and records the
fingerprint that proves the original archive was never modified. All
conversion work happens in the workspace — the original is treated as
read-only from discovery to acceptance.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`INSPECTED`. `GATEWAY` = `../../gateways/source-read-only` relative to this
SKILL.md.

## Steps

1. **Fingerprint the original** before anything else:

   ```bash
   uv run "$GATEWAY/fingerprint_source.py" record "<source-path>" "$WS/manifests/source-fingerprint.json"
   ```

   The manifest includes per-file SHA-256 hashes and an aggregate
   fingerprint sufficient to detect accidental modification.

2. **Copy** the source into `WS/source-copy/` (plain filesystem copy — no
   VCS operations against the original).

3. **Verify the copy** matches the recorded fingerprint:

   ```bash
   uv run "$GATEWAY/fingerprint_source.py" verify "$WS/source-copy" "$WS/manifests/source-fingerprint.json"
   ```

4. Where the platform supports it, mark `WS/source-copy/` read-only as a
   belt-and-braces guard for the converters.

After migration acceptance, the same `verify` command against the
**original** source path proves the archive is intact — a completion
criterion.

## State

On success append a transition → `SOURCE_SNAPSHOTTED`, recording the
aggregate fingerprint as the input fingerprint. A verify failure at any
point → `FAILED`, stop, escalate.

## Handoff

The matching conversion skill (`convert-mercurial-to-git` or
`convert-svn-to-git`) operates on `WS/source-copy/` only.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
