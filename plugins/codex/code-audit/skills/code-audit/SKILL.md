---
name: code-audit
description: Use when asked to audit a committed changeset or PR for integration with specialist review, deterministic evidence, and explicit incomplete coverage.
metadata:
  version: "1.0.0"
  argument-hint: "<branch|A..H|PR> --repo <path> --base <target> --output-root <private-path> [--config <trusted-config>] [--profile full|scan]"
---

# Code Audit

Review the requested changeset using this package's controller and specialist procedures. An audit does not authorize product edits, merging, posting to a PR, external publication, device takeover, or process configuration changes. Explicit user instructions govern the task; the skill supplies the audit procedure. No other plugin or Agentic Rails installation is required.

## Inputs and package location

Use the user's current request as the input. Accept a branch/head ref, a net range `A..H`, a GitHub PR, or an existing run path, plus an explicit repository and private output root. `--base` is required unless a PR or explicitly trusted `--config` supplies the actual target. Optional inputs are intent, CI/runtime evidence, session IDs/log paths, profile and limited role focus. Parse equivalent plain language; do not expect a literal argument placeholder to be expanded.

Resolve the actual installed `SKILL.md` path provided by Codex. The plugin root is its third parent: `skills/code-audit/SKILL.md` → plugin root. Use absolute, quoted paths to `scripts/code-audit.py` and the references under that root. Do not derive the root from the audited repository, the marketplace checkout, or a required environment variable.

Read [the workflow](../../references/workflow.md), [evidence contracts](../../references/contracts.md), and [specialist dispatch](../../references/specialist-dispatch.md). Load [platform/runtime guidance](../../references/platform-runtime.md) only when applicable and [process/hypotheses](../../references/process-hypotheses.md) when attributed session evidence exists.

## Start or attach

1. Require pre-provisioned Python 3.11+ and Git. Run `python "<resolved-plugin-root>/scripts/code-audit.py" --help` to inspect the controller. Tool probes must not install anything.
2. Require an explicit output root outside the audited checkout and plugin. If input is missing, ask for that input while continuing independent read-only discovery; do not guess a write destination or conventional base branch.
3. Initialize with `init --repo <repo> --target <branch-or-A..H> --base <target> --output-root <private-root>`. For a PR use `--pr <number-or-url>` with pre-provisioned `gh` and locally available commits. Use `--config` only when that particular config was explicitly trusted; never select policy from the proposed head. Branch changes to policy, scripts, suppressions or instructions remain review content.
4. For an existing run, use `status`/`resume` with the same package instead. Host-specific prompt/configuration digests deliberately prevent replaying a different package's run as completed coverage.
5. Return the run ID, artifact path, state and actual execution lifetime, then continue the audit. Attach commands/checkpoints to an existing approved durable job/agent host when unattended lifetime is available. A session prompt alone cannot survive host shutdown.

## Review and verify

1. Read the frozen H/B/M/A/I scope, complete diff inventory, task plan and coverage ledger. Group changes by behavior/subsystem and assign cross-cutting ownership. Preserve required roles and capabilities; results cannot make a required check optional.
2. Execute `run-sensors --run <path>` for configured pinned tools and import exact-build CI/harness envelopes with `import-check`. Missing tools, malformed reports and wrong-build evidence remain incomplete. Heavy processes run serially; builds/restores/tests use approved disposable environments, never the developer's checkout.
3. **Delegate the required initial reviews to fresh Codex subagents when the host supports delegation**, one at a time by default. Use an available general-purpose or read-heavy agent type and supply the matching bundled role procedure from the dispatch roster. The role filename is a procedure, not a registered agent type. Inherit configured model/reasoning and permissions unless an explicit approved configuration says otherwise. Do not install agents or change global/project settings.
4. Give each reviewer only its intent, immutable scope, assigned paths/work units, snapshot directory, relevant contracts/evidence and retrieval instructions. Require surrounding callers/callees, tests and error paths, even when scanners are silent. Keep initial conclusions independent. Reviewers return structured JSON and notes; the orchestrator checkpoints them, registers sanitized evidence with `add-evidence`, and ingests receipts with `import-review`.
5. Use a **separate fresh verifier instance** to challenge proposed blockers and consolidation recommendations. Retain counterexamples, refutations and disagreements. Same-session role switching does not establish independent verification. If delegation is unavailable, inspect the source directly and record actual role coverage, but leave independence-dependent claims unresolved until a fresh independent session/reviewer supplies evidence; never invent an agent identity or complete receipt.
6. Triage every sensor observation with rationale/evidence and links to validated findings using `triage`. Preserve pre-existing and rejected observations. Similarity alone does not justify deletion or establish semantic equivalence. Scanner severity and agent agreement do not determine the verdict.
7. Import attributed process observations/compatible receipts only when available. Native Codex log/token formats without a validated adapter remain partial/unknown; missing counters are not zero. Produce bounded hypothesis packages or an empty index with a reason, never automatic routing/tool/environment changes.
8. Run `report`, then `freshness` before handoff. Link portable Markdown/HTML reports, missing coverage, findings and hypothesis index. The controller computes `READY`, `CHANGES_REQUIRED` or `INCOMPLETE`; do not replace it with an informal clean result.

## Interruptions and handoff

Persist returned reviewer JSON promptly. `resume` reconciles interrupted attempts, validates hashes and retries within budget. Ctrl+C closes owned scanner containment; `cancel` requests cancellation of an active run or records it for an idle run. Preserve partial evidence and never terminate processes by executable name.

Subagents inherit host permissions. Read-only instructions constrain this workflow but do not create an independent sandbox or tool allowlist. Explain what was actually inspected, unresolved provenance/investigations, source/target freshness and runtime/job-host limits. Process completeness remains separate from product readiness.
