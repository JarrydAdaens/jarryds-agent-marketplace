# orchestrate-localmodel-workflow

An installable plugin in which one frontier session acts as **Boss** and drives a **single local pi session** as its worker: one story at a time, continuously and unattended, across a large Agentic Rails story queue.

The worker implements, runs the project's test harness, self-revises on failure, and commits. The Boss owns the queue, durable run state, RPC session supervision, cheap independent verification, and — when a story defeats the local worker three times — a frontier rescue that finishes that one story, files an incident report, and **stops the run**.

The Boss's governing purpose is that the work does not stop until it is complete.

## Rails exception (read this)

This marketplace's standing rule is that artifacts must not impose Agentic Rails framework policy. **This plugin is a documented exception**, decided 17 August 2026: the author works exclusively in Agentic Rails, and the experimental artifact does not belong in the framework repos while it is still being proven.

It reads `context/implementation-plans/<milestone>/<story>/plan.md`, writes run state to `context/_localmodel-runs/<run-slug>/` in the **target** repository, and marks source stories complete. It is not framework policy, and it is not a flag on `rails-boss-execute-workflow`.

## Install

**Claude Code / Codex:** add the `jarryds-agents` marketplace, then `/plugin install orchestrate-localmodel-workflow@jarryds-agents`.

**Cursor:** copy this plugin folder to `%USERPROFILE%\.cursor\plugins\local\orchestrate-localmodel-workflow\` (must contain `.cursor-plugin/plugin.json` at that root), then **Developer: Reload Window**. See the marketplace root `README.md`.

One install brings the orchestration skill, five project-control skills, the three references, and the Pi RPC client.

## Project configuration and controls

Each consuming project opts in with `harness/orchestrate-localmodel-workflow/cursor-config.json`:

```text
/localmodel-init
```

That JSONC config defaults the local Pi worker to `qwen3.8`, with a 180-second idle liveness check and a 900-second think-grace timeout. It is deliberately project-scoped; it does not change the plugin cache or global Pi configuration.

```text
/localmodel-help
/localmodel-model                 # view choices
/localmodel-model 1               # qwen3.8
/localmodel-model 2               # local-model-placeholder
/localmodel-model <pi-model-slug> # another valid Pi model slug
/localmodel-health
/localmodel-timeout idle 240
/localmodel-timeout think default
```

The selected model and timeouts are passed to each new Pi worker. Health is non-mutating and does not start a worker.

## Invoke

```text
/orchestrate-localmodel-workflow <docs, plans, or story ids>
/orchestrate-localmodel-workflow --dry-run <docs>
/orchestrate-localmodel-workflow --resume <run-slug>
```

There is no parallelism flag. The hardware forbids it.

Run artifacts in the target repository:

```text
context/_localmodel-runs/<run-slug>/
  briefing.md
  progress.md
  logs/
```

## What the consuming machine must provide

- **Pi** installed (`@earendil-works/pi-coding-agent`), typically via pi's own Node at `%LOCALAPPDATA%\pi-node\current\`. The client spawns `dist/cli.js` through that `node.exe` directly — never `pi.cmd`.
- The **pi guardrails** from `agentic_rails_marketplace/plugins/pi/`, installed and enabled. This plugin does not install them.
- A **runnable test harness** in the target project. The workflow requires the command and will not invent one.
- A local model endpoint configured in `~/.pi/agent/` (the client reads `settings.json` + `models.json` only to probe liveness; it does not hardcode a host).
- The `commit-log` skill available to the worker, invoked **by name**.

Optional override if pi is installed somewhere unusual: set `PI_NODE_EXE` and `PI_CLI_JS`.

## Known limitations

- **Serial by construction.** One RTX-class GPU serving one model; a second session starves rather than slows.
- **Pi only.** The seam is worth leaving open; this plugin does not drive Codex, Cursor, or Claude as the local worker.
- **No CER routing.** Stories that plausibly fit the 131k window are attempted; failures are data. The escalation ladder catches the ones the local model cannot do.
- Cheap Boss verification, including `verdict.json` when the upstream review-bot story has landed. A missing verdict file is stand-down, not success. Continuity, not deep review.
- Production transport is **RPC** (prompt on stdin). `--mode json` is the intended one-shot transport once the prerequisite guardrail lands and Q7 is measured; it cannot carry a real worker contract on Windows because the prompt is a CLI argument.
- **Rescue ends the run.** Throughput is sacrificed so the operator never returns to a half-finished tree. `--resume` after a rescue is legal but must be re-announced.
- **Nothing is pushed**, from any layer.
- Windows-first (the reference run was Windows). The client has a Unix process-listing fallback that is less battle-tested.

## Provenance

Generalized from the 16–17 August 2026 pi guardrail port: six headless runs, five phases, no rework, one 6h40m loss to a supervision failure. The operational facts in `skills/orchestrate-localmodel-workflow/references/pi-session-operations.md` are the load-bearing content; the loop around them is ordinary queue-and-dispatch.
