# jarryds-agent-marketplace

A personal marketplace of skills, agents, and other AI artifacts for agentic IDEs (Claude Code and Codex), collected from across my projects.

Everything here is **general-purpose**: each artifact works on any repository, with no assumptions about project structure. That is the admission rule — skills that require a specific framework live with that framework. In particular, skills specific to the Agentic Rails system stay in `agentic_rails_tooling`; this repo holds what was deliberately extracted from it because it wasn't Rails-specific.

## Layout

- `source/skills/` — portable Agent Skills, one folder per skill with a `SKILL.md` entry point.
- `source/agents/` — named specialist personas.
- `source/audit-lib/` — shared Python helpers used by the `audit-*` skills.
- `context/` — material about this repo itself (notes, plans), never deployed.

## Inventory

| Family | Artifacts | Purpose |
| --- | --- | --- |
| General | `commit-log`, `grade` | Structured VCS commit messages; decisive letter-grading of artifacts |
| Grugg | `grugg`, `grugg-compress` | Token-efficient communication mode and memory-file compression |
| Oracle | `oracle-generate-stats`, `oracle-token-appraise`, `oracle-token-stats` | Token counting, file-cost appraisal, and session usage accounting |
| WPF | `wpf-tree-sensor`, `wpf-starter-update` | UI Automation tree inspection; WPF-Starter reconciliation |
| Audit | `audit-*` skills, `open-source-auditor-persona`, `source/audit-lib/` | Pre-publication open-source audit: deterministic sensors (secrets, tone, quality, dependency, provenance, hygiene), a triaging guardrail with a PASS/BLOCK verdict, licensing, and cleanup |

## Status

This repo is currently a plain collection synced into IDE config locations. Packaging the families as installable plugins (native Claude Code / Codex marketplace format) is planned; the folder layout already keeps each family self-contained to make that split easy.
