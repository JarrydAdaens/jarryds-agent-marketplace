# Plan: Split jarryds-agent-marketplace Into Three Per-Host Source Roots

## Metadata

- Task Type: `REFACTOR`
- Status: `Complete`
- Owner: `Jarryd Adaens`
- Last Updated: `17 August 2026`

## Linked Context

- Milestone: `context/implementation-plans/milestone-per-ide-marketplace/` (no `context/milestones/` document exists yet; the milestone is defined by this folder)
- Story: none recorded; this plan is the story of record
- Related Plans:
  - `context/implementation-plans/milestone-local-model-orchestration/orchestrate-localmodel-workflow/plan.md` — **In Progress.** Its remaining steps and its already-landed paths reference `plugins/orchestrate-localmodel-workflow/`. Amend those paths after this split; do not block the split on that story.
- Precedent: `agentic_rails_marketplace` commit `31923e0` (`[BUG] - Fix Windows BOM silently disabling every Cursor write gate`) — the commit that actually split `plugins/` into `plugins/claude/`, `plugins/codex/`, and `plugins/cursor/` (8 / 5 / 11 folders) and repointed the three catalogs. Merged to `main` as PR #1 (`8e6091b`) on 17 August 2026. The planning artifact for that split is `agentic_rails_marketplace/context/implementation-plans/milestone-per-ide-marketplace/split-plugins-by-host/plan.md`.
- External Tooling: none required. This is a mechanical layout change. Do not run `rails-planning-phaser`; CER is under threshold and the work is one reviewable change.

## CER

- Complexity: `3`
- Effort: `3`
- Risk: `3`
- Notes: Hand-graded against the rails-grade-cer axes. Complexity is low — membership is already declared by per-plugin `.{host}-plugin/plugin.json` files, there is no runtime host-branching to delete (these plugins are skills/agents/scripts, not hook gates), and the target layout is a known copy of the rails marketplace. Effort is about two hours of mid-engineer time: five `git mv`s, ten copies, a prune of foreign manifests, three catalog rewrites, and the layout docs. Risk, read from the objective alone, is a personal experimental marketplace whose install paths can strand until the next push; recovery is a git revert. This is deliberately simpler than the rails split (CER 5/6/5), which had to delete host-branching in safety-critical gates and land cross-tree tests in the same change.

## Objective

Replace the single `plugins/<plugin-name>/` tree — where one payload carries three host manifests and every catalog is kept in sync — with three independent source roots, `plugins/claude/`, `plugins/codex/`, and `plugins/cursor/`, matching the layout `agentic_rails_marketplace` already shipped. Each root holds only the plugins that host already supports. A plugin supported on more than one host is duplicated into each of those roots and then pruned to a single host manifest. Hosts a plugin does not already support do not get a new copy. After this lands, work on a Cursor plugin cannot break a Claude or Codex copy, because they are separate folders.

## Scope

### In Scope

- Create `plugins/claude/`, `plugins/codex/`, and `plugins/cursor/`.
- Distribute the five existing plugins into those roots according to the membership table below.
- Prune every copy to exactly one host manifest, matching its parent root.
- Repoint each catalog at its own subtree only.
- Drop the "keep all three catalogs in sync" rule from `AGENTS.md` and describe the new layout in `AGENTS.md` and `README.md`.
- Update the `.gitignore` un-ignore for the game-verifier `lib/` so copies under all three roots stay tracked.
- Amend path references in the in-progress `orchestrate-localmodel-workflow` plan so later execution does not write to a dead path.

### Out Of Scope

- Installing, smoke-testing, or otherwise verifying the marketplace in any IDE. That happens later, when the plugins are used. Further fixes can be pushed then.
- Behavioral changes to any plugin. The split copies what exists; it does not improve, port, or rewrite payloads.
- Adding a host a plugin does not already support. No new `.claude-plugin/`, `.cursor-plugin/`, or `.codex-plugin/` files.
- A `plugins/pi/` root. This repository has no Pi catalog and no Pi package; do not invent one.
- `source/skills/`. Those are still unpackaged file-copy skills, not marketplace plugins.
- Cross-tree drift tests, VM harnesses, payload fixtures, or `claude plugin validate .` as a gate. The rails marketplace needed those because its plugins are hook gates; this one does not, and the owner has deferred verification.
- Bumping Codex `version` fields. The payload is unchanged; a path move is not a plugin update.

## Non-Goals

- Deduplicating the resulting copies behind a shared library or a generation step. Drift is accepted; a sync mechanism would re-create the coupling this split exists to remove.
- Renaming any plugin. `name` stays stable across trees — only the catalog `source` path changes.
- Making the three trees identical after this change. They start as copies and are free to diverge.
- Recollapsing later. There is no reversal condition to record here; this marketplace is experimental and the isolation is the point.

## Current Understanding

### Why the current shape stopped working

`AGENTS.md` currently mandates the opposite of isolation:

> **Keep all three catalogs in sync.** Adding or removing a plugin means updating `.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json`, and `.agents/plugins/marketplace.json`, plus all three per-plugin manifests.

That rule is why every plugin folder today carries `.claude-plugin/`, `.cursor-plugin/`, and `.codex-plugin/` side by side, and why all three catalogs list all five plugins. It is the same author-once shape `agentic_rails_marketplace` tried, and it failed there for the same reason it is failing here: an edit made for one IDE lands in the shared folder and can break another IDE's install. The owner has already hit this — Cursor plugin work has broken Claude plugins. The rails marketplace solved it on 16–17 August 2026 by splitting into per-host roots (commit `31923e0`, merged as `8e6091b`). This repository still looks like the rails marketplace *before* that commit.

These plugins have no hook-level host branching to delete. The payoff here is isolation of the folder, not simplification of a gate. That is enough. The mashed-together tree is blocking progress today.

### Membership is already declared by manifests

Do **not** use catalog listings as the support signal. The catalogs currently list every plugin on every host *because* of the keep-in-sync rule this plan removes. Support is the presence of a real `.{host}-plugin/plugin.json` inside the plugin folder. Inspected 17 August 2026, every plugin has all three:

| Plugin | claude | codex | cursor |
| --- | :---: | :---: | :---: |
| `open-source-auditor` | ● | ● | ● |
| `repository-savior` | ● | ● | ● |
| `game-golden-screenshot-verifier` | ● | ● | ● |
| `wpf-visual-quality-gate` | ● | ● | ● |
| `orchestrate-localmodel-workflow` | ● | ● | ● |

| Root | Count | Rule |
| --- | --- | --- |
| `plugins/claude/` | 5 | has `.claude-plugin/plugin.json` |
| `plugins/codex/` | 5 | has `.codex-plugin/plugin.json` |
| `plugins/cursor/` | 5 | has `.cursor-plugin/plugin.json` |

15 folders, from 5. No plugin is host-only today, so no plugin is omitted from a root. If a later plugin lands with only one manifest, it goes in only that host's root — that is the new rule, not a special case.

READMEs already claim Claude Code, Codex, and Cursor for all five. The visual verifiers are "skills only, no hooks"; the auditor, savior, and orchestrate plugins ship personas + skills + scripts. Nothing here registers a host-specific hook file, so pruning is manifests only.

### Likely files and directories

- `plugins/` — the five existing folders, all moving. After the split, `plugins/` contains only `claude/`, `codex/`, and `cursor/`.
- `.claude-plugin/marketplace.json` — Claude catalog, currently `source: "./plugins/<name>"` for all five. Repoint to `./plugins/claude/<name>`.
- `.cursor-plugin/marketplace.json` — Cursor catalog, currently `source: "./plugins/<name>"`. Repoint to `./plugins/cursor/<name>`.
- `.agents/plugins/marketplace.json` — Codex catalog, currently `source.path: "./plugins/<name>"`. Repoint to `./plugins/codex/<name>`.
- `AGENTS.md` — Layout section and the keep-in-sync hard rule.
- `README.md` — Layout, Cursor local-copy instructions (currently `plugins/open-source-auditor` → must become `plugins/cursor/open-source-auditor`), and the installable-plugins table paths.
- `.gitignore` — two negation lines pin the game-verifier `lib/` against a global `lib/` ignore. Those paths break the moment the folder moves.
- `context/implementation-plans/milestone-local-model-orchestration/orchestrate-localmodel-workflow/plan.md` — remaining work still names `plugins/orchestrate-localmodel-workflow/`.

### Existing behaviors to preserve

- Plugin `name` is a stable identifier. Do not rename.
- No `version` in `.claude-plugin/plugin.json` or `.cursor-plugin/plugin.json`. Codex keeps its existing `version` values unchanged (`open-source-auditor` 0.4.0, `repository-savior` 0.1.0, `game-golden-screenshot-verifier` 2.0.0, `wpf-visual-quality-gate` 1.1.0, `orchestrate-localmodel-workflow` 1.0.0).
- A plugin cannot reference files outside its own folder. The split deepens the path by one level and does not change this.
- `source/skills/` stays at the repo root, unpackaged.
- Catalog identity names stay `jarryds-agents`. Do not rename the marketplace.

### Assumptions and constraints

- Each host reads only its own catalog, so the same plugin `name` in all three trees cannot collide — no host ever sees two.
- Git rename detection follows only one copy. Cursor inherits history (`git mv`); Claude and Codex copies start fresh. Cursor is the host whose work is currently breaking the others, so its history is the one worth keeping readable. Same choice the rails split made.
- This repository is public (`JarrydAdaens/jarryds-agent-marketplace` assumed from sibling naming; confirm remote if a migration note needs a URL). Marketplace registration by URL needs no credentials.
- Windows execution: use `git mv` and PowerShell `Copy-Item`, not `cp -r`.
- `.pytest_cache/` under `repository-savior` is gitignored. `Copy-Item` may copy it onto disk; do not `git add` it.
- The owner has deferred install verification. Do not stall the split on a marketplace round-trip.

## Questions / Unknowns

- Q: Does each vendor treat a catalog entry whose `name` is unchanged but whose `source` path moved as an **update** to the installed plugin, or as a different plugin?
  Impact: Existing installs may strand a stale copy until the owner reinstalls. That is an inconvenience, not a blocker — this marketplace is personal and experimental, and verification is explicitly later.
  Assumption: Treat it as "reinstall later if an IDE looks stale." Do not spend time on a VM experiment. Do not invent a `renames` map; this repo has never used one.
  Status: `ANSWERED` (accepted, not investigated)
  Answer: Deferred to post-split use. If a host strands, uninstall and reinstall from the new path. Record whatever is observed then; do not block this change on it.

- Q: Should Cursor inherit git history, as the rails split did?
  Impact: Only one `git mv` per plugin preserves rename detection.
  Assumption: Yes — Cursor is the host under active churn and the reason this split is happening today.
  Status: `ANSWERED`
  Answer: Cursor inherits history. Claude and Codex are copies.

No other open questions. Membership, Pi, testing, and drift are decided by the user in the request that produced this plan.

## Execution Steps

1. **Create the three host roots and move every plugin under Cursor.**
   - Why: One `git mv` per plugin preserves history on the tree that is currently being edited. A pure move, reviewable as a move, with no pruning yet.
   - Edits: From the repository root, in PowerShell:
     ```powershell
     New-Item -ItemType Directory -Force -Path plugins/claude, plugins/codex, plugins/cursor | Out-Null
     foreach ($name in @(
       'open-source-auditor',
       'repository-savior',
       'game-golden-screenshot-verifier',
       'wpf-visual-quality-gate',
       'orchestrate-localmodel-workflow'
     )) {
       git mv "plugins/$name" "plugins/cursor/$name"
     }
     ```
     After this step `plugins/` contains only `claude/`, `codex/`, and `cursor/`, and `plugins/cursor/` holds all five folders still carrying all three manifests.
   - Dependencies: none.

2. **Copy each Cursor folder into the Claude and Codex roots.**
   - Why: Every plugin in the membership table is supported on all three hosts, so every plugin is duplicated. Do not invent a fourth copy, and do not skip a host that already has a manifest.
   - Edits:
     ```powershell
     foreach ($name in @(
       'open-source-auditor',
       'repository-savior',
       'game-golden-screenshot-verifier',
       'wpf-visual-quality-gate',
       'orchestrate-localmodel-workflow'
     )) {
       Copy-Item -Recurse "plugins/cursor/$name" "plugins/claude/$name"
       Copy-Item -Recurse "plugins/cursor/$name" "plugins/codex/$name"
     }
     ```
     If `Copy-Item` brings along `plugins/*/repository-savior/.pytest_cache`, leave it on disk; `.gitignore` keeps it out of the index.
   - Dependencies: Step 1.

3. **Prune each copy to its own host manifest.**
   - Why: A folder with more than one `.*-plugin/` directory is the mashed-together bug in miniature. After this step, a Cursor edit cannot touch a Claude manifest because that file is no longer in the Cursor tree.
   - Edits: Delete the two foreign manifest directories from every copy:
     | Root | Keep | Delete |
     | --- | --- | --- |
     | `plugins/claude/<name>/` | `.claude-plugin/` | `.cursor-plugin/`, `.codex-plugin/` |
     | `plugins/codex/<name>/` | `.codex-plugin/` | `.claude-plugin/`, `.cursor-plugin/` |
     | `plugins/cursor/<name>/` | `.cursor-plugin/` | `.claude-plugin/`, `.codex-plugin/` |
     There are no `hooks.json` / `cursor-hooks.json` files, no `docs/hosts/`, and no runtime host-detection in these payloads. Pruning stops at the manifests. Do not rewrite skills, agents, scripts, or READMEs in this step.
   - Dependencies: Step 2.

4. **Fix the `.gitignore` `lib/` un-ignore before staging the copies.**
   - Why: The global `lib/` ignore would otherwise drop `game-golden-screenshot-verifier`'s `skills/.../lib/` from the two new trees. The current negations name the pre-split path and will not match after the move.
   - Edits: In `.gitignore`, replace:
     ```
     !plugins/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/
     !plugins/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/**
     ```
     with the three host paths:
     ```
     !plugins/claude/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/
     !plugins/claude/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/**
     !plugins/codex/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/
     !plugins/codex/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/**
     !plugins/cursor/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/
     !plugins/cursor/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/**
     ```
     Confirm `git status` shows `lib/capture.py`, `lib/compare.py`, `lib/config.py`, and `lib/__init__.py` tracked under all three roots before committing.
   - Dependencies: Step 2. Can run in parallel with Step 3.

5. **Repoint the three catalogs at their own subtrees.**
   - Why: Each host must resolve its own root and nothing else. Catalog `name` values stay exactly `jarryds-agents` / plugin names unchanged.
   - Edits:
     - `.claude-plugin/marketplace.json` — every `source` becomes `./plugins/claude/<name>`.
     - `.cursor-plugin/marketplace.json` — every `source` becomes `./plugins/cursor/<name>`.
     - `.agents/plugins/marketplace.json` — every `source.path` becomes `./plugins/codex/<name>`. Keep the Codex `{ "source": "local", "path": "..." }` object shape; only the path string changes.
     Do not add, remove, or reorder plugins. Do not add a `renames` map.
   - Dependencies: Step 1 (paths must exist). Prefer after Step 3 so a catalog never points at a folder that still has three manifests, but the catalogs do not inspect manifests, so this is sequencing hygiene rather than a hard gate.

6. **Rewrite the layout docs and drop keep-in-sync.**
   - Why: `AGENTS.md` currently orders the executor to keep the mashed-together shape. Leaving that rule in place would undo the split on the next plugin add.
   - Edits:
     - `AGENTS.md` Layout: catalogs list only their own host root (`./plugins/<host>/<name>`). `plugins/` is three host roots, each plugin folder carries exactly one host manifest, and a plugin folder with more than one `.*-plugin/` directory is a bug. A plugin supported on more than one host is a separate copy, free to drift.
     - `AGENTS.md` Hard rules: **delete** "Keep all three catalogs in sync." Replace with: adding a plugin means adding it only to the hosts that actually support it — create the folder under `plugins/<host>/`, add that host's manifest only, and list it only in that host's catalog. Do not add a stub manifest "for completeness."
     - `AGENTS.md` Validate-before-commit: drop the implication that every plugin must have all three manifests. Claude validate still applies to the Claude tree; Cursor/Codex checks apply to their own trees.
     - `README.md` Layout: same three-root picture. Cursor local-copy step 1 currently says copy `plugins/open-source-auditor` to `%USERPROFILE%\.cursor\plugins\local\open-source-auditor\` — change the example to `plugins/cursor/open-source-auditor`. Plugin table README links become `plugins/<host>/<name>/README.md` or a Cursor-tree example; do not list three paths per row.
     - Plugin READMEs: only retouch install sentences that name a pre-split folder path. Leave payload documentation alone.
   - Dependencies: Steps 1–5, so the docs describe what is on disk.

7. **Amend the in-progress orchestrate plan's paths.**
   - Why: That plan is still In Progress (dry-run and fault injection not done) and names `plugins/orchestrate-localmodel-workflow/` in Scope, Constraints, Execution Steps, and the Execution Log. Leaving it pointed at a deleted folder will send the next session to write the mashed-together shape back.
   - Edits: In `context/implementation-plans/milestone-local-model-orchestration/orchestrate-localmodel-workflow/plan.md`, replace `plugins/orchestrate-localmodel-workflow/` with `plugins/<host>/orchestrate-localmodel-workflow/` (and note that Claude/Codex/Cursor are independent copies). Add a one-line revision note under Metadata: paths updated after the per-host split, `Last Updated` set. Do not otherwise revise that story.
   - Dependencies: Step 1.

8. **Stage, inspect, commit when asked.**
   - Why: The catalogs, the trees, and the docs must land together so no intermediate commit advertises a layout that is not on disk.
   - Edits: `git add` the three roots, the three catalogs, `AGENTS.md`, `README.md`, `.gitignore`, and the amended orchestrate plan. `git status` must show no leftover `plugins/<name>/` at the old depth. Do not commit until the owner asks.
   - Dependencies: Steps 1–7.

## Validation

### Automated Checks

None required for this story. The owner has deferred marketplace testing. Do not add a test suite as part of this split.

Optional sanity, not a gate:

- `git ls-files "plugins/*"` shows only `plugins/claude/`, `plugins/codex/`, and `plugins/cursor/` prefixes.
- `git ls-files "plugins/*/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/*"` lists the lib files under all three roots.

### Manual Checks

Deferred. When the owner next installs or uses a plugin:

1. Claude Code / Codex: marketplace update or reinstall if the old path looks stale.
2. Cursor local: recopy from `plugins/cursor/<name>/` into `%USERPROFILE%\.cursor\plugins\local\<name>\`, then Reload Window.
3. If a host still serves a pre-split copy, uninstall and reinstall rather than debugging the old cache.

Those observations belong in this plan's `## Execution Log` / `## Complaints / Friction` after the fact, not in this change.

### Acceptance Criteria

- `plugins/` contains exactly three directories: `claude/`, `codex/`, and `cursor/`, each holding the five plugin folders named in the membership table.
- Every plugin folder contains exactly one `.*-plugin/` directory, and it matches its parent root (`.claude-plugin` under `claude/`, `.codex-plugin` under `codex/`, `.cursor-plugin` under `cursor/`).
- Each catalog lists only its own host's plugins, with `source` / `source.path` of `./plugins/<host>/<name>`. Plugin `name` values are unchanged. Marketplace catalog `name` remains `jarryds-agents`.
- No plugin folder remains at `plugins/<name>/` (the old depth).
- `source/skills/` is untouched.
- `.gitignore` un-ignores the game-verifier `lib/` under all three host roots, and those files are tracked.
- `AGENTS.md` no longer says to keep all three catalogs in sync, and describes one-manifest-per-folder as the rule.
- `README.md` Cursor local-copy instructions point at `plugins/cursor/<name>/`.
- The orchestrate-localmodel-workflow plan no longer names the pre-split plugin path as a live edit target.
- Codex `version` fields are unchanged from the values listed under Existing behaviors.

## Risk Mitigation

- Risk: The split converts "one edit breaks three hosts" into "one fix misses two hosts."
  Mitigation: Accepted. The owner stated that drift is fine and that this collective marketplace is experimental. Do not add cross-tree tests as part of this change.

- Risk: A vendor treats the moved `source` path as a new plugin and strands the installed copy.
  Mitigation: Accepted for now. Reinstall from the new path when next using that host. Do not block the split on a VM check.

- Risk: Two of three trees lose readable git history per plugin.
  Mitigation: Accepted. History follows Cursor. Pre-split history remains in the git log; only rename-following across the copy boundary is lost.

- Risk: The global `lib/` gitignore drops the game-verifier library from the Claude and Codex copies, so those installs miss capture/compare/config.
  Mitigation: Step 4 is mandatory and is checked by `git ls-files` before commit.

- Risk: The in-progress orchestrate plan writes the old path back and recreates the mashed-together folder.
  Mitigation: Step 7 amends that plan in the same change as the split.

- Risk: `Copy-Item` copies `.pytest_cache` into the new trees.
  Mitigation: `.gitignore` already lists `.pytest_cache/`. Do not `git add -f` it.

## Evidence / References

- Rails marketplace split as shipped: `agentic_rails_marketplace` commit `31923e0` (16 August 2026), merged `8e6091b` (17 August 2026, PR #1). Resulting layout is `plugins/claude/` (8), `plugins/codex/` (5), `plugins/cursor/` (11), plus a non-peer `plugins/pi/` that this repository does not copy. Design text: `agentic_rails_marketplace/context/design.md` §4. Agent rules: `agentic_rails_marketplace/AGENTS.md` Layout ("A plugin folder with more than one `.*-plugin/` directory is a bug").
- Rails planning artifact this plan mirrors, then strips of VM/fixture/test requirements the owner waived: `agentic_rails_marketplace/context/implementation-plans/milestone-per-ide-marketplace/split-plugins-by-host/plan.md`.
- Current mashed-together rule: `jarryds-agent-marketplace/AGENTS.md` line "Keep all three catalogs in sync."
- How this repo grew the mashed shape: `fe20b68` (Cursor dual-layout manifests on the then-Claude-only auditor and savior), `28a301f` (Codex dual-layout, "three-vendor dual layout — Claude, Cursor, and Codex share one skills/agents payload"), `d6e2440` (game and WPF verifiers added with all three manifests from day one), `b72fb04` (orchestrate-localmodel-workflow, same three-manifest pattern).
- Membership inspected from disk, 17 August 2026: all five plugins have `.claude-plugin/plugin.json`, `.cursor-plugin/plugin.json`, and `.codex-plugin/plugin.json`. All three catalogs list all five. No hooks directories exist under `plugins/`.
- `.gitignore` footgun: global `lib/` with negations only at `plugins/game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier/lib/`.
- In-progress consumer of the old path: `context/implementation-plans/milestone-local-model-orchestration/orchestrate-localmodel-workflow/plan.md` Execution Log ("Implemented 17 August 2026 … as `plugins/orchestrate-localmodel-workflow/`"); steps 9–10 still open.

## Complaints / Friction

### The keep-in-sync rule is what made Cursor work unsafe for Claude

**What happened:** Adding Cursor and then Codex was done by placing a second and third manifest beside a shared payload and requiring all three catalogs to list the same plugins.

**Why this made the task harder:** Any edit for one IDE is an edit to the only copy the other IDEs install. The rails marketplace already demonstrated that this fails in practice; this repo copied the pre-split shape anyway because that was the documented rule.

**What was tried:** Thin per-tool manifests with a shared `skills/` / `agents/` payload (`fe20b68`, `28a301f`). That is exactly the author-once principle the rails marketplace later abandoned.

**What would improve this:** The split. Unlike the rails marketplace, there is no gate logic to prune and no test suite that must land in the same commit. Isolation of the folder is the whole fix.

**What I think:** Do not re-introduce "keep catalogs in sync" as a courtesy. A plugin that is only useful on Cursor should exist only under `plugins/cursor/`.

## Execution Log

Executed 17 August 2026.

| Step | Result |
| --- | --- |
| 1 Move to Cursor | `git mv` of all five plugins into `plugins/cursor/`. |
| 2 Copy | `Copy-Item` into `plugins/claude/` and `plugins/codex/`. |
| 3 Prune | Foreign `.*-plugin/` directories removed from each copy; one manifest per folder verified. |
| 4 `.gitignore` | Game-verifier `lib/` un-ignore extended to all three host roots; 12 lib files tracked. |
| 5 Catalogs | All three `marketplace.json` files repointed to `./plugins/<host>/<name>`. |
| 6 Docs | `AGENTS.md` and `README.md` updated; keep-in-sync rule removed. |
| 7 Orchestrate plan | Paths amended to `plugins/<host>/orchestrate-localmodel-workflow/`. |
| 8 Stage | `git add -A`; changes staged, not committed. |

Install verification deferred per plan.
