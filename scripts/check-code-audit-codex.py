"""Native local catalog smoke check in an isolated profile; no install or model calls."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/codex/code-audit'


def main():
    executable = shutil.which('codex')
    if not executable:
        print('NOT TESTED: native Codex catalog discovery (CLI unavailable)')
        return 0
    manifest = json.loads((PACKAGE / '.codex-plugin/plugin.json').read_text(encoding='utf-8'))
    catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text(encoding='utf-8'))
    identifier = manifest['name'] + '@' + catalog['name']
    try:
        with tempfile.TemporaryDirectory(prefix='code-audit-codex-native-') as temporary:
            # Set the documented variable only in children, never mutate the caller's profile.
            env = dict(os.environ, CODEX_HOME=str(Path(temporary).resolve()))
            def invoke(*args):
                result = subprocess.run([executable, '--no-daemon', *args], cwd=ROOT,
                                        env=env, capture_output=True, text=True, timeout=60)
                if result.returncode:
                    raise ValueError('Codex catalog command failed: ' + result.stderr[:2000])
                return result.stdout
            version = invoke('--version').strip()
            invoke('plugin', 'marketplace', 'add', str(ROOT))
            marketplaces = json.loads(invoke('plugin', 'marketplace', 'list', '--json'))
            if not any(x['name'] == catalog['name'] for x in marketplaces['marketplaces']):
                raise ValueError('Native CLI did not discover the registered local marketplace')
            listing = json.loads(invoke('plugin', 'list', '--available', '--marketplace', catalog['name'], '--json'))
            matches = [x for x in listing['available'] if x['pluginId'] == identifier]
            if len(matches) != 1:
                raise ValueError('Native CLI did not return exactly one Code Audit package')
            plugin = matches[0]
            if plugin['version'] != manifest['version']:
                raise ValueError('Native CLI returned the wrong component version')
            if plugin['source']['source'] != 'local' or Path(plugin['source']['path']).resolve() != PACKAGE.resolve():
                raise ValueError('Native CLI resolved a different host package')
            if plugin['installed'] or plugin['enabled']:
                raise ValueError('Discovery unexpectedly installed or enabled Code Audit')
            print(f'PASS: {version} discovers {identifier} {manifest["version"]} from the native Codex package.')
            print('Disposable profile removed; no plugin installed, user profile modified, or model invoked.')
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print('Native Codex catalog check: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
