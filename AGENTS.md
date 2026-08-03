# AGENTS.md

This file provides repository guidance for agentic IDEs and coding agents working in this repository. It is vendor-neutral: Cursor, Claude Code, Codex, Windsurf, and other agents should treat it as the project-level instruction entry point. `CLAUDE.md` here simply imports this file.

## What this repository is

`jarryds-agent-marketplace` is Jarryd's **personal marketplace** of skills, agents, and plugins for agentic coding tools. Everything here is general-purpose: each artifact works on any repository, with no framework assumptions. Artifacts specific to the Agentic Rails framework live in `agentic_rails_tooling`; lifecycle artifacts for that framework live in `agentic_rails_marketplace`. This repo is neither — it is the home for personal capability that outgrew, or never belonged to, a framework.

## Layout

- `.claude-plugin/marketplace.json` — the Claude Code plugin catalog. Every installable plugin must be listed here.
- `.cursor-plugin/marketplace.json` — the Cursor plugin catalog. Same plugins, Cursor's manifest layout.
- `plugins/` — one folder per installable plugin. Payload lives in the default component directories (`skills/`, `agents/`), discovered natively on install. Thin per-tool manifests sit beside the payload: `.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`.
- `source/skills/` — plain skills not yet packaged as plugins (deployed by file copy for now). The goal is to migrate families here into `plugins/` over time.
- `context/` — material about this repo itself (notes, plans). Never deployed or installed.

## Hard rules

- **Never edit installed copies.** Installed plugins live in a per-tool cache (Claude) or Cursor's plugin install / `~/.cursor/plugins/local/` tree. Edit here, commit, and let the marketplace update mechanism (or a fresh local copy) deliver the change.
- **A plugin cannot reference files outside its own folder.** Installs copy the plugin directory into a cache, so `../` paths out of the plugin break. Shared helpers live inside the plugin (e.g. `open-source-auditor/audit-lib/`).
- **No personal data in the repo.** This repo is public. Watchlists, employer/colleague names, credentials, and machine-specific paths belong in local config the user fills in from shipped sanitized templates — never in committed files.
- **Plugins that write per-project output must take the output location as an explicit argument** and refuse to run without it — never guess or default a write location into someone's repository.
- **Do not set `version` in `.claude-plugin/plugin.json` or `.cursor-plugin/plugin.json`.** Plugins are versioned by commit SHA; every push is an update.
- **Keep both catalogs in sync.** Adding or removing a plugin means updating `.claude-plugin/marketplace.json` and `.cursor-plugin/marketplace.json`, plus both per-plugin manifests.
- **Plugin `name` is a stable identifier** — renames need a migration note, not a silent change.

## Conventions

- File and folder names are kebab-case except tool-mandated names (`SKILL.md`, `AGENT.md`, `README.md`, `AGENTS.md`, `CLAUDE.md`) and language-idiomatic code files. American English throughout.
- Every plugin folder has a `README.md` stating what it does, how to invoke it, what the consuming machine must provide, and known limitations.
- Skill frontmatter carries `name` (matching the folder), a "Use when…" `description`, an `argument-hint` when the skill takes arguments, and `metadata.version`.
- Validate before committing plugin changes: `claude plugin validate .` from the repo root (Claude layout). For Cursor, confirm each plugin has `.cursor-plugin/plugin.json` and that marketplace `source` paths resolve, then smoke-test via `~/.cursor/plugins/local/<plugin>/` + Reload Window.
- Commit messages follow the structured `commit-log` format (heading ≤72 chars, `~ Problem:` / body lines / `~ Resolution:`).
