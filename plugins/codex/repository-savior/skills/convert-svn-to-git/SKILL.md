---
name: convert-svn-to-git
description: Use when an authorized legacy repository migration reaches the convert svn to git stage. Requires an explicit migration root.
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Convert SVN to Git

Converts an SVN source into a native local Git repository at
`WS/converted.git/`. SVN branches and tags are directory conventions, not
native objects — the layout is verified from the inventory, never assumed.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`SOURCE_SNAPSHOTTED`; inventory in `WS/manifests/source-inventory.json`;
author map from config `history.author_map`.

## Contract

- Operates on `WS/source-copy/` (repository storage served locally via
  `file://` or `svnserve`) or an approved reachable SVN URL — never the
  original archive directly.
- **Verify the actual layout** from the inventory before configuring
  trunk/branches/tags. Non-standard layouts get explicit
  `--trunk/--branches/--tags` arguments matching reality; ambiguous layouts
  stop (`REQUIRES_HUMAN_DECISION`).
- **Explicit author mapping** via `--authors-file`; `git svn` halts on an
  unmapped author, which is the desired behavior — resolve with the human,
  never guess.
- A plain SVN **working copy** without server data or reachable remote can
  only yield the checked-out snapshot; report that honestly instead of
  fabricating history.
- Decide and record the **empty-directory preservation policy** (SVN
  tracks them; Git cannot) as an accepted deviation.
- **Disclose** in the conversion map any history semantics that cannot be
  represented exactly in Git (e.g. mixed-revision copies, directory-level
  operations).

## Tooling

Conceptual invocation:

```bash
git svn clone "<svn-url>" --trunk=<t> --branches=<b> --tags=<g> \
  --authors-file="<migration-root>/config/authors.map" "$WS/converted.git"
```

Post-process imported `refs/remotes/origin/tags/*` refs into native,
immutable Git tags where appropriate, and convert branch remote refs into
local branches per `include_all_svn_branches` / `include_all_tags`.

## Outputs

`WS/converted.git/`, `WS/manifests/conversion-map.json` (layout used,
branch/tag ref mapping, disclosed inexact semantics, empty-directory
policy), converter logs under `WS/logs/`.

## State

On success append a transition → `CONVERTED` recording `git svn` and the
git version. Errors → `FAILED`; ambiguity → `REQUIRES_HUMAN_DECISION`.

## Handoff

`normalize-git-repository` applies approved normalization next.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
