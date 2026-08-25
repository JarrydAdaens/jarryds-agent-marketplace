---
name: localmodel-init
description: >-
  Create harness/orchestrate-localmodel-workflow/cursor-config.json with the
  local Pi worker model and liveness-timeout defaults. Use when configuring the
  local-model workflow for a project for the first time.
disable-model-invocation: true
---

# Local-model workflow init

Resolve the installed plugin root, then run this from that root against the project workspace:

```text
node ./scripts/localmodel-config.mjs init --workspace <PROJECT_ROOT>
```

If the user explicitly wants fresh defaults, add `--force`. Copy stdout verbatim. The config is JSONC and is created at `harness/orchestrate-localmodel-workflow/cursor-config.json`; it is project-scoped, not a file in the plugin cache. Suggest `/localmodel-health` after initialization.
