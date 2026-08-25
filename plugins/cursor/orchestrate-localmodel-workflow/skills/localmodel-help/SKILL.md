---
name: localmodel-help
description: >-
  Explain the orchestrate-localmodel-workflow Cursor plugin, its project config,
  local Pi worker controls, health check, and serial orchestration behavior.
disable-model-invocation: true
---

# Local-model workflow help

`orchestrate-localmodel-workflow` lets a frontier Boss supervise exactly one local Pi worker through a serial Agentic Rails story queue. The Boss dispatches, supervises, cheaply verifies, records progress, and performs one terminal frontier rescue after three failed local attempts. It never pushes.

Project settings live in JSONC at `harness/orchestrate-localmodel-workflow/cursor-config.json`. Create it with `/localmodel-init`; it controls the Pi `--model` slug, the idle liveness-check delay, the think-grace hang threshold, and an optional probe URL. The settings apply to new worker launches only.

| Skill | Purpose |
| --- | --- |
| `localmodel-init` | Create the project config with defaults. |
| `localmodel-model` | View or change the model slug for new workers. |
| `localmodel-timeout` | View or change idle and think-grace liveness timeouts. |
| `localmodel-health` | Check that Pi and the configured local endpoint are reachable. |
| `localmodel-help` | This overview. |
| `orchestrate-localmodel-workflow` | Start, dry-run, or resume the serial story workflow. |

The bundled worker choices are `qwen3.8` and `local-model-placeholder`; the latter is intentionally a replaceable placeholder. `/localmodel-model <slug>` also accepts another valid Pi model slug. Health does not launch a worker or alter the project. An OFFLINE result means do not start a run until Pi, its model configuration, or the endpoint is fixed.
