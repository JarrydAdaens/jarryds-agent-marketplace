---
name: audit-dependency-sensor
description: >-
  Dependency, vulnerability, and license-compatibility scanner for the
  open-source pre-publication audit. Use when auditing a target repo for known
  CVEs in dependencies and — critically for an Apache 2.0 release — copyleft or
  unknown-license dependencies that create viral-scrap risk. Generates an SBOM,
  scans it, and cross-checks with a multi-tool pass. Read-only. Triggers: "audit
  dependencies", "SBOM the repo", "check for copyleft licenses", "scan for CVEs
  before publish".
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: audit-mode-sensor
---

# Audit — Dependency Sensor

Dependency, vulnerability, and **license-compatibility** risk — the last one is
critical now that everything ships Apache 2.0. A GPL/AGPL dependency in an
Apache repo is a Critical finding.

## Contract

- **Read-only on the target repo.** All output to the run's `raw/` folder.

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
`raw/license-check.json`, then normalize. The SBOM also feeds
`audit-license-apply` for required NOTICE attributions.
