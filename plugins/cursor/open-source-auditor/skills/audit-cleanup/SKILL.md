---
name: audit-cleanup
description: >-
  Post-abort janitor for the open-source pre-publication audit. Use after any
  audit run is interrupted, crashed, or resumed — or before starting a new run
  when a previous one did not finish cleanly. Finds orphaned scanner processes
  (ScanCode/python especially), incomplete run folders, and stale artifacts;
  reports first, kills/prunes only on approval. Requires the report folder to
  inspect run artifacts (process cleanup works without it). Triggers: "audit
  cleanup", "check for orphaned scanners", "the audit crashed", "clean up
  before re-running the audit".
argument-hint: <report-folder>
metadata:
  version: "0.2"
  owner: Jarryd Adaens
  stage: maintenance
---

# Audit — Cleanup

Audit runs spawn heavy external processes. When a run is aborted — session
killed, machine rebooted, subagent stopped — those processes are **not**
reliably killed with it. ScanCode is the dangerous one: it buffers all results
in RAM and grows until it finishes or dies, and orphaned instances took a 32 GB
machine down on 2026-07-21/22 (~59 GB of commit across three pythons). Run this
skill after any unclean end, and before starting a fresh run if the previous
one's state is unknown.

## Contract

- **Report first, act second.** Every kill and every folder prune is listed to
  the human before execution; nothing is terminated or deleted silently.
- Never touches a target repo — only processes and the
  `<report-folder>/open-source-audit-report-<repo-name>/` tree.
- `report-folder` is the same path the audit was run with. **If it was not
  explicitly provided, do Step 1 (processes) and Step 3 (headroom) only, and ask
  for it before Step 2** — never guess where run folders live.

## Step 1 — find orphaned scanner processes

```powershell
# Audit-tool processes still alive (python covers ScanCode + uvx tools;
# CommandLine tells you which is which)
Get-CimInstance Win32_Process |
  Where-Object { $_.Name -match '^(python|scancode|gitleaks|trufflehog|syft|grype|trivy|lychee)' } |
  Select-Object ProcessId, Name, CreationDate,
    @{n='PrivMB';e={[math]::Round((Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue).PrivateMemorySize64/1MB)}},
    @{n='CmdLine';e={$_.CommandLine}} |
  Format-List
```

Judge by **command line**, not name: a python belonging to
`uv\tools\scancode-toolkit` or `uvx` is audit tooling; a python belonging to
something else (NVIDIA, an IDE) is not yours to kill. Anything from the audit
toolchain whose parent run is no longer active is an orphan.

**On approval:** `Stop-Process -Id <pid> -Force` — kill the whole set, parents
before workers (ScanCode runs 1 parent + N `--processes` workers).

## Step 2 — find incomplete run folders

A sensor that died mid-run leaves a fingerprint: a `*.stderr.txt` **without its
matching output** (e.g. `scancode.stderr.txt` with no `scancode.json`), or a
`raw/` folder that is empty despite the run folder existing.

```powershell
$auditRoot = "<report-folder>\open-source-audit-report-<repo-name>"
Get-ChildItem $auditRoot -Directory |
  Where-Object { $_.Name -ne 'audit-config' } | ForEach-Object {
  Get-ChildItem $_.FullName -Directory -ErrorAction SilentlyContinue
} | ForEach-Object {
  $raw = Join-Path $_.FullName 'raw'
  $files = @(Get-ChildItem $raw -File -ErrorAction SilentlyContinue)
  $orphanedStderr = $files | Where-Object {
    $_.Name -like '*.stderr.txt' -and
    -not (Test-Path (Join-Path $raw ($_.Name -replace '\.stderr\.txt$', '.json')))
  }
  if ($files.Count -eq 0 -or $orphanedStderr) {
    [PSCustomObject]@{
      Run     = $_.FullName
      Status  = if ($files.Count -eq 0) { 'EMPTY (never produced output)' }
                else { 'INCOMPLETE: ' + ($orphanedStderr.Name -join ', ') }
    }
  }
} | Format-Table -AutoSize -Wrap
```

**On approval:** delete empty run folders (they are noise that makes the report
tree lie about coverage). Incomplete runs: keep the folder if any sensor output
is worth salvaging, otherwise delete and re-run the audit fresh — a partial
`raw/` must never feed the guardrail, since a missing sensor would read as
"no findings."

## Step 3 — sanity-check system headroom

Before green-lighting the next run:

```powershell
$os = Get-CimInstance Win32_OperatingSystem
'{0:N1} GB commit used of {1:N1} GB limit; {2:N1} GB RAM free' -f
  (($os.TotalVirtualMemorySize - $os.FreeVirtualMemory)/1MB),
  ($os.TotalVirtualMemorySize/1MB), ($os.FreePhysicalMemory/1MB)
```

If commit is already near the limit, find and resolve the consumer before
starting an audit — an audit launched into a squeezed machine is how the
2026-07-22 incident compounded.

## Output

A short cleanup summary in chat (processes killed with PIDs and reclaimed MB,
folders pruned, headroom verdict). No file artifact — this skill maintains the
system, it does not produce audit evidence.
