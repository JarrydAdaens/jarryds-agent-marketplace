// Shared response accounting. Reasoning is a subset of output, never added twice.
import { priceReceipt } from './pricing.js';

export const TOKEN_FIELDS = [
  'input_tokens', 'cache_creation_input_tokens', 'cached_input_tokens',
  'output_tokens', 'reasoning_output_tokens',
];

export function responseTotals(responses) {
  const totals = Object.fromEntries(TOKEN_FIELDS.map((field) => [field, 0]));
  for (const response of responses) {
    for (const field of TOKEN_FIELDS) totals[field] += response[field] ?? 0;
  }
  totals.total_tokens = totals.input_tokens + totals.cache_creation_input_tokens +
    totals.cached_input_tokens + totals.output_tokens;
  return totals;
}

export function withResponses(receipt, responses) {
  const models = [...new Set(responses.map((r) => r.model || 'unknown'))];
  return priceReceipt({ ...receipt, ...responseTotals(responses), responses,
    turns: responses.length, model: models.length === 1 ? models[0] : 'mixed', models });
}

// Retain legacy snapshots in storage but select one accounting version for reports.
export function latestReceipts(receipts) {
  const selected = new Map();
  for (const receipt of receipts) {
    const key = JSON.stringify([receipt.provider, receipt.session_id]);
    const old = selected.get(key);
    const version = receipt.schema_version || 1;
    const oldVersion = old?.schema_version || 1;
    if (!old || version > oldVersion || (version === oldVersion &&
      String(receipt.updated_at || '') >= String(old.updated_at || ''))) selected.set(key, receipt);
  }
  return [...selected.values()];
}

// Forks or copied transcripts repeat responses across files. Count maxima once.
export function uniqueResponseReceipts(receipts) {
  const selected = latestReceipts(receipts);
  const owners = new Map();
  const requests = new Map();
  for (const receipt of selected) for (const response of receipt.responses || []) {
    if (!response.message_id || !response.request_id) continue;
    const key = JSON.stringify([receipt.provider, response.message_id]);
    if (!requests.has(key)) requests.set(key, new Set());
    requests.get(key).add(response.request_id);
  }
  const output = selected.map((r) => ({ ...r, responses: r.responses ? [] : undefined }));
  selected.forEach((receipt, index) => {
    for (const response of receipt.responses || []) {
      const knownRequests = requests.get(JSON.stringify([receipt.provider, response.message_id]));
      const requestId = response.request_id || (knownRequests?.size === 1 ? [...knownRequests][0] : null);
      const identity = response.message_id ? JSON.stringify([requestId, response.message_id]) : response.response_id;
      const key = JSON.stringify([receipt.provider, identity]);
      const old = owners.get(key);
      if (!old) {
        const copy = { ...response };
        owners.set(key, copy);
        output[index].responses.push(copy);
      } else {
        output[index].coverage = { ...output[index].coverage,
          issues: [...new Set([...(output[index].coverage?.issues || []), 'shared-response-deduplicated'])] };
        for (const field of TOKEN_FIELDS) {
          if (response[field] !== null && response[field] !== undefined)
            old[field] = Math.max(old[field] ?? 0, response[field]);
        }
        if (!old.model) old.model = response.model;
        else if (response.model && old.model !== response.model) {
          old.model = 'unknown';
          output[index].coverage.issues.push('conflicting-response-model');
        }
      }
    }
  });
  return output.map((r) => r.responses ? withResponses(r, r.responses) : r);
}
