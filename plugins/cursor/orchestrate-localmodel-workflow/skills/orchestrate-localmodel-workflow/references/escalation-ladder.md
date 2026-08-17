---
name: orchestrate-localmodel-workflow-escalation-ladder
description: Three pi attempts, then a frontier rescue that finishes the story, files an incident report, and ends the run.
metadata:
  version: "1.0"
---

# Escalation Ladder

Two ladders operate at different levels and must not be confused.

**Inside the worker**, the tenacity doctrine in [worker-contract.md](worker-contract.md) applies. The worker exhausts its own options before returning failure.

**At the Boss level**, failure of a story is counted. This ladder is the user's protection against returning to a heap of half-finished code. It is loud, reported, and it ends the run.

## Attempt counter

The counter lives in `progress.md` (the `Attempt` column) and is written **before** the next dispatch. Failures are also appended under `logs/` so a compacted Boss can rebuild the evidence.

| Attempt | Actor | Action |
| --- | --- | --- |
| 1 | local pi | Dispatch with the full worker contract. |
| 2 | local pi | Re-dispatch with the failure evidence from attempt 1. Keep the dirty tree. |
| 3 | local pi | Re-dispatch with evidence from attempts 1 and 2. Keep the dirty tree. |
| 4 | frontier subagent | **Abandon pi for this story.** Rescue: finish it properly, test, commit, file the incident report, **end the run**. |

What counts as a failed attempt:

- Client outcome `hung` or unexpected `spawn_failed` after a session actually started
- Worker returned but the Boss's cheap verification failed (harness fail, missing commit, missing `commit-log` signature, scope-fence breach)
- Worker reported itself blocked after exhausting tenacity
- `verdict.json` status `rejected` (attempts remain → retry with the rejection text; last rung → rescue)
- `verdict.json` status `budget-exhausted` (failed attempt; on the last rung, escalate rather than resetting the budget)
- Client outcome `hard_cap` (must not happen in production; still a failed attempt if a test enabled the cap)

What does **not** count as a failed attempt:

- `refused_existing` — no session was started; ask the user
- `rig_down` — the row becomes `BLOCKED` and the run stops; this is not a worker failure
- Pre-dispatch size flag (plan plus named files obviously exceed the 131k window) — the story is `BLOCKED` as too large; the queue continues
- `verdict.json` status `reviewer-unavailable` — **not a story failure.** Retry the same attempt once; if it persists, mark `BLOCKED` and stop, as with a downed rig. An Opus outage must not march a good story to a frontier rescue.
- `verdict.json` status `stand-down`, or the file absent — the guardrail declined to review. Record it in `progress.md` and rely on the Boss's own cheap checks. Never infer success from a missing file.

### `verdict.json`

Prerequisite (not this plugin): the review-bot guardrail writes `harness/claude-as-review-bot-guardrail/verdict.json` in the **target** repository. Until that story lands, the file will be absent; treat that as `stand-down`.

```json
{
  "status": "approved | rejected | budget-exhausted | stand-down | reviewer-unavailable",
  "cyclesUsed": 1, "cyclesMax": 10,
  "fingerprint": "<status+diff hash>",
  "lastRejection": "<capped review text>",
  "ts": "<iso8601>"
}
```

| Verdict status | Boss action |
| --- | --- |
| `approved` | Cheap-verify, accept, advance the queue. |
| `rejected`, attempts remain | Re-dispatch the same story carrying `lastRejection` forward. |
| `budget-exhausted` | Failed attempt. Last rung → rescue, do not reset the budget. |
| `reviewer-unavailable` | Not a story failure. Retry once; persist → `BLOCKED` and stop. |
| `stand-down` | Record it; cheap-check only. |
| file absent | Same as `stand-down`. Say so in `progress.md`. |

Do not build policy on pi's process exit code. The verdict file is the contract; the exit code is unreliable (plan Q6).

Hung workers: keep the dirty tree. The next attempt's prompt says so. Do not revert, stash-drop, or otherwise discard work to "start clean" unless the failure evidence says the partial work is the bug.

## The frontier rescue (attempt 4)

The rescue is a real subagent at frontier capability and high reasoning effort. It takes the worker's place for **this one story**, then the run ends.

**Default model:** Claude Sonnet 5 at high effort — the natively dispatchable option in Claude Code.

**Named equivalents, only where the harness can actually select them:** GPT-5.6 Terra, Grok 4.6. In Cursor, that currently means the Task tool's `gpt-5.6-terra-medium` and `cursor-grok-4.6-high` (or the high-reasoning Grok 4.6 equivalent the harness exposes). **Do not promise a model the current harness cannot select.** If the model parameter cannot be set, inherit the session model, record `inherited (unresolved)` in `progress.md`, and say so. Do not write a model name that was only wished for.

Rescue inputs:

- the story id and source document
- whatever partial work exists in the tree
- the three failure records from `logs/`
- the same scope fence, harness command, `commit-log`-by-name rule, and never-push rule as the worker
- an instruction to write the incident report (format below) into the source folder **and include that file in the rescue commit**

Rescue obligations:

- complete the story, including tests
- run the harness and do not return with it failing
- make a real commit worded by `commit-log`
- never push

Then the Boss cheap-verifies the rescue the same way it verifies a worker (harness re-run from the Boss's own shell, signature, scope fence). A rescue that fails verification is still the end of the run: mark the row `BLOCKED`, keep the incident report, and stop. Do not silently start a fifth attempt.

## The run ends after the rescue

This is deliberate. The user may lose hours of throughput, but never returns to a heap of half-finished code demanding full attention. The story is either done by the local worker or done properly by a frontier model, and the run stops so a human can look at what happened.

`--resume` after a rescue is **legal**, but the Boss must re-announce, before dispatching anything, that a rescue already happened, which story it touched, the commit SHA, and where the incident report lives. Resuming is never accidental. See the skill's resume rules.

## Incident report

Lineage: shape follows `agentic_rails_tooling/source/skills/rails-minion-workflow/references/intervention-report.md` v1.0 as it stood on 17 August 2026 (the blocker record), plus rescue-specific fields. Plugin isolation forbids linking there.

**Location:** the same folder as the document the story came from. For a story whose source is `plan.md`, that folder. For a phased plan whose source is `phase-3.md`, that folder.

**Name:** `escalation-report-<story-slug>.md` — filesystem-safe slug of the story id (lowercase, non-alphanumerics to hyphens, no leading/trailing hyphens). Several reports can coexist; none collides with `readme.md`.

Write the report **before** the rescue commit, and add it to that commit.

```markdown
# Escalation report: «story-id»

**Run:** `context/_localmodel-runs/<run-slug>/`
**Source:** «path to plan or phase document»
**Ended the run:** yes
**Rescue commit:** «SHA or pending»

## Blocked on

«the concrete technical issue that defeated the local worker»

## Evidence

«commands, errors, client_result outcomes, harness output»

## Attempts made

- Attempt 1: «what happened»
- Attempt 2: «what happened»
- Attempt 3: «what happened»
- Attempt 4 (frontier rescue): «what the rescue did»

## Partial progress completed

- «what the local worker left that is usable»

## Possible next paths

- «what a future local attempt should try first, if a human chooses to continue locally»

## Human input required

«only when genuinely required, and what exactly — otherwise "none; rescue completed the story"»

## Can other milestone work continue?

Yes — but this run has stopped. Remaining queue rows stay `TODO` in `progress.md` for an explicit `--resume`.

## Next autonomous action

«none — the run ended after rescue, by design»
```

A report that lists a blocker with no attempts, no partial work, and no recommended next path is describing an abandoned story rather than a routed one. Fill every section.
