---
name: unfuck-sandbox
description: Use when Codex sandboxed commands fail, require repeated escalation, or the user asks to diagnose or repair Codex sandbox configuration. Distinguish launcher, sandbox, policy, and application failures; verify the selected repair.
metadata:
  version: "0.1.0"
---

# Unfuck the sandbox

Fix the user's actual Codex sandbox problem. Explain what failed and what you are doing in plain language. Keep updates short, and report the outcome and any remaining action directly.

1. Reproduce with one harmless sandboxed command. Capture the exact error and whether it occurs before the shell starts. Inspect the active permission profile, relevant configuration, executable path, and bounded sandbox-log failure signatures. Do not read credentials, `.sandbox-secrets`, transcripts, or unrelated data. Identify the actual host and effective settings; a user configuration file alone may not describe the active session.
2. Check current official OpenAI Windows sandbox documentation when relevant: https://learn.chatgpt.com/docs/windows/windows-sandbox. Test hypotheses rather than asserting a root cause from an error code. `CreateProcessAsUserW` error 5 is access denied; a WindowsApps PowerShell alias and an ignored explicit shell override are useful leads, not proof of the cause.
3. On Windows, check the selected implementation and whether MXC is available. On Codex CLI 0.162 or later, the documented one-command probe runs the test **inside MXC** without changing saved configuration:

   ```powershell
   codex -c windows.sandbox=mxc sandbox --include-managed-config --permission-profile :workspace -- cmd.exe /d /c echo MXC_OK
   $LASTEXITCODE
   ```

   Record both output and exit code. If the broken launcher prevents running the probe, use an authorized execution route only to start this narrowly scoped diagnostic; explain that the probe itself remains sandboxed. Do not present general escalation as a fix.
4. Select the smallest supported remedy supported by evidence. If the MXC probe succeeds and policy permits it, `features.prefer_mxc = true` is an option that preserves the configured legacy fallback. Other causes may need different repairs; do not blindly switch modes or disable security. Preserve existing configuration, make a uniquely named backup, validate syntax, and use an atomic update when changing configuration. Respect filesystem permissions and managed policy; never modify installed packages, ACLs, firewall rules, accounts, or security settings without authority for the specific change.
5. Verify both the saved configuration and a **new session's actual sandboxed shell**. A successful compatibility probe does not prove that an already-running session has reloaded settings or that its shell launcher works. If a restart is required, explain that plainly and stop until the user can resume. If it still fails, report exactly what was tested and investigate the selected launcher, WindowsApps alias versus an accessible system-wide executable, policy and sandbox logs. Avoid repeated identical attempts or unsourced configuration keys.

Finish with: what was wrong, what changed, what passed, and what remains. Do not claim a repair is complete until the affected sandboxed command actually works. Preserve unrelated work and do not print secrets or full user command lines from logs.
