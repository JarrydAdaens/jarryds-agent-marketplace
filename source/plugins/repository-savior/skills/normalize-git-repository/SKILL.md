---
name: normalize-git-repository
description: Use when an authorized legacy repository migration reaches the normalize git repository stage. Requires an explicit migration root.
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Normalize Git Repository

Applies only **approved** normalization to `WS/converted.git/` after
conversion. Normalization is bookkeeping, not beautification.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`CONVERTED`; conversion map in `WS/manifests/conversion-map.json`.

## Permitted operations (and nothing else)

- Map verified author identities (only where the converter could not apply
  the author map directly, and only per the approved map).
- Create native Git tags where required by the conversion map.
- Select or rename the default branch according to the explicit
  `default_branch_policy` (`preserve-or-explicitly-map`) — never an
  unstated rename.
- Remove converter-only temporary refs **after** they have been recorded in
  the ref map.
- Add migration metadata (e.g. a note or a `MIGRATION.md` on a metadata
  ref) **outside historical commits** — history is never amended for
  metadata.

## Prohibited

- Rewriting history to look cleaner, squash noise, or fix old messages.
- Discarding any branch, tag, or revision without it being recorded and
  approved.
- Touching anything outside `WS/converted.git/`.

## Outputs

`WS/manifests/ref-map.json` — every ref before and after normalization,
including every removed converter ref and every rewritten ref name, plus
the resolved default branch.

## State

Stays `CONVERTED` (normalization is part of conversion); append a
transition recording the operations applied. Anything outside the permitted
list that seems needed → `REQUIRES_HUMAN_DECISION`.

## Handoff

`assess-github-publishability` inspects the normalized repository next.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
