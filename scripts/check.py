"""Repository check entrypoint. No installation, publishing, or desktop launch."""
import json
import subprocess
import sys
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command):
    print('CHECK:', ' '.join(map(str, command)), flush=True)
    return subprocess.run(command, cwd=ROOT).returncode


def main():
    failures = run([sys.executable, 'scripts/generate-packages.py', '--check'])
    for host, catalog, manifest in [
        ('claude', '.claude-plugin/marketplace.json', '.claude-plugin/plugin.json'),
        ('codex', '.agents/plugins/marketplace.json', '.codex-plugin/plugin.json'),
        ('cursor', '.cursor-plugin/marketplace.json', '.cursor-plugin/plugin.json'),
    ]:
        for plugin in json.loads((ROOT / catalog).read_text(encoding='utf-8'))['plugins']:
            source = plugin['source']
            if isinstance(source, dict):
                source = source.get('path')
            if not isinstance(source, str) or not source.startswith(f'./plugins/{host}/'):
                raise ValueError(f'{host}: invalid source {source}')
            folder = ROOT / source
            data = json.loads((folder / manifest).read_text(encoding='utf-8'))
            if not data.get('name') or not data.get('description'):
                raise ValueError(f'incomplete manifest: {folder}')
            if host == 'codex' and not data.get('version'):
                raise ValueError(f'missing Codex version: {folder}')
            manifests = list(folder.glob('.*-plugin/plugin.json'))
            if len(manifests) != 1:
                raise ValueError(f'mixed host manifests: {folder}')
    failures |= run(['uv', 'run', '--with', 'pillow', '--with', 'numpy',
                     'python', '-m', 'unittest', 'discover', '-s', 'tests', '-v'])
    for host in ['claude', 'codex']:
        failures |= run([sys.executable, '-m', 'unittest', 'discover', '-s',
                         f'plugins/{host}/code-audit/tests', '-v'])
    failures |= run(['uv', 'run', '--with', 'pytest', '--with', 'jsonschema',
                     '--with', 'pyyaml', '--with', 'pillow', '--with', 'numpy',
                     'pytest', 'source/plugins/repository-savior/tests', '-q'])
    failures |= run(['uv', 'run', '--with', 'pillow', '--with', 'numpy',
                     'source/plugins/game-golden-screenshot-verifier/skills/'
                     'game-golden-screenshot-verifier/tests/test_compare.py'])
    failures |= run(['node', '--test', *map(str, sorted(
        (ROOT / 'source/skills/oracle-token-stats/scripts/test').glob('*.test.js')))])
    for suite in ['oracle-generate-stats/test_generate_stats.py',
                  'oracle-token-appraise/test_appraise.py']:
        failures |= run(['uv', 'run', '--with', 'pytest', '--with', 'tiktoken', 'pytest',
                         'source/skills/' + suite, '-q'])
    failures |= run(['git', 'diff', '--check'])
    claude = shutil.which('claude')
    if claude:
        failures |= run([claude, 'plugin', 'validate', '.'])
        failures |= run([claude, 'plugin', 'validate', 'plugins/claude/code-audit'])
    else:
        print('NOT TESTED: native Claude catalog validation (CLI unavailable)')
    failures |= run([sys.executable, 'scripts/check-code-audit-codex.py'])
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
