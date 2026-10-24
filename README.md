# jarryds-agent-marketplace

A personal marketplace of skills, agents, and plugins for agentic IDEs (Claude Code, Cursor, and Codex), collected from across my projects.

This is deliberately **personal and opinionated**. Plugins may target a technology stack, but Agentic Rails framework policy stays in `agentic_rails_tooling` or `agentic_rails_marketplace`.

## Layout

- `.claude-plugin/marketplace.json` — the Claude Code plugin catalog (`plugins/claude/*` only).
- `.cursor-plugin/marketplace.json` — the Cursor plugin catalog (`plugins/cursor/*` only).
- `.agents/plugins/marketplace.json` — the Codex plugin catalog (`plugins/codex/*` only).
- `plugins/` — three host roots (`claude/`, `codex/`, `cursor/`). Each plugin folder carries exactly one host manifest matching its root. A plugin supported on more than one host is duplicated per root and may drift.
- `source/skills/` — plain skills not yet packaged as plugins (deployed by file copy for now).
- `context/` — material about this repo itself (notes, plans), never deployed.

## Registering and installing

### Claude Code

```shell
/plugin marketplace add <git-url-or-local-path-to-this-repo>
/plugin install open-source-auditor@jarryds-agents
/plugin install repository-savior@jarryds-agents
```

A local clone path is fine while experimenting.

### Codex

```shell
/plugin marketplace add <git-url-or-local-path-to-this-repo>
/plugin install open-source-auditor@jarryds-agents
/plugin install repository-savior@jarryds-agents
```

Same local-clone recommendation as Claude Code. After a `git pull`, refresh with `/plugin marketplace update jarryds-agents`. Codex requires `name`, `version`, and `description` in each `.codex-plugin/plugin.json` — bump `version` when you want Codex to treat a push as a distinct plugin update.

### Cursor

Register the Git marketplace from Cursor CLI:

```shell
agent plugin marketplace add <git-url-to-this-repo>
```

Then install the desired plugin from **Customize → Marketplace**. For local development, `agent --plugin-dir <path-to-plugin>` loads one plugin directly; the `%USERPROFILE%\.cursor\plugins\local\` workflow below remains useful for Cursor desktop.

**Local / personal (recommended while private):**

1. Copy each plugin folder into `%USERPROFILE%\.cursor\plugins\local\<plugin-name>\` (on macOS/Linux: `~/.cursor/plugins/local/<plugin-name>/`). The folder you place there must contain `.cursor-plugin/plugin.json` at its root — i.e. copy `plugins/cursor/open-source-auditor` to `...\local\open-source-auditor`, not the whole marketplace repo.
2. Prefer a real copy over a symlink to a path outside `plugins/local` — current Cursor builds often reject external symlink targets.
3. Run **Developer: Reload Window**.
4. Confirm skills and agents under **Customize**.

**Team Marketplace (Teams/Enterprise):** import this GitHub repo from **Dashboard → Plugins**, then install from Customize. Enable Auto Refresh if you want push updates.

**Public Cursor Marketplace:** submit later via [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish) if you want curated listing; not required for personal use.

## Installable plugins

| Plugin | Purpose |
| --- | --- |
| `code-audit` (Claude Code, Codex) | Standalone changeset review with specialist correctness/test/reuse coverage, pinned Git scope, deterministic evidence/verdicts, private reports and process hypothesis packages. See [Claude Code](plugins/claude/code-audit/README.md) or [Codex](plugins/codex/code-audit/README.md). |
| `open-source-auditor` | Pre-publication open-source audit in one install: auditor persona + six deterministic sensors (secrets, tone, quality, dependency, provenance, hygiene), a triaging PASS/BLOCK guardrail, Apache 2.0 licensing, and post-abort cleanup. Writes only to an explicit, user-specified report folder. See `plugins/cursor/open-source-auditor/README.md`. |
| `repository-savior` | Migrates archived Mercurial/SVN repos to native Git and publishes them to GitHub as **private** only: orchestrating persona + fifteen pipeline skills, private-only gateways, resumable state machine. Requires an explicit migration-root. See `plugins/cursor/repository-savior/README.md`. |
| `game-golden-screenshot-verifier` | Engine-independent runtime smoke verifier for games using deterministic input, screenshots, and versioned goldens. |
| `wpf-visual-quality-gate` | Evaluator-run visual quality gate for WPF desktop UI changes using real input and screenshot evidence. |

## Skills awaiting packaging (`source/skills/`)

| Family | Artifacts | Purpose |
| --- | --- | --- |
| General | `commit-log`, `grade` | Structured VCS commit messages; decisive letter-grading of artifacts |
| Oracle | `oracle-generate-stats`, `oracle-token-appraise`, `oracle-token-stats` | Token counting, file-cost appraisal, and session usage accounting |
| WPF | `wpf-tree-sensor`, `wpf-starter-update` | UI Automation tree inspection; WPF-Starter reconciliation |

These are synced into IDE config locations by file copy today; the plan is to package each family as an installable plugin over time.

## Reproducible personal packages

Author the Auditor, Savior, game screenshot, and WPF gate payloads in
`source/plugins/`, then run `python scripts/generate-packages.py`. Host manifests
remain native and generated packages include all runtime helpers. Run
`python scripts/check.py` for parity, catalog, safety, and component checks.
See `source/plugins/README.md` for adapter behavior and live activation scenarios.
Package receipts label installed host activation as untested until rollout evidence
exists.
