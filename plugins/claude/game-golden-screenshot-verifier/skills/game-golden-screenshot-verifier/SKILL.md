---
name: game-golden-screenshot-verifier
description: Use when asked to verify game rendering against an approved screenshot or when the project explicitly adopts this verifier.
metadata:
  version: "2.0"
---

# Game Golden-Screenshot Verifier

A one-command runtime verifier an agent can run unattended to answer "does the
game still boot and render correctly?" The runner (`run_eval.py`, next to this
file) ships in the plugin and never moves into the project; the project owns a
small **seam folder** holding everything game-specific. Requires Python 3.10+
and `uv` (dependencies are declared inline in the runner and install on first
`uv run`), plus a real desktop session for screen capture and input.

Throughout, `<skill-dir>` means the directory containing this SKILL.md, and
`<seam-dir>` means the project's seam folder.

## First-time setup in a project

1. Create the seam folder — `harness/game-golden-screenshot/` by convention
   (any location works; all relative paths in the config resolve against it).
2. Copy `<skill-dir>/eval_config.example.json` to `<seam-dir>/eval_config.json`
   and fill in the executable path, launch arguments, window title, capture
   size, threshold, timeout, and warmup/settle delays. Relative paths resolve
   against `<seam-dir>`, so an executable elsewhere in the repo needs `../`
   segments or an absolute path.
3. Copy `<skill-dir>/drivers/input_stub.py` to `<seam-dir>/drivers/` and
   replace its `drive()` body with the game's real route to a repeatable
   visual state (launch flag into a fixed scene, scripted menu path, or a
   static screen needing no input — the stub's docstring ranks the options).
   The stub only moves the mouse and taps Shift; it does not produce a
   meaningful scene.
4. Add to the project's `.gitignore`:

   ```gitignore
   # Transient game-verifier run artifacts
   harness/game-golden-screenshot/last-run/
   ```

5. Verify the install without a game: `uv run "<skill-dir>/run_eval.py" --self-test`

## Capturing a golden

Only after the user explicitly approves reference creation or replacement. First
run eval to capture `last-run/current.png` (a missing golden fails after capture);
inspect the candidate and record the approval. Promote the inspected candidate:

```bash
uv run "<skill-dir>/run_eval.py" --config "<seam-dir>/eval_config.json" --mode golden --approve-reference --reference-candidate "<seam-dir>/last-run/current.png"
```

The prior reference is retained beside it with its SHA-256 in the backup name.
Never refresh a golden merely to make a failing evaluation pass. Direct capture
with an explicitly approved reference update is also available:

```bash
uv run "<skill-dir>/run_eval.py" --config "<seam-dir>/eval_config.json" --mode golden --approve-reference
```

Review `<seam-dir>/goldens/golden.png` by eye, then commit it. Goldens are
versioned, human-approved reference images.

## Running the verifier

```bash
uv run "<skill-dir>/run_eval.py" --config "<seam-dir>/eval_config.json"
```

Exit 0 = pass, 1 = fail. Every run writes its artifacts to
`<seam-dir>/last-run/` (`current.png` and `golden.png`) for side-by-side
inspection. A crash, early exit, or failed capture is always a hard fail —
never a silent pass.

## Tuning

The similarity metric is the mean absolute per-pixel RGBA difference mapped to
`accuracy = 1 − meanAbsDiff/10`, scored out of 100; identical images score 100
and the default threshold is 95. It is sensitive: for scenes with unavoidable
noise (animation, particles), lower `threshold` or capture a `region` that
excludes the noisy area. A capture/golden size mismatch fails loudly rather
than scoring low.

## Activation and scope

Run only for the explicit request or adopted project workflow described above.
A file extension, repository discovery, documentation edit, or unrelated code change
does not authorize this operation. Require the user or project packet to name the
output location before writing project artifacts.
