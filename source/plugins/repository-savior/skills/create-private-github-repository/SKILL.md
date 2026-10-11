---
name: create-private-github-repository
description: Use when an authorized legacy repository migration reaches the create private github repository stage. Requires an explicit migration root.
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Create Private GitHub Repository

Creates the empty GitHub repository under the configured owner. Visibility
is not a choice: the gateway hardcodes `--private`, and this skill must
never run `gh repo create` or `gh repo edit` directly — the gateway is the
only permitted path (privacy Gates 2 and 3).

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`AUDIT_PASSED`; owner and feature flags from config `github.*`; repository
name from `naming.*` policy applied to the source name. `GATEWAY` =
`../../gateways/github-private-only` relative to this SKILL.md.

## Steps

1. Confirm `gh auth status` succeeds (the gateway also checks). Never run
   any command that reveals the token.
2. Resolve the repository name per `naming` policy; on collision the policy
   is `stop` — never overwrite or suffix silently.
3. Create through the gateway:

   ```bash
   uv run "$GATEWAY/create_private_repo.py" "<owner>" "<name>" \
     --description "<default_description_prefix>: <name>"
   ```

   Issues/wiki stay disabled unless config enables them
   (`--allow-issues` / `--allow-wiki`). Projects cannot be disabled at
   creation; record that as a follow-up if config demands it.
4. Record the returned repository identity (owner, name, verified_private)
   into `WS/state.json`'s `github` block.

Exit codes: `3` = collision → `BLOCKED` pending a human naming decision;
`4` = created but not verifiably private → **do not push, `BLOCKED`,
high-severity escalation**; any other nonzero → `FAILED`.

Never import source through a GitHub web workflow — it would bypass the
local gates and verification.

## State

Gateway exit 0 → transition to `REMOTE_CREATED`.

## Handoff

`verify-remote-privacy` performs the independent check next — the gateway's
own verification does not replace it.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
