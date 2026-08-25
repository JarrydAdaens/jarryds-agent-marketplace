---
name: localmodel-timeout
description: View or persist the local Pi worker idle and think-grace supervision timeouts.
argument-hint: "[idle|think] [seconds|default]"
disable-model-invocation: true
---

# Local-model supervision timeouts

From the installed plugin root, run:

```text
node ./scripts/localmodel-config.mjs timeout --workspace <PROJECT_ROOT> --timeout <idle|think> <SECONDS|default>
```

With no user value, omit `--timeout` and show the status screen. `idle` is the silence period before the client checks worker liveness; `think` is reachable, low-CPU silence before it declares the worker hung. Both must be positive whole seconds. `default` restores idle to 180 seconds or think grace to 900 seconds. Copy stdout verbatim.
