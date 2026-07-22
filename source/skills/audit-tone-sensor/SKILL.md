---
name: audit-tone-sensor
description: >-
  Custom wordlist scanner for the open-source pre-publication audit. Use when
  auditing a target repo for profanity, frustration venting, or negative
  references to colleagues, employers, or vendors — in commit messages, code
  comments, docs, and the Rails provenance surfaces (complaining.md, thinking.md,
  dictations, execution logs) where venting is designed to accumulate. Read-only.
  Expected to over-report; the guardrail separates legitimate/quoted use from
  real violations. Triggers: "audit tone", "scan for swearing", "check for venting
  at colleagues", pre-publish tone sweep.
metadata:
  version: "0.1"
  owner: Jarryd Adaens
  stage: audit-mode-sensor
---

# Audit — Tone Sensor

No off-the-shelf tool catches personal venting, so this sensor is custom:
wordlist + pattern grep driven entirely by `context/audit-config/global.json`.
It is **expected to produce false positives** (legitimate uses, quoted text).
That is correct — separating those is the guardrail's job, not this sensor's.

## Contract

- **Read-only on the target repo.** Output goes only to the run's `raw/` folder.
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
- `properNounWatchlist` — **employer / colleague / vendor names** (ExampleCorp,
  AcmeStudios, named individuals, "IT team"). Always reported.
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
matched, snippet}`. Then normalize with the shared script.

## Handoff

Do not decide what is a real violation. The guardrail classifies
colleague-directed venting (Critical), profanity in commit messages (High), and
quoted/legitimate matches (noise).
