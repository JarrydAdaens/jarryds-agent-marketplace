---
name: wtf
description: >-
  Use when the user invokes /wtf or $wtf to recover from a confusing explanation,
  unexpected agent behavior, unclear work status, or a decision they cannot follow.
  Reconstruct the relevant context and give a short, literal explanation that
  restores understanding and control.
disable-model-invocation: true
disallowed-tools: Edit, Write, NotebookEdit, Task, Agent, Workflow, Skill, SendMessage, TaskStop, Artifact
argument-hint: "[optional: the confusing point]"
metadata:
  version: "1.1"
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
  the smallest relevant read-only check the freeze below allows. Do not start a
  broad audit or troubleshoot indefinitely. If the gap remains, say what is
  unknown and what evidence would settle it.
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

These are STE-based writing constraints, not the standard's controlled
dictionary. Do not claim formal ASD-STE100 compliance, and do not mention this
limit in an explanation.

Default to one short paragraph of two to four sentences, usually under 100 words.
Make the explanation shorter than the original, and as short as accuracy allows.
Never trade away grammar, cause, or a necessary warning to save words. A long
original does not justify a long answer.

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

The invocation interrupts execution so the user can catch up. This is a freeze:
explain, and change nothing. Use only tools and commands that read. Whatever a
tool is named on this host, do not call it if it writes a file, publishes a page,
creates or updates a document, sends a message, starts or controls a worker,
invokes another skill or command, or changes anything outside this conversation.
Answer in the conversation itself. The frontmatter withdraws several of these
tools, but the rule covers every tool the list does not name.

Reading stays open. Any command that only reports stored state is allowed, and
one targeted documentation lookup may verify a factual claim about a product's
current behavior. Do not invoke the project's package manager, build tool, test
runner, or application for any purpose, including listing, inspection, and
dry-run modes, whether or not they modify a file. If a check falls between these
cases, treat it as not allowed and say what you would run instead.

If you notice an unrelated defect while explaining, state it in one sentence and
stop. Do not write the fix anywhere, including a scratch or temporary file.

Do not stop, pause, redirect, or message work already running, announced or not.
Report its last known state and distinguish it from verified current progress.

An action request in the same message as the invocation does not lift the freeze,
and neither does one the user made before it. Explain first, then name the action
you would take as the next step. Only a message the user sends after the
explanation can authorize it.

Answer follow-up questions in this clear style. The freeze covers this turn only.
On a later turn, when the user asks to continue or gives a code task, resume
implementation and treat that authorization as still in force; do not turn
recovery into repeated permission requests.

If `/wtf` is repeated, keep the original unresolved topic as the reference. Find
a different missing connection or use a smaller literal example. Do not keep
cutting words from the last rewrite. Ask one focused question only if the
remaining ambiguity prevents a useful explanation.

Before replying, check: can the user tell what happened, why it matters, and what
it means for their question? Remove process announcements, skill commentary,
unrequested deliverables, and stock endings such as "Does that make sense?"
Return the explanation itself.
