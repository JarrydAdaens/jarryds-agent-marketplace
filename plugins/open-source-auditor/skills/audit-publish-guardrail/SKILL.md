---
name: audit-publish-guardrail
description: >-
  The enforcing + reasoning half of the open-source pre-publication audit. Use
  after the sensors have run to triage raw/normalized findings into true positives
  vs. noise, assign severity from config policy (not vibes), and emit
  audit-report.md ending in a machine-readable PASS/BLOCK verdict. Finds nothing
  itself — it judges what the sensors found. BLOCK on any unresolved Critical is
  non-overridable except by a recorded human waiver. Requires the user-specified
  report folder; refuses to run without one. Triggers: "triage the audit
  findings", "write the audit report", "is this repo safe to publish", "give me
  the publish verdict".
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: guardrail
---

# Audit — Publish Guardrail

The enforcing half and the AI reasoning layer. It **finds nothing itself**. It
consumes `raw/` + `normalized/` from the sensors and does three things.

## Required arguments & paths

Invocation: `<target-repo> <report-folder> [run-timestamp]`

- `report-folder` — absolute path where `open-source-audit-report/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- `run-timestamp` — which run to triage; defaults to the newest
  `<YYYY-MM-DD_HHMM>` folder under `<report-folder>/open-source-audit-report/`.

Derived: `RUN = <report-folder>/open-source-audit-report/<run-timestamp>`. Reads
every sensor's `RUN/<sensor-name>/raw|normalized`; writes only
`RUN/audit-publish-guardrail/audit-report.md`. Config comes from
`<report-folder>/open-source-audit-report/audit-config/` (`global.json` +
`<repo-name>.json`).

## Standing Critical check — the report tree itself

Before triaging findings, check whether any of
`<report-folder>/open-source-audit-report/` is **tracked by the target repo's
git** (`git -C "$REPO" ls-files "<path>"`). The report tree contains the very
findings the audit exists to catch (secret locations, names, venting quotes)
and the personal `audit-config/` watchlists; if any of it is tracked, raise a
**Critical** finding — it must be untracked, ignored, or deleted before publish.

## 1. Triage — true positive vs. noise

Every finding is judged with cited evidence:

- A gitleaks hit on a fake key in a test fixture **allowlisted in the repo
  config** is noise (cite the allowlist entry: path + fingerprint). A real-looking
  token in a months-old commit is Critical.
- A hardcoded `localhost` is fine; an internal company hostname is not.
- Quoted profanity in a reference doc is noise; venting at a named colleague in
  a commit message is a fix.

If a finding cannot be traced to a `raw/` artifact, it does not go in the report.

## 2. Severity in context (policy is data)

Severity comes from `audit-config/global.json` → `severityPolicy`, never
from intuition. See `references/severity-rubric.md` for the category → tier map
and the meaning of each tier:

- **Critical** — blocks publish: live secrets, company identity in history,
  copyleft dependency in an Apache repo, colleague-directed venting.
- **High** — fix before publish: dead secrets in history, profanity in commit
  messages, broken README claims.
- **Medium** — should fix: dead code, dead links, typos, known vulnerabilities.
- **Low / Info** — note: TODO census, undocumented-but-harmless branches.

The guardrail may move a finding within policy **only with cited evidence**
(e.g. an allowlist downgrades; a confirmed live credential upgrades).

## 3. Report + verdict

Write `RUN/audit-publish-guardrail/audit-report.md`: prioritized findings, each with
file, line, evidence snippet, why it is a red flag, and the concrete fix. End
with a machine-readable verdict block:

```yaml
verdict: PASS | BLOCK
blocking_finding_ids: [ ... ]   # empty on PASS
critical_count: N
high_count: N
generated_from:
  raw: <path>
  normalized: <path>
  toolVersions: <snapshot>
```

**BLOCK while any Critical finding is unresolved is non-negotiable and not
overridable by the persona.** Only the human waives a finding, and waivers are
recorded in the per-repo config (`waivers.entries`) with a reason. The verdict
is the validator; the prose is the reasoning.
