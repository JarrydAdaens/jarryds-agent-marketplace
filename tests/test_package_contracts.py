"""Focused personal package regressions; no desktop or external services."""
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'source/plugins'


class PackageContracts(unittest.TestCase):
    def test_payload_parity(self):
        generator = runpy.run_path(str(ROOT / 'scripts/generate-packages.py'))
        self.assertFalse(generator['generate'](True))

    def test_non_claude_personas_are_portable(self):
        for host in ['codex', 'cursor']:
            for path in (ROOT / 'plugins' / host).glob('*/agents/*.md'):
                text = path.read_text()
                self.assertNotIn('\nmodel:', text)
                self.assertNotIn('\ntools:', text)
                self.assertNotIn('C:\\Users\\', text)

    def test_discovery_is_selective(self):
        for path in SOURCE.glob('*/skills/*/SKILL.md'):
            text = path.read_text()
            description = next(line for line in text.splitlines() if line.startswith('description:'))
            self.assertLess(len(description), 220)
            self.assertIn('Use when', description)
            self.assertIn('does not authorize', text)
        for family in ['game-golden-screenshot-verifier', 'wpf-visual-quality-gate']:
            text = (SOURCE/family/'skills'/family/'SKILL.md').read_text()
            self.assertIn('explicitly adopts', text)
            self.assertIn('explicit user approval' if family.startswith('wpf') else
                          'user explicitly approves', text.lower())

    def test_normalization_nested_order_and_malformed_input(self):
        path = SOURCE/'open-source-auditor/audit-lib/normalize.py'
        module = runpy.run_path(str(path))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = root/'raw'; raw.mkdir()
            a = raw/'a.json'
            a.write_text(json.dumps({'findings': [{'file': 'z', 'timestamp': 'old'}, {'file': 'a'}]}))
            normalized = module['normalize_file'](a, root)
            self.assertEqual(normalized, {'findings': [{'file': 'a'}, {'file': 'z'}]})
            a.write_text('{broken')
            proc = subprocess.run([sys.executable, str(path), str(root), str(raw), str(root/'norm')], capture_output=True)
            self.assertEqual(proc.returncode, 2)

    def test_missing_sensor_tools_and_traceability(self):
        result = runpy.run_path(str(SOURCE/'open-source-auditor/audit-lib/sensor-result.py'))['result']
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = root/'raw'; raw.mkdir()
            norm = root/'normalized'; norm.mkdir()
            (raw/'a.json').write_text('[]'); (norm/'a.json').write_text('[]')
            self.assertEqual(result('secrets', raw, norm, {'gitleaks': {'available': False}})['status'], 'incomplete')
            self.assertEqual(result('secrets', raw, norm, {'gitleaks': {'available': True}})['status'], 'complete')
            with self.assertRaises(ValueError):
                result('secrets', raw, norm, {}, [{'finding_id': 'one', 'evidence_path': 'invented'}])
            with self.assertRaises(ValueError):
                result('secrets', raw, norm, {}, [{'finding_id': 'one', 'evidence_path': 'normalized/a.json'}])

    def test_reference_refusal_backup_and_path_containment(self):
        from PIL import Image
        folder = SOURCE/'game-golden-screenshot-verifier/skills/game-golden-screenshot-verifier'
        sys.path.insert(0, str(folder))
        module = runpy.run_path(str(folder/'run_eval.py'))
        config = module['config_mod']
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            current = root/'current.png'; golden = root/'golden.png'
            Image.new('RGB', (3, 3), 'red').save(current)
            Image.new('RGB', (3, 3), 'blue').save(golden)
            old = golden.read_bytes()
            with self.assertRaises(ValueError):
                module['approve_reference'](current, golden, False)
            self.assertEqual(golden.read_bytes(), old)
            module['approve_reference'](current, golden, True)
            backups = list(root.glob('*.backup'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_bytes(), old)
            self.assertEqual(golden.read_bytes(), current.read_bytes())
            config_path = root/'config.json'
            for name in ['../outside.png', '..\\outside.png', '/absolute.png']:
                config_path.write_text(json.dumps({'executable': 'game', 'golden_name': name}))
                with self.assertRaises(ValueError):
                    config.load_config(config_path)

    def test_snapshot_manifest_cannot_modify_source_or_prior_evidence(self):
        script = SOURCE/'repository-savior/gateways/source-read-only/fingerprint_source.py'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root/'archive'; source.mkdir()
            (source/'code.txt').write_bytes(b'original')
            manifest = source/'manifest.json'
            command = [sys.executable, str(script), 'record', str(source), str(manifest)]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertFalse(manifest.exists())
            outside = root/'manifest.json'; command[-1] = str(outside)
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            before = outside.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual(outside.read_bytes(), before)
            command[2] = 'verify'
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            (source/'code.txt').write_bytes(b'changed')
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 1)


if __name__ == '__main__':
    unittest.main()
