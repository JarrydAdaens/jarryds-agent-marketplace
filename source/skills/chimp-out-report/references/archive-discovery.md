# Archive discovery and format limits

Use the profile and environment on the machine being audited. Never bake the
author's username, drive letters, repositories, transcripts, or report paths into
the skill. The helper's `--home` redirects profile discovery; environment overrides
are honored only for the actual current profile. `--root provider=path` adds an
explicit archive/export source and can be repeated. It does not remove normal
discovery. Record missing and unreadable locations separately.

## Sources to check

| Host | Common local roots | Readable evidence and follow-up |
| --- | --- | --- |
| OpenAI Codex | `$CODEX_HOME`, otherwise `~/.codex`; `sessions/`, `archived_sessions/`, `history.jsonl`; versioned state/thread-history SQLite files | Read `response_item` messages or user events as fallback, not both as new incidents. `.jsonl.zst` is important for older threads. Session metadata supplies thread ID, cwd, and subagent provenance. SQLite projections can supply recent messages absent from rollouts. |
| Claude Code | `$CLAUDE_CONFIG_DIR`, otherwise `~/.claude`; `projects/`, archived/exported JSONL, `history.jsonl` | User/assistant message envelopes with actual text blocks. Tool results and injected/meta messages are not owner speech. `isSidechain` and subagent directories identify delegated work. Prompt history often outlives full transcripts; label it as prompt-only. |
| Cursor | `~/.cursor/projects/*/agent-transcripts/`, `~/.cursor/chats/`; application User/globalStorage and User/workspaceStorage | Exported JSONL and older `user:`/`assistant:` text transcripts; CLI prompt histories and store.db JSON blobs; desktop `cursorDiskKV` composer/bubble records. Prefer exported chronological transcripts over blob insertion order. Read explicit `<user_query>` content; exclude injected context. |
| Antigravity | `~/.gemini/antigravity/`, `antigravity-cli/`, `antigravity-ide/`, backups; `conversations/`, history/export files | JSON histories/exports and SQLite JSON message tables are readable. Many `.pb` and `steps.step_payload` archives use protobuf or encrypted payloads. Locate and count them; use a verified local schema/decoder or an existing export if available. Do not identify their author from printable strings. |
| Windsurf | `~/.codeium/windsurf/cascade/`, `database/`, `~/.windsurf/`, application data | Cascade archives may be binary/protobuf/encrypted. Search readable exports and supported JSON message tables; record opaque archives explicitly. Brain/task files are corroborating artifacts, not automatically original owner messages. |
| Gemini CLI | `$GEMINI_CLI_HOME`, `~/.gemini/tmp/*/chats/`, history/export files | Session JSON with messages, timestamps, role/type; distinguish human text from tool envelopes. |
| Pi | `~/.pi/agent/sessions/` | JSONL session header and `message` events. Exclude tool result and reasoning blocks. |
| GitHub Copilot CLI | `~/.copilot/session-state/`, `~/.copilot/history-session-state/` | JSONL events such as `user.message`, `assistant.message`, session metadata. Logs may retain only operational events; do not treat log strings as operator utterances. |
| Cline / Roo Code | VS Code-family User/globalStorage extension directories, task subdirectories | `api_conversation_history.json` contains role-aware messages; UI history such as `ui_messages.json`/`cline_messages.json` needs its own verified mapping. User-role tool results are not human messages. |
| Continue | `~/.continue/sessions/` and exports | JSON `history` entries often wrap a `message` object with role/content. Verify role and conversation ID. |
| T3 | `~/.t3/userdata/state.sqlite` | `projection_thread_messages` joined with thread metadata. Source provider can differ from the frontend; do not double-count the provider's own archived copy. |
| Other hosts / exports | `~/.config`, application-specific roots, user-selected export directories | Search filenames before content. Use role-aware JSON/JSONL/export adapters when the schema is recognizable. Report unknown schemas rather than inferring author from arbitrary text. |

For desktop app data, Windows commonly uses `%APPDATA%/<app>/User/`; macOS uses
`~/Library/Application Support/<app>/User/`; Linux uses
`${XDG_CONFIG_HOME:-~/.config}/<app>/User/`. Cursor, Windsurf, Antigravity, Code,
Code - Insiders, and VSCodium may each carry relevant extension storage. Inspect
the existing app names, including case variants. Follow explicitly configured
portable/profile paths when discovered; this table is a starting inventory.

## Read-only database handling

The helper reads copied database snapshots, including an adjacent WAL when present,
inside a temporary private directory. It never opens source databases for writing
or treats an immutable main-file-only read as complete live history. A stable
main/WAL copy with SQLite integrity checks is still not an atomic application
export; concurrent updates or locked files must appear in the coverage ledger.
Temporary copies are removed after each source. If a verified native read-only
history API offers a better snapshot, prefer it and record how it was obtained.

## Coverage and chronology

The helper emits a coverage entry for every discovered source file and a root
entry even when a required host is absent. Statuses include searched, partial,
unsupported, unreadable, and missing. A successful empty prompt history is not
evidence that the whole host has no conversations.

Keep original UTC timestamps and explicit local offsets. Display dates without
inventing the reader's timezone. Preserve absent dates as unknown. Blob insertion
order, workspace-grouped history, and file mtime cannot establish the order of a
conversation. Inherited fork messages must not count as independent evidence.

If a file changes during collection, report that the snapshot may be incomplete.
If one malformed record can be isolated, retain other readable records and log
the failing locator. Long user messages may contain a short genuine correction:
extract explicit human-query sections and rank a bounded excerpt rather than
dropping all long messages. Keep enough original text for later source review.
