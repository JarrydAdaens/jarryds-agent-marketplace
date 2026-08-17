---
name: inspect-source-history
description: >-
  Use when building the pre-conversion source inventory of one discovered
  legacy repository (Mercurial or SVN): revisions, authors, branches,
  bookmarks, tags, heads, timestamps, largest files, binary-heavy paths,
  nested repositories, encoding problems, and corruption indicators. The
  inventory becomes the baseline every later verification reconciles
  against. Read-only on the source; writes only into the user-specified
  migration root and refuses to run without one. Triggers: "inspect source
  history", "inventory the repo before conversion".
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Inspect Source History

Builds the source inventory that later verification reconciles against.
Conversion must never start from an uninspected source, and the converter
choice (and its branch-mapping decisions) come from this inventory.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state in `WS/state.json`
(must be `DISCOVERED` or later); output in `WS/manifests/`.

## Contract

- **Read-only on the source.** Use only query commands (`hg log`,
  `hg branches`, `hg bookmarks`, `hg tags`, `hg heads`, `svn log`,
  `svnadmin lsrevs`-style queries against repository storage, `svn info`).
- Record every identity found — the author map is validated against this
  list, and `unknown_author_policy: stop` means a missing identity halts
  conversion later.

## Inventory contents

Write `WS/manifests/source-inventory.json` covering:

- revision count;
- authors and email identities (distinct, exactly as recorded);
- branch names (including Mercurial closed branches);
- bookmarks where relevant;
- tags;
- heads;
- earliest and latest timestamps;
- repository root layout (for SVN: the actual trunk/branches/tags reality,
  never the assumed standard layout);
- file count;
- largest files across history;
- binary-heavy paths;
- subrepositories, SVN externals, or nested repositories;
- unusual encodings or invalid filenames;
- source corruption indicators.

## State

On success append a transition to `WS/state.json` → `INSPECTED`. Corruption
indicators or unreadable history → `REQUIRES_HUMAN_DECISION` with the
evidence recorded.

## Handoff

`snapshot-source` fingerprints the source next; the conversion skills read
this inventory to choose their mapping strategy and to stop on ambiguity.
