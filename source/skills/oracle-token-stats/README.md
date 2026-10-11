# oracle-token-stats

Durable, agent-neutral token receipts and estimated cost for agentic IDE sessions.
Real counts from logs — no AI estimation, no stored prompt text.

## What it does

`token-stats` is a small Node CLI (stdlib only, Node 18+) with a provider-neutral core
and per-provider adapters. It reads the token counts a provider already records in its
session logs, normalizes them into a receipt, keeps a JSONL ledger in your user profile,
and reports current/recent/aggregate usage with **estimated** cost.

Token totals come only from retained session logs. Existing historical receipts remain
readable as stored; new scans do not inspect project markers for style metadata.

## Providers

- **Claude Code** (forensic parser) — recursively reads `$CLAUDE_CONFIG_DIR/projects/**/*.jsonl`
  (default `~/.claude/projects`), with full accounting of fresh input, cache-write,
  cache-read, and output tokens.
  It counts request/message identities once, merges evolving category counters using
  maxima, discovers nested agents, and prices each response with its recorded model.
  Reasoning is included in output and is never added again to totals or cost.
  The private transcript format is forensic evidence; retained logs provide partial
  coverage and do not establish a supported collection or billing contract.
- **Codex** (research stub) — deliberately not implemented against a private transcript
  format. See [`references/codex-research.md`](./references/codex-research.md).

## Install / run

No install — zero dependencies. Run with `node`:

```
node skills/oracle-token-stats/scripts/token-stats.js <command> [flags]
```

Optionally `npm link` inside `scripts/` to expose a global `token-stats` binary.

## Commands

```bash
token-stats current  --provider claude            # current session receipt
token-stats scan     --provider claude            # refresh the ledger from logs
token-stats summary  --since 7d                   # totals for the last 7 days
token-stats summary  --by project                 # totals grouped by project
token-stats sessions --project "MyBrain"          # session rows for one project
token-stats export   --format csv                 # CSV of filtered receipts
token-stats prices                                # show the bundled pricing table
token-stats live                                  # today/week burn from Oracle Server
```

Filters: `--provider`, `--project <substring>`, `--model <prefix>`, `--since <7d|24h|ISO>`.
`--json` gives machine-readable output. `summary`/`sessions`/`export` auto-refresh the
Claude ledger first; pass `--no-scan` to read the ledger as-is.

## Example output

```
Provider: claude
Model:    claude-opus-4-8
Project:  D:\Code Projects\MyBrain
Session:  3f9c…  (47 turns)

Input:        12,304 tokens (uncached)
Cache write:   8,900 tokens
Cache read:  211,400 tokens
Output:        3,891 tokens
Total:       236,495 tokens

Est. cost:    $0.2143 (pricing 2026-06-18)
```

## Server mode

`token-stats live` reports today/this-week burn from an Oracle Server instance
(`GET /health` probe, then `GET /v1/usage/window`), falling back to the local
ledger when the server is unreachable. Output always names its data source
(`server` vs `offline — local ledger`). Configure the server with
`ORACLE_SERVER_URL` (default `http://localhost:5140`). See
[`SKILL.md`](./SKILL.md#server-mode-live) for the fallback semantics and the
known session-level gap.

## Storage

- Windows: `%LOCALAPPDATA%\token-stats\ledger.jsonl`
- macOS/Linux: `~/.local/share/token-stats/ledger.jsonl`
- Override with `TOKEN_STATS_DIR`.

Only metadata and token counters are stored — never prompt text.

Schema version 2 receipts record parser version, response identity, model attribution,
directory-derived parentage, source SHA-256, and missing or ambiguous telemetry.
Missing counters stay null on responses; session sums include known categories only.
Legacy receipts remain as historical snapshots in the ledger. Reports select the
highest schema version per session, then deduplicate shared responses in combined
totals. Mixed-model filters and summaries use response attribution. Session listings
show each transcript's own totals, which may overlap with forked/copied transcripts.
Day/time filters use session snapshot timestamps, not exact response time windows.

## Cost model

Rates live in [`scripts/pricing.json`](./scripts/pricing.json), versioned and kept
separate from the parsers. Cache tokens use the provider's write/read multipliers.
Unknown models report tokens **without** a dollar cost. Every report names the pricing
table version. Dollars are estimates, not billing truth.

## Tests

```
cd source/skills/oracle-token-stats/scripts
npm test
```

## See also

- [`SKILL.md`](./SKILL.md) — trigger, workflow, and hook contract
- [`references/codex-research.md`](./references/codex-research.md) — Codex open questions and v1 plan
