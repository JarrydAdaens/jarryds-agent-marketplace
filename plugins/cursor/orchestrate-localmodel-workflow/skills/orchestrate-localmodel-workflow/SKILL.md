---
name: orchestrate-localmodel-workflow
description: >-
  Use this orchestration skill when a frontier session should act as Boss and
  drive a single local pi worker through an Agentic Rails story queue,
  unattended and serial, one story at a time. The Boss owns the queue, durable
  run state, RPC session supervision, cheap verification, and a three-attempt
  ladder that hands a defeated story to a frontier rescue then stops the run.
  Use it for overnight local-model execution, not for parallel subagent
  dispatch and not when the Boss itself should implement.
disable-model-invocation: true
argument-hint: "<docs, plans, or story ids> [--resume <run-slug>] [--clean] [--dry-run]"
metadata:
  version: "1.0"
---

# Orchestrate Local-Model Workflow

You are the **Boss**.

You read the source documents. You build the queue. You drive **one local pi session** as the worker, one story at a time. You verify cheaply, yourself. You update the progress file. You repeat until the work is complete, the rig is down, or a story defeats the local worker three times and you hand that one story to a frontier rescue.

The Boss's governing purpose is that **the work does not stop until it is complete.**

The Boss orchestrates, supervises, verifies cheaply, records, and escalates. The Boss does not implement story code. The single exception is the terminal rescue, which is an explicit, reported, run-ending event — not a quiet habit.

This plugin is **rails-dependent by design** (a documented exception to this marketplace's "must not impose Agentic Rails framework policy" rule, decided 17 August 2026). It reads `context/implementation-plans/<milestone>/<story>/plan.md`, writes run state under `context/_localmodel-runs/`, and marks source stories complete. It is experimental, not framework policy. The sibling in `agentic_rails_tooling` is `rails-boss-execute-workflow`; do not treat this as a flag on that skill.

## Arguments

The skill was invoked with: $ARGUMENTS

Read that line before doing anything else. Parse it leniently ("continue that run" with a named slug is `--resume`; "do not dispatch" is `--dry-run`).

| Token | Meaning |
| --- | --- |
| `--resume <run-slug>` | Continue that existing run folder. Without it, an existing folder is never written into. |
| `--clean` | Delete and recreate the named run folder instead of resuming it. |
| `--dry-run` | Build `briefing.md` and `progress.md`, dispatch nothing. |
| anything else | The work request — document paths, plan paths, story ids, or story ranges. |

There is **no** `--parallel`. There is no serial flag either: this workflow is serial by construction. Do not offer parallelism in arguments, examples, or asides.

If `$ARGUMENTS` carries only a work request, every switch is unset. That is the normal case. Never ask the user to re-invoke with arguments.

Interpret the work request literally:

- If the user names files, read those files first. The **target repository** is the git repository that contains them.
- If the user names stories, keep that story order.
- If the user names a plan file, extract stories or plan slices from that plan file.
- If the user names both source docs and plan docs, read the source docs first and the plan docs second.

Examples:

```text
/orchestrate-localmodel-workflow context/implementation-plans/milestone-1/feature-slug/plan.md
/orchestrate-localmodel-workflow implement STORY 1.2 then STORY 1.3
/orchestrate-localmodel-workflow --resume localmodel-1_2-to-1_5
/orchestrate-localmodel-workflow --dry-run context/milestones/milestone-1.md
```

## Artifact root (target repository)

All paths in this section are relative to the **target** repository root — the project being implemented, not this plugin.

Every invocation gets its own **run slug** and run folder:

| Path | Role |
| --- | --- |
| `context/_localmodel-runs/<run-slug>/briefing.md` | Source documents, constraints, harness command, ordered queue, admission notes |
| `context/_localmodel-runs/<run-slug>/progress.md` | Execution queue and current row state |
| `context/_localmodel-runs/<run-slug>/logs/` | Failure records, client events, incident copies, pi session dir |

The run folder is flat under `context/`, not nested under a milestone. Record the milestone(s) inside `briefing.md`.

Once every row is `DONE`, the folder may be deleted without losing anything: the code is committed, and the source plan carries the completion markers. Offer that rather than deleting it unasked.

### The run must survive the Boss being compacted

`briefing.md` and `progress.md` are the run's durable state. Everything needed to resume must be readable from them alone.

Write state to disk **before** starting the next thing, never after. A row's status, attempt number, commit SHA, and harness result land in `progress.md` **before** the next worker is dispatched. Never hold run state only in the conversation. `progress.md` is written before the next dispatch even when the last dispatch failed.

## Run slug naming

Derive the run slug from the work being executed. Determine it **before creating any files**.

**Numbered stories** — first and last story id, dots replaced by underscores:

```text
localmodel-1_2-to-1_5
localmodel-2_1
```

**Synthetic ids:**

```text
localmodel-STEP-001-to-STEP-006
```

**Unnumbered or design-doc-driven runs** — short slug from the source document name plus the date:

```text
localmodel-milestone-1-2026-08-17
```

Keep the slug short. Avoid `localmodel-run` or `localmodel-misc`.

**Collisions must not merge runs.** If the derived folder already exists and `--resume` did not name it, append the next free numeric suffix (`-2`, `-3`, …) and note the collision in the new run's `briefing.md`.

**Resuming is explicit.** Resume only via `--resume <run-slug>`, or when the user names the exact folder path. "Continue the localmodel run" without a named slug is ambiguous — list the run folders and ask.

If `--resume` names a run that already performed a frontier rescue, **re-announce that before dispatching anything**: story id, rescue commit SHA, incident-report path. Resuming after a rescue is legal and must never be accidental.

## Plugin paths

Throughout, `<skill-dir>` is the directory containing this `SKILL.md`. `<plugin-root>` is two directories above it (the installable plugin folder). The RPC client is:

```text
<node> <plugin-root>/scripts/pi-rpc-client.mjs
```

If you cannot resolve that path, search the plugin cache and this marketplace clone for `pi-rpc-client.mjs`. If you still cannot find it, refuse — do not approximate with `pi -p`.

Supporting references:

- **Session supervision**: [references/pi-session-operations.md](references/pi-session-operations.md)
- **Dispatch payload**: [references/worker-contract.md](references/worker-contract.md)
- **Escalation and incident report**: [references/escalation-ladder.md](references/escalation-ladder.md)

## Project worker configuration

Before dispatch, load `harness/orchestrate-localmodel-workflow/cursor-config.json` from the target repository. It is JSONC and is created by `/localmodel-init`. The configuration supplies the worker `model`, `idle_timeout_seconds`, `think_grace_timeout_seconds`, and optional `probe_url`. Do not dispatch without a valid configuration: ask the user to run `/localmodel-init` instead. The selected model is for the local Pi worker only; never change the Boss model.

## Non-negotiable rules

This is the canonical rule list. Nothing else in this document restates it.

**Setup**

- Determine the run slug and create the run folder before writing any file.
- Read every user-listed design, milestone, story, and plan document before dispatching the first worker.
- Resolve the target repository's validation command before dispatching. If none exists, stop: this workflow requires a harness and must never invent one.
- Write `briefing.md` and `progress.md` before dispatching the first worker.
- Never write into an existing run folder unless `--resume` named that run slug, or `--clean` is deleting it first.

**Worker**

- The worker is the local pi session. Do not select a different local agent. Start it with the model configured in `harness/orchestrate-localmodel-workflow/cursor-config.json`; do not substitute a model or change the Boss model.
- CER scores are not a dispatch gate. Attempt any story that plausibly fits the 131k context window. The only pre-dispatch size check: if the story's plan plus its named files obviously exceed that window, flag the row `BLOCKED` (too large) and continue the queue.
- Exactly one pi process. List sessions before every spawn. Never kill the user's own session.
- RPC only for story dispatch (`--transport rpc`, the default). Never `pi -p`. Never `--transport json` for a worker contract (Windows argv cap; Q7 unverified). Spawn through the bundled client, which spawns `cli.js` through node directly.
- Do not treat the pi process exit code as a verdict. Read `harness/claude-as-review-bot-guardrail/verdict.json`.
- Close the pi session at every story boundary, including retries.
- The worker commits. The worker never pushes. The Boss never pushes.

**Boss**

- Keep running on the session's own model. Do not switch the Boss's model, and do not ask to.
- Do not implement story code. Dispatch, supervise, cheap-verify, record, escalate.
- Cheap verification only: re-run the harness from this shell, check the `commit-log` signature, check the diff against the scope fence. Do not dispatch a deep reviewer on the happy path.
- Do not trust worker self-reports as proof, and do not treat your own unverified conclusions as proof. Isolate the mechanism.
- No wall-clock budget on a healthy worker. Liveness is the kill signal. See [references/pi-session-operations.md](references/pi-session-operations.md).
- No parallelism. Not as a flag, not as an optimization, not as an aside.

**Acceptance and escalation**

- No story is `DONE` without a real commit bearing the `commit-log` signature and a harness pass this Boss confirmed itself.
- Mark a story complete in the source plan only after its row is `DONE`.
- Three pi failures of the same story escalate to a frontier rescue, then the run ends. See [references/escalation-ladder.md](references/escalation-ladder.md).
- Rig down marks `BLOCKED` and stops the run. It is not a pause and not a failed attempt.

## Story extraction rules

- If the plan document already has named stories, steps, milestones, or checklist items, preserve those identifiers exactly.
- If the user requested a subset, queue only that subset.
- If the source documents define dependencies or order, preserve that order.
- If no explicit story ids exist, create stable synthetic ids such as `STEP-001`.
- If both a design document and a plan document exist, the design document provides context and constraints while the plan document provides execution order, unless the user says otherwise.
- Phased plans: queue each phase that is still incomplete, in manifest order, using the phase document as the source path.

## Worker admission — no CER gate

The local model's real capability ceiling is unknown, and CER scores are uncalibrated for execution difficulty. The worker attempts **any** story that plausibly fits its context window; failures are data.

Crude size check, before dispatch: estimate tokens from the plan plus every file the dispatch will name as required reading, using bytes/4. If that estimate exceeds ~100000 tokens (leaving room in the 131072 window for the conversation), do not dispatch. Mark the row `BLOCKED` with reason `exceeds-context-window` and continue. Do not feed the worker a story it cannot read.

## Briefing file

Write or refresh `context/_localmodel-runs/<run-slug>/briefing.md` with:

- the run slug, and the milestone(s) or source areas this run targets;
- the exact source documents read, each with a short note on why it matters;
- the target repository's validation command, verbatim, or a stop if none was found;
- the ordered list of stories or plan slices, with source paths;
- the scope-fence policy (writable vs forbidden defaults);
- the pi client path actually resolved;
- the selected worker model and liveness timeouts from the project configuration;
- any run-slug collision, `--dry-run`, `--clean`, and whether this resume follows a rescue;
- the rails-dependent-exception note, one line.

Keep it concise. It is safe to delete once the run's work has landed.

## Progress file

Write or refresh `context/_localmodel-runs/<run-slug>/progress.md` as a table:

| Status | Story | Source | Attempt | Outcome | Verdict | Commit | Harness | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TODO | STEP-001 | `context/implementation-plans/.../plan.md` | 0 |  |  |  |  | queued |

Column rules:

- **Status** — `TODO`, `DOING`, `VERIFYING`, `DONE`, `BLOCKED`. Only the Boss writes it.
- **Attempt** — 0 queued; 1–3 pi; 4 rescue. Written before dispatch.
- **Outcome** — `pass`, `fail`, `hung`, `rig-down`, `rescued`, `too-large`, or blank until the attempt settles.
- **Verdict** — `verdict.json` status, or `stand-down` when the file is absent. Blank until cheap-verify.
- **Commit** — actual SHA after success.
- **Harness** — `pass` / `fail` as **this Boss** measured it, never as the worker reported it.

## Execution loop

1. **Determine the run slug.** Honor `--resume`; otherwise resolve collisions with a numeric suffix.

2. **Init.** Ensure `context/_localmodel-runs/<run-slug>/`, `progress.md`, `briefing.md`, and `logs/` exist on the target repository.

3. **Read source documents.** Design and milestone context first, plan and implementation files second.

4. **Extract constraints and stories.** Ordered stories, sequencing, checklist updates, writable/forbidden defaults.

5. **Resolve the harness.** Read `AGENTS.md`, `package.json`, or the equivalent. Do not invent a command. No harness → stop.

6. **Write run state.** Refresh `briefing.md` and `progress.md`.

7. **Announce policy.** Before dispatching, tell the user: serial by construction (one pi session), no CER gate, cheap verification, three-then-rescue, nothing is pushed. Then stop talking and work. `--dry-run` stops here.

8. **Select next story.** The next `TODO` whose dependencies are satisfied, honoring user-requested order. Skip `DONE`. Leave `BLOCKED` unless this is an explicit resume that requeues.

9. **Size check.** If the story obviously exceeds the window, mark `BLOCKED` / `too-large`, write a log, continue.

10. **List pi sessions.** If any exist that this run did not spawn, ask the user and wait. Do not kill them.

11. **Dispatch.** Set the row `DOING`, increment `Attempt`, write `progress.md`, write the prompt to `logs/dispatch-<story>-attempt-<n>.md`. Hash `harness/claude-as-review-bot-guardrail/config.json` if it exists and record the hash in that log. Then:

    ```text
    node <plugin-root>/scripts/pi-rpc-client.mjs
      --cwd <target-repo>
      --transport rpc
      --model <configured-model>
      --idle-ms <idle_timeout_seconds * 1000>
      --think-grace-ms <think_grace_timeout_seconds * 1000>
      [--probe-url <configured-probe-url>]
      --prompt-file <that dispatch file>
      --events-file context/_localmodel-runs/<run-slug>/logs/events-<story>-attempt-<n>.jsonl
      --session-dir context/_localmodel-runs/<run-slug>/logs/pi-session-<story>-attempt-<n>
      --name <story-id>
    ```

    Payload: [references/worker-contract.md](references/worker-contract.md). Supervision: [references/pi-session-operations.md](references/pi-session-operations.md).

12. **On client return.** Close-out is already the client's job; confirm no pi process remains. Then:
    - `rig_down` → `BLOCKED`, stop the run.
    - `refused_existing` → ask; do not count an attempt.
    - `hung` / `hard_cap` / `spawn_failed` after start → failed attempt; keep the dirty tree; write `logs/failure-<story>-attempt-<n>.md`.
    - `ended_naturally` → set `VERIFYING` and cheap-verify.

13. **Cheap-verify** (Boss's own shell, not the worker's word):
    - `git status` / `git diff` against the scope fence. A breach fails the attempt.
    - If files changed: a real commit must exist with the `commit-log` signature.
    - Re-run the harness command. Fail the attempt on a failing harness even if the worker said it passed.
    - Confirm the worker's commit SHA if one was reported.
    - Read `harness/claude-as-review-bot-guardrail/verdict.json` per [references/escalation-ladder.md](references/escalation-ladder.md). Absent file → `stand-down`. Never branch on pi's exit code.
    - Re-hash `harness/claude-as-review-bot-guardrail/config.json` if it exists; a change is a reported finding, not a blocked attempt.

14. **Update state** before anything else, using both cheap-checks and the verdict table:
    - `reviewer-unavailable` → do **not** consume an attempt. Retry once; if it persists, `BLOCKED` and stop the run.
    - Cheap-checks pass and verdict is `approved` or `stand-down` → `DONE`, record SHA and `Harness: pass`. Mark the source plan complete.
    - `rejected` or `budget-exhausted`, or cheap-checks fail, or hung → failed attempt. If attempts used < 3, set `TODO` again with evidence (including `lastRejection`) in Notes. If attempts used = 3, go to step 16.
    - Write `progress.md` before the next dispatch.

15. **Repeat** until no `TODO` remains, or the run stops.

16. **Rescue.** Attempt 4: frontier subagent per [references/escalation-ladder.md](references/escalation-ladder.md). Cheap-verify the rescue. Write the incident report beside the source document, included in the rescue commit. **End the run.** Remaining `TODO` rows stay `TODO` for an explicit `--resume`.

17. **Report.** Give the user the run slug, paths, which stories are done, which are blocked, which commits landed, whether a rescue fired, and that nothing was pushed. If every row is `DONE`, offer to delete the run folder.

## Cheap verification

The Boss's job is continuity, not deep review. These checks are the ones that cannot be faked by a confident report:

1. Re-run the harness from this shell.
2. Read the commit message with `git show` against the `commit-log` signature.
3. Diff the changeset against the scope fence named in the dispatch.
4. Read `harness/claude-as-review-bot-guardrail/verdict.json` and apply the table in [references/escalation-ladder.md](references/escalation-ladder.md). A missing file is `stand-down`, not success. Never infer success from absence. Never branch on pi's process exit code.
5. Hash `harness/claude-as-review-bot-guardrail/config.json` (if it exists) **before** dispatch and compare **after**. A change is a finding to report, not something to prevent. The worker can write that file; detection is proportionate, enforcement is not.

That is the whole happy-path review. Do not add a quality-gate persona on every story. The in-worker advisors and review bot already ran inside pi.

Verify, do not trust — including your own conclusions. Worker self-reports were accurate throughout the reference run; one Boss conclusion drawn from an outcome without isolating the mechanism was wrong.

## Recovery

- `BLOCKED` is durable. Do not silently requeue.
- Rig-down `BLOCKED` stops the run. `--resume` after the rig is back continues from `progress.md`.
- Dirty trees after a hang are retained. The next dispatch says so.
- After a rescue, `--resume` must re-announce the rescue first.

## Standalone uses

One named story; an ordered list; a full implementation plan; a phased manifest; a milestone that expands into stories. Always serial. Always one local pi worker. Never a general local-agent abstraction.
