---
name: memory-shitlist
description: >-
  Use when the user invokes /skillz:memory-shitlist or asks which running apps waste
  memory on embedded web technology. Audits the running processes on Windows, finds every
  app built on Chromium (Electron, CEF, WebView2 and Chromium browsers), and reports how
  much RAM each one takes. It changes nothing and offers to stop nothing.
argument-hint: "[help]"
allowed-tools: Read, Bash, PowerShell
metadata:
  version: "1.0"
---

# Memory shitlist

An audit of the running software that ships a Chromium engine to draw its user interface.
Electron, CEF and WebView2 apps make development cheaper for their vendors and pass the
cost to the user as RAM. Each window is a browser renderer, each app carries its own copy
of the engine, and the memory grows while the app stays open. On a memory-constrained
machine that cost is no longer acceptable now that writing native code is cheap.

The output is evidence for the user's decision to remove, replace or ban software. This
skill is read-only: it stops nothing, offers to stop nothing, and gives no IDs to stop.

Arguments: `$ARGUMENTS`

If the arguments contain `help`, explain in five lines or fewer what the audit finds, the
kinds it reports, that it changes nothing, and that the figures are working set. Then stop.

## 1. Scan

Run the scan script from this skill's base directory:

```
powershell -NoProfile -ExecutionPolicy Bypass -File "<base>/scripts/Get-MemoryScan.ps1" -MinMB 0 -ChromiumOnly
```

The script changes nothing. It prints:

- `SYSTEM`: total, free and used memory in MB.
- `CHROMIUM`: the memory of all Chromium-based groups together.
- One `GROUP` line for each Chromium-based group: one app with its helper processes. `kind`
  is one of:
  - `Electron`: the app ships Electron (Chromium plus Node.js).
  - `CEF`: the app embeds the Chromium Embedded Framework.
  - `WebView2`: a native app that hosts Microsoft Edge WebView2 for its UI.
  - `Browser`: a Chromium web browser.
  - `Chromium`: Chromium helper processes were found, but the packaging was not recognized.
  `renderers` is the number of renderer processes. For a browser it approximates the
  number of open tabs and windows.

## 2. Make the rows

Make one row for each product. Merge the groups of one product (an app and its updater or
agent, for example). Use the `description` or the executable name for the product name.

Give each row one verdict:

- **Replace**: `Electron`, `CEF`, `WebView2` and `Chromium` apps. The web engine is a
  development shortcut. A native app can do the same job.
- **Trim**: browsers. A browser is the right place for Chromium, but the user can close
  windows and tabs. Give the renderer count.
- **Windows**: groups with the `windows` flag (Search, Widgets). Say which Windows setting
  turns the feature off only when you are certain of it.

Do not leave out small rows. The audit lists every Chromium-based app that runs, at any
size. Do not leave out the current session or Windows components.

## 3. Report

Use this format:

```
**Chromium-based software is using <X> GB of the <used> GB in use (<P>%), on a
machine with <total> GB.**

| App | Kind | Processes | Renderers | MB | Running since | Verdict |
|---|---|---|---|---|---|---|
| Visual Studio Code | Electron | 13 | 3 | **1,159** | 26 Nov 16:25 | Replace |
| Microsoft Edge | Browser | 24 | 18 | **2,310** | 27 Nov 09:02 | Trim (18 renderers) |
| Windows Search | WebView2 | 7 | 1 | 392 | 26 Nov 15:11 | Windows |
```

- Sort the rows by MB, largest first. Make the MB bold for rows of 400 MB or more.
- After the table, give the total for each verdict: Replace, Trim and Windows.
- Add one line: working set counts shared memory more than one time, so the real cost is
  approximately 30% less than the table shows.
- If no Chromium-based software runs, say so in one line.
- Do not recommend a specific replacement product unless you are certain that it is
  native and does the same job.
- Do not offer to stop, close or uninstall anything. The user decides and acts.

## Limits

- Windows only. The script uses Windows PowerShell and CIM.
- Detection reads the files next to each executable. An app that packages Chromium in an
  unusual way shows as `Chromium` when its helper processes carry Chromium arguments, and
  is missed when they do not.
- Processes that run as another user can hide their path. Those are reported by name only.
