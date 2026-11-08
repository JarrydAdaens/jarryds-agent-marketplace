#!/usr/bin/env python3
"""Local, role-aware conversation triage. No network, source writes, or LLM calls."""
import argparse
import collections
import contextlib
import csv
import datetime as dt
import hashlib
import html
import io
import json
import os
import pathlib
import platform
import re
import shutil
import sqlite3
import sys
import tempfile
import uuid

VERSION = '1.0'
PATTERNS = {
    'profanity': r'\b(?:fuck\w*|bullshit|shit|piss(?:ed)?\s+off|ffs)\b',
    'direct-insult': r'\b(?:retard(?:ed)?|idiot|moron|fuckwit|asshole|arsehole|cunt|dipshit|dickhead|imbecile|incompetent|useless)\b',
    'what-the-fuck': r'\bwhat\s+(?:the\s+)?fuck\b|\bwtf\b',
    'for-fucks-sake': r'\bfor\s+fuck[\x27’]?s?\s+sake\b|\bffs\b',
    'confusion': r'\b(?:i\s+(?:don[\x27’]?t|dont|do not)\s+(?:fucking\s+)?(?:understand|get|follow)|(?:you|this|that)\s+(?:don[\x27’]?t|doesn[\x27’]?t|does not)\s+make\s+(?:any\s+)?sense|i\s+cannot\s+parse)\b',
    'plain-language': r'\b(?:speak\s+(?:fucking\s+)?english|plain\s+(?:english|language)|speak\s+plainly|simple\s+terms|full\s+descriptions|stop\s+(?:using\s+)?metaphors|parsing\s+negatives)\b',
    'repeated-correction': r'\b(?:i\s+(?:already\s+)?(?:said|told|asked)|you keep|how many times|stop\s+(?:asking|coding|editing)|just\s+(?:fucking\s+)?(?:answer|talk|do)|of course i want)\b',
    'explicit-frustration': r'\b(?:frustrat(?:ed|ing|ion)|angry|pisses? me off|sick of|losing patience|ruins? my trust|cannot trust|can.t trust)\b',
}
REGEX = {k: re.compile(v, re.I) for k, v in PATTERNS.items()}
WEIGHTS = {'profanity': 2, 'direct-insult': 4, 'what-the-fuck': 4,
           'for-fucks-sake': 5, 'confusion': 3, 'plain-language': 4,
           'repeated-correction': 3, 'explicit-frustration': 3}
SKIP_DIRS = {'.git', 'node_modules', 'extensions', 'plugins', 'skills', 'agents',
             'cache', 'caches', 'secrets', 'credentials', 'attachments', 'generated_images',
             'terminals', 'agent-tools', 'logs', 'browser', 'chrome', '__pycache__'}
INJECTED = ('<skill', '<manually_attached_skills>', '<system_reminder>',
            '# AGENTS.md instructions', '<environment_context>', '<local-command',
            '<command-message>', '[Request interrupted')
AUDIT_PROMPT = re.compile(r'^\s*[/\$]chimp-out-report\b', re.I)


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def textof(content):
    if isinstance(content, str):
        return content
    if isinstance(content, dict):
        return textof(content.get('text', content.get('parts', content.get('content', ''))))
    if not isinstance(content, list):
        return ''
    return '\n'.join(x if isinstance(x, str) else x.get('text', '')
                     for x in content if isinstance(x, str) or
                     (isinstance(x, dict) and x.get('type') in ('text', 'input_text', 'output_text')))


def owner_text(text):
    query = re.search(r'<user_query>(.*?)</user_query>', text, re.S)
    if query:
        return query[1].strip()
    if '## My request for Codex:' in text:
        return text.split('## My request for Codex:', 1)[1].strip()
    if text.lstrip().startswith(INJECTED) or '<turn_aborted>' in text:
        return ''
    if any(s in text for s in ('>>> TRANSCRIPT', 'The following is the Codex agent history',
                               'Message Type: MESSAGE', '<user_info>', '<tool_result')):
        return ''
    return text.strip()


def timestamp(value):
    if value is None or value == '':
        return ''
    if isinstance(value, (int, float)):
        try:
            return dt.datetime.fromtimestamp(value / (1000 if value > 1e11 else 1), dt.timezone.utc).isoformat()
        except (ValueError, OverflowError, OSError):
            return str(value)
    return str(value)


def norm(text):
    # Matching text is a copy group, not an assertion of independent incidents.
    return re.sub(r'\s+', ' ', text).strip().casefold()


def filehash(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inside(path, parent):
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


@contextlib.contextmanager
def open_text(path):
    if path.suffix != '.zst':
        with path.open(encoding='utf-8-sig', errors='replace') as f:
            yield f
        return
    try:
        from compression import zstd
        with zstd.open(path, 'rt', encoding='utf-8', errors='replace') as f:
            yield f
    except ImportError:
        try:
            import zstandard
        except ImportError as e:
            raise RuntimeError('Zstandard decoder unavailable; use Python 3.14 or an existing zstandard module') from e
        with path.open('rb') as raw, zstandard.ZstdDecompressor().stream_reader(raw) as stream:
            with io.TextIOWrapper(stream, encoding='utf-8', errors='replace') as f:
                yield f


def stamp(path):
    try:
        st = path.stat()
        return [st.st_size, st.st_mtime_ns]
    except FileNotFoundError:
        return None


@contextlib.contextmanager
def snapshot(path, temp_parent=None):
    """Copy main + WAL without touching source locks/SHM. Never silently omit WAL."""
    wal = pathlib.Path(str(path) + '-wal')
    with tempfile.TemporaryDirectory(prefix='chimp-out-snapshot-', dir=temp_parent) as tmp:
        copied = pathlib.Path(tmp) / path.name
        stable = False
        for _ in range(2):
            before = [stamp(path), stamp(wal)]
            shutil.copyfile(path, copied)
            destwal = pathlib.Path(str(copied) + '-wal')
            if before[1] is not None:
                shutil.copyfile(wal, destwal)
            elif destwal.exists():
                destwal.unlink()
            after = [stamp(path), stamp(wal)]
            if before == after:
                stable = True
                break
        if not stable:
            raise RuntimeError('Database changed during both snapshot attempts; obtain a stable export')
        con = sqlite3.connect(copied.as_uri() + '?mode=ro', uri=True)
        try:
            con.execute('PRAGMA query_only=ON')
            result = con.execute('PRAGMA quick_check(1)').fetchone()
            if not result or result[0] != 'ok':
                raise RuntimeError('Database snapshot integrity check failed')
            yield con
        finally:
            con.close()


def discover(home, explicit):
    current = home.resolve() == pathlib.Path.home().resolve()
    roots = []
    def add(host, path):
        roots.append((host, pathlib.Path(path).expanduser()))
    codex = pathlib.Path(os.environ.get('CODEX_HOME', str(home / '.codex'))) if current else home / '.codex'
    claude = pathlib.Path(os.environ.get('CLAUDE_CONFIG_DIR', str(home / '.claude'))) if current else home / '.claude'
    for host, base, children in [
        ('codex', codex, ['sessions', 'archived_sessions', 'history.jsonl']),
        ('claude', claude, ['projects', 'history.jsonl']),
        ('cursor', home / '.cursor', ['projects', 'chats']),
        ('antigravity', home / '.gemini', ['antigravity/conversations', 'antigravity-backup',
            'antigravity-cli/conversations', 'antigravity-cli/history.jsonl', 'antigravity-ide/conversations']),
        ('windsurf', home / '.codeium/windsurf', ['cascade', 'database']),
        ('windsurf', home / '.windsurf', ['conversations', 'sessions']),
        ('gemini', home / '.gemini', ['tmp']),
        ('pi', home / '.pi/agent', ['sessions']),
        ('copilot', home / '.copilot', ['session-state', 'history-session-state']),
        ('continue', home / '.continue', ['sessions']),
        ('t3', home / '.t3', ['userdata/state.sqlite']),
    ]:
        for child in children:
            add(host, base / child)
    if current and os.environ.get('GEMINI_CLI_HOME'):
        add('gemini', pathlib.Path(os.environ['GEMINI_CLI_HOME']) / 'tmp')
    for db in sorted(codex.glob('thread_history_*.sqlite')):
        add('codex', db)
    # Metadata is consumed before projections so delegated/review threads can be excluded.
    states = [('codex', p) for p in sorted(codex.glob('state_*.sqlite'))]
    roots = states + roots
    configs = [home / 'AppData/Roaming', home / 'Library/Application Support',
               pathlib.Path(os.environ.get('XDG_CONFIG_HOME', str(home / '.config'))) if current else home / '.config']
    for base in configs:
        for app, host in [('Cursor', 'cursor'), ('cursor', 'cursor'), ('Windsurf', 'windsurf'),
                          ('Antigravity', 'antigravity'), ('Code', 'vscode'),
                          ('Code - Insiders', 'vscode'), ('VSCodium', 'vscode')]:
            user = base / app / 'User'
            if host == 'cursor':
                add(host, user / 'globalStorage/state.vscdb')
                for db in sorted((user / 'workspaceStorage').glob('*/state.vscdb')):
                    add(host, db)
            storage = user / 'globalStorage'
            if storage.exists():
                for extension in storage.iterdir():
                    if extension.is_dir() and any(n in extension.name.lower() for n in ('cline', 'roo-cline', 'rooveterinary', 'continue')):
                        add('cline-roo' if 'continue' not in extension.name.lower() else 'continue', extension)
    for arg in explicit:
        if '=' not in arg:
            raise ValueError('--root requires provider=path')
        host, path = arg.split('=', 1)
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', host) or not path:
            raise ValueError('Invalid provider/path in --root')
        add(host, path)
    seen = set()
    for host, path in roots:
        k = (host, str(path.resolve()))
        if k not in seen:
            seen.add(k)
            yield host, path


def walk(root, output):
    if root.is_file():
        if not inside(root, output):
            yield root
        return
    for folder, dirs, files in os.walk(root, followlinks=False):
        base = pathlib.Path(folder)
        dirs[:] = [d for d in dirs if d.lower() not in SKIP_DIRS and not (base / d).is_symlink()
                   and not inside(base / d, output)]
        for name in sorted(files):
            p = base / name
            if p.is_symlink() or inside(p, output):
                continue
            low = name.lower()
            if any(s in low for s in ('credential', 'auth.json', 'settings.json', 'token', 'mcp_config')):
                continue
            if low.endswith(('.jsonl', '.ndjson', '.jsonl.zst', '.db', '.sqlite', '.vscdb', '.pb')):
                yield p
            elif low.endswith(('.json', '.txt')) and (('agent-transcripts' in str(p)) or
                    any(s in low for s in ('history', 'conversation', 'session', 'chat', 'events', 'export'))):
                yield p


class Collector:
    def __init__(self, output):
        self.output = output
        self.db = sqlite3.connect(output / 'conversation-index.sqlite')
        self.db.executescript('''CREATE TABLE messages(
          id TEXT PRIMARY KEY, host TEXT, thread TEXT, stream TEXT, seq INTEGER,
          role TEXT, time TEXT, text TEXT, source TEXT, locator TEXT, quality TEXT);
          CREATE INDEX stream_order ON messages(stream,seq);''')
        self.coverage = []
        self.record = None
        self.seq = 0
        self.non_owner_threads = set()

    def add(self, host, thread, role, text, when, source, locator, quality='ordered transcript'):
        if role not in ('user', 'assistant'):
            return
        if not when:
            m = re.search(r'<timestamp>(.*?)</timestamp>', text, re.S)
            when = m[1] if m else ''
        if role == 'user':
            text = owner_text(text)
            if AUDIT_PROMPT.search(text):
                return
        if not text.strip():
            return
        quality = self.record.get('quality', quality)
        if host == 'codex' and str(thread) in self.non_owner_threads:
            return
        source = str(source)
        stream = hashlib.sha256((host + '\0' + str(thread) + '\0' + source).encode()).hexdigest()[:20]
        mid = hashlib.sha256((stream + '\0' + str(locator) + '\0' + str(self.seq)).encode()).hexdigest()[:20]
        self.db.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                        (mid, host, str(thread), stream, self.seq, role, timestamp(when), text,
                         source, str(locator), quality))
        self.seq += 1
        self.record['messages'] += 1

    def json_event(self, host, path, d, loc, state):
        if not isinstance(d, dict):
            return
        typ = d.get('type', '')
        if typ == 'session_meta':
            pl = d.get('payload', {})
            state['thread'] = pl.get('id', pl.get('session_id', state['thread']))
            state['excluded'] = 'subagent' in json.dumps(pl.get('source', '')).lower() or pl.get('agent_role') == 'guardian'
            return
        if typ in ('session', 'session.start', 'session.created'):
            state['thread'] = d.get('sessionId', d.get('id', state['thread']))
        if state.get('excluded') or d.get('isSidechain') or d.get('isMeta') or 'subagents' in path.parts:
            return
        pl = d.get('payload', {})
        if typ == 'response_item':
            if pl.get('type') == 'message':
                self.add(host, state['thread'], pl.get('role'), textof(pl.get('content')),
                         d.get('timestamp'), path, loc)
                if pl.get('role') == 'user':
                    state['response_users'] = True
            return
        if typ == 'event_msg':
            if pl.get('type') == 'user_message':
                state.setdefault('events', []).append((pl.get('message', ''), d.get('timestamp'), loc))
            return
        if 'display' in d or (path.name == 'history.jsonl' and 'text' in d and 'ts' in d):
            if d.get('type') == 'slash_command':
                return
            tid = d.get('sessionId', d.get('session_id', state['thread']))
            self.add(host, tid, 'user', d.get('display', d.get('text', '')), d.get('timestamp', d.get('ts')), path, loc, 'prompt-only')
            return
        msg = d.get('message', d)
        if not isinstance(msg, dict):
            return
        role = msg.get('role') or d.get('role')
        if not role and typ in ('user', 'assistant', 'model', 'gemini', 'human', 'user.message', 'assistant.message'):
            role = {'model': 'assistant', 'gemini': 'assistant', 'human': 'user', 'user.message': 'user', 'assistant.message': 'assistant'}.get(typ, typ)
        role = {'model': 'assistant', 'gemini': 'assistant', 'human': 'user'}.get(role, role)
        if isinstance(msg.get('author'), dict):
            role = msg['author'].get('role', role)
        data = d.get('data', {}) if isinstance(d.get('data'), dict) else {}
        content = msg.get('content', msg.get('text', data.get('content', data.get('text', ''))))
        tid = d.get('sessionId', d.get('session_id', state['thread']))
        self.add(host, tid, role, textof(content), d.get('timestamp', d.get('created_at', msg.get('create_time'))), path, loc)

    def parse_lines(self, host, path):
        name = path.name.removesuffix('.zst').removesuffix('.jsonl').removesuffix('.ndjson')
        state = {'thread': path.parent.name if name in ('events', 'history', 'messages') else name, 'events': []}
        with open_text(path) as f:
            for ln, line in enumerate(f, 1):
                if not line.strip():
                    continue
                try:
                    self.json_event(host, path, json.loads(line), 'line:' + str(ln), state)
                except (ValueError, TypeError, KeyError) as e:
                    self.record['errors'].append({'locator': 'line:' + str(ln), 'error': str(e)})
        if not state.get('response_users') and not state.get('excluded'):
            for text, when, loc in state['events']:
                self.add(host, state['thread'], 'user', text, when, path, loc, 'user-event fallback; agent context may be incomplete')

    def parse_json(self, host, path):
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        state = {'thread': path.parent.name if path.name in ('prompt_history.json', 'api_conversation_history.json', 'conversation.json', 'messages.json') else path.stem}
        if path.name == 'prompt_history.json':
            if not isinstance(data, list):
                raise ValueError('Unrecognized prompt history schema')
            for i, text in reversed(list(enumerate(data))):
                if isinstance(text, str):
                    self.add(host, state['thread'], 'user', text, '', path, 'index:' + str(i), 'prompt-only; individual timestamps absent')
            return
        if isinstance(data, dict) and 'mapping' in data:
            # ChatGPT-style exports can branch. Preserve mapping keys and don't invent order.
            self.record['quality'] = 'unknown chronology; mapping export may branch'
            for k, node in data['mapping'].items():
                if isinstance(node, dict) and isinstance(node.get('message'), dict):
                    self.json_event(host, path, node, 'mapping:' + k, state)
            self.record['notes'].append('Mapping export may branch; inspect parent links before causal attribution')
            return
        if isinstance(data, dict):
            state['thread'] = data.get('sessionId', data.get('session_id', data.get('id', state['thread'])))
            data = data.get('messages', data.get('history', data.get('conversation', [data])))
        if not isinstance(data, list):
            raise ValueError('Unrecognized JSON conversation schema')
        for i, d in enumerate(data):
            self.json_event(host, path, d, 'index:' + str(i), state)

    def parse_txt(self, host, path):
        text = path.read_text(encoding='utf-8-sig', errors='replace')
        parts = list(re.finditer(r'(?m)^(user|assistant):\s*$', text))
        for i, m in enumerate(parts):
            body = text[m.end():parts[i + 1].start() if i + 1 < len(parts) else len(text)].strip()
            self.add(host, path.stem, m[1], body, '', path, 'line:' + str(text[:m.start()].count('\n') + 1))

    def parse_db(self, host, path):
        with snapshot(path, self.output) as c:
            tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.record['notes'].append('Stable copied main/WAL snapshot; not an atomic application export')
            if host == 'codex' and 'threads' in tables:
                for tid, source, title in c.execute('SELECT id,source,title FROM threads'):
                    if 'subagent' in str(source).lower() or str(title).casefold() == 'guardian review':
                        self.non_owner_threads.add(tid)
                self.record['notes'].append('Thread metadata used to exclude delegated/review threads')
                return
            if 'thread_items' in tables:
                for tid, mid, ordinal, when, typ, raw in c.execute("SELECT thread_id,item_id,rollout_ordinal,created_at_ms,item_type,item_json FROM thread_items WHERE item_type IN ('userMessage','agentMessage') ORDER BY thread_id,rollout_ordinal"):
                    d = json.loads(raw)
                    self.add(host, tid, 'user' if typ == 'userMessage' else 'assistant',
                             textof(d.get('content')) if typ == 'userMessage' else d.get('text', ''),
                             when, path, 'thread_items.item_id=' + mid, 'ordered projection; provenance filtered where state metadata exists')
                return
            if 'projection_thread_messages' in tables:
                for mid, tid, role, text, when in c.execute('SELECT message_id,thread_id,role,text,created_at FROM projection_thread_messages ORDER BY thread_id,created_at,message_id'):
                    self.add(host, tid, role, text, when, path, 'message_id=' + mid)
                return
            if 'blobs' in tables:
                if 'meta' in tables:
                    for (raw_meta,) in c.execute('SELECT value FROM meta'):
                        try:
                            meta = json.loads(bytes.fromhex(raw_meta).decode('utf-8'))
                            if meta.get('subagentInfo', {}).get('parentAgentId'):
                                self.record['notes'].append('Excluded delegated Cursor session')
                                return
                        except (ValueError, TypeError, AttributeError):
                            continue
                for blobid, raw in c.execute('SELECT id,data FROM blobs ORDER BY rowid'):
                    try:
                        d = json.loads(raw)
                    except (ValueError, UnicodeDecodeError, TypeError):
                        continue
                    if not isinstance(d, dict):
                        continue
                    role = d.get('role')
                    text = textof(d.get('content'))
                    self.add(host, path.parent.name, role, text, '', path, 'blobs.id=' + blobid,
                             'unknown chronology; blob insertion order is not conversation order')
                return
            if 'cursorDiskKV' in tables:
                for key, raw in c.execute("SELECT key,value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'"):
                    try:
                        d = json.loads(raw)
                    except (ValueError, TypeError, UnicodeDecodeError):
                        continue
                    if not isinstance(d, dict):
                        continue
                    role = {1: 'user', 2: 'assistant'}.get(d.get('type'))
                    text = d.get('text', '')
                    tid = key.split(':')[1]
                    self.add(host, tid, role, text if isinstance(text, str) else '', d.get('createdAt'), path,
                             'cursorDiskKV.key=' + key, 'unknown chronology; desktop bubble records need composer ordering')
                return
            # Other hosts sometimes expose simple role/text or JSON-message tables.
            for table in sorted(tables & {'messages', 'chat_messages', 'conversation_messages'}):
                cols = {r[1] for r in c.execute('PRAGMA table_info("' + table + '")')}
                if {'role', 'content'} <= cols or {'role', 'text'} <= cols:
                    field = 'text' if 'text' in cols else 'content'
                    tidcol = next((x for x in ('thread_id', 'conversation_id', 'session_id') if x in cols), None)
                    timecol = next((x for x in ('created_at', 'timestamp', 'createdAt') if x in cols), None)
                    fields = 'rowid,role,"' + field + '",' + ('"' + tidcol + '"' if tidcol else "''") + ',' + ('"' + timecol + '"' if timecol else "''")
                    for rowid, role, content, tid, when in c.execute('SELECT ' + fields + ' FROM "' + table + '" ORDER BY rowid'):
                        self.add(host, tid or path.stem, role, textof(content), when, path, table + '.rowid=' + str(rowid), 'unknown chronology; generic table requires schema review')
                    return
            self.record['status'] = 'unsupported'
            self.record['notes'].append('No supported message table; tables: ' + ', '.join(sorted(tables)))

    def file(self, host, path):
        self.seq = 0
        before = stamp(path)
        self.record = dict(host=host, path=str(path), kind='file', status='searched', messages=0,
                           errors=[], notes=[], snapshot=before)
        try:
            if path.suffix == '.pb':
                self.record.update(status='unsupported')
                self.record['notes'].append('Opaque binary/protobuf archive; verified decoder/export required')
            elif path.name.endswith(('.jsonl', '.ndjson', '.jsonl.zst')):
                self.parse_lines(host, path)
            elif path.suffix == '.json':
                self.parse_json(host, path)
            elif path.suffix == '.txt':
                self.parse_txt(host, path)
            else:
                self.parse_db(host, path)
        except Exception as e:
            self.record['status'] = 'partial' if self.record['messages'] else 'unreadable'
            self.record['errors'].append({'error': str(e)})
        if self.record['errors'] and self.record['status'] == 'searched':
            self.record['status'] = 'partial'
        if before != stamp(path):
            self.record['status'] = 'partial'
            self.record['notes'].append('Source changed during collection')
        if not self.record['messages'] and self.record['status'] == 'searched':
            self.record['notes'].append('No recognized user/assistant messages; does not imply this host has no conversations')
        self.coverage.append(self.record)
        self.db.commit()


def triage(con):
    con.row_factory = sqlite3.Row
    groups = {}
    for row in con.execute("SELECT * FROM messages WHERE role='user'"):
        m = dict(row)
        tags = [name for name, regex in REGEX.items() if regex.search(m['text'])]
        if not tags:
            continue
        score = sum(WEIGHTS[t] for t in tags)
        if len(tags) > 1:
            score += 2  # co-occurrence deserves review, not a diagnosis
        if tags == ['profanity']:
            score = 1
        # Keep a bounded search excerpt even when the original message is long.
        match = next(r.search(m['text']) for r in REGEX.values() if r.search(m['text']))
        start = max(0, match.start() - 160)
        excerpt = m['text'][start:start + 1600]
        identity = norm(m['text'])
        group = groups.setdefault(identity, dict(hit_id=hashlib.sha256(identity.encode()).hexdigest()[:16],
            tags=tags, priority=score, excerpt=excerpt, occurrences=[]))
        group['occurrences'].append({k: m[k] for k in ('id', 'host', 'thread', 'stream', 'seq', 'time', 'source', 'locator', 'quality')})
    hits = sorted(groups.values(), key=lambda h: -h['priority'])
    for hit in hits:
        hit['occurrences'].sort(key=lambda m: ('prompt-only' in m['quality'], 'unknown chronology' in m['quality'], not m['time']))
        hit['primary_message_id'] = hit['occurrences'][0]['id']
        hit['repeated_turns'] = max(collections.Counter((m['host'], m['thread'], m['stream']) for m in hit['occurrences']).values())
    return hits


def write_csv(output, hits, reviews=None):
    groups = collections.defaultdict(list)
    for h in hits:
        for host, tid in set((m['host'], m['thread']) for m in h['occurrences']):
            groups[(host, tid)].append(h)
    with (output / 'flagged-threads.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['host', 'thread_id', 'distinct_candidate_texts', 'highest_priority', 'tags',
                         'primary_message_id', 'excerpt', 'source', 'locator', 'review_status'])
        for (host, tid), hs in sorted(groups.items(), key=lambda item: -max(h['priority'] for h in item[1])):
            best = max(hs, key=lambda h: h['priority'])
            m = next(m for m in best['occurrences'] if m['host'] == host and m['thread'] == tid)
            # Prevent spreadsheet formula evaluation in a human-opened CSV.
            statuses = sorted({reviews[occ['id']] for h in hs for occ in h['occurrences']
                               if reviews and occ['id'] in reviews and occ['host'] == host and occ['thread'] == tid})
            status = 'contains ' + '; '.join(statuses) + '; remaining hits may be unreviewed' if statuses else 'unreviewed candidate'
            values = [host, tid, len(hs), best['priority'], ', '.join(sorted({t for h in hs for t in h['tags']})),
                      m['id'], best['excerpt'], m['source'], m['locator'], status]
            writer.writerow(["'" + x if isinstance(x, str) and x.startswith(('=', '+', '-', '@')) else x for x in values])
    return len(groups)


def collect(args):
    output = pathlib.Path(args.output).expanduser().resolve()
    skill = pathlib.Path(__file__).resolve().parents[1]
    if inside(output, skill):
        raise ValueError('Choose a private output folder outside the skill source')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output folder must be absent or empty; use a new run folder')
    output.mkdir(parents=True, exist_ok=True)
    run = dict(schema_version=1, tool_version=VERSION, run_id=str(uuid.uuid4()), machine=platform.node(),
               collected_at=dt.datetime.now(dt.timezone.utc).isoformat(), home=str(pathlib.Path(args.home).expanduser().resolve()),
               note='Storage records include copies and automation. Keyword hits are unreviewed candidates.')
    dump(output / 'run.json', run)
    collector = Collector(output)
    seen = set()
    for host, root in discover(pathlib.Path(args.home).expanduser(), args.root):
        collector.coverage.append(dict(host=host, path=str(root), kind='root',
            status='located' if root.exists() else 'missing', messages=0, errors=[], notes=[]))
        if not root.exists():
            continue
        try:
            for path in walk(root, output):
                key = str(path.resolve())
                if key in seen:
                    continue
                seen.add(key)
                collector.file(host, path)
        except OSError as e:
            collector.coverage.append(dict(host=host, path=str(root), kind='root', status='unreadable',
                                          messages=0, errors=[{'error': str(e)}], notes=[]))
    hits = triage(collector.db)
    count = write_csv(output, hits)
    dump(output / 'coverage.json', collector.coverage)
    dump(output / 'candidates.json', hits)
    dump(output / 'review.json', {'summary': [], 'cases': []})
    collector.db.close()
    print(json.dumps(dict(output=str(output), candidate_text_groups=len(hits), candidate_threads=count,
                          source_files=len(seen), next='Read candidates, inspect context, then fill review.json and render.')))


@contextlib.contextmanager
def open_index(output):
    path = output / 'conversation-index.sqlite'
    if not path.exists():
        raise ValueError('Temporary index absent. Recollect into a new run folder to inspect more context.')
    c = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)
    c.row_factory = sqlite3.Row
    try:
        yield c
    finally:
        c.close()


def context_rows(con, mid, before=6, after=5):
    m = con.execute('SELECT * FROM messages WHERE id=?', (mid,)).fetchone()
    if m is None:
        raise ValueError('Unknown message ID: ' + mid)
    # seq belongs to the source file; filter by stream to avoid unrelated threads.
    rows = con.execute('SELECT * FROM messages WHERE stream=? ORDER BY seq', (m['stream'],)).fetchall()
    index = next(i for i, r in enumerate(rows) if r['id'] == mid)
    return [dict(r) for r in rows[max(0, index - before):index + after + 1]]


def context_cmd(args):
    if args.before < 0 or args.after < 0:
        raise ValueError('Context window sizes must be nonnegative')
    with open_index(pathlib.Path(args.output).resolve()) as con:
        print(json.dumps(context_rows(con, args.message, args.before, args.after), ensure_ascii=False, indent=2))


def quote_matches(text, quote):
    if quote.get('redacted'):
        chunks = quote['text'].split('[REDACTED]')
        if len(chunks) == 1 or not any(chunks):
            return False
        pos = 0
        for chunk in chunks:
            if not chunk:
                continue
            found = text.find(chunk, pos)
            if found < 0:
                return False
            pos = found + len(chunk)
        return True
    return bool(quote['text']) and quote['text'] in text


STYLE = '''body{font:17px/1.55 system-ui,sans-serif;background:#f4f6f8;color:#182331;max-width:1120px;margin:auto;padding:28px}section,article{background:white;border:1px solid #d9dfe7;border-radius:10px;margin:20px 0;padding:22px}h1,h2{line-height:1.2}a{color:#065ab8}blockquote{border-left:4px solid #ac492e;background:#fff5ef;padding:12px;margin:15px 0;white-space:pre-wrap}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:12px;font:14px/1.5 system-ui}input{padding:12px;font-size:17px;width:100%;box-sizing:border-box}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:9px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}.meta{font-size:13px;overflow-wrap:anywhere;color:#526171}summary{cursor:pointer;font-weight:600}.hidden{display:none}@media(max-width:650px){body{padding:10px}section,article{padding:14px}table{display:block;overflow-x:auto}}'''


def render(args):
    output = pathlib.Path(args.output).resolve()
    review = json.loads((output / 'review.json').read_text(encoding='utf-8'))
    hits = json.loads((output / 'candidates.json').read_text(encoding='utf-8'))
    coverage = json.loads((output / 'coverage.json').read_text(encoding='utf-8'))
    run = json.loads((output / 'run.json').read_text(encoding='utf-8'))
    cases = review.get('cases', [])
    seen = set()
    evidence = []
    hashes = {}
    all_redactions = []
    with open_index(output) as con:
        for case in cases:
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9-]*', case.get('id', '')) or case['id'] in seen:
                raise ValueError('Case IDs must be unique simple identifiers')
            seen.add(case['id'])
            required = ['title', 'message_ids', 'status', 'trigger', 'observed', 'inference', 'recommendation', 'confidence', 'limitations', 'quotes']
            if any(k not in case for k in required) or not case['message_ids']:
                raise ValueError('Incomplete review entry: ' + case['id'])
            if case['status'] not in ('reviewed', 'prompt-only', 'external', 'false-positive'):
                raise ValueError('Invalid review status')
            selected = []
            for mid in case['message_ids']:
                m = con.execute('SELECT * FROM messages WHERE id=?', (mid,)).fetchone()
                if m is None or m['role'] != 'user':
                    raise ValueError('Review signals must identify user messages: ' + str(mid))
                selected.append(dict(m))
            if len({m['stream'] for m in selected}) != 1:
                raise ValueError('An episode must use one source stream; cite copies separately')
            if case['status'] == 'reviewed' and any('prompt-only' in m['quality'] or 'unknown chronology' in m['quality'] for m in selected):
                raise ValueError('Prompt-only/unknown-order sources cannot be marked context reviewed')
            selected_by_id = {m['id']: m for m in selected}
            for q in case['quotes']:
                if q.get('message_id') not in selected_by_id or not quote_matches(selected_by_id[q['message_id']]['text'], q):
                    raise ValueError('Quote does not match the selected owner message: ' + case['id'])
            if not case['quotes']:
                raise ValueError('Each review entry needs at least one verified quote')
            rows = {}
            for mid in case['message_ids']:
                for m in context_rows(con, mid, case.get('before', 6), case.get('after', 5)):
                    rows[m['id']] = m
            context = sorted(rows.values(), key=lambda m: m['seq'])
            # Explicit replacements also redact the exported surrounding exchange.
            # Otherwise a redacted headline could leak its secret in the details.
            redactions = case.get('redactions', [])
            if any(not isinstance(s, str) or not s for s in redactions):
                raise ValueError('Redactions must be nonempty exact strings')
            if any(q.get('redacted') for q in case['quotes']) and not redactions:
                raise ValueError('A redacted quote also requires exact redactions for its context')
            all_redactions.extend(redactions)
            for m in context:
                for secret in redactions:
                    m['text'] = m['text'].replace(secret, '[REDACTED]')
            public_case = {k: v for k, v in case.items() if k != 'redactions'}
            public_case = redact_tree(public_case, redactions)
            for m in selected:
                src = m['source']
                if src not in hashes:
                    try:
                        hashes[src] = {'sha256': filehash(src), 'captured_at': dt.datetime.now(dt.timezone.utc).isoformat()}
                        source_info = next((r for r in coverage if r['kind'] == 'file' and r['path'] == src), {})
                        hashes[src]['changed_since_collection'] = source_info.get('snapshot') != stamp(pathlib.Path(src))
                        wal = pathlib.Path(src + '-wal')
                        if wal.exists():
                            hashes[src]['wal_sha256'] = filehash(wal)
                    except OSError as e:
                        hashes[src] = {'error': str(e), 'note': 'Saved excerpts remain available'}
            evidence.append({'case': public_case, 'signals': [{k: m[k] for k in ('id', 'host', 'thread', 'time', 'source', 'locator', 'quality')} for m in selected], 'context': context})
    # Redact every exported excerpt, not only the highlighted quote.
    evidence = redact_tree(evidence, all_redactions)
    hits = redact_tree(hits, all_redactions)
    dump(output / 'candidates.json', hits)
    write_csv(output, hits, {mid: c['status'] + ': ' + c['id'] for c in cases for mid in c['message_ids']})
    dump(output / 'reviewed-evidence.json', evidence)
    dump(output / 'source-manifest.json', {'run_id': run['run_id'], 'sources': hashes, 'note': 'Hashes identify source state at rendering; live sources may change after collection.'})
    counts = collections.Counter(c['status'] for c in cases)
    threads = {(m['host'], m['thread']) for h in hits for m in h['occurrences']}
    e = html.escape
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Chimp-out report</title><style>' + STYLE + '</style><h1>Chimp-out report</h1>',
             '<p class="meta">Machine: ' + e(run['machine']) + ' · Run: ' + e(run['run_id']) + ' · Collected: ' + e(run['collected_at']) + '</p>',
             '<section><h2>Findings</h2><p>' + str(len(hits)) + ' candidate text groups across ' + str(len(threads)) + ' host/thread groups; ' + str(counts['reviewed']) + ' reviewed episodes; ' + str(counts['prompt-only']) + ' prompt-only leads. Search hits are not confirmed angry threads. Repeated turns and stored copies remain in occurrence lists.</p>']
    summaries = redact_tree(review.get('summary', []), all_redactions)
    if isinstance(summaries, str):
        summaries = [summaries]
    for text in summaries:
        parts.append('<p>' + e(text) + '</p>')
    if not cases:
        parts.append('<p><strong>Context review is not complete.</strong> This report contains candidates only; no cause has been established.</p>')
    parts.append('<p><a href="flagged-threads.csv">Candidate CSV</a> · <a href="reviewed-evidence.json">Reviewed evidence</a> · <a href="coverage.json">Coverage ledger</a> · <a href="source-manifest.json">Source hashes</a></p></section><label for="search">Search reviewed examples and candidates</label><input id="search" type="search" placeholder="Phrase, cause, host, or thread"><p id="visible"></p>')
    for ev in evidence:
        case = ev['case']
        parts.append('<article class="searchable" id="' + case['id'] + '"><h2>' + e(case['id'] + ' · ' + case['title']) + '</h2><p class="meta">' + e(case['status'] + ' · ' + case.get('category', '') + ' · ' + case['confidence']) + '</p>')
        for q in case['quotes']:
            parts.append('<blockquote>' + e(q['text']) + '</blockquote>')
        for key, label in [('trigger', 'Requested help / trigger'), ('observed', 'Observed behavior and outcome'),
                           ('inference', 'Cause assessment'), ('recommendation', 'Workflow improvement'), ('limitations', 'Limits')]:
            parts.append('<p><strong>' + label + ':</strong> ' + e(case[key]) + '</p>')
        for m in ev['signals']:
            parts.append('<p class="meta">' + e(m['host'] + ' · ' + (m['time'] or 'Date unknown') + ' · thread ' + m['thread'] + '\n' + m['source'] + ' · ' + m['locator'] + ' · ' + m['quality']) + '</p>')
        parts.append('<details><summary>Surrounding exchange</summary>')
        for m in ev['context']:
            parts.append('<p class="meta">' + e(m['role'].upper() + ' · ' + (m['time'] or 'Date unknown') + ' · ' + m['locator']) + '</p><pre>' + e(m['text']) + '</pre>')
        parts.append('</details></article>')
    parts.append('<section><h2>Unreviewed search candidates</h2><p>Priority is a review aid. A quote alone does not establish its target or cause. Identical text groups retain every stored occurrence and repeated turn.</p>')
    reviewed_ids = {mid for c in cases for mid in c['message_ids']}
    for h in hits:
        if any(m['id'] in reviewed_ids for m in h['occurrences']):
            continue
        m = h['occurrences'][0]
        parts.append('<details class="searchable"><summary>' + e(m['host'] + ' · ' + ', '.join(h['tags']) + ' · priority ' + str(h['priority'])) + '</summary><blockquote>' + e(h['excerpt']) + '</blockquote><p class="meta">' + e('message ' + m['id'] + ' · thread ' + m['thread'] + ' · ' + (m['time'] or 'Date unknown') + '\n' + m['source'] + ' · ' + m['locator'] + ' · ' + m['quality']) + '</p><p>' + str(len(h['occurrences'])) + ' stored occurrence(s); max ' + str(h['repeated_turns']) + ' identical turns in one source stream.</p></details>')
    parts.append('</section><section><h2>Coverage and gaps</h2><p>Roots are discovery starting points, not a full-disk guarantee. Binary archives require a verified decoder or export. No-match, absent, unsupported, and unreadable mean different things. Database snapshots are stable copied main/WAL pairs, not atomic application exports. Cross-machine copies and inherited fork history require further deduplication before aggregating incident counts.</p><table><tr><th>Host</th><th>Status</th><th>Sources</th><th>Messages</th></tr>')
    aggregate = collections.defaultdict(lambda: [0, 0])
    for r in coverage:
        aggregate[(r['host'], r['status'])][0] += 1
        aggregate[(r['host'], r['status'])][1] += r['messages']
    for (host, status), (n, messages) in sorted(aggregate.items()):
        parts.append('<tr><td>' + e(host) + '</td><td>' + e(status) + '</td><td>' + str(n) + '</td><td>' + str(messages) + '</td></tr>')
    parts.append('</table><details><summary>Per-source details</summary>')
    for r in coverage:
        parts.append('<p class="meta">' + e(r['host'] + ' · ' + r['status'] + ' · ' + r['path']) + '</p><pre>' + e(json.dumps({'notes': r['notes'], 'errors': r['errors']}, ensure_ascii=False)) + '</pre>')
    parts.append('</details><p>The temporary broad index may be discarded after evidence review. Regenerating from changed live archives creates a different run. No source threads were tagged, renamed, edited, or published.</p></section><script>const input=document.querySelector("#search"),items=[...document.querySelectorAll(".searchable")],label=document.querySelector("#visible");input.addEventListener("input",()=>{let n=0;const q=input.value.toLocaleLowerCase();for(const x of items){const show=x.textContent.toLocaleLowerCase().includes(q);x.classList.toggle("hidden",!show);if(show)n++}label.textContent=`Showing ${n} of ${items.length} examples and candidates.`});</script></html>')
    (output / 'chimp-out-report.html').write_text('\n'.join(parts), encoding='utf-8')
    print(json.dumps(dict(report=str(output / 'chimp-out-report.html'), reviewed_status_counts=dict(counts), verified_quotes=sum(len(c['quotes']) for c in cases))))


def redact_tree(value, secrets):
    if isinstance(value, str):
        for secret in secrets:
            value = value.replace(secret, '[REDACTED]')
        return value
    if isinstance(value, list):
        return [redact_tree(v, secrets) for v in value]
    if isinstance(value, dict):
        return {k: redact_tree(v, secrets) for k, v in value.items()}
    return value


def discard(args):
    output = pathlib.Path(args.output).resolve()
    run = json.loads((output / 'run.json').read_text(encoding='utf-8'))
    if run.get('tool_version') != VERSION or not (output / 'reviewed-evidence.json').exists() or not (output / 'chimp-out-report.html').exists():
        raise ValueError('Verified report artifacts are required before discarding the helper index')
    path = output / 'conversation-index.sqlite'
    if path.is_symlink():
        raise ValueError('Refusing a symlink index')
    if path.exists():
        path.unlink()
    print('Removed only the helper-created conversation-index.sqlite; source archives retained.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    collect_parser = sub.add_parser('collect')
    collect_parser.add_argument('--output', required=True)
    collect_parser.add_argument('--home', default=str(pathlib.Path.home()))
    collect_parser.add_argument('--root', action='append', default=[])
    collect_parser.set_defaults(func=collect)
    context_parser = sub.add_parser('context')
    context_parser.add_argument('--output', required=True)
    context_parser.add_argument('--message', required=True)
    context_parser.add_argument('--before', type=int, default=6)
    context_parser.add_argument('--after', type=int, default=5)
    context_parser.set_defaults(func=context_cmd)
    render_parser = sub.add_parser('render')
    render_parser.add_argument('--output', required=True)
    render_parser.set_defaults(func=render)
    discard_parser = sub.add_parser('discard-index')
    discard_parser.add_argument('--output', required=True)
    discard_parser.set_defaults(func=discard)
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except (ValueError, OSError, sqlite3.Error, json.JSONDecodeError) as e:
        print('chimp-out-report: ' + str(e), file=sys.stderr)
        return 2


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
