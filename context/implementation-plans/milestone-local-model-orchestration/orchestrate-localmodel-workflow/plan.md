# Plan: orchestrate-localmodel-workflow — a Frontier Boss Supervising a Local Pi Worker

## Metadata

- Task Type: `FEATURE`
- Status: `In Progress`
- Owner: `Jarryd Adaens`
- Last Updated: `17 August 2026`

## Linked Context

- Milestone: `context/implementation-plans/milestone-local-model-orchestration/` — **the first implementation plan in this repository.** `context/` existed but was empty; the milestone is defined by this folder.
- Story: none recorded separately; this plan is the story of record.
- Model skill: `agentic_rails_tooling/source/skills/rails-boss-execute-workflow/SKILL.md` v2.0 (+ `references/state-model.md`) — the sibling this forks from. Referenced for lineage only; the plugin cannot link to it (see Constraints).
- Doctrine reuse: `agentic_rails_tooling/source/skills/rails-minion-workflow/references/blocker-ladder.md` and `references/intervention-report.md` — **currently uncommitted work in that repo.** See Questions Q1.
- Operational evidence: `agentic_rails_marketplace/context/pi-agentic-ide/pi-agentic-ide.md` §9, and the `## Completion Review` of `agentic_rails_marketplace/.../pi-marketplace-and-guardrail-port/plan.md` — the live run this generalizes.
- Prerequisite: the pi guardrails from `agentic_rails_marketplace/plugins/pi/`, installed and enabled in the target project.
- External Tooling: `commit-log` (worker commit wording).

## CER

- Complexity: `6`
- Effort: `7`
- Risk: `6`
- Notes: Hand-graded. Complexity sits in three places that are not prose — RPC session supervision, the escalation ladder's hand-off from a local worker to a frontier rescue, and encoding operational facts that were each learned by losing time. Effort rose from the earlier draft because this is now a **packaged plugin** (three manifests, three catalogs, a README, a bundled script) rather than a bare skill folder. Risk rose because the design target is now unattended 24/7 operation over dozens of sessions: a supervision bug does not cost one story, it costs a night. The artifact itself is Markdown plus one script and cannot break a build.
- **CER is deliberately not used to route work to the pi worker.** Decided 17 August 2026 — see the Worker admission policy.

## Objective

Build `orchestrate-localmodel-workflow`, an installable plugin in this personal marketplace, in which one frontier Claude session acts as Boss and drives a **single local pi session** as its worker, one story at a time, continuously and unattended, across a large story queue. The worker implements, runs the project's test harness, self-revises on failure without Boss intervention, and commits its own work. The Boss owns the queue, durable run state, session supervision, cheap independent verification, and — when a story defeats the local worker three times — a terminal escalation that hands that one story to a frontier subagent, finishes it properly, files an incident report, and stops the run.

The Boss's governing purpose is that **the work does not stop until it is complete.**

## Scope

### In Scope

- `plugins/orchestrate-localmodel-workflow/` as an installable plugin:
  - `skills/orchestrate-localmodel-workflow/SKILL.md` — the orchestration skill.
  - `references/pi-session-operations.md` — supervising pi as an external process: single-session enforcement, RPC transport, liveness, teardown, rig-down handling.
  - `references/worker-contract.md` — the dispatch payload spec, prompt template, scope fence, and the tenacity doctrine handed to the worker.
  - `references/escalation-ladder.md` — the three-attempt ladder, the frontier rescue, and the incident report format.
  - `scripts/pi-rpc-client.mjs` — the JSONL RPC client.
  - `README.md`, plus `.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`, `.codex-plugin/plugin.json`.
- Registration in all three catalogs: `.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json`, `.agents/plugins/marketplace.json`.
- A run-folder layout for durable, compaction-surviving state.
- `claude plugin validate .` clean from the repo root.

### Out Of Scope

- Any change to `rails-boss-execute-workflow` or `rails-minion-workflow`. This is a sibling, and those repos have uncommitted work in flight.
- Parallelism of any kind. The hardware forbids it; this is serial by construction, not serial by default.
- Worker model selection. The worker is whatever the local rig serves.
- The four guardrail changes in `agentic_rails_marketplace` that this workflow depends on — awaited non-injecting review, `verdict.json`, the operator commands, and the per-project budget. **They are a prerequisite story in that repository and need their own plan**, not a section of this one. This plan defines the contract it needs; it does not implement it.
- Driving any local agent other than pi. The seam is worth leaving open; building for it is speculation.
- Building the target project's test harness. The workflow invokes one and requires that it exists.

## Non-Goals

- **Do not have the Boss implement story code.** It reads, queues, dispatches, supervises, verifies cheaply, records, and escalates. A Boss that starts implementing is `rails-minion-workflow` with extra latency. The single exception is the terminal escalation, which is an explicit, reported, run-ending event — not a quiet habit.
- **Do not forbid the worker from committing.** The worker commits. This is also empirically the only stable posture: pi committed against an explicit instruction not to during the reference run.
- **Do not gate stories on CER.** Decided — see Worker admission policy.
- **Do not build a general local-agent abstraction.** One worker, one transport, named honestly.
- **Do not push.** Ever, from any layer.

## Current Understanding

### What is being generalized

The 16–17 August 2026 pi guardrail port ran this loop by hand: decompose a plan into phases, write a bounded prompt per phase, launch one headless pi run, supervise it, verify the result independently, commit, launch the next. Six runs, five phases, no rework. This plugin is that loop, written down — plus the three orchestration failures it exposed.

### Decisions taken from the Q&A of 17 August 2026

| Question | Decision |
| --- | --- |
| Transport | **RPC mode**, not `pi -p`. See below. |
| Name and home | `orchestrate-localmodel-workflow`, in this personal marketplace, as a plugin. Experimental, not framework policy. |
| Boss verification depth | **Cheap checks only.** The Boss's job is continuity, not deep review. |
| Rig unreachable | **Stop and mark `BLOCKED`.** Not a pause. |
| Wall-clock budget | **None.** Advisors plus a review bot legitimately make stories long. Liveness is the only kill signal. |
| Repeated failure | **Three pi attempts, then a frontier rescue, then the run ends.** |
| Rails dependency | Accepted and documented. |
| CER routing | **Not used.** Attempt anything that plausibly fits the context window; study the failures. |

### Transport — revised 17 August 2026 after a measurement that overturned the earlier answer

The first draft of this plan chose RPC mode on the grounds that the review bot could not function headless. **That premise was wrong**, and the correction came from the local worker itself reviewing this design.

Measured: **pi awaits an async `agent_settled` handler before exiting in print mode.** A probe whose handler slept eight seconds and then wrote a file produced both markers before the prompt's own output. What genuinely fails headless is *injection* — `sendUserMessage` has no further agent run to drive because `-p` exits. The handler itself runs to completion.

That changes the design materially, and in the orchestrator's favour:

- A wrap-up review **can** run in a non-interactive session, provided the handler returns its promise so pi awaits it, and it **reports rather than injects**.
- Under orchestration, each worker process is one work unit with a fresh in-memory budget by construction. The in-session self-correction loop that injection provides is largely redundant, because the **orchestrator** is the thing that re-tasks. Reject becomes a verdict the Boss reads, not a message the worker bounces back to itself.

Two consequences worth stating plainly:

1. **A guardrail that stands down on `ctx.mode === "print"` is more conservative than necessary**, and the check is also the wrong shape — `--mode json` is equally non-interactive and would take the injecting path. The correct condition is "do not inject in any non-interactive mode".
2. **`--mode json` is the transport to evaluate first.** It is one-shot like `-p` but streams events to stdout, which restores the real-time liveness signal that print mode's buffered output costs. That combination — one-shot semantics plus a live event stream plus an awaited review — is strictly better than either of the original two options. Print mode is the fallback if json mode has a surprise; RPC is the fallback if both do.

**This makes the workflow depend on a change to the review-bot guardrail** in `agentic_rails_marketplace`. See Prerequisites.

### Prerequisites — upstream guardrail work in `agentic_rails_marketplace`

This workflow needs a deterministic, machine-readable outcome from each worker run. Prose in a buffered log is not an orchestration contract. Four changes are required in `plugins/pi/claude-as-review-bot-guardrail/`, and they are **a separate story in a separate repository** — this plan depends on them rather than containing them.

1. **Awaited, non-injecting review in non-interactive modes.** Run the review, await it, write the verdict, do not inject. Replace the `ctx.mode === "print"` standdown with a "do not inject when non-interactive" condition so `--mode json` is covered too.

2. **A verdict file** at `harness/claude-as-review-bot-guardrail/verdict.json` — the seam the Boss reads:

   ```json
   {
     "status": "approved | rejected | budget-exhausted | stand-down | reviewer-unavailable",
     "cyclesUsed": 1, "cyclesMax": 10,
     "fingerprint": "<status+diff hash>",
     "lastRejection": "<capped review text>",
     "ts": "<iso8601>"
   }
   ```

   **Do not build the contract on the process exit code.** Pi's `-p` exit status is driven by the assistant's stop reason and is overwritten, so it is not a stable extension API. This is currently an unverified-but-credible claim (see Q6); the verdict file makes the workflow immune to it either way, which is the point of choosing a file.

3. **Operator commands** via `pi.registerCommand()` — `/review-bot-reset`, `/review-bot-disable`, `/review-bot-enable`. Commands are typed by an operator or an orchestrator and **never appear in the model's tool list**, so the worker cannot invoke them on itself. This is strictly better than shipping skills for the same job: a skill is markdown telling someone to write a file the worker could already write, whereas `reset` genuinely zeroes an in-process counter that nothing else can reach.

4. **Budget stays at 2 by default**, raised per project via the existing `harness/claude-as-review-bot-guardrail/config.json` seam (`{"maxCycles": 10}` for a heavy orchestrated project). A global default change is an Opus spend knob and should follow measured reject-loop counts, not a guess.

**Known gap, accepted.** Nothing prevents the worker from writing that config file to disable its own review. Command-only controls narrow the surface but do not close it, and adversarial enforcement here would be over-engineering on a single-user box where the operator owns the repository. One cheap, non-adversarial mitigation is worth taking: the Boss records a hash of the guardrail config before each dispatch and compares it after, and reports a change rather than preventing one. Detection is proportionate; enforcement is not.

### Worker admission policy — no CER gate

The local model's real capability ceiling is unknown, and CER scores are explicitly uncalibrated for execution difficulty. So the worker attempts **any** story that plausibly fits its context window; failures are data. The only pre-dispatch guard is a crude size sanity check — if a story's plan plus its named files obviously exceed the 131k window, flag it rather than feeding it a story it cannot read. Everything else goes to the worker, and the escalation ladder is what catches the ones it cannot do.

This is a deliberate trade: more failures, better information about where the ceiling actually is.

### The escalation ladder

Two ladders operate at different levels and must not be confused.

**Inside the worker**, the tenacity doctrine already written for `rails-minion-workflow` applies — a blocker is a routing decision, not an ending condition; try alternatives, spike, decompose, complete a useful subset. That doctrine is handed to the worker in its dispatch prompt so it exhausts its own options before returning failure.

**At the Boss level**, failure of a story is counted:

| Attempt | Action |
| --- | --- |
| 1 | Dispatch pi. |
| 2 | Re-dispatch pi with the failure evidence from attempt 1. |
| 3 | Re-dispatch pi with evidence from both prior attempts. |
| 4 | **Abandon pi for this story.** Dispatch a frontier subagent to finish it. |

The Boss decides which rung applies by reading `verdict.json` plus its own cheap checks. The policy lives here, in the orchestrator; the guardrail only reports status:

| Verdict status | Boss action |
| --- | --- |
| `approved` | Cheap-verify, accept, advance the queue. |
| `rejected`, attempts remain | Re-dispatch the same story carrying the rejection text forward. |
| `budget-exhausted` | Treat as a failed attempt. On the last rung, escalate rather than resetting the budget — a story that consumed its whole review budget is exactly the kind the rescue exists for. |
| `reviewer-unavailable` | **Not a story failure.** Do not consume an attempt. Retry once; if it persists, it is an environment problem — mark `BLOCKED` and stop, as with a downed rig. |
| `stand-down` | The guardrail declined to review. Record it, and rely on the Boss's own cheap checks for that story. |
| file absent | Treat as `stand-down` and say so in `progress.md`. Never infer success from a missing verdict. |

The `reviewer-unavailable` row matters: burning attempts on an Opus outage would march a perfectly good story to a frontier rescue for reasons that have nothing to do with the story.

The frontier rescue is a real subagent at frontier capability and high reasoning effort — Sonnet 5 is the natively dispatchable option in this harness; GPT-5.6 Terra and Grok 4.6 are the named equivalents where the harness can reach them. It takes the worker's place: it reads the story, whatever partial work exists, and the three failure records; completes the story including tests; and commits.

**Then the run ends.** This is deliberate and is the whole point of the design: the user may lose hours of throughput, but never returns to a heap of half-finished code demanding full attention. The story is either done by the local worker or done properly by a frontier model, and the run stops so a human can look at what happened.

**The incident report** is written to disk beside the plan or phase the story was following, and is included in the rescue commit. Its shape follows the blocker-record format already established in `rails-minion-workflow`'s intervention report — reproduced inside this plugin rather than referenced, because plugin isolation forbids cross-folder paths.

### Constraints

- **Serial by construction.** The rig is one RTX 3090 serving one model; a second concurrent session starves rather than slows.
- **Plugin isolation.** Installs copy the plugin folder into a per-tool cache, so `../` paths break. Every reference and script must live inside `plugins/orchestrate-localmodel-workflow/`.
- **This repo's stated rule is that artifacts must not impose Agentic Rails framework policy.** This one is rails-dependent by design — it reads `context/implementation-plans/<milestone>/<story>/plan.md`, writes run state under `context/`, and marks source stories complete. Accepted as a **documented exception**, decided 17 August 2026, on the grounds that the author works exclusively in Agentic Rails. Record it in the plugin README so it is not mistaken for drift.
- The Boss runs on the session's own model and does not switch it.
- The target project must have a runnable test harness. The workflow requires the command and must never invent one.
- Nothing is pushed, from any layer.

### Operational facts, all measured 16–17 August 2026

The load-bearing content of the skill. Each cost time to learn, and each reads like fussy over-specification to anyone who has not lost the time.

1. **One pi session at a time.** A third concurrent session hung 6h40m having burned 4.8 s of CPU.
2. **Liveness is activity, not reachability.** During that hang a `/v1/models` probe answered in 120 ms and a completion probe in 1.4 s. The endpoint was healthy; the session was dead. In RPC the direct signal is event-stream silence; CPU burn rate (~0.01 vs ~0.4+ s/min) remains the fallback.
3. **A heartbeat is mandatory.** Completion notification alone is insufficient: a hung process never exits and therefore never notifies. That is exactly how 6h40m was lost.
4. **Distinguish "ended" from "cut off".** A supervisor that stops on a fixed clock cannot tell a finished run from a truncated one. Exit on stream idle and report the two outcomes differently — a fixed-clock exit invalidated a test during the reference run.
5. **Launch hygiene:** stdin closed so a background pipe cannot block, and spawn pi's `cli.js` through node directly rather than the `.cmd` shim, which is fragile to path escaping.
6. **The scope fence is load-bearing.** Every dispatch named the exact writable paths and the forbidden ones. Nothing escaped scope across six runs.
7. **The worker corrects the Boss.** Twice, pi went to source and found the Boss's instructions wrong — an incomplete CLI flag list, and a field name that would have produced a silently dead gate. The contract must invite this.
8. **Verify, do not trust — including your own conclusions.** Worker self-reports were accurate throughout; one Boss conclusion drawn from an outcome without isolating the mechanism was wrong.
9. **Never kill the user's own pi session.** Check for existing sessions and ask.

## Questions / Unknowns

- Q1: **`rails-minion-workflow`'s blocker ladder and intervention report are uncommitted in `agentic_rails_tooling`.** This plan reuses both by concept.
  Impact: If they change before this is built, the reproduced copies drift from their source on day one.
  Assumption: Build against them as they currently stand, and note the lineage in the reproduced files.
  Status: `ANSWERED` — built against the working-tree text of `blocker-ladder.md` and `intervention-report.md` as they stood on 17 August 2026. Lineage is noted in `worker-contract.md` and `escalation-ladder.md`.

- Q2: **Can the harness dispatch a subagent at a non-Anthropic model?** The rescue names GPT-5.6 Terra and Grok 4.6 as acceptable equivalents.
  Impact: Determines whether the rescue rung is one option or three.
  Assumption: Sonnet 5 at high effort is the dispatchable default; the others are reachable only where the harness supports them, and the skill should say so rather than promise a model it cannot select.
  Status: `ANSWERED` — Claude Code: Sonnet 5 / high is the native default. Cursor Task currently exposes `cursor-grok-4.6-high` and `gpt-5.6-terra-medium`. The skill names Sonnet 5 as default and the others only where the harness can select them.

- Q3: **Where exactly does the incident report go for a phased plan?** "Beside the plan or phase it was following" is clear for `plan.md`, less so when the story is `phase-3.md` inside a phased manifest.
  Impact: Discoverability of the report six months later.
  Assumption: Same folder as the document the story came from, named for the story rather than generically — `escalation-report-<story-id>.md` — so several can coexist and none collides with `readme.md`-style generic naming.
  Status: `ANSWERED` — taken as assumed: `escalation-report-<story-slug>.md` in the source document's folder.

- Q4: **Should the Boss resume automatically after a rescue, if the user asks?** The design says the run ends.
  Impact: Whether `--resume` after a rescue is legal or refused.
  Assumption: `--resume` is legal but must re-announce that a rescue happened and which story it touched, so resuming is never accidental.
  Status: `ANSWERED` — taken as assumed. Encoded in the skill's resume rules.

- Q6: **Is pi's `-p` exit code really unusable as a signal?** The claim is that it is driven by the assistant's stop reason and overwritten.
  Impact: Low, deliberately — the verdict file exists so nothing depends on the answer. It matters only for a secondary "did the process fail outright" check.
  Assumption: Treat the exit code as unreliable and never branch orchestration policy on it. Cheap to measure if it ever becomes tempting.
  Status: `ANSWERED` — treated as assumed. The skill and client never branch policy on the exit code; `verdict.json` (or `stand-down` if absent) is the contract.

- Q7: **Does `--mode json` behave like print mode for the awaited review, and does it stream usefully?** The awaited-handler behavior was measured in `-p`, not in json mode.
  Impact: Decides the transport. Json mode would give one-shot semantics *and* live liveness, which is better than either original option.
  Assumption: It behaves the same, since both are non-interactive. Verify before building on it — this is one probe, and the same probe shape that settled the print-mode question.
  Status: `OPEN` — not probed during this implementation (an existing pi TUI session was running; spawning a second process is forbidden). The client supports `--transport json` for that probe. Production dispatch stays RPC for two independent reasons: Q7 unverified, and Windows argv cannot carry a real worker contract. See `pi-session-operations.md`.

- Q5: **What counts as "the rig is down" versus "the model is thinking"?** Both look like silence on the event stream.
  Impact: Directly sets the false-positive rate of the `BLOCKED` transition on an unattended run — a wrong call here wastes a night.
  Assumption: Silence plus an unreachable endpoint is rig-down (`BLOCKED`); silence plus a reachable endpoint and a live process is a hang (kill and retry). Probe the endpoint only to disambiguate silence — never as a liveness signal on its own.
  Status: `ANSWERED` for build, still worth measuring — client watchdog: silence + unreachable → `rig_down`; descendants (advisor/review CLIs) → still working; reachable + low CPU past think-grace with no descendants → `hung`; `agent_settled` then idle → `ended_naturally`. Starting timers: idle 3 min, think-grace 15 min.

## Execution Steps

1. **Settle Q1 and Q2.**
   - Why: Q1 decides whether reproduced doctrine is stable; Q2 decides whether the rescue rung can name three models or one.
   - Edits: none — discussion gate.

2. **Scaffold the plugin.**
   - Why: This repo's hard rules are mechanical and easiest to satisfy up front.
   - Edits: `plugins/orchestrate-localmodel-workflow/` with `skills/orchestrate-localmodel-workflow/SKILL.md`, `references/`, `scripts/`, `README.md`; the three per-plugin manifests (`version` set **only** in `.codex-plugin/plugin.json`); entries added to all three catalogs.
   - Dependencies: step 1.

3. **Write `references/pi-session-operations.md`.**
   - Why: These rules are unguessable, and they are the reason this exists rather than a flag on the sibling.
   - Edits: single-session enforcement and the process-listing check; the RPC transport and why print mode was rejected; liveness by event-stream silence with CPU burn rate as fallback, including the measured figures and the explicit warning that endpoint reachability proves nothing on its own; mandatory heartbeat supervision with its reasoning; launch hygiene; session teardown at every story boundary; rig-down detection and the `BLOCKED` transition; never killing the user's session.
   - Dependencies: step 2.

4. **Write `scripts/pi-rpc-client.mjs`.**
   - Why: RPC needs a client; a working one exists and should be adapted, not rewritten.
   - Edits: spawn `cli.js` through node directly; send one prompt; stream JSONL events; expose events to the Boss; exit on stream idle and report **"ended naturally" versus "hard cap hit" as distinct outcomes**; close the session on exit.
   - Dependencies: step 2.

5. **Write `references/worker-contract.md`.**
   - Why: Six hand-written dispatches converged on one shape; that shape is the reusable asset.
   - Edits: required payload — story id; exact documents to read first; acceptance criteria; the explicit scope fence naming writable and forbidden paths; the test harness command with the instruction to run it and self-revise on failure before finishing; the commit instruction naming `commit-log` **by name, never by path**; the never-push rule; the tenacity doctrine; and the standing invitation to report anything in the Boss's instructions that turned out to be wrong. Plus a worked example.
   - Dependencies: step 2.

6. **Write `references/escalation-ladder.md`.**
   - Why: This is the design's distinguishing feature and the user's stated protection against returning to a mess.
   - Edits: the attempt counter and what evidence each retry carries forward; the abandon-pi trigger; the frontier rescue dispatch spec (model, effort, inputs — story, partial work, three failure records — and its obligation to test and commit); the run-ending rule; and the incident report format with its lineage noted.
   - Dependencies: steps 1, 5.

7. **Write `SKILL.md`.**
   - Why: The loop is the skill; everything else is reference material it links to.
   - Edits: frontmatter (`name` matching the folder, "Use when…" description, `argument-hint`, `metadata.version`); declared arguments — work request, `--resume <run-slug>`, `--clean`, `--dry-run`, and deliberately **no** `--parallel`; run folder under `context/_localmodel-runs/<run-slug>/` with `briefing.md`, `progress.md`, `logs/`; one canonical rule list; the execution loop; the cheap-verification policy; compaction survival stated explicitly.
   - Dependencies: steps 3–6.

8. **Validate and self-check.**
   - Why: This repo's definition of well-formed.
   - Edits: `claude plugin validate .` clean; confirm all three catalogs and all three manifests agree; confirm no path escapes the plugin folder; confirm the skill never offers parallelism anywhere.
   - Dependencies: steps 2–7.

9. **Dry-run, then one real story.**
   - Why: Unproven until it drives a story it did not author.
   - Edits: none in this repo. `--dry-run` against the story-heavy project to inspect the queue, then one real story end to end.
   - Dependencies: step 8.

10. **Fault-injection pass.**
    - Why: The failure paths are the product. An orchestrator whose happy path works and whose escalation is untested is worse than no orchestrator, because it is trusted overnight.
    - Edits: none. Kill the worker mid-story; stop the rig mid-story; force three consecutive failures on one story and confirm the rescue fires, commits, reports, and ends the run.
    - Dependencies: step 9.

## Validation

### Automated Checks

- `claude plugin validate .` from the repo root — clean.
- `node --check scripts/pi-rpc-client.mjs`, plus a smoke run against a throwaway prompt.
- All three catalogs list the plugin; all three per-plugin manifests exist; `version` present **only** in the Codex manifest.

### Manual Checks

1. No file in the plugin references a path outside the plugin folder.
2. The skill never offers parallelism — in arguments, examples, or asides.
3. Every one of the nine operational facts appears with its evidence attached.
4. `--dry-run` on a real multi-story project builds the queue and dispatches nothing.
5. One real story end to end: exactly one pi process during the run; the worker runs the harness and commits; the Boss verifies cheaply and advances; `progress.md` is written **before** the next dispatch; the session is closed at the story boundary.
6. Kill the worker mid-story — the Boss detects it by silence, not by clock, and handles the dirty tree without discarding work.
7. Stop the rig mid-story — the Boss marks `BLOCKED` and stops, rather than thrashing.
8. Force three failures on one story — the rescue fires at attempt 4, completes the story with tests, commits, writes the incident report beside the source document, includes it in the commit, and the run ends.
9. Resume test: discard the Boss's context and resume from `--resume <run-slug>` using only `briefing.md` and `progress.md`.

### Acceptance Criteria

- A Boss following only the written plugin reproduces the reference run's loop without the operator re-explaining any operational fact.
- Never more than one pi process; the session is closed at every story boundary.
- A hung worker is detected by silence and terminated; a downed rig marks `BLOCKED` and stops.
- Run state is written before each dispatch; a compacted Boss resumes from disk alone.
- No story is `DONE` without a real commit bearing the `commit-log` signature and a harness pass the Boss confirmed itself.
- Three failures escalate to a frontier rescue that finishes the story, commits, reports, and ends the run.
- Nothing is pushed, from any layer.

## Risk Mitigation

- Risk: **A supervision bug costs a night, not a story.** The design target is unattended 24/7 operation.
  Mitigation: The fault-injection pass (step 10) is a required step, not a nicety. The failure paths get tested before the workflow is trusted overnight.

- Risk: **Silence is ambiguous** — a thinking model, a hung session, and a downed rig all look the same on an idle stream, and the three demand opposite responses.
  Mitigation: Q5 exists to settle this by measurement. Endpoint probing is used **only** to disambiguate silence, never as a liveness signal on its own — that conflation is exactly what cost 6h40m.

- Risk: **The rescue never fires, or fires constantly.** Either extreme defeats the design.
  Mitigation: Attempt counts are durable in `progress.md`, and every failure record is written to `logs/` before the next attempt. If the rescue fires often, that is data about the admission policy, and the fix is the queue, not the ladder.

- Risk: **The Boss drifts into implementing** because it is faster than another dispatch cycle.
  Mitigation: Canonical rule, enforced in acceptance. The only sanctioned Boss-side implementation is the escalation rescue, which is loud, reported, and ends the run.

- Risk: **Scope creep accumulates across dozens of stories** into an unreviewable diff.
  Mitigation: The scope fence is a required dispatch element, and post-story verification checks the diff against it. A breach is a finding, not a shrug.

- Risk: **A worker commits work that never passed the harness**, and the Boss accepts the commit's existence as proof.
  Mitigation: The Boss re-runs the harness from its own shell. It is the cheapest check that cannot be faked by a confident report, and it is the core of the cheap-verification policy.

- Risk: **Reproduced doctrine drifts from its source** in `rails-minion-workflow`.
  Mitigation: Accepted — plugin isolation forces the copy. Note the lineage in each reproduced file so a reader knows where the original lives.

- Risk: **This plugin and `rails-boss-execute-workflow` become two half-maintained near-copies.**
  Mitigation: Accepted. They live in different repositories with different worker mechanisms, and a shared abstraction over a harness subagent and an external OS process would be worse than the duplication.

## Evidence / References

- The reference run: `agentic_rails_marketplace/context/implementation-plans/milestone-pi-host-support/pi-marketplace-and-guardrail-port/plan.md` — `## Execution Log` and `## Completion Review`. Six pi runs, five phases, no rework, one 6h40m loss, three named orchestration failures with root causes.
- Measured pi behavior: `agentic_rails_marketplace/context/pi-agentic-ide/pi-agentic-ide.md` §9.6 (reentrancy; the two loop guards that do not work), §9.7 (print mode cannot host a wrap-up guardrail), §2 (the rig, and the 131k window).
- Sibling: `rails-boss-execute-workflow` v2.0 and its `state-model.md` — whose three-strikes rule was, as of 17 August 2026, being amended in flight to keep the run going rather than end it.
- Doctrine source: `rails-minion-workflow`'s `blocker-ladder.md` and `intervention-report.md` — uncommitted at the time of writing.
- This repository's rules: `AGENTS.md` — plugin isolation, three-catalog sync, `version` only in the Codex manifest, per-plugin README.
- Unverified and carried: whether the harness can dispatch non-Anthropic rescue models (Q2), and how reliably rig-down separates from a slow think (Q5).

## Complaints / Friction

### The valuable knowledge here is the kind that gets tidied away

**What happened:** Several rules — the mandatory heartbeat, liveness-by-silence rather than reachability, one session at a time — read like superstition to a reader who has not lost hours to them. Each is one line of rule and one paragraph of evidence.

**Why this made the task harder:** A future editor shortening `SKILL.md` will see "check for stream silence on a heartbeat" and reasonably conclude the harness's completion notification covers it. It does not, and the failure is silent, expensive, and invisible until morning.

**What was tried:** Every such rule carries its measured evidence inline, and the operations reference exists partly so they have room to stay at full length without bloating `SKILL.md`.

**What I think:** The loop is an ordinary queue-and-dispatch pattern. The operational facts and the escalation ladder are the entire value; the rest is scaffolding around them.

### The repository's own rule says this artifact does not belong here

**What happened:** `AGENTS.md` states that artifacts here "must not impose Agentic Rails framework policy". This plugin reads Rails plan paths, writes run state into a Rails `context/` tree, and marks Rails stories complete.

**Why this made the task harder:** It is a genuine, if small, contradiction between a stated repository boundary and a deliberate owner decision, and a future reader will hit it.

**What was tried:** Recorded as an explicit, dated exception here and in the plugin README rather than quietly ignored.

**What I think:** The decision is defensible — the owner works exclusively in Agentic Rails, and the experimental artifact does not belong in the framework repos while it is still being proven. But the rule in `AGENTS.md` is now inaccurate as written, and should eventually either gain this exemption in its own words or be narrowed to what it actually means.

## Execution Log

Implemented 17 August 2026 in `jarryds-agent-marketplace` as `plugins/orchestrate-localmodel-workflow/`.

| Step | Result |
| --- | --- |
| 1 Q1/Q2 | Settled as above. |
| 2 Scaffold | Plugin folder, three manifests (`version` only in Codex), three catalog entries, marketplace README row. |
| 3 Session ops | `skills/.../references/pi-session-operations.md` — nine operational facts with evidence; RPC as production transport; json as probe; verdict file as the outcome contract. |
| 4 RPC client | `scripts/pi-rpc-client.mjs` — spawn `cli.js` through node, JSONL (no readline), idle vs hard-cap outcomes, session listing, rig probe, `--transport rpc\|json`. `node --check` clean. `--self-check` resolved pi 0.84.2, probe 200 in 145 ms, listed two existing sessions (operator TUI + `config`) and therefore did **not** spawn a throwaway prompt. |
| 5 Worker contract | Dispatch payload, scope fence, tenacity doctrine (lineage noted), worked example. |
| 6 Escalation ladder | Three-then-rescue, `verdict.json` table, incident report path/name, resume-after-rescue re-announce. |
| 7 SKILL.md | Arguments, run folder, canonical rules, loop, cheap-verify including verdict + config hash, compaction survival. No `--parallel`. |
| 8 Validate | `claude plugin validate .` passed (the five "no version" warnings are the standing Claude/Cursor rule, including this plugin). Catalogs and manifests agree. |
| 9 Dry-run / real story | **Not done.** Requires a story-heavy target project and a free rig. An operator pi session was live during implementation. |
| 10 Fault injection | **Not done.** Depends on step 9. |

The four upstream guardrail changes remain a separate story in `agentic_rails_marketplace`. Until they land, `verdict.json` will be absent and the Boss treats that as `stand-down`.
