# Code Audit 1.0 for Codex

A standalone Codex plugin for evidence-backed review of committed changesets before integration. It packages the Code Audit 1.0 Python controller, a native Codex skill, nine specialist review procedures, private reports and process experiment exports. Copy this whole folder when vendoring; no Claude plugin, sibling source tree, Agentic Rails installation, database or service is required.

## Install and invoke

This repository's `.agents/plugins/marketplace.json` lists `code-audit` at `plugins/codex/code-audit`. Its native compatibility manifest is `.codex-plugin/plugin.json`, version **1.0.0**, with `skills: "./skills/"`.

For a local client exposing these commands (including Codex CLI 0.164.0), register the marketplace root and install the package:

```text
codex plugin marketplace add "/path/to/marketplace"
codex plugin add code-audit@jarryds-agents
```

You can also install from the registered source through the client's plugin UI. Inspect `codex plugin --help` on the consuming version; this package does not alter your installed profile automatically. With the plugin enabled, invoke the skill with a request such as:

```text
$code-audit feature/example --repo /path/to/project --base origin/develop --output-root /private/audits
```

An explicit private output root outside the source checkout is mandatory. Use the actual target branch, a PR target, or an explicitly trusted `--config`; a conventional branch is never guessed. The skill resolves helpers from its installed file path rather than requiring host-specific environment expansion.

OpenAI documents this compatibility manifest and local marketplace layout in [Package your plugin](https://developers.openai.com/plugins/build/plugins). Live activation and supported install surfaces depend on the consuming host version.

## Host adaptation

The plugin includes one Codex entry skill and nine procedures for correctness, test adequacy, security, duplication/reuse, architecture, platform, cross-cutting review, independent verification and process efficiency. The skill dispatches the selected procedure to an available general-purpose/read-heavy Codex subagent. Procedures are not magically registered custom agent types. No project/global agent installation, hardcoded model selection or capability escalation is required.

The orchestrator persists actual reviewer receipts and sanitized evidence. Subagents inherit the host's permissions; a read-only instruction is not a separate sandbox. A fresh verifier challenges blockers and consolidation. If delegation is unavailable, direct source review can continue, but independent verification remains unresolved until an actual independent session/reviewer provides evidence. The controller never substitutes a fictional reviewer identity for missing coverage.

This follows OpenAI's [Claude porting guidance](https://developers.openai.com/plugins/guides/submit-claude-plugin), which places reusable agent procedures in skills, and [subagent guidance](https://developers.openai.com/codex/subagents), which describes inherited permissions and available agent workflows.

## Controller and outputs

The bundled standard-library controller is equivalent to the initial Claude 1.0 controller and is copied into this package. Its frozen inputs include implementation, prompt, policy and source digests; start a new run when switching host packages rather than treating another package's checkpoints as validated coverage.

- Pins H (head), B (target), M (merge base), A (net-range base) and I (integration source/tree), retaining source snapshots and introduced history.
- Validates typed JSON/JSONL/SARIF/CPD/Gitleaks evidence, exact-build CI/runtime provenance, role coverage, findings and independent verification.
- Runs pinned sensors serially in disposable workspaces with owned process containment, timeout/attempt budgets, cancellation and checkpoints.
- Computes `CHANGES_REQUIRED`, `INCOMPLETE` or `READY`, with separate completion/freshness and historical reports.
- Writes portable Markdown and escaped self-contained HTML, machine-readable findings/coverage/verdicts and hypothesis indexes.
- Consumes attributed compatible process receipts/observations and creates evaluator-private hypothesis ZIPs plus separate candidate ZIPs.

Missing required evidence, stale refs, scan-only/limited review and unresolved blocking investigations cannot yield readiness. A ready audit is not proof of defect absence. Source-backed agent findings are allowed even without scanner observations.

## Prerequisites and configuration

Python **3.11+**, Git and a Codex client with skill support. The controller needs no third-party Python package; full YAML optionally uses pre-provisioned PyYAML, while `config/example.code-audit.yml` uses dependency-free JSON-compatible YAML. Provision exact tool versions, approved isolation, private output permissions and any required CI/device integrations before the run. GitHub PR resolution optionally uses already-installed/authenticated `gh`; it does not fetch missing commits automatically.

Copy the example into private trusted policy, select the actual target/required capabilities and configure installed tools or imported evidence. The required secrets/dependency baseline remains explicit; the example contains no machine paths or tool auto-installation. For Gitleaks, use an absolute `executable`, exact `version`, `version_args: ["version"]`, `adapter: "gitleaks-json"`, a private pinned `rules_file` outside the proposed checkout, `isolation: "approved-local-disposable"` and `completed_exit_codes: [0,1]`. It scans introduced history and the current tree with native redaction and rejects branch suppression attempts. No live credential verification is enabled.

See [workflow and commands](references/workflow.md), [evidence contracts](references/contracts.md), [specialist dispatch](references/specialist-dispatch.md), [platform/runtime](references/platform-runtime.md) and [process/hypotheses](references/process-hypotheses.md). Source scripts/builds can execute code: use the approved disposable/CI boundary, never the developer checkout.

## Telemetry and version limits

The initial controller supports already-normalized Oracle-compatible Claude usage receipts. A Codex port does not validate native Codex session-log schemas or cumulative token counters. Unsupported Codex/provider usage stays **partial/unknown**, not zero, a fabricated saving or an invoice. Explicitly attributed process observations and hypothesis packages remain usable without complete token accounting. The host's model/configuration identity must be recorded honestly.

Existing durable job/agent infrastructure owns unattended lifetime. A session prompt cannot keep the host running after shutdown. Windows scanners use Job Objects; POSIX process groups need existing sandbox enforcement against deliberate escape. Provision Windows private-root ACLs on the consuming host. Runtime checks use the existing governing harness and preserve exclusive device ownership and infrastructure/product failure distinctions.

1.0 does not add a daemon, device platform, experiment runner, native Codex log collector, automatic cross-run cache, risk-waiver authority, product repair, merge, PR posting or public publication. Ordinary Git merge candidates and committed branch/net ranges are supported; uncommitted/selected-commit snapshots and custom merge strategies require future validated adapters. Retention is host-managed; old evidence is not automatically deleted. A primary structural duplication scanner remains a deployment choice; repository-search reuse review works immediately.

## Validate and trial

From this marketplace root:

```text
python -m unittest discover -s plugins/codex/code-audit/tests -v
python scripts/check-code-audit-codex.py
python scripts/check.py
```

A vendored package runs its fixtures with `python -m unittest discover -s tests -v`. Repository checks verify native manifest/catalog fields, contained references, shared controller parity, exported execution and package-bound resume integrity. Native catalog discovery can use a disposable profile; it does not invoke a model or establish installed model-driven activation. Trial independently assessed regressions and clean changes in a fresh consuming session before relying on readiness.
