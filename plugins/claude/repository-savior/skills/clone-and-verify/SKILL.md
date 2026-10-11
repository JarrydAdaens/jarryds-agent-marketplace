---
name: clone-and-verify
description: Use when an authorized legacy repository migration reaches the clone and verify stage. Requires an explicit migration root.
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Clone and Verify

Clones the just-pushed repository from GitHub into a clean directory and
reconciles it against the approved local conversion. Verification against
the migration workspace proves nothing — only the fresh clone does.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be `PUSHED`;
clone target `<migration-root>/verification/<repository-name>/` — must be
empty or absent before cloning.

## Checks

- the clone succeeds using normal user authentication (no embedded
  credentials);
- the default branch checks out;
- all expected remote branches and tags exist (reconcile against the
  approved push set);
- `git fsck --full` passes in the clone;
- commit IDs match the approved local Git repository ref for ref;
- branch and tag tip **tree hashes** match;
- Git LFS objects resolve, when LFS is in use;
- repository-specific build or smoke tests pass, when configured for this
  repository.

## State

Clone succeeded → transition to `RECLONED`. All checks reconciled →
transition to `REMOTE_VERIFIED`, recording the clone fingerprint. Any
mismatch → `FAILED` with the diff of expected vs. found refs; never claim
success on partial verification.

## Handoff

`write-migration-report` closes the migration out.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
