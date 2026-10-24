---
name: code-audit-codex
description: Standalone Codex port of the committed Code Audit 1.0 Claude package.
metadata:
  version: "1.0"
---

# Code Audit for Codex

Status: Complete
Authority: After local Claude commit `3b6ff33`, the user requested the Codex version. Preserve the standalone requirement. Following the implementation handoff, the user explicitly authorized a local commit through `commit-log --commit`. No push is authorized.

## Outcome and scope

Add `plugins/codex/code-audit`, version 1.0.0, and its Codex catalog entry. Copy the committed standalone controller, configuration, evidence contracts, license and behavioral tests into the package. Author Codex-specific skill, review-procedure references and README. No runtime dependency on the Claude package, installed caches, source generator, Agentic Rails or an external service.

OpenAI's current documentation supports this repository's `.codex-plugin/plugin.json` compatibility layout and recommends converting Claude agent procedures into skill content. Bundle nine role references; dispatch the appropriate reference to an available general-purpose Codex subagent rather than pretending Markdown files register custom Codex agents. Permissions remain host-enforced and inherited. No project/global agent installation, hardcoded model, Claude environment expansion or synthetic claim of independent verification.

## Steps and acceptance

1. Create self-contained Codex payload with native name/version/description/skills manifest and local catalog source.
2. Adapt entry point, role dispatch, private paths, checkpointing and host-specific documentation. Keep controller behavior equivalent and unsupported telemetry explicitly partial.
3. Add package/cross-host parity, contained-reference, exported-runtime and resume-isolation regressions. Run all controller fixtures against the Codex copy.
4. Run repository checks, supported skill validation and native Codex catalog discovery using an isolated disposable profile with no model calls or installed-user configuration changes.
5. Record evidence, known baseline failures, trial limits and final Git status. Leave this implementation uncommitted unless separately requested.

## Decisions and limits

- Preserve the native Codex compatibility manifest required by this repository. Do not add a Claude or Cursor manifest to the Codex folder.
- The Codex skill stores its argument hint in metadata and its input section because the generic Codex skill schema does not accept Claude's top-level `argument-hint`.
- Keep controller modules/scripts/configuration byte-identical between these initial host versions; add a focused parity check rather than enrolling this family in the existing all-host generator.
- Existing Oracle-compatible Claude usage receipts remain supported. Unvalidated native Codex log/counter formats remain unknown/partial; porting the plugin does not establish a new telemetry schema. Attributed process observations and hypothesis exports remain usable.
- Native discovery is distinct from installed model-driven activation. No live project trial, model invocation, new durable runner, product repair, publication or push is included.
- The full repository check previously failed on twelve unchanged generated-package receipts whose source revision predates the repository HEAD. Preserve and report that baseline rather than regenerating unrelated packages.

## Evidence and execution record

- Verified clean starting tree at Claude commit `3b6ff33`.
- Read repository instructions, native Codex package examples, controller/test contracts, skill-creator and OpenAI Docs guidance.
- Fetched official OpenAI plugin packaging, Claude-porting, skill and subagent documentation. Local Codex CLI 0.164.0 exposes plugin list/marketplace commands but no `plugin validate` command.
- Added the native versioned manifest/catalog entry, Codex skill, nine contained role procedures, dispatch reference and host-specific documentation. Controller modules, scripts, example configuration, license and behavioral suite remain byte-identical to Claude's initial release. The committed Claude package was not edited.
- Codex skill-creator validation passed. Five package tests passed, covering manifest/catalog ownership, core parity, contained references/role roster, a standalone exported controller under Python `-S`, cross-host resume rejection and honest unknown/partial Codex usage imports.
- Full `python scripts/check.py` completed. Claude controller: **27 tests passed in 136.429 seconds**. Codex controller: **27 tests passed in 131.811 seconds**, including native Gitleaks history/current-tree/redaction, source-backed defects, integration/conflict/custom-driver behavior, explicit ranges, malformed/partial evidence, freshness, cancellation/resume, HTML safety, process accounting and hypothesis separation.
- All other functional suites passed: eleven root package tests (including five new Codex tests), 31 Savior tests, four screenshot tests, 42 Oracle JavaScript tests, 13 statistics tests and 14 appraisal tests plus three subtests. Native Claude catalog/package validation and `git diff --check` passed; intentional missing-Claude-version warnings remain unchanged.
- Native Codex CLI **0.164.0** registered this local marketplace in a disposable child profile and discovered **code-audit@jarryds-agents 1.0.0** at the actual Codex directory, uninstalled and disabled. Added `scripts/check-code-audit-codex.py` to repeat that check through the repository entry point. The profile was removed; no model invocation or user-profile installation occurred. Confirmed supported install syntax through the installed CLI's help.
- The full repository entry point exits nonzero only for the pre-existing twelve generated-package receipt mismatches and their `test_payload_parity` assertion. Those receipts are untouched; no unrelated packages were regenerated to hide the baseline failure.
- Final changed-file scope: Codex package/catalog, shared repository instructions/README, check integration, package tests, native catalog-check helper and this plan. No Cursor package, installed-cache edit or product-code repair was performed. The implementation was left uncommitted at handoff; the user subsequently requested a local commit. No push was performed.

## Completion and trial limits

The Codex package is complete for a personal-project trial. Installed model-driven skill activation, actual specialist dispatch on a real project, project-specific CI/device evidence and durable-host attachment remain rollout checks. The package preserves independent-verifier requirements and cannot invent an independent reviewer when delegation is unavailable. Native Codex session/token formats remain unvalidated and explicitly partial/unknown; attributed process observations and hypothesis exports are still supported. No missing external integration is represented as passing coverage.
