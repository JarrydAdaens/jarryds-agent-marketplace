---
name: verify-local-conversion
description: >-
  Use when running structural and content verification of a converted Git
  repository against its source inventory: git fsck, commit-count
  reconciliation, branch/tag/author/timestamp reconciliation, file-tree
  manifest comparison of heads and tags, no stray converter or VCS metadata
  files, default branch resolution, and a clean checkout. A repository is
  not publishable until this passes. Writes only into the user-specified
  migration root and refuses to run without one. Triggers: "verify the
  conversion", "reconcile the converted repo against the source".
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Verify Local Conversion

Reconciles `WS/converted.git/` against the source inventory recorded by
`inspect-source-history`. This is the local integrity gate — publication
gates all depend on it.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`CONVERTED`; baseline in `WS/manifests/source-inventory.json`, mappings in
`WS/manifests/conversion-map.json` and `ref-map.json`.

## Minimum checks

- `git fsck --full` passes;
- converted commit count vs. source revision inventory — a mismatch is not
  automatically a failure **if** the converter intentionally represents
  source metadata differently, but the difference must be explained and
  accepted by a specific recorded rule, never waved through;
- branch reconciliation (every inventoried branch accounted for through the
  mapping, including closed Mercurial branches per policy);
- tag reconciliation;
- author reconciliation (every source identity maps to exactly the approved
  Git identity);
- timestamp range reconciliation (earliest/latest match the inventory);
- **file-tree manifests**: for each source head and tag, compare its file
  manifest against the corresponding Git ref's tree;
- no unexpected converter files committed;
- no source-control metadata (`.hg*`, `.svn`, `.hgignore`-only artifacts)
  accidentally committed;
- default branch resolves to the intended tip;
- the working tree checks out without errors.

## Outputs

`WS/manifests/local-verification.json`: per-check result, every deviation
with its accepting rule or its failure, and the overall verdict.

## State

All checks pass (or deviations explicitly accepted by rule) → transition to
`LOCAL_VERIFIED`. Any unexplained deviation → `FAILED` with the evidence;
never claim success while verification is incomplete.

## Handoff

`request-repository-audit` runs against the verified conversion next.
