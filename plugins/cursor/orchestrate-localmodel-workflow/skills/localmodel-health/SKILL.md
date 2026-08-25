---
name: localmodel-health
description: >-
  Check whether Pi can be launched and the configured local model endpoint can
  be reached, without starting a worker or changing project configuration.
disable-model-invocation: true
---

# Local-model health check

Resolve the installed plugin root. First show the project configuration, then run the bundled non-mutating probe:

```text
node ./scripts/localmodel-config.mjs show --workspace <PROJECT_ROOT>
node ./scripts/pi-rpc-client.mjs --self-check [--probe-url <configured probe_url>]
```

When `probe_url` is null, omit `--probe-url`; the client reads Pi's own `~/.pi/agent/settings.json` and `models.json` configuration. Copy both command outputs verbatim. Report **ONLINE** only when the self-check has a non-null `launch` and `probe.ok` is true. Otherwise report **OFFLINE**, include the probe reason, and state that no worker was launched. A running Pi session is informational; never stop it.
