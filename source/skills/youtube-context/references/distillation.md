# Distillation

How to turn a transcript into notes worth keeping. The test is simple: six months
from now, can the reader use this file instead of rewatching the video, and can
they check any single claim in one click?

## Fill the scaffold

`fetch` writes a notes file with pending sections. Replace every `_Pending._`
marker. Remove a section that does not apply rather than leaving it empty, except
`Summary` and `Key points`, which are always required.

### Summary

Three to five sentences. State what the video covers, who it is for, and what the
speaker is actually arguing. A viewer who reads only this should know whether the
rest of the file is relevant to them.

Do not open with "This video discusses". Lead with the content.

### Chapters

`fetch` fills this from the video's own chapter markers when the author published
them. Leave it as written. If the chapter titles are marketing rather than
description, add a short clarifying phrase after each, but keep the original title
so the reader can match it to the YouTube timeline.

### Key points

The substance of the file. One bullet per distinct claim, instruction, or finding,
each opening with its `[MM:SS]` timestamp.

Order by the structure of the argument, not strictly by time, when the video
doubles back on itself. A reader looking for one fact scans this section, so keep
each bullet to a single idea.

Record what the speaker claims, not what you believe. When a claim is wrong or
outdated, keep it and append the correction:

```text
- [14:22] Says the API requires a service account key. That changed in 2025;
  workload identity federation is now the documented path.
```

### Commands and code

Copy commands, file paths, flags, and code exactly as shown. Do not paraphrase
them, reformat them, or silently fix an apparent typo.

This is the section automatic captions damage most. Speech recognition mangles
package names, flags, and punctuation. When the command came from the narration
rather than from a frame you read, mark it:

```text
- [08:05] `npm install --save-dev vitest` (heard in narration, not read on screen)
```

When you read a command from a frame, cite the frame file. That lets a later
reader confirm it without rewatching.

### Open questions

What the video leaves unresolved, what it asserts without evidence, and what you
could not verify. Include anything the audio or captions lost: an inaudible
passage, an on-screen detail no sampled frame captured, a reference to a resource
the speaker never names.

An empty Open questions section on a technical video is usually a sign the pass
was shallow, not that the video was complete.

## Rules that hold across every section

**Timestamp every substantive claim.** A `[MM:SS]` prefix turns the notes into an
index into the video. Without it the reader must rewatch to verify anything, and
the file loses most of its value.

**Separate the video's claim from your knowledge.** The notes record what the
video said. When you add context the video did not provide, attribute it, as in
the correction example above. Never blend the two into a single unmarked
assertion.

**Preserve the speaker's terms.** Keep the names, library versions, and jargon the
video uses, even when a better term exists. A reader matching the notes against
the video needs the same words. Explain an unfamiliar term at first use instead of
replacing it.

**Do not pad.** A twenty-minute video with one real idea gets short notes. Length
should track content, not runtime. Sponsor reads, channel promotion, and
restatement of the intro are not key points.

**Quote sparingly and exactly.** A direct quote is worth it for a precise
definition or a strong claim. Mark it as a quote and keep the wording intact.
Automatic captions are not reliable enough for a verbatim quote; say so if you
quote from one anyway.

## Reporting back

Return the notes path, the transcript source, and the gaps. Keep the chat summary
to a few sentences; the file holds the detail. Do not paste the transcript or the
full notes into the conversation — that undoes the point of writing them to disk.
