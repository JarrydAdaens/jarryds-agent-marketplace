// Forensic accounting of retained Claude Code JSONL transcripts. This private
// format is not a billing or supported telemetry contract; coverage is explicit.
import { readdirSync, readFileSync, statSync, existsSync } from 'node:fs';
import { join, basename, dirname, relative } from 'node:path';
import { createHash } from 'node:crypto';
import { claudeProjectsDir } from '../lib/paths.js';
import { withResponses } from '../lib/receipts.js';

export const name = 'claude';
export const PARSER_VERSION = 'claude-jsonl/2';
const CATEGORIES = {
  input_tokens: 'input_tokens', cache_creation_input_tokens: 'cache_creation_input_tokens',
  cache_read_input_tokens: 'cached_input_tokens', output_tokens: 'output_tokens',
  reasoning_output_tokens: 'reasoning_output_tokens',
};

function findSessionFiles(root) {
  if (!existsSync(root)) return [];
  const files = [];
  function visit(dir) {
    for (const entry of readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (entry.isDirectory()) visit(join(dir, entry.name)); // no symlink traversal
      else if (entry.isFile() && entry.name.endsWith('.jsonl')) files.push(join(dir, entry.name));
    }
  }
  visit(root);
  return files;
}

// Exposed for read-only reconciliation of a specific local evidence file.
export function parseSessionFile(file) {
  const raw = readFileSync(file, 'utf8');
  const digest = createHash('sha256').update(raw).digest('hex');
  const entries = [];
  let malformed = 0;
  raw.split('\n').forEach((line, index) => {
    if (!line.trim()) return;
    try {
      const entry = JSON.parse(line);
      if (!entry || typeof entry !== 'object' || Array.isArray(entry)) malformed += 1;
      else entries.push({ entry, line: index + 1 });
    } catch { malformed += 1; }
  });
  const nested = basename(dirname(file)) === 'subagents';
  let sessionId = nested ? basename(file, '.jsonl') : '';
  let projectPath = '';
  const timestamps = [];
  const responses = new Map();
  const issues = new Set(malformed ? ['malformed-records'] : []);
  let assistantRows = 0;
  let missingTelemetry = 0;
  const requests = new Map();
  for (const { entry } of entries) {
    if (entry.type !== 'assistant' || !entry.message?.id || !entry.requestId) continue;
    if (!requests.has(entry.message.id)) requests.set(entry.message.id, new Set());
    requests.get(entry.message.id).add(entry.requestId);
  }
  for (const { entry, line } of entries) {
    if (!sessionId && typeof entry.sessionId === 'string') sessionId = entry.sessionId;
    if (typeof entry.cwd === 'string') projectPath = entry.cwd;
    const timestamp = Date.parse(entry.timestamp || '');
    if (Number.isFinite(timestamp)) timestamps.push(timestamp);
    if (entry.type !== 'assistant') continue;
    assistantRows += 1;
    const message = entry.message;
    const usage = message?.usage;
    if (!usage || typeof usage !== 'object' || Array.isArray(usage)) {
      missingTelemetry += 1;
      issues.add('missing-usage');
      continue;
    }
    const messageId = typeof message.id === 'string' && message.id ? message.id : null;
    let requestId = typeof entry.requestId === 'string' ? entry.requestId : null;
    const knownRequests = requests.get(messageId);
    if (!requestId && knownRequests?.size === 1) requestId = [...knownRequests][0];
    if (!requestId && knownRequests?.size > 1) issues.add('ambiguous-request-identity');
    // Anonymous rows stay distinct even when their counters match.
    const responseId = messageId ? JSON.stringify([requestId, messageId]) :
      JSON.stringify(['anonymous', file, line]);
    if (!messageId) issues.add('missing-response-identity');
    const model = typeof message.model === 'string' ? message.model : '';
    if (!model) issues.add('missing-model');
    let response = responses.get(responseId);
    if (!response) {
      response = { response_id: responseId, message_id: messageId, request_id: requestId,
        model, source_lines: [], updated_at: Number.isFinite(timestamp) ? new Date(timestamp).toISOString() : null,
        reasoning_included_in_output: true };
      for (const target of Object.values(CATEGORIES)) response[target] = null;
      responses.set(responseId, response);
    } else if (model && response.model && model !== response.model) {
      response.model = 'unknown';
      issues.add('conflicting-response-model');
    } else if (!response.model) response.model = model;
    response.source_lines.push(line);
    if (Number.isFinite(timestamp) && (!response.updated_at || timestamp > Date.parse(response.updated_at)))
      response.updated_at = new Date(timestamp).toISOString();
    for (const [source, target] of Object.entries(CATEGORIES)) {
      const value = usage[source];
      if (value === undefined || value === null) continue;
      if (!Number.isSafeInteger(value) || value < 0) { issues.add('invalid-token-counter'); continue; }
      if (response[target] !== null && value < response[target]) issues.add('decreasing-usage-revision');
      response[target] = Math.max(response[target] ?? 0, value);
    }
  }
  if (!responses.size) return { receipt: null, malformed, missingTelemetry };
  const values = [...responses.values()];
  for (const response of values) {
    response.missing_categories = Object.values(CATEGORIES).filter((field) => response[field] === null);
    if (response.missing_categories.some((field) => field !== 'reasoning_output_tokens')) issues.add('missing-token-categories');
    if (response.reasoning_output_tokens > response.output_tokens && response.output_tokens !== null)
      issues.add('reasoning-exceeds-output');
  }
  const fallback = statSync(file).mtime.toISOString();
  if (!timestamps.length) issues.add('missing-timestamps');
  const receipt = withResponses({
    schema_version: 2, parser_version: PARSER_VERSION, provider: 'claude',
    session_id: sessionId || basename(file, '.jsonl'),
    parent_session_id: nested ? basename(dirname(dirname(file))) : null,
    parentage_source: nested ? 'transcript-directory' : null,
    project_path: projectPath,
    started_at: timestamps.length ? new Date(Math.min(...timestamps)).toISOString() : fallback,
    updated_at: timestamps.length ? new Date(Math.max(...timestamps)).toISOString() : fallback,
    source_file: file,
    provenance: { kind: 'forensic-local-transcript', source_sha256: digest,
      deduplication: 'request-and-message-id/category-maxima' },
    coverage: { status: 'partial-retained-corpus', issues: [...issues].sort(),
      assistant_rows: assistantRows, malformed_records: malformed, missing_telemetry_records: missingTelemetry,
      duplicate_usage_rows: values.reduce((sum, r) => sum + r.source_lines.length - 1, 0),
      reasoning_telemetry: values.every((r) => r.reasoning_output_tokens !== null) ? 'available' : 'missing-or-partial' },
  }, values);
  return { receipt, malformed, missingTelemetry };
}

export function scan({ root = claudeProjectsDir() } = {}) {
  const files = findSessionFiles(root);
  const results = files.map(parseSessionFile);
  const receipts = results.map((r) => r.receipt).filter(Boolean);
  const byRelativeFile = new Map(receipts.map((r) => [relative(root, r.source_file), r]));
  for (const receipt of receipts) {
    if (!receipt.parent_session_id) continue;
    const parentFile = relative(root, join(dirname(dirname(receipt.source_file)), '..', `${receipt.parent_session_id}.jsonl`));
    const parent = byRelativeFile.get(parentFile);
    if (parent) receipt.parent_session_id = parent.session_id;
    else receipt.coverage.issues.push('parent-transcript-unavailable');
  }
  return { receipts, malformed: results.reduce((n, r) => n + r.malformed, 0),
    missingTelemetry: results.reduce((n, r) => n + r.missingTelemetry, 0), scanned: files.length, root,
    coverage: 'partial-retained-corpus', collection: 'forensic-local-transcript' };
}

export function current({ root = claudeProjectsDir(), project } = {}) {
  const { receipts } = scan({ root });
  const candidates = receipts.filter((r) => !r.parent_session_id && (!project ||
    (r.project_path || '').toLowerCase().includes(String(project).toLowerCase())));
  return candidates.sort((a, b) => a.updated_at < b.updated_at ? 1 : -1)[0] || null;
}
