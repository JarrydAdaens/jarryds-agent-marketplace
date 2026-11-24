"""Synthetic behavior tests; never read the machine's real conversation archives."""
import argparse
import contextlib
import importlib.util
import io
import json
import os
import pathlib
import sqlite3
import tempfile
import unittest

PATH = pathlib.Path(__file__).with_name('chimp-out-report.py')
SPEC = importlib.util.spec_from_file_location('chimp_out_report', PATH)
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='chimp-out-test-', dir=os.environ.get('CHIMP_OUT_TEST_TMP'))
        self.root = pathlib.Path(self.temp.name)
        self.home = self.root / 'profile'
        self.home.mkdir()
        self.out = self.root / 'private-report'

    def tearDown(self):
        self.temp.cleanup()

    def write(self, rel, data, lines=False):
        p = self.home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        text = '\n'.join(json.dumps(x) for x in data) if lines else json.dumps(data)
        p.write_text(text, encoding='utf-8')
        return p

    def collect(self):
        with contextlib.redirect_stdout(io.StringIO()):
            APP.collect(argparse.Namespace(output=str(self.out), home=str(self.home), root=[]))

    def read(self, name):
        return json.loads((self.out / name).read_text(encoding='utf-8'))

    def test_multihost_roles_and_repeated_turns(self):
        self.write('.codex/sessions/a.jsonl', [
            {'type': 'session_meta', 'payload': {'id': 'thread-a', 'source': 'cli'}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'developer', 'content': [{'type': 'input_text', 'text': 'you idiot'}]}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'content': [{'type': 'output_text', 'text': 'I will change the code.'}]}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Stop coding. Just talk to me.'}]}},
            {'type': 'event_msg', 'payload': {'type': 'user_message', 'message': 'Stop coding. Just talk to me.'}},
            {'type': 'response_item', 'payload': {'type': 'message', 'role': 'user', 'content': [{'type': 'input_text', 'text': 'Stop coding. Just talk to me.'}]}},
        ], True)
        self.write('.claude/projects/sample/a.jsonl', [
            {'type': 'user', 'sessionId': 'thread-b', 'message': {'role': 'user', 'content': [
                {'type': 'tool_result', 'content': 'for fucks sake'}, {'type': 'text', 'text': "I don't understand this flow."}]}},
            {'type': 'user', 'isSidechain': True, 'message': {'role': 'user', 'content': 'you moron'}},
        ], True)
        self.write('.cursor/projects/sample/agent-transcripts/c.jsonl', [
            {'role': 'user', 'message': {'content': [{'type': 'text', 'text': '<user_query>Speak plainly, for fucks sake.</user_query>'}]}}], True)
        self.write('.gemini/tmp/project/chats/session-a.json', {'sessionId': 'gemini-a', 'messages': [{'type': 'user', 'content': 'Why do you keep asking? I already told you.'}]})
        self.write('.pi/agent/sessions/a.jsonl', [{'type': 'message', 'message': {'role': 'user', 'content': [{'type': 'text', 'text': 'What the fuck is this?'}]}}], True)
        self.collect()
        hits = self.read('candidates.json')
        hosts = {m['host'] for h in hits for m in h['occurrences']}
        self.assertTrue({'codex', 'claude', 'cursor', 'gemini', 'pi'} <= hosts)
        repeated = next(h for h in hits if h['excerpt'] == 'Stop coding. Just talk to me.')
        self.assertEqual(2, len(repeated['occurrences']))
        self.assertEqual(2, repeated['repeated_turns'])
        self.assertFalse(any('idiot' in h['excerpt'] or 'moron' in h['excerpt'] for h in hits))
        self.assertFalse(any(h['excerpt'] == 'for fucks sake' for h in hits))

    def test_opaque_and_malformed_sources_are_coverage_gaps(self):
        p = self.home / '.codeium/windsurf/cascade/archive.pb'
        p.parent.mkdir(parents=True)
        p.write_bytes(b'\x00user: you idiot')
        bad = self.home / '.claude/projects/a/a.jsonl'
        bad.parent.mkdir(parents=True)
        bad.write_text('{bad json}\n' + json.dumps({'type': 'user', 'message': {'role': 'user', 'content': 'I already told you.'}}), encoding='utf-8')
        self.collect()
        ledger = self.read('coverage.json')
        self.assertTrue(any(r['host'] == 'windsurf' and r['status'] == 'unsupported' for r in ledger))
        self.assertTrue(any(r['path'] == str(bad) and r['status'] == 'partial' and r['messages'] == 1 for r in ledger))
        self.assertFalse(any('idiot' in h['excerpt'] for h in self.read('candidates.json')))

    def test_prompt_only_and_redaction_never_leak_in_html(self):
        original = 'For fucks sake, secret=synthetic-secret. <script>alert(1)</script>'
        self.write('.claude/history.jsonl', [{'sessionId': 'h', 'display': original, 'timestamp': 1800000000000}], True)
        self.collect()
        mid = self.read('candidates.json')[0]['primary_message_id']
        case = dict(id='L01', title='Prompt lead', message_ids=[mid], status='prompt-only', trigger='Reported failure',
                    observed='Only the prompt remains.', inference='Cause unknown.', recommendation='Recover preceding response.',
                    confidence='Limited', limitations='No agent context.', quotes=[{'message_id': mid, 'text': 'secret=[REDACTED].', 'redacted': True}],
                    redactions=['synthetic-secret'])
        APP.dump(self.out / 'review.json', {'cases': [case]})
        with contextlib.redirect_stdout(io.StringIO()):
            APP.render(argparse.Namespace(output=str(self.out)))
        for file in ['chimp-out-report.html', 'reviewed-evidence.json', 'flagged-threads.csv', 'candidates.json']:
            self.assertNotIn('synthetic-secret', (self.out / file).read_text(encoding='utf-8-sig'))
        markup = (self.out / 'chimp-out-report.html').read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', markup)
        self.assertNotIn('<script>alert(1)</script>', markup)
        case['status'] = 'reviewed'
        APP.dump(self.out / 'review.json', {'cases': [case]})
        with self.assertRaisesRegex(ValueError, 'cannot be marked'):
            APP.render(argparse.Namespace(output=str(self.out)))

    def test_wal_snapshot_retains_committed_messages_and_sources(self):
        path = self.home / '.t3/userdata/state.sqlite'
        path.parent.mkdir(parents=True)
        c = sqlite3.connect(path)
        try:
            c.execute('PRAGMA journal_mode=WAL')
            c.execute('PRAGMA wal_autocheckpoint=0')
            c.execute('CREATE TABLE projection_thread_messages(message_id TEXT,thread_id TEXT,role TEXT,text TEXT,created_at TEXT)')
            c.commit()
            c.execute('INSERT INTO projection_thread_messages VALUES(?,?,?,?,?)', ('m', 't', 'user', 'For fucks sake, test the installed command.', '2026-01-01T00:00:00Z'))
            c.commit()
            wal = pathlib.Path(str(path) + '-wal')
            before = (path.read_bytes(), wal.read_bytes())
            self.collect()
            self.assertTrue(any('installed command' in h['excerpt'] for h in self.read('candidates.json')))
            self.assertEqual(before, (path.read_bytes(), wal.read_bytes()))
        finally:
            c.close()

    def test_projection_excludes_guardian_via_metadata(self):
        folder = self.home / '.codex'
        folder.mkdir()
        with contextlib.closing(sqlite3.connect(folder / 'state_99.sqlite')) as c:
            c.execute('CREATE TABLE threads(id TEXT, source TEXT, title TEXT)')
            c.execute('INSERT INTO threads VALUES(?,?,?)', ('g', '{"subagent": "review"}', 'Guardian review'))
            c.commit()
        with contextlib.closing(sqlite3.connect(folder / 'thread_history_99.sqlite')) as c:
            c.execute('CREATE TABLE thread_items(thread_id TEXT,item_id TEXT,rollout_ordinal INTEGER,created_at_ms INTEGER,item_type TEXT,item_json TEXT)')
            c.execute('INSERT INTO thread_items VALUES(?,?,?,?,?,?)', ('g', 'm', 0, 0, 'userMessage', json.dumps({'content': [{'type': 'text', 'text': 'What the fuck?'}]})))
            c.commit()
        self.collect()
        self.assertEqual([], self.read('candidates.json'))

    def test_output_collision_and_explicit_output(self):
        self.out.mkdir()
        sentinel = self.out / 'unrelated.txt'
        sentinel.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'absent or empty'):
            self.collect()
        self.assertEqual('keep', sentinel.read_text())
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            APP.main(['collect'])

    def test_cursor_timestamp_gemini_reply_and_copilot_thread_identity(self):
        self.write('.cursor/projects/p/agent-transcripts/a.jsonl', [{'role': 'user', 'message': {'content': [{'type': 'text', 'text': '<timestamp>2026-01-01T05:00:00+10:00</timestamp><user_query>Speak plainly.</user_query>'}]}}], True)
        self.write('.gemini/tmp/p/chats/session-a.json', {'sessionId': 'gemini-a', 'messages': [
            {'type': 'user', 'content': 'I already asked.'}, {'type': 'gemini', 'content': 'Here is the explanation.'}]})
        for thread in ['one', 'two']:
            self.write('.copilot/session-state/' + thread + '/events.jsonl', [{'type': 'user.message', 'data': {'content': 'What the fuck?'}}], True)
        self.collect()
        with APP.open_index(self.out) as c:
            cursor = c.execute("SELECT time FROM messages WHERE host='cursor'").fetchone()
            self.assertEqual('2026-01-01T05:00:00+10:00', cursor[0])
            self.assertEqual(1, c.execute("SELECT count(*) FROM messages WHERE host='gemini' AND role='assistant'").fetchone()[0])
            self.assertEqual({'one', 'two'}, {r[0] for r in c.execute("SELECT thread FROM messages WHERE host='copilot'")})

    def test_long_explicit_query_and_quote_fabrication(self):
        self.write('.cursor/projects/sample/agent-transcripts/a.jsonl', [{'role': 'user', 'message': {'content': [
            {'type': 'text', 'text': ('x' * 18000) + '<user_query>I do not understand. Speak plainly.</user_query>'}]}}], True)
        self.collect()
        hits = self.read('candidates.json')
        self.assertEqual(1, len(hits))
        mid = hits[0]['primary_message_id']
        case = dict(id='F01', title='Confusion', message_ids=[mid], status='reviewed', trigger='Question', observed='A confused prompt.', inference='Unknown',
                    recommendation='Explain.', confidence='Limited', limitations='No answer.', quotes=[{'message_id': mid, 'text': 'fabricated insult'}])
        APP.dump(self.out / 'review.json', {'cases': [case]})
        with self.assertRaisesRegex(ValueError, 'Quote does not match'):
            APP.render(argparse.Namespace(output=str(self.out)))


if __name__ == '__main__':
    unittest.main()
