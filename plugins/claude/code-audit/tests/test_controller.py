"""Behavioral decision-system fixtures. No model calls, devices, remote services or installs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))
from audit import adapters, engine
from audit.common import AuditError, atomic, digest, read, sha
from audit.processes import execute
from audit.process_review import ingest_process, package_hypothesis
from audit.scope import git


class ControllerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / 'source'
        self.repo.mkdir()
        git(self.repo, 'init', '-b', 'trunk')
        git(self.repo, 'config', 'user.name', 'Fixture')
        git(self.repo, 'config', 'user.email', 'fixture@example.invalid')
        self.file = self.repo / 'app.py'
        self.file.write_text('def divide(a, b):\n    return a / b\n', encoding='utf-8')
        self.commit('base')
        self.base = git(self.repo, 'rev-parse', 'HEAD')
        git(self.repo, 'checkout', '-b', 'feature')
        self.file.write_text('def divide(a, b):\n    return a / 0\n', encoding='utf-8')
        self.commit('seeded regression')
        self.head = git(self.repo, 'rev-parse', 'HEAD')

    def tearDown(self):
        self.temp.cleanup()

    def commit(self, message):
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-m', message)

    def init(self, **kwargs):
        return engine.initialize(self.repo, 'feature', self.root / 'audits', base='trunk', **kwargs)

    def note(self, run, text='Inspected the pinned implementation and caller contract.'):
        path = self.root / 'notes.txt'
        path.write_text(text, encoding='utf-8')
        return engine.evidence(run, path, 'notes.txt')

    def check(self, run, spec, **updates):
        state = engine.load(run)
        scope = state['inputs']['scope']
        folder = self.root / 'imports' / spec['id']
        folder.mkdir(parents=True, exist_ok=True)
        atomic(folder / 'data.json', [])
        payload = {'schema_version': 1, 'run_id': run.name, 'task_id': spec['id'],
                   'snapshot': spec['snapshot'], 'state': 'completed', 'tool': 'fixture-ci',
                   'tool_version': '1.0', 'environment': {'image': 'fixture-pinned'},
                   'scope_paths': spec['paths'], 'coverage_complete': True, 'omissions': [],
                   'adapter': 'observations-json', 'report': 'data.json', 'expected_records': 0,
                   'exit_code': 0, 'completed_exit_codes': [0], 'config_digest': digest('fixture'),
                   'history_commits': scope['history_commits'],
                   'dependencies': {'graph_sha256': digest('resolved')},
                   'advisory_database': {'sha256': digest('fixed-advisories')},
                   'build': {'source': spec['snapshot'], 'tree': scope['integration_tree'],
                             'configuration': 'fixture', 'toolchain': 'fixture-1.0'}}
        payload.update(updates)
        atomic(folder / 'envelope.json', payload)
        return folder / 'envelope.json'

    def review(self, run, spec, findings=None, **updates):
        ref = self.note(run)
        payload = {'schema_version': 1, 'run_id': run.name, 'task_id': spec['id'],
                   'snapshot': spec['snapshot'], 'reviewer': 'reviewer-' + spec['id'],
                   'state': 'completed', 'reviewed_paths': spec['paths'],
                   'summary': 'Traced behavior, callers, error paths and supplied contract.',
                   'model': {'provider': 'fixture', 'model': 'deterministic-fixture', 'version': '1', 'reasoning': 'none'},
                   'evidence': [ref], 'findings': findings or []}
        payload.update(updates)
        path = self.root / (spec['id'] + '.json')
        atomic(path, payload)
        return path

    def complete(self, run, finding=None):
        for spec in engine.load(run)['inputs']['tasks']:
            if spec['kind'] == 'sensor':
                engine.ingest_check(run, self.check(run, spec))
            else:
                findings = [finding] if finding and spec['id'] == 'review-correctness' else []
                engine.ingest_review(run, self.review(run, spec, findings))
        return engine.report(run)

    def finding(self, run, verified=True):
        ref = self.note(run, 'app.py line 2 divides every input by zero; any call raises ZeroDivisionError.')
        f = {'id': 'COR-1', 'category': 'correctness', 'priority': 'P1', 'evidence_status': 'verified',
             'attribution': 'introduced', 'locations': [{'snapshot': self.head, 'path': 'app.py', 'start_line': 1, 'end_line': 2}],
             'trigger': 'Call divide(2, 1).', 'impact': 'Every call raises instead of returning a quotient.',
             'evidence': [ref], 'reasoning': 'The divisor is the literal zero irrespective of b.',
             'remediation': 'Restore the divisor b and assert the quotient for nonzero b.', 'disposition': 'open'}
        if verified:
            f['verification'] = {'reviewer': 'independent-verifier', 'outcome': 'upheld',
                                 'challenge': 'Checked there is no alternate binding or guarded caller; literal zero always fails.',
                                 'evidence': [ref]}
        return f

    def test_missing_base_output_and_dirty_checkout(self):
        with self.assertRaises(AuditError):
            engine.initialize(self.repo, 'feature', self.root / 'audit')
        with self.assertRaises(AuditError):
            engine.initialize(self.repo, 'feature', self.repo / 'reports', base='trunk')
        self.file.write_text('unrelated local edits\n')
        before = git(self.repo, 'status', '--porcelain')
        run = self.init()
        self.assertTrue(engine.load(run)['inputs']['scope']['local_edits_excluded'])
        self.assertEqual(git(self.repo, 'status', '--porcelain'), before)
        self.assertEqual((run / 'snapshots/H/app.py').read_text(), 'def divide(a, b):\n    return a / 0\n')

    def test_missing_scanners_no_clean_verdict_and_resume(self):
        run = self.init()
        engine.run_sensors(run)
        first = engine.load(run)
        self.assertTrue(all(x[-1]['state'] == 'unavailable' for x in first['results'].values()))
        self.assertEqual(engine.report(run)['verdict'], 'INCOMPLETE')
        engine.run_sensors(run, retry=True)
        self.assertTrue(all(len(x) == 2 for x in engine.load(run)['results'].values()))
        engine.run_sensors(run, retry=True)
        self.assertTrue(all(len(x) == 2 for x in engine.load(run)['results'].values()))

    def test_ready_is_current_and_historical_ready_survives_branch_move(self):
        run = self.init()
        verdict = self.complete(run)
        self.assertEqual(verdict['verdict'], 'READY')
        historical = run / engine.load(run)['latest_report'] / 'verdict.json'
        self.file.write_text('def divide(a, b):\n    return a / b\n')
        self.commit('move head')
        self.assertEqual(engine.report(run)['freshness'], 'stale')
        self.assertEqual(read(historical)['verdict'], 'READY')
        self.assertEqual(read(run / 'verdict.json')['verdict'], 'INCOMPLETE')

    def test_agent_originated_defect_blocks_without_any_scanner_observation(self):
        run = self.init()
        result = self.complete(run, self.finding(run))
        self.assertEqual(result['verdict'], 'CHANGES_REQUIRED')
        self.assertEqual(result['blocking_ids'], ['COR-1'])
        self.assertEqual(result['completion'], 'completed')

    def test_unverified_blocker_and_unsafe_consolidation_stay_incomplete(self):
        run = self.init()
        finding = self.finding(run, verified=False)
        self.assertEqual(self.complete(run, finding)['verdict'], 'INCOMPLETE')
        finding.update(category='reuse', priority='P2', consolidation={'definitions_and_callers': ['a', 'b'],
                       'behavioral_comparison': 'Cancellation differs.', 'domain_contract': 'Different cancellation ownership.',
                       'retained_implementation': 'unknown', 'affected_dependencies': ['caller'],
                       'validation': 'Cancel mid-operation; assert side effects.', 'unresolved_differences': ['cancellation']})
        validated = engine.validate_findings(run, engine.load(run), [finding], 'first-reviewer')
        self.assertEqual(validated[0]['evidence_status'], 'unverified')

    def test_policy_comes_from_target_and_cannot_be_weakened_by_head(self):
        (self.repo / '.code-audit.yml').write_text('{"schema_version":1,"required_capabilities":[]}')
        self.commit('branch attempts to weaken baseline')
        run = self.init()
        frozen = engine.load(run)['inputs']
        self.assertEqual(frozen['policy_origin'], 'built-in-conservative-policy')
        self.assertTrue({'secrets', 'dependencies', 'tests'}.issubset({x['capability'] for x in frozen['tasks']}))
        (run / 'snapshots/H/app.py').write_text('changed after pinning')
        with self.assertRaises(AuditError):
            engine.report(run)

    def test_export_attributes_cannot_hide_or_rewrite_reviewed_source(self):
        (self.repo / '.gitattributes').write_text('app.py export-ignore\nversion.txt export-subst\n')
        (self.repo / 'version.txt').write_text('$Format:%H$\n')
        self.commit('attempt archive exclusion')
        run = self.init()
        self.assertTrue((run / 'snapshots/H/app.py').exists())
        self.assertEqual((run / 'snapshots/H/version.txt').read_text(), '$Format:%H$\n')

    def test_wrong_ci_tree_partial_scope_and_failure_contract_rejected(self):
        run = self.init()
        spec = next(x for x in engine.load(run)['inputs']['tasks'] if x['id'] == 'check-tests')
        for updates in [{'build': {'source': self.head, 'tree': 'wrong', 'configuration': 'a', 'toolchain': 'b'}},
                        {'coverage_complete': False}, {'completed_exit_codes': [0, 99]},
                        {'product_failure': True}, {'expected_records': 1}]:
            with self.subTest(updates=updates), self.assertRaises(AuditError):
                engine.ingest_check(run, self.check(run, spec, **updates))
        review = next(x for x in engine.load(run)['inputs']['tasks'] if x['kind'] == 'expert')
        with self.assertRaises(AuditError):
            engine.ingest_review(run, self.review(run, review, reviewed_paths=[]))

    def test_real_merge_candidate_and_conflict_leave_source_unchanged(self):
        git(self.repo, 'checkout', 'trunk')
        (self.repo / 'other.py').write_text('value = 1\n')
        self.commit('target moves independently')
        git(self.repo, 'checkout', 'feature')
        before = git(self.repo, 'status', '--porcelain')
        run = self.init()
        scope = engine.load(run)['inputs']['scope']
        self.assertEqual(scope['integration'], 'merge-candidate')
        self.assertTrue((run / 'snapshots/I/other.py').exists())
        self.assertEqual(git(self.repo, 'status', '--porcelain'), before)
        self.assertEqual(self.complete(run)['verdict'], 'READY')
        git(self.repo, 'checkout', 'trunk')
        self.file.write_text('def divide(a, b):\n    return 99\n')
        self.commit('conflicting target')
        git(self.repo, 'checkout', 'feature')
        conflict = self.init()
        self.assertEqual(engine.report(conflict)['verdict'], 'CHANGES_REQUIRED')

    def test_target_is_resolved_once_even_if_it_moves_while_loading_policy(self):
        actual_policy = engine.policy
        def move_target(repo, base, config):
            result = actual_policy(repo, base, config)
            git(self.repo, 'branch', '-f', 'trunk', self.head)
            return result
        with patch.object(engine, 'policy', side_effect=move_target):
            run = self.init()
        scope = engine.load(run)['inputs']['scope']
        self.assertEqual(scope['B'], self.base)
        self.assertEqual(engine.report(run)['freshness'], 'stale')

    def test_explicit_range_pins_its_own_comparison_snapshot(self):
        start = self.head
        (self.repo / 'extra.py').write_text('extra = True\n')
        self.commit('range endpoint')
        run = engine.initialize(self.repo, start + '..feature', self.root / 'ranges', base='trunk')
        scope = engine.load(run)['inputs']['scope']
        self.assertEqual(scope['A'], start)
        self.assertNotEqual(scope['A'], scope['M'])
        self.assertEqual([x['path'] for x in scope['changes']], ['extra.py'])
        self.assertEqual((run / 'snapshots/A/app.py').read_text(), 'def divide(a, b):\n    return a / 0\n')
        location = engine.source_location(run, engine.load(run), {'snapshot': start, 'path': 'app.py', 'start_line': 1, 'end_line': 2})
        self.assertTrue(location['content_sha256'])

    def test_custom_merge_driver_is_incomplete_not_silently_replaced(self):
        (self.repo / '.gitattributes').write_text('*.py merge=fixture-custom\n')
        self.commit('custom merge requirement')
        git(self.repo, 'checkout', 'trunk')
        (self.repo / 'other.py').write_text('target_change = True\n')
        self.commit('independent target')
        git(self.repo, 'checkout', 'feature')
        run = self.init()
        self.assertEqual(engine.load(run)['inputs']['scope']['integration'], 'unavailable')
        self.assertEqual(engine.report(run)['verdict'], 'INCOMPLETE')

    def test_typed_adapters_preserve_meaning_and_reject_malformed(self):
        path = self.root / 'raw.json'
        payload = [{'rule': 'R', 'path': 'app.py', 'message': 'user from host is trusted',
                    'host': {'user': 'meaningful'}, 'symbol': 'divide'}]
        atomic(path, payload)
        before = path.read_bytes()
        self.assertEqual(len(adapters.parse(path, 'observations-json')), 1)
        self.assertEqual(path.read_bytes(), before)
        path.write_text('{"rule":"R","path":"app.py","message":"one"}\n{broken\n')
        with self.assertRaises(AuditError):
            adapters.parse(path, 'observations-jsonl')
        atomic(path, {'version': '2.1.0', 'runs': [{'invocations': [{'executionSuccessful': False}], 'results': []}]})
        with self.assertRaises(AuditError):
            adapters.parse(path, 'sarif')
        path.write_text('<!DOCTYPE x [<!ENTITY y SYSTEM "file:///secret">]><pmd-cpd/>')
        with self.assertRaises(AuditError):
            adapters.parse(path, 'cpd-xml')

    def test_rename_matching_no_resolution_from_failed_head_or_new_advisories(self):
        a = adapters.observation('R', 'old.py', 'problem', line=1)
        b = adapters.observation('R', 'new.py', 'problem', line=80)
        self.assertEqual(adapters.compare([a], [b], True, True, {'old.py': 'new.py'})[0]['comparison'], 'unchanged')
        self.assertEqual(adapters.compare([a], [], True, False), [])
        self.assertEqual(adapters.compare([a], [b], False, True)[0]['comparison'], 'unknown')

    def test_imported_baseline_keeps_advisory_deltas_separate(self):
        run = self.init()
        spec = next(x for x in engine.load(run)['inputs']['tasks'] if x['id'] == 'check-dependencies')
        path = self.check(run, spec)
        data = read(path)
        record = {'rule': 'CVE-fixture', 'path': 'app.py', 'message': 'Dependency exposure fixture', 'symbol': 'dependency-A'}
        atomic(path.parent / 'data.json', [record])
        atomic(path.parent / 'baseline.json', [dict(record, line=90)])
        baseline = {key: data[key] for key in ['tool_version', 'config_digest', 'environment', 'dependencies', 'advisory_database', 'scope_paths']}
        baseline.update(snapshot=self.base, report='baseline.json', adapter='observations-json', expected_records=1, state='completed')
        data.update(expected_records=1, baseline=baseline)
        atomic(path, data)
        result = engine.ingest_check(run, path)
        self.assertEqual(result['observations'][0]['comparison'], 'unchanged')
        data['baseline']['advisory_database'] = {'sha256': 'different-old-advisories'}
        atomic(path, data)
        result = engine.ingest_check(run, path)
        self.assertEqual(result['observations'][0]['comparison'], 'unknown')
        self.assertIn('advisory_database', result['comparison_inputs']['environmental_deltas'])

    def test_introduced_history_includes_secret_removed_at_head_and_requires_redaction(self):
        (self.repo / 'credential.txt').write_text('SYNTHETIC_TEST_MARKER_ONLY\n')
        self.commit('synthetic credential introduction')
        introduced = git(self.repo, 'rev-parse', 'HEAD')
        (self.repo / 'credential.txt').unlink()
        self.commit('remove synthetic credential')
        run = self.init()
        scope = engine.load(run)['inputs']['scope']
        self.assertIn(introduced, scope['history_commits'])
        path = self.root / 'gitleaks.json'
        atomic(path, [{'RuleID': 'fixture', 'File': 'credential.txt', 'StartLine': 1,
                      'Secret': 'REDACTED', 'Match': 'key=REDACTED', 'Commit': introduced}])
        observations = adapters.parse(path, 'gitleaks-json')
        self.assertEqual(len(observations), 1)
        self.assertNotIn('SYNTHETIC_TEST_MARKER_ONLY', json.dumps(observations))
        location = engine.source_location(run, engine.load(run), {'snapshot': introduced, 'path': 'credential.txt',
                                                                  'start_line': 1, 'end_line': 1})
        self.assertTrue(location['content_sha256'])
        data = read(path); data[0]['Secret'] = 'UNREDACTED_TEST_ONLY'; atomic(path, data)
        with self.assertRaises(AuditError):
            adapters.parse(path, 'gitleaks-json')

    @unittest.skipUnless(shutil.which('gitleaks'), 'Pre-provisioned Gitleaks unavailable')
    def test_native_pinned_gitleaks_detects_removed_and_current_synthetic_markers(self):
        (self.repo / 'removed.txt').write_text('audit_fixture_key = "AUDIT_FIXTURE_0123456789"\n')
        self.commit('introduce synthetic marker')
        (self.repo / 'removed.txt').unlink()
        (self.repo / 'current.txt').write_text('audit_fixture_key = "AUDIT_FIXTURE_9876543210" # gitleaks:allow\n')
        (self.repo / '.gitleaksignore').write_text('*\n')
        self.commit('remove one marker and keep another')
        rules = self.root / 'rules.toml'
        rules.write_text('title = "Code Audit fixture rules"\n[[rules]]\nid = "audit-fixture"\n'
                         'description = "Synthetic noncredential fixture"\n'
                         'regex = \'AUDIT_FIXTURE_[0-9]{10}\'\n')
        executable = shutil.which('gitleaks')
        version = subprocess.check_output([executable, 'version'], text=True).strip()
        config = self.root / 'policy.json'
        atomic(config, {'schema_version': 1, 'sensors': {'secrets': {
            'executable': executable, 'version': version, 'version_args': ['version'],
            'adapter': 'gitleaks-json', 'rules_file': str(rules),
            'isolation': 'approved-local-disposable', 'completed_exit_codes': [0, 1]}}})
        run = self.init(config=config)
        engine.run_sensors(run)
        result = engine.get_attempt(engine.load(run), 'check-secrets')
        self.assertEqual(result['state'], 'completed', result.get('reason'))
        paths = {x['path'] for x in result['observations']}
        self.assertTrue({'removed.txt', 'current.txt'}.issubset(paths))
        self.assertNotIn('AUDIT_FIXTURE_0123456789', json.dumps(result))
        self.assertEqual(engine.report(run)['verdict'], 'INCOMPLETE')

    def test_html_hostile_text_is_inert_and_evidence_tampering_invalidates_ready(self):
        run = self.init()
        f = self.finding(run)
        f['impact'] = '<script>alert("hostile")</script>'
        self.complete(run, f)
        html = (run / 'report.html').read_text()
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)
        ref = f['evidence'][0]
        (run / ref['path']).write_text('modified evidence')
        self.assertEqual(engine.report(run)['verdict'], 'INCOMPLETE')

    def test_scan_and_limited_reviews_never_ready(self):
        scan = self.init(profile='scan')
        self.assertEqual(self.complete(scan)['verdict'], 'INCOMPLETE')
        limited = self.init(limited_roles=['correctness'])
        self.assertEqual(self.complete(limited)['verdict'], 'INCOMPLETE')

    def test_owned_timeout_preserves_evidence_and_other_process(self):
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            result = execute([sys.executable, '-c', 'import time; print("partial", flush=True); time.sleep(30)'],
                             self.root, self.root / 'process', 0.5, memory_mb=256)
            self.assertTrue(result['timed_out'])
            self.assertIn('partial', (self.root / 'process/stdout.txt').read_text())
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.terminate()
            unrelated.wait()

    def test_owned_cancellation_and_interrupted_task_resume(self):
        cancel = self.root / 'cancel.json'; atomic(cancel, {'requested': True})
        result = execute([sys.executable, '-c', 'import time; time.sleep(30)'], self.root,
                         self.root / 'cancelled-process', 30, memory_mb=256, cancel_file=cancel)
        self.assertTrue(result['cancelled'])
        run = self.init()
        state = engine.load(run)
        spec = next(x for x in state['inputs']['tasks'] if x['kind'] == 'sensor')
        interrupted = engine.attempt(state, spec, 'running')
        engine.record(run, state, interrupted)
        engine.run_sensors(run, retry=True)
        attempts = engine.load(run)['results'][spec['id']]
        self.assertEqual(attempts[0]['state'], 'partial')
        self.assertEqual(attempts[1]['state'], 'unavailable')

    def test_scanner_findings_exit_is_completed_but_malformed_output_is_partial(self):
        config = self.root / 'sensor-policy.json'
        version = subprocess.check_output([sys.executable, '--version'], text=True).strip()
        sensor = {'executable': sys.executable, 'version': version, 'version_args': ['--version'],
                  'adapter': 'observations-json', 'isolation': 'approved-local-disposable',
                  'report': 'raw.json', 'completed_exit_codes': [0, 7],
                  'args': ['-c', 'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("[]"); sys.exit(7)', '{report}']}
        atomic(config, {'schema_version': 1, 'sensors': {'lint': sensor}})
        run = self.init(config=config)
        engine.run_sensors(run)
        result = engine.get_attempt(engine.load(run), 'check-lint')
        self.assertEqual(result['state'], 'completed', result.get('reason'))
        self.assertEqual(result['exit_code'], 7)
        sensor['args'][1] = 'import pathlib,sys; pathlib.Path(sys.argv[1]).write_text("[broken"); sys.exit(0)'
        atomic(config, {'schema_version': 1, 'sensors': {'lint': sensor}})
        broken = self.init(config=config)
        engine.run_sensors(broken)
        result = engine.get_attempt(engine.load(broken), 'check-lint')
        self.assertEqual(result['state'], 'partial')
        self.assertEqual(engine.report(broken)['verdict'], 'INCOMPLETE')

    def test_runtime_device_lock_or_wrong_owner_cannot_complete_coverage(self):
        config = self.root / 'runtime-policy.json'
        atomic(config, {'schema_version': 1, 'required_capabilities': ['secrets', 'dependencies', 'tests', 'runtime']})
        run = self.init(config=config)
        spec = next(x for x in engine.load(run)['inputs']['tasks'] if x['id'] == 'check-runtime')
        runtime = {'harness': 'fixture-SNAG', 'device_fingerprint': 'fixture-image', 'scenario_version': '1',
                   'assertions': ['expected final state'], 'initial_state': 'clean', 'final_state': 'unknown',
                   'ownership': 'exclusive-granted', 'failure_kind': 'locked', 'application_hash': digest('fixture-app')}
        with self.assertRaises(AuditError):
            engine.ingest_check(run, self.check(run, spec, runtime=runtime))
        runtime.update(failure_kind='none', ownership='another-controller')
        with self.assertRaises(AuditError):
            engine.ingest_check(run, self.check(run, spec, runtime=runtime))

    def test_shallow_clone_and_nonexistent_refs_are_not_guessed(self):
        with self.assertRaises(AuditError):
            engine.initialize(self.repo, 'not-a-real-ref', self.root / 'audit', base='trunk')
        (self.repo / '.git/shallow').write_text(self.base + '\n')
        with self.assertRaisesRegex(AuditError, 'Shallow'):
            self.init()

    def test_oracle_receipts_deduplicate_and_unknown_stays_unknown(self):
        run = self.init()
        ref = self.note(run)
        response = {'message_id': 'm', 'request_id': 'r', 'input_tokens': 20,
                    'cache_creation_input_tokens': 3, 'cached_input_tokens': 10,
                    'output_tokens': 8, 'reasoning_output_tokens': 4}
        payload = {'schema_version': 1, 'run_id': run.name,
                   'attribution': {'repository_identity': engine.load(run)['inputs']['scope']['repository_identity'],
                                   'sessions': ['s'], 'status': 'exact', 'evidence': [ref]},
                   'receipts': [{'provider': 'claude', 'session_id': 's', 'schema_version': 2,
                                 'coverage': {'status': 'complete'}, 'responses': [response, response]}], 'observations': []}
        path = self.root / 'process.json'; atomic(path, payload)
        result = ingest_process(run, path)
        self.assertEqual(result['total_tokens'], 41)
        self.assertIsNone(result['estimated_cost'])
        payload['attribution']['status'] = 'unknown'; atomic(path, payload)
        self.assertIsNone(ingest_process(run, path)['total_tokens'])
        payload['schema_version'] = 99; atomic(path, payload)
        with self.assertRaises(AuditError):
            ingest_process(run, path)

    def test_hypothesis_candidate_has_no_reference_or_evaluator(self):
        run = self.init()
        root = self.root / 'experiment'
        for folder in ['sample', 'environment', 'evaluation', 'reference']:
            (root / folder).mkdir(parents=True)
            (root / folder / 'input.txt').write_text(folder + ' unique fixture\n')
        (root / 'README.md').write_text('Private experiment rationale')
        (root / 'prompt.md').write_text('Review the supplied helper behavior.')
        data = {'schema_version': 1, 'id': 'bounded-fixture', 'origin_evidence': [self.note(run)],
                'claim': 'One bounded task intervention', 'population': ['fixture task'],
                'intervention': {'model': 'candidate/pinned'}, 'baseline': {'model': 'baseline/pinned'},
                'metrics': ['correctness', 'tokens'], 'success_criteria': 'All assertions pass.',
                'failure_criteria': 'Any behavior regression.', 'readiness': 'ready', 'missing': [],
                'package_root': 'experiment'}
        path = self.root / 'hypothesis.json'; atomic(path, data)
        item = package_hypothesis(run, path)
        with zipfile.ZipFile(run / 'hypotheses' / item['candidate_package']) as archive:
            self.assertEqual(set(archive.namelist()), {'prompt.md', 'sample/input.txt', 'environment/input.txt'})
        data['id'] = 'leaked-fixture'; atomic(path, data)
        (root / 'sample/input.txt').write_text((root / 'reference/input.txt').read_text())
        with self.assertRaises(AuditError):
            package_hypothesis(run, path)

    def test_exported_plugin_runs_without_marketplace_or_python_dependencies(self):
        standalone = self.root / 'standalone'
        shutil.copytree(PACKAGE, standalone, ignore=shutil.ignore_patterns('__pycache__'))
        proc = subprocess.run([sys.executable, '-S', str(standalone / 'scripts/code-audit.py'), 'init',
                               '--repo', str(self.repo), '--target', 'feature', '--base', 'trunk',
                               '--output-root', str(self.root / 'portable-output')], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        output = json.loads(proc.stdout)
        self.assertTrue(Path(output['run'], 'report.html').exists())


if __name__ == '__main__':
    unittest.main()
