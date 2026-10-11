import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { parseSessionFile, scan, current } from '../adapters/claude.js';
import { summarize, filterReceipts } from '../lib/summary.js';
import { readLedger, upsertReceipts } from '../lib/ledger.js';

const here = dirname(fileURLToPath(import.meta.url));
function row(id, overrides = {}) {
  return { type: 'assistant', sessionId: 'parent', cwd: '/sample/project',
    timestamp: '2026-10-01T10:00:00Z', message: { id, model: 'claude-opus-4-8',
      usage: { input_tokens: 2, cache_creation_input_tokens: 10, cache_read_input_tokens: 30,
        output_tokens: 8, reasoning_output_tokens: 3 } }, ...overrides };
}
function corpus(t, files) {
  const root = mkdtempSync(join(tmpdir(), 'oracle-accounting-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  for (const [name, rows] of Object.entries(files)) {
    const file = join(root, name);
    mkdirSync(dirname(file), { recursive: true });
    writeFileSync(file, rows.map((r) => typeof r === 'string' ? r : JSON.stringify(r)).join('\n'));
  }
  return root;
}

test('sanitized observed duplicate counts one response, not content rows', () => {
  const { receipt } = parseSessionFile(join(here, 'fixtures/accounting/duplicate-response.jsonl'));
  assert.equal(receipt.turns, 1);
  assert.equal(receipt.total_tokens, 61382); // naive row sum = 122764
  assert.equal(receipt.coverage.duplicate_usage_rows, 1);
  assert.equal(receipt.schema_version, 2);
  assert.equal(receipt.parser_version, 'claude-jsonl/2');
  assert.match(receipt.provenance.source_sha256, /^[a-f0-9]{64}$/);
});

test('evolving usage uses maxima, preserves distinct requests, and counts reasoning once', (t) => {
  const early = row('evolving', { requestId: 'one' });
  const final = structuredClone(early);
  final.message.usage.output_tokens = 18;
  final.message.usage.reasoning_output_tokens = 9;
  const second = row('evolving', { requestId: 'two' });
  const root = corpus(t, { 'project/session.jsonl': [early, final, early, second] });
  const receipt = scan({ root }).receipts[0];
  assert.equal(receipt.turns, 2);
  assert.equal(receipt.output_tokens, 26);
  assert.equal(receipt.reasoning_output_tokens, 12);
  assert.equal(receipt.total_tokens, 110);
  assert.ok(receipt.coverage.issues.includes('decreasing-usage-revision'));
});

test('recursive discovery keeps child/grandchild identities distinct and resolves parentage', (t) => {
  const root = corpus(t, {
    'project/session.jsonl': [row('root')],
    'project/session/subagents/agent-a.jsonl': [row('child', { timestamp: '2026-10-02T10:00:00Z' })],
    'project/session/subagents/agent-a/subagents/agent-b.jsonl': [row('grandchild')],
  });
  const result = scan({ root });
  assert.equal(result.scanned, 3);
  assert.equal(result.receipts.find((r) => r.session_id === 'agent-a').parent_session_id, 'parent');
  assert.equal(result.receipts.find((r) => r.session_id === 'agent-b').parent_session_id, 'agent-a');
  assert.equal(summarize(result.receipts).total.total_tokens, 150);
  assert.equal(current({ root }).session_id, 'parent');
});

test('combined totals deduplicate fork/copied responses and remain stable on rescans', (t) => {
  const shared = row('shared');
  const later = structuredClone(shared);
  later.message.usage.output_tokens = 18;
  const root = corpus(t, {
    'project/session.jsonl': [shared],
    'project/session/subagents/agent-a.jsonl': [later, row('unique')],
  });
  const first = scan({ root });
  assert.equal(summarize(first.receipts).total.total_tokens, 110);
  assert.equal(summarize(first.receipts).total.turns, 2);
  assert.deepEqual(scan({ root }), first);
});

test('requestless copies join a unique known request across files', (t) => {
  const root = corpus(t, {
    'project/session.jsonl': [row('shared', { requestId: 'known' })],
    'project/session/subagents/agent-a.jsonl': [row('shared')],
  });
  const summary = summarize(scan({ root }).receipts);
  assert.equal(summary.total.total_tokens, 50);
  assert.equal(summary.total.turns, 1);
  assert.ok(summary.total.issues.includes('shared-response-deduplicated'));
});

test('conflicting response models remain unpriced and do not silently choose the last model', (t) => {
  const changed = row('one');
  changed.message.model = 'claude-sonnet-4-6';
  const root = corpus(t, { 'project/session.jsonl': [row('one'), changed] });
  const receipt = scan({ root }).receipts[0];
  assert.equal(receipt.turns, 1);
  assert.equal(receipt.model, 'unknown');
  assert.equal(receipt.estimated_cost_usd, null);
  assert.ok(receipt.coverage.issues.includes('conflicting-response-model'));
});

test('missing identity, malformed objects, invalid counters and absent usage stay explicit', (t) => {
  const anonymous = row(undefined);
  anonymous.message.usage.input_tokens = '100';
  delete anonymous.message.usage.cache_read_input_tokens;
  const missingModel = row('missing-model');
  delete missingModel.message.model;
  const root = corpus(t, { 'project/session.jsonl': [null, [], 'bad JSON', anonymous, anonymous,
    missingModel, { type: 'assistant', message: {} }] });
  const result = scan({ root });
  const receipt = result.receipts[0];
  assert.equal(result.malformed, 3);
  assert.equal(result.missingTelemetry, 1);
  assert.equal(receipt.turns, 3, 'anonymous records are not merged');
  assert.equal(receipt.input_tokens, 2, 'string counters never concatenate or become guesses');
  assert.equal(receipt.estimated_cost_usd, null, 'missing models are not priced using session model');
  assert.ok(receipt.coverage.issues.includes('missing-response-identity'));
  assert.ok(receipt.coverage.issues.includes('missing-token-categories'));
  assert.equal(receipt.responses[0].cached_input_tokens, null);
});

test('mixed-model summaries and filters select only the matching responses', (t) => {
  const sonnet = row('sonnet');
  sonnet.message.model = 'claude-sonnet-4-6';
  const root = corpus(t, { 'project/session.jsonl': [row('opus'), sonnet] });
  const { receipts } = scan({ root });
  const summary = summarize(receipts, 'model');
  assert.equal(summary.groups.length, 2);
  assert.equal(summary.groups.find((r) => r.key === 'claude-opus-4-8').total_tokens, 50);
  const filtered = filterReceipts(receipts, { model: 'claude-sonnet' });
  assert.equal(summarize(filtered).total.total_tokens, 50);
  assert.equal(filtered[0].model, 'claude-sonnet-4-6');
});

test('schema upgrade preserves historical receipt bytes and excludes superseded totals', (t) => {
  const root = corpus(t, { 'project/session.jsonl': [row('one'), row('one')] });
  const ledger = join(root, 'ledger.jsonl');
  const historical = { provider: 'claude', session_id: 'parent', updated_at: '2026-10-01T10:00:00Z',
    total_tokens: 100, estimated_cost_usd: 999 };
  upsertReceipts([historical], ledger);
  const prior = readFileSync(ledger, 'utf8').trim();
  upsertReceipts(scan({ root: join(root, 'project') }).receipts, ledger);
  assert.equal(readFileSync(ledger, 'utf8').split('\n')[0], prior);
  assert.equal(readLedger(ledger, { includeHistorical: true }).length, 2);
  assert.equal(readLedger(ledger)[0].total_tokens, 50);
  assert.equal(summarize(readLedger(ledger, { includeHistorical: true })).total.total_tokens, 50);
  upsertReceipts(scan({ root: join(root, 'project') }).receipts, ledger);
  assert.equal(readLedger(ledger, { includeHistorical: true }).length, 2);
});

test('CLI scan and model summary use an isolated ledger and corrected accounting', (t) => {
  const root = corpus(t, { 'projects/project/session.jsonl': [row('one'), row('one')] });
  const cli = join(here, '..', 'token-stats.js');
  const env = { ...process.env, CLAUDE_CONFIG_DIR: root, TOKEN_STATS_DIR: join(root, 'receipts') };
  const run = (...args) => JSON.parse(execFileSync(process.execPath, [cli, ...args], { env, encoding: 'utf8' }));
  const scanned = run('scan', '--json');
  assert.equal(scanned.receipts[0].turns, 1);
  assert.equal(scanned.receipts[0].total_tokens, 50);
  const summary = run('summary', '--by', 'model', '--json');
  assert.equal(summary.total.total_tokens, 50);
  assert.equal(summary.groups[0].key, 'claude-opus-4-8');
  assert.equal(readLedger(join(root, 'receipts/ledger.jsonl')).length, 1);
});
