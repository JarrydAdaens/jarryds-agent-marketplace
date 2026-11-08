---
name: wtf
description: >-
  Use when the user invokes /wtf or $wtf to recover from a confusing explanation,
  unexpected agent behavior, unclear work status, or a decision they cannot follow.
  Reconstruct the relevant context and give a short, literal explanation that
  restores understanding and control.
metadata:
  version: "1.0"
  argument-hint: "[optional: the confusing point]"
---

# WTF — What the Fuck?

The user needs to understand what is happening. Treat this as a failed transfer
of understanding, not a request to repeat the last answer or make it even denser.
The user is an experienced engineer who may not know this system or domain.

## Recover the question

Read the recent exchange, including the user's purpose, corrections, and supplied
evidence. Find the unresolved question behind the invocation. It may concern an
explanation, something the agent did, the current state of work, or a choice.
An optional topic after `/wtf` narrows the focus. Do not require one.

Usually the target is the last substantive explanation. Include earlier turns
when they contain the missing connection. Ignore unrelated status chatter. Do
not make the user diagnose the communication failure or repeat available context.
If the target is genuinely ambiguous, name the likely topic and explain it. If
there is no usable context, ask one short question about the topic or statement
they want explained. Do not invent a preceding exchange.

## Establish what is true

Identify the smallest useful account: what happened, what caused it, and what
that means for the user's immediate goal. Find the missing connection rather
than condensing every detail from the original answer.

- Check the explanation against the user's evidence. A prior agent statement is
  a claim, not independent proof. Correct a wrong claim rather than preserve it.
- Distinguish observed facts, likely causes, and unknowns in ordinary sentences.
  Keep any qualification that changes the user's decision. Do not turn uncertainty
  into a confident yes or no to save words.
- Use existing context first. If one factual gap prevents a useful answer, make
  the smallest relevant read-only check that available tools and permissions
  allow. Verify current product claims when needed. Do not start a broad audit or
  troubleshoot indefinitely. If the gap remains, say what is unknown and what
  evidence would settle it.
- Name the actual application, component, location, or process. Do not guess
  whether the user is in a terminal, desktop app, browser, or another machine.
  Give an instruction's execution surface when it matters.

## Explain it differently

Lead with the answer to the user's actual question. For a supported yes/no
answer, start with yes or no and give the reason. For a mechanism, name the actor
and what it does. Connect the cause to its visible effect.

Use literal, grammatical prose based on ASD-STE100 Simplified Technical English:

- Use familiar, concrete words and active voice. Give each sentence one main
  point. Aim for sentences of 20 words or fewer, without breaking useful meaning.
- Keep subjects, articles, pronouns, and connecting words. Short prose must still
  read like one engineer explaining something to another.
- Keep necessary technical names. Explain an unfamiliar term through its role
  at first use, then use the same name consistently. Describe a change or feature
  instead of making the user decode a story ID, acronym, or file path.
- Explain what something does. Avoid lists of what it is not, double negatives,
  metaphors, invented labels, and textbook introductions. State a necessary
  negative fact directly, such as "The fix is not implemented."
- Replace the failed presentation: use a concrete cause and effect, identify two
  components and their relationship, or give one small literal example. Merely
  deleting words from the same jargon-heavy structure is insufficient.

These are STE-based writing constraints, not a complete implementation of the
standard's controlled dictionary. Do not claim formal ASD-STE100 compliance
without checking the applicable rules and vocabulary. Do not add this caveat to
each explanation; it describes the skill's assurance limit.

Default to one short paragraph of two to four sentences, usually under 100 words.
Aim for no more than 20% of both the words and characters of the failed
explanation. This is a shortening target, not a reason to lose grammar, cause,
accuracy, or a necessary warning. A short original may need a slightly longer
replacement. A long original does not justify a long answer.

For that comparison, use only the relevant original explanatory passage or
passages. Exclude unrelated turns and pasted logs or code dumps. Count
whitespace-separated words and all characters, including whitespace and Markdown,
on both sides. Do not pad the baseline or show counting arithmetic to the user.
Exact counting tools are not required for this target.

Use a few complete-sentence bullets only when separate states or choices are
easier to understand that way. Avoid large tables, diagrams, and code blocks by
default; use one only if it explains the missing connection more clearly.

## Restore the user's bearings

Include only what this question needs:

- If the user is lost in the workflow, say what is actually complete, what is
  still pending or blocked, and the next concrete step. Distinguish planned,
  edited, built, tested, and observed behavior when that distinction matters.
- If the user asks for guidance, recommend one path and explain the consequence
  that makes it fit. Help them own the decision; do not substitute "trust me" or
  an unexplained menu of options.
- If the agent made a consequential mistake, name the specific mistake and
  correct it briefly. Avoid long apologies, defensiveness, or claims about the
  user's emotions. Ordinary confusion does not require an admission of fault.

The invocation interrupts execution so the user can catch up. Do not start edits,
configuration changes, builds, commits, or new workers as part of explaining.
Do not silently terminate work already running; distinguish its last known state
from verified current progress when relevant. A separate explicit action request
can authorize action, but explain first and honor any discussion-only boundary.

Answer follow-up questions in this clear style. Resume implementation when the
user asks to continue or gives a code task. Keep earlier authorization within
that scope; do not turn recovery into repeated permission requests.

If `/wtf` is repeated, keep the original unresolved topic as the reference. Find
a different missing connection or use a smaller literal example. Do not keep
shrinking the last rewrite by another 80%. Ask one focused question only if the
remaining ambiguity prevents a useful explanation.

Before replying, check: can the user tell what happened, why it matters, and what
it means for their question? Remove process announcements, skill commentary,
unrequested deliverables, and stock endings such as "Does that make sense?"
Return the explanation itself.
