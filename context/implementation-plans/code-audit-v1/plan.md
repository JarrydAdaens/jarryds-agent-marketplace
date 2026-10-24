---
name: code-audit-v1
description: Standalone Claude Code changeset audit plugin implementation and validation.
metadata:
  version: "1.0"
---

# Code Audit 1.0

Status: Complete
Authority: User supplied revised Code Audit design on October 24, 2026 and requested implementation, standalone, Claude first; personal project trials follow delivery. No commit, deployment, or audit of a personal project was requested.

## Outcome and boundaries

Add `plugins/claude/code-audit` and its Claude catalog entry only. This new Claude-only family is authored directly in its self-contained package; existing generated families are unchanged. Include a portable deterministic Python controller, native skill and specialist prompts, trusted configuration example, contracts, and meaningful regression fixtures. Version the component and protocol as 1.0; omit Claude manifest version under repository policy.

The supplied design is the authority, not a source of company-specific policy. Do not publish its company context or embed machine paths. Preserve read-only source review, explicit output destinations, immutable scope, fail-closed coverage/verdicts, source-backed agent findings, evidence integrity, serial owned processes, resume, exact-build CI/runtime imports, process observations and hypothesis packages. External scanners and job/device hosts are provisioned integrations, not bundled commercial tools or invented infrastructure. Unsupported capabilities must remain visibly incomplete.

## Delivery steps

1. Implement pinned Git scope/snapshots, trusted policy loading and frozen task/coverage plans.
2. Implement typed adapters, evidence ingestion, findings/verification, serial owned process execution, checkpoint/resume and freshness checks.
3. Implement deterministic reports/verdicts, attributed process receipts and separate candidate/evaluator hypothesis exports.
4. Add Claude skill, specialist roles, configuration/contracts/portability instructions and catalog/README/check integration.
5. Run behavioral fixtures, repository suite and native Claude validation. Inspect final diff and record limitations.

## Acceptance and recovery

Use temporary Git repositories and exported standalone packages to test wrong/missing base, target/head movement, rename matching, removed historical secrets, malformed adapters, scanner exit codes, missing tools, CI build mismatch, task interruption, hostile HTML, source-backed findings, unsafe consolidation, incomplete coverage and hypothesis separation. Source working trees must stay unchanged. Run `python scripts/check.py`, native `claude plugin validate` and package tests. Keep all new files uncommitted. Recover by removing this new package and its catalog/documentation integration; no product code or installed copies are edited.

## Decisions and uncertainty

- Runtime host and external device platform remain unspecified. Persist controller checkpoints and document an existing-job-host command contract; session-only execution cannot promise survival after Claude exits.
- No automatic cross-run cache reuse in 1.0: repeated runs execute again; resume reuses validated attempt records within the identical frozen run only. This avoids unsafe cache equivalence claims.
- The primary secrets integration is pinned, pre-provisioned Gitleaks with native redaction. Other CI/sensor evidence uses explicit typed adapters and provenance envelopes.
- JSON is accepted as a YAML-compatible configuration subset without dependencies; full YAML uses pre-provisioned PyYAML if available.
- No broad model routing, device management, experiment runner, repair, merge, public posting, or Codex plugin.

## Evidence and execution record

- Read repository AGENTS, package generator, checks, design sections and native Claude plugin/subagent references. Existing repository clean at start.
- Implemented the standalone Claude package, thin skill, nine read-only specialists, deterministic controller, direct Git-blob snapshots (resistant to export-ignore/export-subst), isolated integration, strict adapters/baseline comparisons, exact-build imports, serial Windows Job Object execution, cancellation/resume, evidence-backed verdicts, historical Markdown/HTML reports, Oracle-compatible receipt ingestion and separated hypothesis exports.
- Exported package fixture runs with Python `-S`, without marketplace/runtime Python dependencies. Native Gitleaks 8.30.1 fixture passed, detecting removed/current synthetic markers despite branch inline allow/ignore attempts; native redacted evidence retained.
- Claude Code 2.1.226 validates the package and catalog. Warnings about absent Claude manifest versions are intentional under repository policy. All ten native frontmatters parse with unique names and skill version 1.0.0. The generic Codex quick validator rejects Claude's required `argument-hint` field; it is not the owning-host validator and the valid Claude field remains present.
- Full repository check finished with one pre-existing class of failure: receipt drift in the twelve generated packages (also reported by `test_payload_parity`). Validation baseline HEAD was `46ec87c5b73fb1ffd454bc83e293492a9b53520f`, while existing receipts name baseline `92154517cbca4c1656e922bfa3c46e510297f47d`. These tracked receipts are unchanged by this work; unrelated Codex/Cursor packages were not regenerated. All other repository checks passed: six remaining package tests, 31 Savior tests, four screenshot tests, 42 Oracle JavaScript tests, 13 statistics tests, 14 appraisal tests plus three subtests, native Claude catalog/package validation and `git diff --check`.
- Final standalone regression run: **27 tests passed in 122.098 seconds**, including native Gitleaks 8.30.1, exact integration and conflict behavior, immutable explicit-range A snapshots, target-policy resolution races, custom-driver refusal, malformed/partial evidence, stale report retention, source-backed seeded defects, cancellation/resume, HTML injection resistance, process accounting, baseline advisory deltas and evaluator/candidate separation. Exported controller runs with Python `-S`. Windows Git clone requires permission to run its local transport helper; fixtures passed outside the restrictive application sandbox without changing product source.
- Verified Claude-only catalog/manifest scope and reviewed the final changed-file set. The new family is directly authored under its Claude package; no Codex or Cursor catalog/package was added or modified. Changes were left uncommitted at implementation handoff.
- The user subsequently invoked `commit-log --commit`, authorizing a local commit of this implementation and its documentation, with the disclosed pre-existing receipt failure recorded. No push is authorized by that invocation.

## Completion and rollout limits

Implementation is complete for a personal-project trial. Actual Claude model-driven review/discovery, project-specific CI/build envelopes, device harness compatibility, approved output ACLs and durable job-host attachment remain rollout checks on the consuming machine. This work did not run a live personal-project audit, invoke a model, modify installed caches, commit, publish or configure external services. Structural duplication-tool adoption, uncommitted/selected-commit snapshots, nonstandard merge strategies, automatic cross-run caches, risk-waiver authority and a downstream experiment runner remain explicit documented version limits. No unavailable integration is represented as passing evidence.
