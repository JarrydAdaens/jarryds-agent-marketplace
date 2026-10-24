# AGENTS.md

This file provides repository guidance for agentic IDEs and coding agents working in this repository. It is vendor-neutral: Cursor, Claude Code, Codex, Windsurf, and other agents should treat it as the project-level instruction entry point. `CLAUDE.md` here simply imports this file.

## What this repository is

`jarryds-agent-marketplace` is Jarryd's **personal, opinionated marketplace** of skills, agents, and plugins for agentic coding tools. Artifacts may be general-purpose or deliberately technology-specific, but they must not impose Agentic Rails framework policy. Framework artifacts live in `agentic_rails_tooling`; framework-wide lifecycle guardrails live in `agentic_rails_marketplace`.

## Layout

- `.claude-plugin/marketplace.json` — the Claude Code plugin catalog. Lists only `plugins/claude/*`.
- `.cursor-plugin/marketplace.json` — the Cursor plugin catalog. Lists only `plugins/cursor/*`.
- `.agents/plugins/marketplace.json` — the Codex plugin catalog. Lists only `plugins/codex/*`.
- `plugins/` — three host roots: `plugins/claude/`, `plugins/codex/`, and `plugins/cursor/`. Each holds only the plugins that host supports. A plugin available on more than one host is a separate copy under each root, not a shared payload. Payload lives in the default component directories (`skills/`, `agents/`), discovered natively on install. Each plugin folder carries exactly one host manifest: `.claude-plugin/plugin.json` under `plugins/claude/`, `.cursor-plugin/plugin.json` under `plugins/cursor/`, `.codex-plugin/plugin.json` under `plugins/codex/`. A plugin folder with more than one `.*-plugin/` directory is a bug.
- `source/skills/` — plain skills not yet packaged as plugins (deployed by file copy for now). The goal is to migrate families here into `plugins/` over time.
- `source/plugins/` — authoring payloads for Auditor, Savior, game screenshot, and WPF gate. Run `python scripts/generate-packages.py` after edits; host payloads are generated and remain self-contained. Host manifests stay under `plugins/<host>/` and are not copied between hosts. Codex and Cursor persona adapters omit Claude tool/model fields.
- `plugins/claude/code-audit/` and `plugins/codex/code-audit/` — standalone Code Audit 1.0 authoring packages, maintained directly per host. They are not part of the shared-family generator. Keep the initial controller/scripts/configuration equivalent through package checks; host skills and review dispatch differ. No Cursor package is currently supported.
- `context/` — material about this repo itself (notes, plans). Never deployed or installed.

## Hard rules

- **Never edit installed copies.** Installed plugins live in a per-tool cache (Claude/Codex) or Cursor's plugin install / `~/.cursor/plugins/local/` tree. Edit here, commit, and let the marketplace update mechanism (or a fresh local copy) deliver the change.
- **A plugin cannot reference files outside its own folder.** Installs copy the plugin directory into a cache, so `../` paths out of the plugin break. Shared helpers live inside the plugin (e.g. `open-source-auditor/audit-lib/`).
- **No personal data in the repo.** This repo is public. Watchlists, employer/colleague names, credentials, and machine-specific paths belong in local config the user fills in from shipped sanitized templates — never in committed files.
- **Plugins that write per-project output must take the output location as an explicit argument** and refuse to run without it — never guess or default a write location into someone's repository.
- **Do not set `version` in `.claude-plugin/plugin.json` or `.cursor-plugin/plugin.json`.** Those tools version by commit SHA. **Do set and maintain `version` in `.codex-plugin/plugin.json`** — Codex requires `name`, `version`, and `description`.
- **Add plugins only to the hosts that support them.** Create the folder under `plugins/<host>/`, add that host's manifest only, and list it only in that host's catalog. Do not add stub manifests "for completeness," and do not keep all three catalogs listing the same plugins by default. Copies under different host roots may drift.
- **Plugin `name` is a stable identifier** — renames need a migration note, not a silent change.

## Conventions

- File and folder names are kebab-case except tool-mandated names (`SKILL.md`, `AGENT.md`, `README.md`, `AGENTS.md`, `CLAUDE.md`) and language-idiomatic code files. American English throughout.
- Every plugin folder has a `README.md` stating what it does, how to invoke it, what the consuming machine must provide, and known limitations.
- Skill frontmatter carries `name` (matching the folder), a "Use when…" `description`, an argument hint when the skill takes arguments, and `metadata.version`. Native Codex skills put the hint under `metadata.argument-hint` and describe inputs in the body; Claude skills use top-level `argument-hint`.
- Validate before committing plugin changes: `claude plugin validate .` from the repo root (Claude layout). For Cursor, confirm each plugin under `plugins/cursor/` has `.cursor-plugin/plugin.json` and that the Cursor catalog `source` paths resolve, then smoke-test via `~/.cursor/plugins/local/<plugin>/` + Reload Window. For Codex, confirm `.agents/plugins/marketplace.json` local sources under `plugins/codex/` and each `.codex-plugin/plugin.json` has `name`, `version`, and `description`.
- Run `python scripts/check.py` for repository and component checks, including generated parity, host manifests, safety regressions, Savior tests, screenshot metric, and Oracle suites. Native Claude validation and actual installed-host activation remain separate rollout checks.
- Commit messages follow the structured `commit-log` format (heading ≤72 chars, `~ Problem:` / body lines / `~ Resolution:`).
