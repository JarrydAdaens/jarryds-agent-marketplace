---
name: audit-publish-guardrail
description: >-
  The enforcing + reasoning half of the open-source pre-publication audit. Use
  after the sensors have run to triage raw/normalized findings into true positives
  vs. noise, assign severity from config policy (not vibes), and emit
  audit-report.md ending in a machine-readable PASS/BLOCK verdict. Finds nothing
  itself — it judges what the sensors found. BLOCK on any unresolved Critical is
  non-overridable except by a recorded human waiver. Triggers: "triage the audit
  findings", "write the audit report", "is this repo safe to publish", "give me
  the publish verdict".
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: guardrail
---

# Audit — Publish Guardrail

The enforcing half and the AI reasoning layer. It **finds nothing itself**. It
consumes `raw/` + `normalized/` from the sensors and does three things.

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

Severity comes from `context/audit-config/global.json` → `severityPolicy`, never
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

Write `audit-report.md` in the run folder: prioritized findings, each with
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

The report lands beside the existing appraisal reports and follows their shape —
it is another report type in `context/reports/`.
