---
name: localmodel-model
description: View or persist the Pi model slug used by new local-model workflow workers.
argument-hint: "[1|2|model-slug]"
disable-model-invocation: true
---

# Local-model worker model

Resolve the installed plugin root and run from it against the project workspace:

```text
node ./scripts/localmodel-config.mjs model --workspace <PROJECT_ROOT> --model <USER_VALUE>
```

With no user value, omit `--model` and present the resulting menu. Option `1` is `qwen3.8`; option `2` is `local-model-placeholder`. A valid Pi model slug is also accepted. Copy stdout verbatim. The selection is persisted only in `harness/orchestrate-localmodel-workflow/cursor-config.json` and is passed to each subsequent worker as Pi's `--model` value.
