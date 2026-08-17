---
name: orchestrate-localmodel-workflow-pi-session-operations
description: Supervising pi as an external process - single-session enforcement, RPC transport, liveness, teardown, and rig-down handling. Each rule carries the measurement that made it load-bearing.
metadata:
  version: "1.0"
---

# Pi Session Operations

These rules are unguessable. Each cost hours to learn. A future editor who shortens them to "watch the process and wait for it to finish" will recreate the 6h40m loss.

The Boss drives pi through the bundled client:

```text
<node> <plugin-root>/scripts/pi-rpc-client.mjs
```

`<plugin-root>` is two directories above this skill's `SKILL.md`. Use pi's own `node.exe` when the client resolves it; otherwise `node --check` and ad-hoc runs may use the system Node. The client locates `dist/cli.js` next to that runtime and **spawns `cli.js` through node directly**. Never spawn `pi.cmd` / `pi.ps1`.

## 1. One pi session at a time

The rig is one GPU serving one model. A second concurrent session does not slow down; it starves.

Measured 16–17 August 2026: a third concurrent session hung 6h40m having burned 4.8 s of CPU.

Before every spawn:

```text
node <plugin-root>/scripts/pi-rpc-client.mjs --list-sessions
```

If any session is listed, **stop and ask**. Never kill the user's own pi session. The client refuses to spawn a second process unless `--allow-existing` is passed, and the Boss must not pass that flag without an explicit human yes.

During a worker run, exactly one pi process is legal: the one the client just spawned. A second appearing mid-story is a stop condition, not a curiosity.

## 2. Transport: RPC is production; JSON is the intended one-shot

The plan's current understanding (17 August 2026, after a measurement that overturned the first draft) is:

- An async `agent_settled` handler **is** awaited before `-p` exits. Injection is what fails headless, not the handler itself.
- A wrap-up review can therefore run non-interactively if it **reports rather than injects**.
- `--mode json` would then be the better one-shot transport: live event stream plus process-exit settle.
- That depends on a prerequisite story in `agentic_rails_marketplace` (non-injecting review + `verdict.json`). It is not this plugin's job to implement those guardrails.

Until that story lands and Q7 is measured, **this client defaults to RPC**. Two further reasons RPC stays the production path even after json mode is verified:

1. **Windows argv length.** JSON mode takes the prompt as a CLI argument (`pi --mode json "prompt"`). A real worker contract will not fit CreateProcess's command line. RPC sends the prompt on JSONL stdin with no argv cap.
2. **`--transport json` exists** for the Q7 probe and for tiny smoke prompts. Do not use it for a story dispatch.

RPC start:

```text
<node.exe> <cli.js> --mode rpc -a [--session-dir <run-logs>] [--name <story-id>]
```

JSON probe start (stdin closed):

```text
<node.exe> <cli.js> --mode json -a [--no-session] "<short prompt>"
```

`-a` trusts project-local files for this run so the session is not blocked on a TUI confirm. `--session-dir` points at `logs/pi-session/` inside the run folder when the Boss wants a reconstructable transcript; otherwise the client passes `--no-session`.

Do not use `--no-extensions`. The pi guardrails are a prerequisite, and they load from the operator's pi package install.

**Do not branch orchestration policy on pi's process exit code** (plan Q6). Read `harness/claude-as-review-bot-guardrail/verdict.json` instead. A missing file is `stand-down`, not success.

## 3. Liveness is activity, not reachability

During the 6h40m hang, a `/v1/models` probe answered in 120 ms and a completion probe in 1.4 s. The endpoint was healthy; the session was dead.

**Never treat endpoint reachability as proof of progress.** Probe the endpoint only to disambiguate silence.

The client's watchdog, which the Boss must not disable:

| Observation | Meaning | Action |
| --- | --- | --- |
| JSONL events continue | Working | Continue |
| Silence, but pi has descendant processes (advisor/review CLIs) | Working; a consult is in flight and those consults are allowed to take up to 600–1800 s | Continue |
| Silence, endpoint unreachable | Rig down | `BLOCKED`; stop the run |
| Silence, endpoint reachable, CPU burn ≥ ~0.2 s/min | Likely still generating | Continue |
| `agent_settled`, then silence, no descendants | Ended naturally | Close the session; verify |
| Silence past think-grace, reachable endpoint, live process, no descendants, low CPU | Hang | Kill this worker; count as a failed attempt; do not discard the dirty tree |

Measured CPU burn: ~0.01 s/min hung versus ~0.4+ s/min working. The client uses 0.2 s/min as the working floor.

Default timers, starting points from the 16–17 August 2026 run, still worth measuring (plan Q5):

- `--idle-ms` 180000 (3 minutes without events before a check)
- `--think-grace-ms` 900000 (15 minutes of "looks like thinking" silence before HUNG)
- `--hard-cap-ms` **0** (off)

A wall-clock budget is forbidden as the kill signal. Advisors plus a review bot legitimately make stories long. The hard-cap flag exists so a test can tell "ended naturally" from "cut off by a clock". A supervisor that stops on a fixed clock cannot tell a finished run from a truncated one — that exact conflation invalidated a review-bot test during the reference run.

## 4. A heartbeat is mandatory

Completion notification alone is insufficient: a hung process never exits and therefore never notifies. That is exactly how 6h40m was lost.

The client **is** the heartbeat for the pi process: it always terminates, with a distinct `client_result` outcome. The Boss still must not "fire and forget" a wait that cannot be inspected. Durable events go to `--events-file` under the run's `logs/` **as they arrive**, not after the client exits. If the client itself is silent past think-grace with no `events-file` growth, the Boss kills the client and treats it as a hung attempt.

## 5. Distinguish "ended" from "cut off"

The client writes a final JSONL object:

```json
{"type":"client_result","outcome":"ended_naturally|hung|hard_cap|rig_down|refused_existing|spawn_failed", ...}
```

| Outcome | Exit code | Boss handling |
| --- | --- | --- |
| `ended_naturally` | 0 | Cheap-verify, then accept or count a failure |
| `hung` | 1 | Failed attempt; keep the dirty tree; retry per the ladder |
| `hard_cap` | 2 | Must not occur in production (cap is off). If a test set a cap, do not treat this as a successful settle |
| `refused_existing` | 3 | Ask the user; do not kill their session |
| `rig_down` | 4 | Mark the row `BLOCKED`, stop the run |
| `spawn_failed` | 5 | Do not retry blindly; record the detail and stop or ask |

`agent_end` is not settle. Pi may retry, compact, or run a queued follow-up (the review bot injects on `agent_settled`). The client waits for stream idle after `agent_settled` so a wrap-up cycle is not cut off.

## 6. Launch hygiene

- Spawn `cli.js` through node directly, never the `.cmd` shim.
- `stdio: ['pipe','pipe','pipe']` so a parent pipe cannot block the child. RPC stdin stays open for `prompt` / `abort` / cancelled extension-UI responses; it is not inherited from the Boss.
- `windowsHide: true` so an unattended run does not pop a console.
- Working directory is the **target repository**, not this plugin.
- Parse stdout with a byte buffer split on `\n` only (strip a trailing `\r`). Node `readline` is not protocol-compliant.

Unattended extension UI: dialog methods (`select`, `confirm`, `input`, `editor`) would block the worker forever. The client auto-cancels them. Fire-and-forget `notify` / `setStatus` / `setWidget` are logged as events and otherwise ignored.

## 7. Session teardown at every story boundary

Close the pi process before the next dispatch, including after a cheap-verify fail that will retry. One story, one session. A session that survives into the next story contaminates context and makes "exactly one pi process" unenforceable.

Teardown order: send `abort` if needed, then kill the process tree (`taskkill /T /F` on Windows). Do not leave orphans.

## 8. Rig down is `BLOCKED`, not a pause

When the client reports `rig_down`:

- Write the row `BLOCKED` with the probe evidence in `logs/`.
- Do not dispatch the next story. The hardware is gone; continuing is thrashing.
- Stop the run. `--resume` later is how it continues, after a human has a rig again.

Silence plus a reachable endpoint is not rig-down. That is either thinking, a hang, or a consult. See the table in §3.

## 9. Never kill the user's own pi session

`--list-sessions` first. If a session exists that this run did not spawn, ask. The operator's interactive TUI is not the worker, and killing it to "clear the way" is forbidden.
