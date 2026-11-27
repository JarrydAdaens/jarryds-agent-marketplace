# skillz

A handful of favorite miscellaneous skills, packaged as one Claude Code plugin so
their lifecycle is managed by the marketplace instead of by file copy. The skills
are unrelated to each other and to any technology stack.

```shell
/plugin install skillz@jarryds-agents
```

## Skills

| Skill | Model can invoke | What it does |
| --- | --- | --- |
| `/skillz:commit-log [--commit] [scope or ticket hint]` | yes | Writes a commit message from a fixed template for git, Perforce, Mercurial, SVN, or similar. Prints it for copying; runs the commit only with `--commit`. |
| `/skillz:grade` | yes | Grades an artifact (code, design, persona, workflow, document, plan) with a decisive letter grade from S to F and short evidence. |
| `/skillz:wtf [the confusing point]` | no | Freezes work and gives a short, literal explanation when an explanation, agent behavior, or work status stops making sense. It cannot edit files or start agents. |
| `/skillz:memory-shitlist [help]` | yes | Audits the running processes on Windows and lists every app built on Chromium (Electron, CEF, WebView2, browsers) with the RAM it uses and a verdict: replace, trim, or Windows component. Read-only; it stops nothing. |
| `/skillz:chimp-out-report <private-output-folder> [roots] [scope]` | yes | Searches local AI conversation archives for operator anger, confusion, and repeated corrections, and writes a searchable report of the workflow failures behind them. |

## Requirements

- `chimp-out-report`: Python 3 (standard library only). Claude Code, Codex, or Cursor
  conversation archives on the local machine.
- `commit-log --commit`: the version-control client for the repository.
- `memory-shitlist`: Windows with Windows PowerShell 5.1.
- The other skills need nothing beyond Claude Code.

## Known limitations

- Claude Code only. There is no Codex or Cursor copy of this plugin.
- `chimp-out-report` requires an explicit output folder and refuses to run without
  one. Reports contain real conversation text, so keep the output folder private
  and outside any public repository.
- `memory-shitlist` reports working set, which counts shared memory once per process,
  so the real cost is lower than the table shows. Detection reads the files next to
  each executable; unusual Chromium packaging can be missed.
- `commit-log` writes this marketplace's structured format. It is not a
  team-specific format; other plugins may provide those.
