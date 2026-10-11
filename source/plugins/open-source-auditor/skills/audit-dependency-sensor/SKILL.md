---
name: audit-dependency-sensor
description: Use when asked to run the dependency sensor in an explicitly requested publication audit. Requires an explicit target repository and report folder.
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.2"
  owner: Jarryd Adaens
  stage: audit-mode-sensor
---

# Audit — Dependency Sensor

Dependency, vulnerability, and **license-compatibility** risk — the last one is
critical now that everything ships Apache 2.0. A GPL/AGPL dependency in an
Apache repo is a Critical finding.

## Required arguments & paths

Invocation: `<target-repo> <report-folder> [run-timestamp]`

- `REPO` — absolute path of the ONE repo being audited.
- `report-folder` — absolute path where `open-source-audit-report-<repo-name>/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- `run-timestamp` — the shared `YYYY-MM-DD_HHMM` stamp when part of a
  persona-led run; mint a fresh one standalone. Never overwrite an earlier run.

Derived: `RUN = <report-folder>/open-source-audit-report-<repo-name>/<run-timestamp>`,
`OUT = RUN/audit-dependency-sensor`, `RAW = OUT/raw`. Config lives in
`<report-folder>/open-source-audit-report-<repo-name>/audit-config/`. `LIB` = the
`audit-lib/` folder at this plugin's root (`../../audit-lib` relative to this
SKILL.md).

## Contract

- **Read-only on the target repo.** All output goes only inside `OUT`.

## Tools & invocations

1. **syft** — generate the SBOM:
   ```bash
   syft "$REPO" -o cyclonedx-json="$RAW/syft-sbom.json"
   ```
2. **grype** — scan the SBOM for known vulnerabilities:
   ```bash
   grype "sbom:$RAW/syft-sbom.json" -o json > "$RAW/grype.json"
   ```
3. **trivy** — multi-tool second pass (vuln + secret + misconfig + license); the
   secret/misconfig overlap with the secrets sensor is by design:
   ```bash
   trivy fs "$REPO" --scanners vuln,secret,misconfig,license \
     --license-full --format json --output "$RAW/trivy.json" \
     --skip-dirs .git
   ```

## License compatibility check

From the SBOM + trivy license output, classify every dependency license and
write `raw/license-check.json`:

- **Pass:** MIT, BSD, Apache-2.0 and equivalents.
- **Critical (blocks):** GPL / AGPL family — viral copyleft in an Apache repo.
- **Informational (not blocking):** weak copyleft (MPL / LGPL) — note the
  per-file / per-library boundary rather than blocking.
- **Flag:** unknown or unresolved license — needs a human decision.

## Output

`raw/syft-sbom.json`, `raw/grype.json`, `raw/trivy.json`,
`raw/license-check.json`, then normalize
(`uv run "$LIB/normalize.py" "$REPO" "$RAW" "$OUT/normalized"`). The SBOM also
feeds `audit-license-apply` for required NOTICE attributions.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.

## Evidence envelope

After preserving raw tool output and successful normalization, write
`sensor-result.json` with the packaged `audit-lib/sensor-result.py`. Record the
required tool statuses, raw and normalized artifact hashes, and coverage status.
Missing tools or malformed results remain incomplete, never a clean result.
