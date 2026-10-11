---
name: discover-legacy-repositories
description: Use when an authorized legacy repository migration reaches the discover legacy repositories stage. Requires an explicit migration root.
argument-hint: <migration-root>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Discover Legacy Repositories

Scans the configured intake directory and classifies every candidate so the
right converter (or a human decision) is selected later. Runs once per
batch, before any per-repository work.

## Required arguments & paths

Invocation: `<migration-root>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Config lives at
`<migration-root>/config/repository-savior.yaml`; the intake directory is
`paths.intake` from that config.

## Contract

- **Read-only on every candidate.** Classification inspects; it never
  modifies, converts, or cleans anything.
- Never silently drop a candidate — unknown or damaged entries are reported
  as such, not skipped.

## Classification rules

Distinguish, in this order of evidence:

1. **Mercurial repository** — contains `.hg/`.
2. **SVN repository storage** — contains `conf/`, `db/`, and repository
   format metadata (`format` / `db/fs-type`). Full history is recoverable.
3. **SVN working copy** — contains `.svn/`. **Not** a complete history
   archive: if the repository server data or a reachable SVN remote is
   absent, report that only the checked-out snapshot may be recoverable
   and classify confidence accordingly.
4. **Existing Git repository** — contains `.git/`. No conversion needed;
   still flows through the audit and publication gates.
5. **Plain folder** — source files without recoverable history.
6. **Unknown or damaged** — anything else, with the evidence noted.

## Outputs

Write `<migration-root>/reports/discovery.json`: an array of entries

```json
{
  "name": "ExampleProject",
  "source_type": "mercurial",
  "source_path": "...",
  "confidence": "high",
  "warnings": []
}
```

For each viable candidate, create
`<migration-root>/workspace/<repository-id>/state.json` (per
`../../schemas/state.schema.json`, relative to this SKILL.md) in state
`DISCOVERED`, unless a state file already exists — existing state is never
reset; resumption picks up from it.

## Handoff

Per repository, the persona proceeds to `inspect-source-history`. Ambiguous
classifications go to `REQUIRES_HUMAN_DECISION`, not to a guessed converter.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
