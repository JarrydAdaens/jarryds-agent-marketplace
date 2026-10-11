# Personal plugin authoring

The four family directories are the single authoring source for shared payloads.
Edit them and run `python scripts/generate-packages.py` from the repository root.
Run `python scripts/generate-packages.py --check` to detect drift. The generator
never deletes unknown files; an unowned payload is an error requiring inspection.
It preserves each host's native manifest and catalogs. Every generated package
contains its helpers, protocols, references, and configuration templates.

Claude personas retain capability labels; Codex and Cursor adapters omit Claude
tool/model fields and use the host's configured tools and model. Native persona
registration must be checked in the consuming host; a skill-guided invocation is
an explicit fallback. No adapter embeds a user directory or reads this source
tree from an installed package.

`python scripts/check.py` runs the owning repository's checks. Python, uv, Node,
and the listed test dependencies must be available. UV's cache may need ordinary
write access; dependency acquisition is an environment setup step. The command
does not install a marketplace package or launch a target desktop application.

Generation receipts contain the Git baseline, worktree payload digest, component
version, and target host. An unknown host version and `activation: not_tested`
are deliberate: reproducible files do not prove discovery or activation.

Before rollout, use a disposable host profile and record the host version,
package source revision/digest, fresh-session discovery, and actual activation:

| Family | Appropriate request | Must remain inactive |
| --- | --- | --- |
| Auditor | Audit this repository for publication, reports at a named output | Ordinary bug fix, missing report argument |
| Savior | Migrate the named legacy intake using a named migration root | Ordinary Git maintenance or public publication |
| Game screenshots | Evaluate configured rendering against the approved golden | Documentation edit or silently replacing a failing golden |
| WPF gate | Evaluate requested UI criteria or an explicitly adopted gate | Backend/documentation change or merely finding XAML |

These are rollout scenarios, not claims that live host tests have occurred.
Repository tests check discovery text and the concrete refusal contracts.
