---
name: audit-hygiene-sensor
description: >-
  First-impression hygiene scanner for the open-source pre-publication audit. Use
  when auditing a target repo for dead links, typos, README-vs-reality mismatches,
  unexplained branches, and repo-completeness (LICENSE / README / NOTICE).
  Read-only on the target repo: writes only into the user-specified report
  folder, and refuses to run without one. Knows that documented experiment
  branches are ASSETS to point at, not clutter to delete. Triggers: "audit
  hygiene", "check for dead links", "does the README match the repo", "audit
  the branches before publish".
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.2"
  owner: Jarryd Adaens
  stage: audit-mode-sensor
---

# Audit — Hygiene Sensor

Everything a reviewer notices in the first five minutes.

## Required arguments & paths

Invocation: `<target-repo> <report-folder> [run-timestamp]`

- `REPO` — absolute path of the ONE repo being audited.
- `report-folder` — absolute path where `open-source-audit-report-<repo-name>/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- `run-timestamp` — the shared `YYYY-MM-DD_HHMM` stamp when part of a
  persona-led run; mint a fresh one standalone. Never overwrite an earlier run.

Derived: `RUN = <report-folder>/open-source-audit-report-<repo-name>/<run-timestamp>`,
`OUT = RUN/audit-hygiene-sensor`, `RAW = OUT/raw`. Config lives in
`<report-folder>/open-source-audit-report-<repo-name>/audit-config/`. `LIB` = the
`audit-lib/` folder at this plugin's root (`../../audit-lib` relative to this
SKILL.md).

## Contract

- **Read-only on the target repo.** All output goes only inside `OUT`.

## Checks

1. **Dead links** — `lychee` over all markdown.
   Default posture is `--offline` (local-path links only). Drop `--offline` only
   when web-link checking is explicitly wanted, and then cap concurrency —
   every web link is a live HTTP request to someone's server:
   ```bash
   lychee --offline --format json "$REPO/**/*.md" > "$RAW/lychee.json"
   # web mode (explicit request only): lychee --max-concurrency 8 --format json ...
   ```
2. **Typos** — `codespell` (via uvx), honoring the per-repo ignore list plus
   `hygiene.codespellIgnoreWords` in `audit-config/global.json` (project
   coinages false-positive):
   ```bash
   uvx codespell --ignore-words-list "<comma-joined codespellIgnoreWords>" "$REPO" > "$RAW/codespell.txt"
   ```
   Convert to `raw/codespell.json`.
3. **README-vs-reality** — deterministic first: every path/file the README
   references exists; every claimed command/script exists. Write
   `raw/readme-check.json`. The AI reasoning pass over whether claims *match
   repo state* belongs to the guardrail.
4. **Branch inventory** — every branch on the public remote with last-commit
   date, ahead/behind main, and head message:
   ```bash
   git -C "$REPO" for-each-ref --format='%(refname:short)|%(committerdate:iso)|%(subject)' refs/remotes/origin > "$RAW/branch-inventory.txt"
   ```
   **Policy:** branches listed in the repo's `documentedExperimentBranches`
   config (e.g. a deliberate model-ablation or A/B experiment kept as evidence)
   are documented experiments and an asset. The finding for them is **"missing
   README pointer,"** never "stale/delete." Turn "what are these?" into "look
   what I did."
5. **Repo-completeness** — presence of LICENSE, README, and (post-licensing)
   NOTICE. Half-finished-with-no-explanation detection is left to the guardrail's
   reasoning over milestone/status docs.

## Output

`raw/lychee.json`, `raw/codespell.json`, `raw/readme-check.json`,
`raw/branch-inventory.json`, then normalize
(`uv run "$LIB/normalize.py" "$REPO" "$RAW" "$OUT/normalized"`).
