---
name: audit-tone-sensor
description: Use when asked to run the tone sensor in an explicitly requested publication audit. Requires an explicit target repository and report folder.
argument-hint: <target-repo> <report-folder> [run-timestamp]
metadata:
  version: "0.2"
  owner: Jarryd Adaens
  stage: audit-mode-sensor
---

# Audit — Tone Sensor

No off-the-shelf tool catches personal venting, so this sensor is custom:
wordlist + pattern grep driven entirely by the run's `audit-config/global.json`.
It is **expected to produce false positives** (legitimate uses, quoted text).
That is correct — separating those is the guardrail's job, not this sensor's.

## Required arguments & paths

Invocation: `<target-repo> <report-folder> [run-timestamp]`

- `REPO` — absolute path of the ONE repo being audited.
- `report-folder` — absolute path where `open-source-audit-report-<repo-name>/` lives.
  **Required: if it was not explicitly provided, STOP and ask — never guess or
  default.**
- `run-timestamp` — the shared `YYYY-MM-DD_HHMM` stamp when part of a
  persona-led run; mint a fresh one standalone. Never overwrite an earlier run.

Derived: `RUN = <report-folder>/open-source-audit-report-<repo-name>/<run-timestamp>`,
`OUT = RUN/audit-tone-sensor`, `RAW = OUT/raw`. Config lives in
`<report-folder>/open-source-audit-report-<repo-name>/audit-config/` (bootstrap from this
plugin's `config/` templates if missing). `LIB` = the `audit-lib/` folder at
this plugin's root (`../../audit-lib` relative to this SKILL.md).

## Contract

- **Read-only on the target repo.** Output goes only inside `OUT`.
- Reports every match with enough context (file/commit, line, matched pattern,
  surrounding snippet) for the guardrail to judge it.

## Matching rules (mandatory)

- **Case-insensitive, with word boundaries** (`\bword\b`). Substring matching is
  a bug: without boundaries "arse" fires on "parse"/"sparse" (a baseline sweep
  hit 140 such false positives) and "crap" fires on "scrap".

## Config-driven lists (`global.json` → `tone`)

- `profanity` — profanity + personal insults. Always reported (word-boundary).
- `ventingPatterns` — frustration phrases ("waste of time", "useless") that
  matter most when adjacent to a tool or person noun.
- `properNounWatchlist` — **employer / colleague / vendor names** (former
  employers, named individuals, internal teams). Always reported.
- `contextSensitiveNouns.terms` — common words that are also names (Meta, Google,
  IT). **Reported ONLY when a profanity or ventingPattern appears in the same
  line/sentence.** This stops "meta-workspace" and "metadata" from flooding the
  report while still catching "google's docs are garbage".
- `provenanceSurfaces` — glob + heading patterns for the venting-prone files.

## Surfaces scanned

1. **Commit messages, all history:**
   ```bash
   git -C "$REPO" log --all --format='%H%x1f%an%x1f%s%x1f%b%x1e' > "$RAW/commit-messages.txt"
   ```
   Then match each message against `profanity` + `ventingPatterns` +
   `properNounWatchlist`.
2. **Code comments & markdown docs:** grep the working tree (respect
   `.gitignore`) for the same lists.
3. **Provenance surfaces:** the files/headings in `provenanceSurfaces` — these
   are where designed venting accumulates and deserve the closest read.

## Output

`raw/tone-findings.json` — a list of `{surface, file_or_commit, line, list,
matched, snippet}`. Then normalize with the shared script:

```bash
uv run "$LIB/normalize.py" "$REPO" "$RAW" "$OUT/normalized"
```

## Handoff

Do not decide what is a real violation. The guardrail classifies
colleague-directed venting (Critical), profanity in commit messages (High), and
quoted/legitimate matches (noise).

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
