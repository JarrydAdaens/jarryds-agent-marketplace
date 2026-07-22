---
name: audit-publish-guardrail
description: >-
  The enforcing + reasoning half of the open-source pre-publication audit. Use
  after the sensors have run to triage raw/normalized findings into true positives
  vs. noise, assign severity from config policy (not vibes), and emit
  audit-report.md ending in a machine-readable PASS/BLOCK verdict, plus a
  self-contained audit-report.html at the run-folder root that ties every
  sensor's evidence together in one navigable page. Finds nothing itself — it
  judges what the sensors found. BLOCK on any unresolved Critical is
  non-overridable except by a recorded human waiver. Requires the user-specified
  report folder; refuses to run without one. Triggers: "triage the audit
  findings", "write the audit report", "is this repo safe to publish", "give me
  the publish verdict".
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.3"
  owner: Jarryd Adaens
  stage: guardrail
---

# Audit — Publish Guardrail

The enforcing half and the AI reasoning layer. It **finds nothing itself**. It
consumes `raw/` + `normalized/` from the sensors and does three things.

## Required arguments & paths

Invocation: `<target-repo> <report-folder> [run-timestamp]`

- `report-folder` — absolute path where `open-source-audit-report-<repo-name>/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- `run-timestamp` — which run to triage; defaults to the newest
  `<YYYY-MM-DD_HHMM>` folder under `<report-folder>/open-source-audit-report-<repo-name>/`.

Derived: `RUN = <report-folder>/open-source-audit-report-<repo-name>/<run-timestamp>`. Reads
every sensor's `RUN/<sensor-name>/raw|normalized`; writes only
`RUN/audit-publish-guardrail/audit-report.md`. Config comes from
`<report-folder>/open-source-audit-report-<repo-name>/audit-config/` (`global.json` +
`<repo-name>.json`).

## Standing Critical check — the report tree itself

Before triaging findings, check whether any of
`<report-folder>/open-source-audit-report-<repo-name>/` is **tracked by the target repo's
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

## 4. The durable HTML report (`RUN/audit-report.html`)

After `audit-report.md`, emit **one self-contained HTML file at the ROOT of the
run folder** — `RUN/audit-report.html` — built from
[references/html-report-template.html](references/html-report-template.html)
(copy its structure, styling, and hash-routing script; fill the placeholders;
delete the template comments). This is the run's durable, human-facing asset:
one file a reader opens to see the whole audit, with every claim linked to the
evidence that backs it.

Requirements:

- **Tabs across the top, pages beneath.** First tab is **Summary**: what was
  done, the verdict hero (PASS/BLOCK), severity count tiles, the findings
  overview table, and concrete **Next actions** — the same summary reported
  back to the orchestrator, made durable. Then one tab per skill folder that
  exists in the run (fixed sensor order, guardrail last).
- **Every skill gets a page even when clean.** A sensor with zero findings
  shows the professional all-clear block ("Nothing found — this check passed")
  with the scope it covered, never a blank page.
- **Every evidence artifact is linked**, relative to the run root (e.g.
  `audit-secrets-sensor/raw/gitleaks.json`), each with a one-line description.
  The report must hold up standalone: a reader can drill from any claim to the
  raw tool output that proves it.
- **Self-contained file** — inline CSS/JS only, no external assets, so it
  survives being moved, zipped, or emailed. Sibling timestamp folders each
  carry their own `audit-report.html`, so successive passes over a big repo
  can be opened side by side and compared.
