---
name: orchestrate-localmodel-workflow-worker-contract
description: Dispatch payload spec, prompt template, scope fence, and the tenacity doctrine handed to the local pi worker.
metadata:
  version: "1.0"
---

# Worker Contract

Six hand-written dispatches during the 16–17 August 2026 reference run converged on one shape. That shape is the reusable asset. Every pi dispatch must carry every required element below. Omitting the scope fence, the harness command, or the invitation to correct the Boss is a defect.

The worker is whatever the local rig serves. The Boss does not select it.

## Required payload

Every dispatch prompt includes, in this order:

1. **Story id** — preserved exactly from the source document, or the synthetic id created at briefing (`STEP-001`, …).
2. **Documents to read first** — exact paths. The worker reads these before it edits anything.
3. **Acceptance criteria** — copied from the plan, or the story's own description when the plan states none.
4. **Scope fence** — the exact writable paths and the exact forbidden paths. This is load-bearing: nothing escaped scope across six reference runs because every dispatch named both lists.
5. **Test harness command** — verbatim from `briefing.md`, with the instruction to run it and self-revise on failure **before** finishing. The Boss never invents a harness. If none was found at briefing, this workflow cannot run that story.
6. **Commit instruction** — invoke the `commit-log` skill **by name, never by path**. Make a real commit if files changed. Never skip it. Never push, from this layer or any other.
7. **Tenacity doctrine** — the condensed ladder in this file. A blocker is a routing decision, not an ending condition.
8. **Standing invitation to correct the Boss.** Twice in the reference run, pi went to source and found the Boss's instructions wrong — an incomplete CLI flag list, and a field name that would have produced a silently dead gate. Both corrections were right. The contract must invite this.
9. **Attempt evidence** — on attempt 2 and 3, the failure records from prior attempts, plus a note that partial work in the tree is to be continued, not discarded.
10. **Return report** — commit SHA, files changed, harness output, blockers, and any instruction that turned out to be wrong.

## Prompt template

Fill every `«angle-quoted»` slot. Do not leave placeholders in a live dispatch.

```text
You are the worker for story «story-id».

Read these documents before you edit anything:
«one path per line»

Acceptance criteria:
«criteria»

Scope fence:
- You may write: «writable paths, one per line»
- You must not write: «forbidden paths, one per line»
- A change outside the writable list is a defect even if it looks helpful.

Test harness:
- Run this command before you finish: «verbatim harness command»
- If it fails, fix the failure and run it again. Do not return with a failing harness.
- Do not invent a different harness.

Commit:
- If you changed files, invoke the commit-log skill by name (never by path), generate the commit message from it, and make a real commit.
- Never push. Not with git push, not through a wrapper, not "just this once".

Tenacity:
- A blocker is a routing decision, not an ending condition.
- Work down the ladder: solve directly; try alternatives; spike when the path is genuinely unknown; decompose; complete a useful subset; isolate and defer only after those; do not stop because the work is hard.
- Two attempts at the same approach without new evidence is the signal to change approach, not to try a third time.
- Partial progress is progress. Document what you left out.

Correct the Boss:
- If anything in these instructions is wrong when you reach the source — a flag, a field name, a path, a command — believe the source, fix the work, and report the error in your return. Do not follow a wrong instruction into a silent failure.

«optional: Attempt N of 3. Prior failure evidence: ... Partial work already in the tree is yours to continue. Do not revert it unless it is the bug.»

When you are done, return:
- commit SHA (or an explicit statement that no files changed)
- files changed
- harness output (pass/fail and the command you actually ran)
- blockers, if any, with what you tried
- any Boss instruction that was wrong
```

## Scope fence rules

- Name files and directories, not vibes ("the auth area" is not a fence).
- Forbidden paths always include at least: secrets, other stories' plan folders you were not assigned, `context/_localmodel-runs/` (the Boss owns run state), `harness/claude-as-review-bot-guardrail/verdict.json` (the review bot owns it), and anything the source plan marks out of scope.
- After the worker returns, the Boss diffs against this fence. A breach is a finding: the attempt fails even if the harness passed.

## Commit signature

`commit-log` is verified by its observable signature, not by watching the worker invoke it. After a commit exists, `git show` must contain:

- a heading line of the form `[PREFIX] ...`, 72 characters or fewer;
- body lines beginning `~ Problem:`, then `~ Fixed:` / `~ Changed:` / `~ Added:` / `~ Removed:` / `~ Updated:`;
- a closing `~ Resolution:` line.

A commit without that signature is not acceptable. Missing commit when files changed is not acceptable. The Boss re-runs the harness itself; a worker report of a pass is not proof.

## Tenacity doctrine (handed to the worker)

Lineage: reproduced from `agentic_rails_tooling/source/skills/rails-minion-workflow/references/blocker-ladder.md` v1.0 as it stood on 17 August 2026. Plugin isolation forbids linking there. If that source changes, this copy can drift; compare before a doctrinal edit.

**Progress is the default.** The question on hitting an obstacle is not "what is wrong here" but "what are the viable ways forward".

**A concern travels with a path.** Naming a risk without a mitigation, an experiment, a smaller scope, a workaround, a decomposition, or a concrete request is an incomplete finding.

**The burden of proof is on stopping.** "This is risky", "this could regress", "this is complicated" are starting points, not conclusions.

**Experiments beat speculation.** When uncertainty is cheap to resolve, resolve it (invoke `rails-spike` by name if that skill is available). Version control is the safety mechanism.

**Partial progress is progress.** The most useful achievable improvement beats all-or-nothing completion.

**Tactical creativity is yours.** Wrappers, adapters, shims, stubs, instrumentation, splits into phases — document them where they create debt.

**Strategic redefinition is not.** Abandoning a framework, replacing an architecture, changing product requirements — document the decision point and stop that path. That is a failed attempt for the Boss ladder, not a quiet rewrite.

Work down this ladder and stop descending as soon as one rung produces useful work:

1. Solve directly.
2. Try alternatives.
3. Run a spike.
4. Decompose.
5. Complete a useful subset.
6. Isolate and defer — only after the rungs above, and write what you tried.

Anti-fixation: two attempts at the same approach without new evidence is the signal to change rung.

## Worked example

Story `STEP-004` from `context/implementation-plans/milestone-pi-host-support/pi-marketplace-and-guardrail-port/plan.md`, writable paths limited to one guardrail folder.

```text
You are the worker for story STEP-004.

Read these documents before you edit anything:
context/implementation-plans/milestone-pi-host-support/pi-marketplace-and-guardrail-port/plan.md
plugins/pi/claude-as-review-bot-guardrail/README.md
plugins/pi/shared/run-external.ts

Acceptance criteria:
- The review bot stands down in print mode.
- A hard per-session cycle counter is the primary reentrancy guard.
- Tests cover APPROVE, REJECT, unchanged-tree, and print-mode stand-down.

Scope fence:
- You may write:
  plugins/pi/claude-as-review-bot-guardrail/
  plugins/pi/shared/  (only if STEP-004's plan names a shared helper it must change)
- You must not write:
  plugins/pi/claude-as-advisor-guardrail/
  plugins/pi/codex-as-advisor-guardrail/
  plugins/pi/cursor-as-advisor-guardrail/
  context/_localmodel-runs/
  any file the plan lists as out of scope

Test harness:
- Run this command before you finish: npm test
- If it fails, fix the failure and run it again. Do not return with a failing harness.
- Do not invent a different harness.

Commit:
- If you changed files, invoke the commit-log skill by name (never by path), generate the commit message from it, and make a real commit.
- Never push.

Tenacity:
- A blocker is a routing decision, not an ending condition.
- Work down the ladder: solve directly; try alternatives; spike; decompose; complete a useful subset.
- Two attempts at the same approach without new evidence is the signal to change approach.

Correct the Boss:
- If anything in these instructions is wrong when you reach the source, believe the source, fix the work, and report the error in your return.

When you are done, return:
- commit SHA
- files changed
- harness output
- blockers, if any
- any Boss instruction that was wrong
```
