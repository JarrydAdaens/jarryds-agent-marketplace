# jarryds-agent-marketplace

A personal marketplace of skills, agents, and plugins for agentic IDEs (Claude Code and Codex), collected from across my projects.

Everything here is **general-purpose**: each artifact works on any repository, with no assumptions about project structure. That is the admission rule — skills that require a specific framework live with that framework. In particular, skills specific to the Agentic Rails system stay in `agentic_rails_tooling`; this repo holds what was deliberately extracted from it because it wasn't Rails-specific.

## Layout

- `.claude-plugin/marketplace.json` — the Claude Code plugin catalog.
- `plugins/` — installable plugins, one folder each; a single install brings a plugin's whole bundle (skills, agents, shared scripts, config templates).
- `source/skills/` — plain skills not yet packaged as plugins (deployed by file copy for now).
- `context/` — material about this repo itself (notes, plans), never deployed.

## Installable plugins

| Plugin | Purpose |
| --- | --- |
| `open-source-auditor` | Pre-publication open-source audit in one install: auditor persona + six deterministic sensors (secrets, tone, quality, dependency, provenance, hygiene), a triaging PASS/BLOCK guardrail, Apache 2.0 licensing, and post-abort cleanup. Writes only to an explicit, user-specified report folder. See `plugins/open-source-auditor/README.md`. |

## Skills awaiting packaging (`source/skills/`)

| Family | Artifacts | Purpose |
| --- | --- | --- |
| General | `commit-log`, `grade` | Structured VCS commit messages; decisive letter-grading of artifacts |
| Grugg | `grugg`, `grugg-compress` | Token-efficient communication mode and memory-file compression |
| Oracle | `oracle-generate-stats`, `oracle-token-appraise`, `oracle-token-stats` | Token counting, file-cost appraisal, and session usage accounting |
| WPF | `wpf-tree-sensor`, `wpf-starter-update` | UI Automation tree inspection; WPF-Starter reconciliation |

These are synced into IDE config locations by file copy today; the plan is to package each family as an installable plugin over time.
