---
name: request-repository-audit
description: >-
  Use when requesting and consuming the mandatory pre-publication security
  audit of a converted Git repository's complete history — secrets, keys,
  connection strings, personal data, proprietary third-party material,
  large binaries, licensing, dangerous scripts. Only an audit result of
  "pass" permits publication; a private destination is never remediation.
  Writes only into the user-specified migration root and refuses to run
  without one. Triggers: "audit the converted repo", "run the
  pre-publication audit", "is this history safe to push".
argument-hint: <migration-root> <repository-id>
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: migration-pipeline
---

# Request Repository Audit

The auditor is a **separate agent** from Repository Savior. This skill
hands it the converted repository, consumes its structured result, and
gates publication on it. A private GitHub repository is still an external
copy — the audit happens before any remote exists.

## Required arguments & paths

Invocation: `<migration-root> <repository-id>`

**Required: if the migration root was not explicitly provided, STOP and
ask — never guess or default.** Derived:
`WS = <migration-root>/workspace/<repository-id>`; state must be
`LOCAL_VERIFIED`.

## What the auditor receives

- converted repository path (`WS/converted.git`);
- complete Git history (all refs that will be pushed);
- source inventory and migration metadata (`WS/manifests/`);
- large-file inventory (`WS/manifests/publishability.json`);
- intended GitHub owner and repository name.

The recommended auditor is the `open-source-auditor` plugin from this
marketplace (invoke its persona with the converted repo and a report folder
inside `WS/`; its sensors cover secrets, provenance, and tone in full
history). Run audits **sequentially** — one repository at a time; never fan
out. Any auditor is acceptable if its result conforms to
`../../schemas/audit-result.schema.json` (relative to this SKILL.md).

## The audit must inspect at least

Secrets and credentials in all reachable history; private keys and
certificates; connection strings; passwords and tokens; personal or
customer information; proprietary third-party material; unexpectedly large
binaries; licensing concerns; dangerous build or deployment scripts.

## Consuming the result

Copy the structured result to
`<migration-root>/reports/<repository-name>.audit.json`. Allowed results:

- **`pass`** — transition `AUDIT_REQUESTED` → `AUDIT_PASSED`; publication
  may proceed.
- **`fail`** — a finding must be **remediated in the local Git conversion
  and re-audited**. Making the repository private is not remediation.
  Approved remediations that rewrite history send the repository back
  through `verify-local-conversion`.
- **`requires_human_decision`** — hold in `REQUIRES_HUMAN_DECISION`.

An auditor that is unavailable or returns a malformed result is a **stop**,
never a skipped gate.

## Handoff

Only from `AUDIT_PASSED` does the persona proceed to
`create-private-github-repository`.
