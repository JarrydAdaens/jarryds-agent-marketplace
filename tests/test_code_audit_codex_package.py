"""Codex packaging boundaries; no installs, model calls, or live project audits."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLAUDE = ROOT / 'plugins/claude/code-audit'
CODEX = ROOT / 'plugins/codex/code-audit'
ROLES = {'correctness', 'test-adequacy', 'security', 'duplication-reuse', 'architecture',
         'platform', 'cross-cutting', 'verifier', 'process-efficiency'}


def payload(folder, components):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*')
            if p.is_file() and '__pycache__' not in p.parts and
            p.relative_to(folder).parts[0] in components}


class CodexCodeAuditPackage(unittest.TestCase):
    def test_native_manifest_and_catalog_have_one_host_and_stable_version(self):
        manifest = json.loads((CODEX / '.codex-plugin/plugin.json').read_text())
        self.assertEqual(manifest['name'], 'code-audit')
        self.assertEqual(manifest['version'], '1.0.0')
        self.assertTrue(manifest['description'])
        self.assertEqual(manifest['skills'], './skills/')
        self.assertTrue((CODEX / manifest['skills'] / 'code-audit/SKILL.md').is_file())
        self.assertEqual([x.parent.name for x in CODEX.glob('.*-plugin/plugin.json')], ['.codex-plugin'])
        catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        matches = [x for x in catalog['plugins'] if x['name'] == 'code-audit']
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['source'], {'source': 'local', 'path': './plugins/codex/code-audit'})
        self.assertEqual(matches[0]['policy']['installation'], 'AVAILABLE')
        cursor = json.loads((ROOT / '.cursor-plugin/marketplace.json').read_text())
        self.assertFalse(any(x['name'] == 'code-audit' for x in cursor['plugins']))

    def test_controller_configuration_license_and_regression_suite_match(self):
        self.assertEqual(payload(CODEX, {'audit', 'scripts', 'config', 'tests'}),
                         payload(CLAUDE, {'audit', 'scripts', 'config', 'tests'}))
        self.assertEqual((CODEX / 'LICENSE').read_bytes(), (CLAUDE / 'LICENSE').read_bytes())

    def test_skill_uses_codex_frontmatter_and_nine_contained_role_procedures(self):
        skill = CODEX / 'skills/code-audit/SKILL.md'
        frontmatter = skill.read_text().split('---', 2)[1]
        keys = set(re.findall(r'^([a-z][a-z-]*):', frontmatter, re.MULTILINE))
        self.assertEqual(keys, {'name', 'description', 'metadata'})
        self.assertRegex(frontmatter, r'(?m)^name: code-audit$')
        self.assertRegex(frontmatter, r'(?m)^  version: "1\.0\.0"$')
        self.assertRegex(frontmatter, r'(?m)^  argument-hint:')
        roles = CODEX / 'references/specialists'
        self.assertEqual({p.stem for p in roles.glob('*.md')}, ROLES)
        dispatch = CODEX / 'references/specialist-dispatch.md'
        linked = {Path(x).stem for x in re.findall(r'\]\((specialists/[^)]+)\)', dispatch.read_text())}
        self.assertEqual(linked, ROLES)

    def test_all_local_markdown_links_stay_in_the_exported_package(self):
        for path in CODEX.rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                if target.startswith(('https://', 'http://', '#')):
                    continue
                resolved = (path.parent / target.split('#')[0]).resolve()
                self.assertTrue(resolved.is_relative_to(CODEX.resolve()), (path, target))
                self.assertTrue(resolved.exists(), (path, target))

    def test_exported_codex_controller_is_standalone_and_host_bound(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            exported = root / 'exported-code-audit'
            shutil.copytree(CODEX, exported, ignore=shutil.ignore_patterns('__pycache__'))
            repo = root / 'project'; repo.mkdir()
            env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1',
                       GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0')
            def git(*args):
                return subprocess.check_output(['git', '-c', 'core.hooksPath=' + os.devnull,
                                                '-C', str(repo), *args], env=env, stderr=subprocess.PIPE)
            git('init', '-b', 'trunk')
            git('config', 'user.name', 'Fixture')
            git('config', 'user.email', 'fixture@example.invalid')
            (repo / 'app.py').write_text('value = 1\n')
            git('add', '.')
            git('commit', '-m', 'base')
            git('checkout', '-b', 'feature')
            (repo / 'app.py').write_text('value = 2\n')
            git('add', '.')
            git('commit', '-m', 'change')
            before = git('status', '--porcelain')
            result = subprocess.run([sys.executable, '-S', str(exported / 'scripts/code-audit.py'),
                                     'init', '--repo', str(repo), '--target', 'feature', '--base', 'trunk',
                                     '--output-root', str(root / 'private-audits')],
                                    cwd=root, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stderr)
            run = Path(json.loads(result.stdout)['run'])
            self.assertEqual(json.loads((run / 'verdict.json').read_text())['verdict'], 'INCOMPLETE')
            run_before = (run / 'run.json').read_bytes()
            wrong_host = subprocess.run([sys.executable, '-S', str(CLAUDE / 'scripts/code-audit.py'),
                                         'status', '--run', str(run)], cwd=root, env=env,
                                        capture_output=True, text=True, timeout=60)
            self.assertEqual(wrong_host.returncode, 2)
            self.assertIn('changed', wrong_host.stderr)
            self.assertEqual((run / 'run.json').read_bytes(), run_before)
            note = root / 'process-notes.txt'
            note.write_text('Synthetic session attribution; no native usage adapter has been validated.\n')
            retained = subprocess.run([sys.executable, '-S', str(exported / 'scripts/code-audit.py'),
                                       'add-evidence', '--run', str(run), '--input', str(note)],
                                      cwd=root, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(retained.returncode, 0, retained.stderr)
            reference = json.loads(retained.stdout)
            process_input = root / 'process.json'
            process_input.write_text(json.dumps({
                'schema_version': 1, 'run_id': run.name,
                'attribution': {'repository_identity': json.loads(run_before)['inputs']['scope']['repository_identity'],
                                'sessions': ['codex-fixture'], 'status': 'exact', 'evidence': [reference]},
                'receipts': [{'provider': 'codex', 'session_id': 'codex-fixture', 'coverage': {'status': 'complete'},
                              'responses': [{'message_id': 'm', 'request_id': 'r', 'input_tokens': 500,
                                             'cache_creation_input_tokens': 0, 'cached_input_tokens': 100,
                                             'output_tokens': 20, 'reasoning_output_tokens': 10}]}],
                'observations': []}))
            imported = subprocess.run([sys.executable, '-S', str(exported / 'scripts/code-audit.py'),
                                       'import-process', '--run', str(run), '--input', str(process_input)],
                                      cwd=root, env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(imported.returncode, 0, imported.stderr)
            process = json.loads(imported.stdout)
            self.assertEqual(process['status'], 'partial')
            self.assertIsNone(process['total_tokens'])
            self.assertTrue(all(x is None for x in process['totals'].values()))
            self.assertEqual(git('status', '--porcelain'), before)


if __name__ == '__main__':
    unittest.main()
