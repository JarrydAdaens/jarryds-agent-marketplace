---
name: clone-and-verify
description: >-
  Use when proving a pushed migration by cloning the new GitHub repository
  into a fresh, empty verification directory and verifying it end to end:
  clone with normal auth, default branch checkout, all expected branches
  and tags present, git fsck, commit IDs and tip tree hashes matching the
  approved local conversion, LFS objects resolving, and configured smoke
  tests. The clean clone — not the workspace — is the proof the published
  repository is usable. Writes only into the user-specified migration root
  and refuses to run without one. Triggers: "verify the published repo",
  "fresh clone check".
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
