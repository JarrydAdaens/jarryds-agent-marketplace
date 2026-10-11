# wpf-visual-quality-gate

Evaluator-run visual quality gate for WPF desktop apps, delivered as a
marketplace plugin. On explicit request or an adopted UI gate, an independent
evaluator sub-agent launches the app, screenshots the initial state, performs
the target interaction through real input, screenshots the result, and
reports pass/fail against explicit criteria — so agents cannot declare
visible UI work done on build and unit tests alone.

Unlike `game-golden-screenshot-verifier`, the runner is not a script: it is an
evaluator sub-agent following a fixed procedure and report format. The payload
is one skill, `wpf-visual-quality-gate`, whose `references/` carry the gate
document (procedure, runner order, pass criteria, attempt loop, report format)
and a filled packet example. Works in Claude Code, Codex, and Cursor (skills
only, no hooks); the preferred evaluator personas (`quality-gate-persona`,
`wpf-persona`) are optional capabilities when registered in the current host.
The packaged checklist supports an equivalent evaluator or a human evaluator;
no external persona path is required.

## Division of ownership

| Lives in the plugin (updated via marketplace) | Lives in the target project (the seam) |
| --- | --- |
| The gate document — procedure, criteria, report format | `harness/wpf-visual-quality-gate/defaults.md` — launch command, window title, cleanup command |
| The packet example | The trigger lines in the project's `AGENTS.md`/`CLAUDE.md` |

Per UI story, the implementing agent writes an evaluator packet and dispatches
the evaluator; the skill documents both steps.

## Requirements

- Windows desktop session able to launch and display the target WPF app.
- Screenshot capture and real UI input in the evaluator environment.
- An independent evaluator sub-agent when available; degrades to a human
  checklist otherwise.

## Provenance

Generalized from the Quota-Tank project's local gate (2026-07-09), previously
maintained as a drop-in verifier in `agentic_rails_tooling` and extracted here
as a plugin (v1.1: the gate document now stays in the plugin; only the
Project Defaults file is created in the target project).

## Packaging and activation evidence

This payload is generated from one repository-owned authoring source. All runtime
helpers and references are inside this package. The `.package-receipt.json` records
the baseline and content digest; discovery and activation require a separate live
host test. Invoke only for an explicit request or an adopted project workflow.
