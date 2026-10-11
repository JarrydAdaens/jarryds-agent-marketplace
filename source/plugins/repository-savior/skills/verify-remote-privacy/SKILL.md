---
name: verify-remote-privacy
description: Use when an authorized legacy repository migration reaches the verify remote privacy stage. Requires an explicit migration root.
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Verify Remote Privacy

Privacy Gate 4: an independent query of GitHub after creation, before any
Git data leaves the machine. Independent means it re-queries GitHub itself
— it does not trust the creation step's output.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`REMOTE_CREATED`; expected owner/name from `WS/state.json`'s `github`
block. `GATEWAY` = `../../gateways/github-private-only` relative to this
SKILL.md.

## The check

```bash
uv run "$GATEWAY/verify_remote_privacy.py" "<owner>" "<name>"
```

Verifies all of:

```text
isPrivate  == true
visibility == PRIVATE
owner      == configured target owner
name       == approved repository name
```

## On failure (exit nonzero)

- **Stop.** Do not add or use the remote. Do not push.
- Transition to `BLOCKED`.
- Produce a high-severity report naming exactly which check failed.
- **Never automatically "fix" a non-private repository** — flipping
  visibility after exposure does not undo exposure. The human decides what
  happens to the bad remote.

## On success

Record the verification output in the transition and move to
`REMOTE_PRIVACY_VERIFIED`. Only from this state may
`push-git-repository` run.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
