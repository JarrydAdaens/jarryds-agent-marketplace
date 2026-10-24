# Code Audit 1.0

A standalone Claude Code plugin for thorough, evidence-backed review of committed changesets before integration. It combines specialist review with a Python controller that pins Git scope, tracks coverage, validates evidence, computes readiness and writes private reports.

No Agentic Rails framework, companion marketplace plugin, database or service is required. Copy this entire directory to vendor it elsewhere. Preserve LICENSE and record the upstream revision plus your modifications for an internal implementation.

## Install and invoke

From the marketplace:

```text
/plugin install code-audit@jarryds-agents
/code-audit:code-audit feature/example --repo /path/to/project --base origin/develop --output-root /private/audits
```

For a disposable local Claude profile, launch Claude Code with `--plugin-dir /path/to/code-audit`, then invoke the namespaced skill. Native discovery depends on the installed Claude version; validation and repository fixtures do not establish live activation.

The output root is mandatory and must be outside the source checkout. Provide the actual target branch; it is never guessed. Use `--config` only for explicitly trusted policy. GitHub PR input uses installed/authenticated `gh` and already-provisioned local commits. Source edits outside commits are excluded and reported.

## What ships

- `/code-audit` skill and nine native agents: correctness, test adequacy, security, duplication/reuse, architecture, platform, cross-cutting, independent verification and process efficiency.
- Standard-library Python controller with frozen H/B/M/I scope, isolated snapshots/candidates, task attempts, strict parsers, evidence hashes, serial owned processes, timeout/retry budgets and resumable checkpoints.
- Typed JSON, JSONL, SARIF, CPD XML and redacted Gitleaks adapters; pre-provisioned Gitleaks execution and exact-build CI/runtime import contracts.
- Portable Markdown and self-contained escaped HTML reports, machine-readable coverage/findings/verdicts, and historical report revisions.
- Oracle-compatible process receipt ingestion and immutable hypothesis ZIPs, with separate candidate exports that withhold evaluator/reference files.
- Configuration example, portable contracts and deterministic regression fixtures.

The controller computes `CHANGES_REQUIRED` for established blockers or merge conflict, `INCOMPLETE` for missing required evidence/investigations/stale inputs, and `READY` only for completed current coverage. Scan-only or deliberately limited review cannot be ready. Missing process logs remain separate from product coverage. A ready audit is not proof of defect absence.

## Prerequisites and configuration

Python **3.11+**, Git and Claude Code. The controller itself needs no third-party Python dependencies. Full YAML optionally uses pre-provisioned PyYAML; the supplied JSON-compatible `.yml` works without it. Provision external tools and exact versions before starting. `gh`, Windows SDKs, UWP build tools, dependency/advisory scanners and device harnesses are needed only for their selected integrations.

Copy `config/example.code-audit.yml` to a trusted private machine/project policy, set the actual target and requirements, and supply it with `--config`. No tools are silently installed. The example intentionally contains no executable paths: absent required evidence produces `INCOMPLETE`.

For local Gitleaks, add a `sensors.secrets` object in private configuration:

```json
{
  "executable": "/absolute/path/to/gitleaks",
  "version": "EXACT OUTPUT OF THE PROVISIONED VERSION COMMAND",
  "version_args": ["version"],
  "adapter": "gitleaks-json",
  "rules_file": "/private/pinned-rules/gitleaks.toml",
  "isolation": "approved-local-disposable",
  "completed_exit_codes": [0, 1]
}
```

Pin rules outside the proposed checkout; branch `.gitleaks.toml` or inline allow comments must not weaken the judging policy. A trusted rules file may extend the installed tool's built-in defaults. The controller scans the introduced history and current tree with native redaction. No live credential verification. Raw diagnostic files stay private; sanitize excerpts before sharing with a model.

Commands and detailed receipt examples are in [workflow](references/workflow.md), [evidence contracts](references/contracts.md), [platform/runtime](references/platform-runtime.md) and [process/hypotheses](references/process-hypotheses.md). The CLI also supplies `--help`.

## Execution and limitations

The skill orchestrates Claude specialists; the controller does not call a model or replace their behavioral judgment. An existing durable agent/CI host must own unattended lifetime. Checkpoints survive interruption; a prompt alone does not keep a session running. Windows scanners use Job Objects; POSIX uses process groups and requires the existing sandbox to prevent deliberate escape. Configure approved disposable execution, private destination permissions and external-access policy on the consuming machine. Source builds, restores and analyzers can execute code; they do not run in the developer checkout.

1.0 supports ordinary Git merge candidates and committed branch/net-range review. Uncommitted/selected-commit snapshots, custom merge strategies, automatic cross-run caching, risk-waiver authority, direct device control, live host-log collection, experiment execution, model-routing promotion, PR posting and product repair are outside this version. These are explicit limits, not silently completed checks. The primary structural duplication tool remains a deployment choice after representative C# validation; repository search/reuse review works immediately. Imported external evidence is validated for scope/integrity, not cryptographically attested by the plugin.

Retain evidence under your host's private-storage and retention policy; 1.0 does not delete old runs automatically. Every consumer must recheck freshness before using readiness. Runtime evidence must identify the exact integration build and remain under the existing harness's device ownership/failure rules. Candidate/evaluator separation is enforced by exports; the later experiment harness must restrict filesystem access and reviewers must check semantic answer leakage.

## Validation and trial

```text
python -m unittest discover -s plugins/claude/code-audit/tests -v
claude plugin validate plugins/claude/code-audit
python scripts/check.py
```

Run those from the marketplace root; a vendored package can run `python -m unittest discover -s tests -v` inside its own directory. Fixtures exercise scope, incomplete evidence, seeded source-backed defects, merge conflict, stale reports, typed adapters, process ownership, tamper detection, receipt accounting and package separation. Trial independently assessed real changes and clean cases before relying on the plugin. Live installed activation and consuming CI/device compatibility require rollout verification on that machine.

Claude manifests deliberately omit `version` under this marketplace's commit-based policy. The controller, skill metadata and protocol record release **1.0.0** / schema **1**.
