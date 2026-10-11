---
name: convert-mercurial-to-git
description: Use when an authorized legacy repository migration reaches the convert mercurial to git stage. Requires an explicit migration root.
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Convert Mercurial to Git

Converts `WS/source-copy/` (a Mercurial repository) into a native local Git
repository at `WS/converted.git/`. The import stream is only part of the
process — the final output is a normal native Git repository.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`SOURCE_SNAPSHOTTED`; source inventory in
`WS/manifests/source-inventory.json`; author map from config
`history.author_map`.

## Contract

- Operates on `WS/source-copy/` only — never the original archive.
- **Explicit author mapping.** Every identity in the source inventory must
  resolve through the author map. `unknown_author_policy: stop` — an
  unmapped or ambiguous identity halts conversion
  (`REQUIRES_HUMAN_DECISION`); never infer when multiple identities are
  plausible.
- **Topology before conversion.** Mercurial's branch model does not always
  map cleanly to Git. From the inventory, decide explicitly how each named
  branch, bookmark, closed branch, and extra head maps; if any mapping is
  ambiguous, stop and ask. Closed branches are included when
  `include_closed_mercurial_branches` is true.
- Never silently discard branches, tags, revisions, or conversion errors —
  every warning from the converter is captured in `WS/logs/`.

## Tooling

- `hg-fast-export`, **pinned to a tested commit** (record the exact commit
  in the migration report; test it against the Mercurial fixture before
  first use on a real archive).
- Conversion streams into `git fast-import` against an empty
  `WS/converted.git/` created with `git init`.
- Conceptual invocation (from the empty destination):

  ```bash
  hg-fast-export.sh -r "$WS/source-copy" -A "<migration-root>/config/authors.map"
  git repack -d
  ```

## Outputs

`WS/converted.git/` plus `WS/manifests/conversion-map.json` recording the
branch/bookmark/tag/head mapping decisions actually applied, and full
converter logs under `WS/logs/`.

## State

On success append a transition → `CONVERTED`, recording the converter tool
and pinned version. Converter errors → `FAILED`; ambiguity →
`REQUIRES_HUMAN_DECISION`.

## Handoff

`normalize-git-repository` applies approved normalization next.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
