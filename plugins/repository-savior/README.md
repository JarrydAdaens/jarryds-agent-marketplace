# Repository Savior

Safely migrates archived Mercurial and SVN repositories into native Git
repositories, publishes approved repositories to GitHub as **private**
repositories, and proves the published result by verifying a fresh clone.

Built for batch-recovering legacy archives (roughly twenty repositories)
without manually repeating conversion, GitHub repository creation, pushing,
cloning, and verification for each one.

## Design priorities

1. **No repository may ever become public.** The only publication policy is
   `PRIVATE_ONLY`. There is no visibility field in the config, the command
   gateway always supplies `--private` and rejects public/visibility flags,
   the remote is independently verified private before any push, and tests
   prove all of it. Changing this requires changing the implementation and
   its tests.
2. **Original archives are never touched.** All work happens in a generated
   workspace; the source is fingerprinted before conversion and re-verified
   after.
3. **Every migration is repeatable, resumable, and auditable** via a durable
   per-repository `state.json` state machine.
4. **Conversion preserves as much history and metadata as the source format
   permits** — and discloses what it cannot represent.
5. **A repository is not migrated until a fresh GitHub clone passes
   verification.**
6. **Secrets and dangerous historical content are audited before
   publication.** Private is not remediation.

## Invocation

The persona drives everything:

```text
@repository-savior-persona <migration-root>
```

`<migration-root>` is the absolute path of your migration working area
(intake, workspace, verification, reports, config). It is **required** — the
persona and every skill refuse to run without it and never write anywhere
else. Persistent configuration lives at
`<migration-root>/config/repository-savior.yaml`; bootstrap it from this
plugin's `config/repository-savior.example.yaml` and fill in your paths and
GitHub owner locally. Local config is personal data — never commit it here.

Individual skills can also be invoked standalone with the same
`<migration-root>` argument (plus a repository id where relevant).

## Pipeline

```text
discover → inspect → snapshot → convert (hg or svn) → normalize
  → assess publishability → verify local → audit (must PASS)
  → create private GitHub repo → verify remote privacy → push
  → fresh clone → verify remote → final report
```

One repository at a time, always. Each repository moves through the state
machine in `schemas/state.schema.json`; a rerun resumes from the last
verified state and never blindly repeats remote or destructive operations.

## What the consuming machine must provide

- `git` (with `git svn` for SVN sources) and `hg` plus a pinned
  `hg-fast-export` checkout for Mercurial sources.
- GitHub CLI (`gh`), already authenticated by the human
  (`gh auth login`). The plugin only ever runs `gh auth status` and never
  reads, prints, or stores tokens.
- `uv` — all Python scripts run through `uv run`, never bare `python`.
- The `open-source-auditor` plugin (same marketplace) for the mandatory
  pre-publication audit, or another auditor producing a report conforming to
  `schemas/audit-result.schema.json`.

## Layout

- `agents/repository-savior-persona.md` — the orchestrator.
- `skills/` — fifteen narrow skills, one pipeline stage each.
- `gateways/github-private-only/` — the **only** permitted path to
  `gh repo create` (always `--private`, rejects visibility flags, verifies
  the remote after creation) plus the independent privacy verifier.
- `gateways/source-read-only/` — source fingerprint recorder/verifier that
  proves the archive was never modified.
- `config/` — sanitized templates for the persistent config and author map.
- `schemas/` — JSON Schemas for config, state, audit result, and migration
  report.
- `templates/migration-report.md` — the human-readable report template.
- `tests/` — privacy-gate and schema tests. Run from this folder:
  `uv run --with pytest --with pyyaml --with jsonschema pytest tests/`.

## Known limitations

- A plain SVN working copy (no server data, no reachable remote) only
  yields the checked-out snapshot, not full history; the skills report this
  rather than pretending otherwise.
- Repositories needing Git LFS or history rewriting stop at
  `REQUIRES_HUMAN_DECISION` — the plugin never silently alters historical
  storage.
- GitHub organization access to private repositories depends on base
  permissions and explicit grants; `inspect-organization-access` reports
  the effective policy but never modifies it.
- The plugin never deletes or cleans up the original archive — that remains
  a separate human decision after acceptance.
