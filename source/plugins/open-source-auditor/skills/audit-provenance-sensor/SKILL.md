---
name: audit-provenance-sensor
description: Use when asked to run the provenance sensor in an explicitly requested publication audit. Requires an explicit target repository and report folder.
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.3"
  owner: Jarryd Adaens
  stage: audit-mode-sensor
---

# Audit — Provenance Sensor

Answers the question at the center of open-sourcing personal work: **is there
code here I don't actually own?** Employer copyright headers, a vendor's name in
a file you claim you authored, third-party code pasted in, a stray license
notice inside a source file. Deeper than the dependency sensor's license scan —
that classifies *declared dependency* licenses; this reads the *source itself*.

## Required arguments & paths

Invocation: `<target-repo> <report-folder> [run-timestamp]`

- `REPO` — absolute path of the ONE repo being audited.
- `report-folder` — absolute path where `open-source-audit-report-<repo-name>/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- `run-timestamp` — the shared `YYYY-MM-DD_HHMM` stamp when part of a
  persona-led run; mint a fresh one standalone. Never overwrite an earlier run.

Derived: `RUN = <report-folder>/open-source-audit-report-<repo-name>/<run-timestamp>`,
`OUT = RUN/audit-provenance-sensor`, `RAW = OUT/raw`. Config lives in
`<report-folder>/open-source-audit-report-<repo-name>/audit-config/`. `LIB` = the
`audit-lib/` folder at this plugin's root (`../../audit-lib` relative to this
SKILL.md).

## Contract

- **Read-only on the target repo.** All output goes only inside `OUT`.
- Runs after the dependency sensor in the fixed order (both are the legal/SBOM
  cluster): `... → dependency → provenance → hygiene`.

## Tool & invocation

**ScanCode Toolkit** — `-c` copyright, `-l` license, `-i` info, `-p` packages,
`-e` emails, `-u` urls:

```bash
scancode -clipeu --json-pp "$RAW/scancode.json" --processes 4 --timeout 120 \
  --max-in-memory 10000 \
  --ignore .git --ignore node_modules --ignore dist --ignore build \
  --ignore .venv --ignore venv --ignore Library --ignore Intermediate \
  --ignore Saved --ignore DerivedDataCache --ignore Binaries \
  --ignore "*.min.js" \
  "$REPO" 2> "$RAW/scancode.stderr.txt"
```

**Windows ignore-glob hazard (verified 2026-07-22):** glob-form ignore values
like `.git/*` can be expanded by ScanCode/Click on Windows into the positional
*input list*, silently hijacking the scan — it completes "successfully" with
`files_count: 0` and directory stubs only. Use **bare directory-name ignores**
(they cannot glob-expand; ScanCode still excludes the directory contents) and
invoke ScanCode without a shell (e.g. a python subprocess with `shell=False`).

ScanCode is heavy and slow (deep per-file scan) — that is expected; it is the
thorough pass, run once per audit, not per commit.

### Memory safety (hard rules — learned 2026-07-21/22)

ScanCode accumulates scan results in RAM and writes the JSON only at the end, so
its footprint grows for the entire scan. Three orphaned/concurrent instances
consumed **~59 GB of commit** on 2026-07-21, exhausting a 32 GB machine (system
crawl, unrelated apps crashing on failed allocations). Therefore:

- **One ScanCode instance machine-wide, ever.** Never run this sensor for two
  repos concurrently.
- `--timeout 120` (per-file) is mandatory — `--timeout 0` lets one pathological
  file grind forever.
- The ignore list is mandatory: provenance value lives in *authored source*;
  scanning node_modules, build output, venvs, or game-engine asset/derived
  folders is pure memory burn.
- **Verify completion:** `scancode.json` must exist afterward. A
  `scancode.stderr.txt` without a `scancode.json` means ScanCode died or was
  orphaned — record the sensor as failed and run `audit-cleanup` before retrying.
- **Verify coverage:** check `files_count` inside `scancode.json`. A near-zero
  count on a non-empty repo means the Windows ignore-glob hazard above hijacked
  the input list — the scan is invalid; fix the ignores and re-run.

## What to surface (deterministic, for the guardrail to triage)

From `scancode.json`, extract and write `raw/provenance-findings.json`:

- **`holders` / `copyright`** — every distinct copyright holder. Red flags:
  a former employer (cross-check `tone.properNounWatchlist` in the run's
  `audit-config/global.json`), a vendor name, any holder that is not the repo
  owner.
- **`license_detections` inside source files** — a GPL/AGPL notice embedded in a
  file, or a license that contradicts the repo's Apache-2.0 intent.
- **`authors` / `emails`** — author tags or emails that point to someone other
  than the owner (company email domains especially).

## Severity mapping (guardrail reads `severityPolicy`)

- `foreign-copyright-holder`, `pasted-third-party-code` → **Critical**.
- `employer-copyright-header`, `unexpected-license-in-source` → **High**.

## Output

`raw/scancode.json` (full), `raw/provenance-findings.json` (extracted), then
normalize (`uv run "$LIB/normalize.py" "$REPO" "$RAW" "$OUT/normalized"`).
Cross-references the dependency sensor's SBOM but does not duplicate its
dependency-license verdict.

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
