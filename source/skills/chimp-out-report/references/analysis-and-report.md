# Reviewing anger and confusion as workflow evidence

## Review unit

An episode can span several operator messages. Read the initial request, the agent
response or actions, the first correction, any ignored correction, the escalation,
and the eventual outcome. Repeated insults within one episode are not independent
causes. Several different failures can occur in one long thread.

Prioritize combinations and sequences, not a profanity leaderboard:

- “I don't understand” → another abstract explanation → demand for plain language.
- “Why does this work?” → agent edits code → “Stop coding; talk to me.”
- Clear authorization → another offer to perform the task → repeated demand to act.
- Claimed success → user runs the actual command → visible failure → demand for proof.
- User supplies contradictory evidence → unchanged hypothesis → escalating frustration.

Check low-profanity examples too: confusion, “which app?”, repeated “I said,” or
requests for a recommendation can reveal the failure before an outburst.

## Attribution and cause

For each selected episode identify:

1. What help the operator requested at that moment: teaching, discussion, diagnosis,
   implementation, review, or verification. Notice changes within the thread.
2. What the agent demonstrably did. Distinguish messages announcing a tool action
   from actual tool evidence when that difference matters.
3. The concrete mismatch or outside problem the operator reacted to.
4. What happened after the correction, including recovery or another ignored request.
5. What is still unknown. A user allegation or an apologetic agent admission is not
   by itself proof that a file was changed, a branch was created, or code was reverted.

Useful categories are intent mismatch, unclear language, missing explanation,
unexplained identifiers, inadequate recommendation, lost author intent, verification
gap, ignored evidence, surprising state, tool cost, repeated permission friction,
and external-software frustration. Add or revise categories to fit the evidence.

Avoid opposite overcorrections. The user may want a decisive recommendation while
also wanting to understand the trade-off. They may want initiative while also
wanting to participate in design. A future intervention should preserve the
operator's current intent rather than impose “always ask,” “always act,” “say less,”
or “explain more” across all situations.

## False positives and limits

- Distinguish agent-directed insults from anger at hardware, a self-directed insult,
  jokes, enthusiastic profanity, quoted examples, filenames, and pasted transcripts.
- Exclude system/developer messages, subagent requests, approval/guardian reviews,
  tool results, attached skill bodies, and this audit's own search request.
- Deduplicate stored copies without erasing repeated genuine operator turns.
  Preserve aliases and repeated occurrences; a fork is not a new outburst merely
  because it inherited an earlier message.
- Treat prompt-only records as leads. A table of unknown-order blobs can locate a
  phrase; it cannot prove which reply caused it. Go to an ordered export if available.
- Keep measured facts separate from user estimates, e.g. token costs and time spent.
- Never infer a psychological condition. The task is to improve collaboration.

## Review file

Collection creates `review.json` with `{"cases": []}`. Add entries after reading
context. Each `message_id` comes from `candidates.json` or the context command.
Use several message IDs for a multi-message episode, all from one thread/source
stream. Quoted fragments must match an owner message exactly.

```json
{
  "cases": [
    {
      "id": "F01",
      "title": "Explanation request triggered another edit",
      "message_ids": ["<message-id>"],
      "status": "reviewed",
      "category": "Intent mismatch",
      "trigger": "The operator asked why the parameter existed.",
      "observed": "The next reply announced a code change; the operator asked it to stop.",
      "inference": "The agent interpreted a question as permission to implement.",
      "recommendation": "Answer the question and preserve the current discussion mode.",
      "confidence": "High for the visible sequence; no claim about unshown tool actions.",
      "limitations": "The extract does not prove that the announced edit was applied.",
      "quotes": [{"message_id": "<message-id>", "text": "<exact fragment>"}]
    }
  ]
}
```

Statuses: `reviewed` for a contextually assessed episode; `prompt-only` for a lead
missing the preceding exchange; `external` for frustration with something other
than the agent; `false-positive` for a search hit that is not the desired evidence.
These statuses are separate from confidence in a proposed cause.

For a quote containing a secret, replace only the secret with `[REDACTED]` and
include `"redacted": true`. The renderer verifies that every remaining fragment
occurs in order in the selected original message. Review redactions manually;
automated pattern matching cannot guarantee that all personal information is gone.
Also include `"redactions": ["<exact private value>"]` on the case so the value is
removed from surrounding context and candidate exports. That list stays in the
private review control file and is omitted from exported evidence. Do not share
the review control file while it contains actual redaction values.

## Report contract

The report should be useful to a future skill author who has not read the chats:

- Open with the strongest recurring drivers and a small set of representative cases.
- State candidate-message, candidate-thread, reviewed-episode, and prompt-only counts
  separately. Do not call search hits “confirmed angry threads.”
- For each example show date with timezone or unknown, host, thread/run ID, source
  file and original locator, exact quotes, and the surrounding exchange.
- Explain trigger, observed behavior, inference, recommendation, confidence, outcome
  if available, and material limitations. Keep citations beside the supported claim.
- Include contrast cases and coverage for Codex, Claude Code, Cursor, and any other
  located hosts. Say which formats could not be decoded and what remains to inspect.
- Keep the report readable without opening source files. Make technical IDs secondary
  to full descriptions of the behavior. Escape all transcript content in HTML.

The helper renders verified review entries and searchable candidates. Add a short
`summary` string or list to `review.json` for the cross-case findings; the helper
does not invent root causes from keyword scores. Links in exported HTML point to
local evidence files, not authenticated session URLs fabricated from thread IDs.
