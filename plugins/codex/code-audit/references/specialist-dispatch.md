# Specialist dispatch in Codex

The nine files below are review procedures bundled with the skill. They are not auto-discovered custom agent registrations. Use an available general-purpose/read-heavy Codex subagent and put the relevant procedure in its task packet. Do not request a nonexistent `code-audit-*` native agent type or install project/global agent definitions as part of an audit.

| Frozen capability or purpose | Procedure |
| --- | --- |
| correctness | [Correctness](specialists/correctness.md) |
| test-adequacy | [Test adequacy](specialists/test-adequacy.md) |
| security | [Security](specialists/security.md) |
| duplication-reuse | [Duplication and reuse](specialists/duplication-reuse.md) |
| architecture | [Architecture](specialists/architecture.md) |
| platform | [Platform](specialists/platform.md) |
| cross-cutting | [Cross-cutting review](specialists/cross-cutting.md) |
| Independent challenge of blockers/consolidation | [Verifier](specialists/verifier.md) |
| Attributed process observations | [Process efficiency](specialists/process-efficiency.md) |

For each assigned review provide:

- Run/task ID, actual reviewer-instance identity and expected receipt contract.
- H/B/M/A/I, actual immutable snapshot directories, assigned paths and behavioral units.
- Available intent, architectural constraints and explicitly missing requirements.
- The selected procedure and absolute path to this package's `references/contracts.md`; platform/process references only when applicable.
- Selected sanitized evidence references/digests plus instructions to retrieve surrounding definitions, callers, tests, bindings and contracts.
- Read-only source scope, actual inherited permission limits and a requirement to return JSON/notes to the orchestrator instead of editing product code or policy.

Use the host's existing model/reasoning configuration. Do not equate labels across providers or claim a configured alias establishes the actual executing model. Record known provider/model/version/settings and explicitly unknown values. Start reviews independently before sharing others' conclusions. Serial dispatch is the default; parallel work requires measured resource headroom and the actual host's limits.

The orchestrator retains sanitized notes with `add-evidence`, then includes returned references and actual coverage in `import-review`. Checkpoint partial work; aggregate work-unit receipts only when all assigned paths have been inspected. The frozen required-role plan does not shrink because a reviewer is unavailable.

A verifier is a fresh instance, distinct from the originating reviewer. Give it the claim, exact source/contracts and evidence, with an instruction to look for counterexamples. It may uphold, refute or leave the claim unresolved. Do not fabricate a fresh identity by relabeling the same agent. If the host cannot delegate, direct review remains useful, but independent verification requires another actual session/reviewer and associated receipts. Unsupported or incomplete review cannot be converted to `READY` by descriptive prose.

Codex permissions remain inherited from the parent. Procedure text is not sandbox enforcement. If stronger isolation is needed, use the existing approved session/CI host; this package does not create or weaken a permission profile.
