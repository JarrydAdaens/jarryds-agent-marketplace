# Visual content and escalation

A transcript carries the narration. It loses everything the speaker pointed at.
This file covers how to recover that locally, and what to do when local frame
sampling is not enough.

## Decide whether you need frames

Frames cost a video download and a few minutes. Spend that when the transcript
shows you are missing something. The signals, in rough order of strength:

- Deictic language with no referent: "as you can see here", "this setting",
  "click that", "the one on the left". The transcript proves information is
  missing but cannot supply it.
- A command or identifier the narration half-states: "run the install script",
  "set it to the higher value".
- Long stretches of the transcript that read as filler while the title promises a
  walkthrough. The content is on the screen.
- The video is a slide talk, a code walkthrough, a UI or editor demo, a hardware
  teardown, or gameplay.

Skip frames for an interview, a podcast, a conference talk whose slides merely
restate the speech, or any video where the narration is self-contained.

## Choose a sampling mode

**Interval**, the default, takes one frame every 30 seconds. Use it to sample a
video evenly when you do not yet know where the visual content sits. Lower
`--interval` for a dense demo, but watch the 60-frame cap: at `--interval 10` the
cap is reached ten minutes in.

**Scene**, `--scene`, triggers on visual change instead. Use it for a slide deck,
a demo that cuts between states, or any video that holds a static screen then
switches. It captures transitions rather than arbitrary moments, so the frames
line up with the structure of the content.

`--scene` takes an optional threshold, default `0.3`. Raise it toward `0.5` when
a video with heavy motion returns the frame cap immediately. Lower it toward
`0.15` when a mostly static screencast returns almost nothing.

## Read frames efficiently

Do not read every frame. Each one consumes context, and most carry nothing the
transcript lacks.

1. Find the moments that matter in the transcript — the deictic phrases, the
   half-stated commands, the section the user asked about.
2. Look up the nearest frames in the frame index, which maps each filename to its
   timestamp.
3. Read those frames only. Widen to the neighbors when a frame lands mid-
   transition or the detail is cut off.

When you read a value off a frame, cite the frame filename in the notes. A reader
can then open the image and confirm it without rewatching the video.

Be careful about what a still frame can prove. A frame shows one moment. A
command visible on screen may be edited, superseded two minutes later, or typed
and then corrected. Check the transcript around the timestamp before recording an
on-screen command as the final answer.

## When frames are not enough

Local sampling fails in specific ways: content that depends on motion rather than
state, a long video where the cap forces sparse coverage, or a demo where the
meaningful change happens between samples.

At that point the options are to re-run with a tighter interval over a bounded
range of the video, or to escalate to a model with native video understanding.

### The Gemini escalation

Google's Gemini API accepts a public YouTube URL directly as a video part and
ingests actual frames, with an agentic mode in which the model chooses what to
inspect. That capability lives in the API, not in any IDE chat panel — selecting
Gemini in an editor's model picker does not provide it.

This skill does not implement that call, for two reasons: it needs an API key
this repository must never hold, and its availability and pricing are moving.
Treat it as a documented escape hatch rather than a step in the pipeline.

To use it, the user supplies a key in the environment, and you write a small
one-off script against the current Gemini API documentation that passes the
YouTube URL as a video input and asks the specific question local frames could
not answer. Check the current docs before writing it; do not rely on a remembered
request shape.

Before escalating, confirm with the user. It sends the video URL and your prompt
to a third-party service and may incur cost. Record in the notes that part of the
analysis came from Gemini rather than from the transcript or local frames.
