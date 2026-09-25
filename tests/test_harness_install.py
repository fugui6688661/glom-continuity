"""Installer contract through its CLI; SDK metadata fixtures are not runtime proof."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/harness_install.py'
PEERS = {
    'dsh': '0.1.5-rc.1', 'cordis': '4.0.2', 'schemastery': '3.18.2',
    'dsh-llm': '0.1.5-rc.1', 'dsh-client-ui-commands': '0.1.5-rc.1',
    'dsh-api-session-controller': '0.1.5-rc.1', 'dsh-client-ui-conversation': '0.1.5-rc.1',
}


@unittest.skipUnless(os.name == 'posix', 'Private-directory installer currently supports POSIX only')
class HarnessInstall(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-install-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / '中文 project'
        self.project.mkdir(mode=0o700)
        initialized = subprocess.run([sys.executable, str(ROOT / 'scripts/continuity.py'),
                                     '--project', str(self.project), 'init', '--name', '安装项目'],
                                    capture_output=True, text=True, check=True)
        self.project_id = json.loads(initialized.stdout)['data']['project_id']
        self.sdk = self.base / 'local sdk' / 'node_modules'
        for name, version in PEERS.items():
            path = self.sdk / '@deepseek-ai' / name
            path.mkdir(parents=True, mode=0o700)
            (path / 'package.json').write_text(json.dumps({'name': '@deepseek-ai/' + name, 'version': version}))
        self.target = self.base / '接入 bundle'

    def command(self, action, ok=True, extra=()):
        args = [sys.executable, str(CLI), action, '--directory', str(self.target)]
        if action != 'status':
            args += ['--project', str(self.project), '--project-id', self.project_id,
                     '--sdk-node-modules', str(self.sdk)]
        result = subprocess.run(args + list(extra), cwd=self.base, capture_output=True,
                                text=True, timeout=15)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope['ok'], ok)
        return envelope

    def test_preflight_is_read_only_and_distinguishes_prepared_from_running(self):
        database = self.project / '.continuity/state.sqlite3'
        before = hashlib.sha256(database.read_bytes()).hexdigest()
        result = self.command('preflight')['data']
        self.assertEqual(result['state'], 'ready_to_stage')
        self.assertEqual(result['project_id'], self.project_id)
        self.assertEqual(result['host_state'], 'not_inspected')
        self.assertFalse(result['model_called'])
        self.assertFalse(self.target.exists())
        self.assertEqual(hashlib.sha256(database.read_bytes()).hexdigest(), before)

    def test_install_copies_complete_bundle_without_starting_or_changing_host(self):
        database = self.project / '.continuity/state.sqlite3'
        before = database.read_bytes()
        result = self.command('install')['data']
        self.assertEqual(result['state'], 'staged_not_activated')
        self.assertFalse(result['profile_changed'])
        self.assertEqual(result['host_state'], 'not_inspected')
        for relative in ('scripts/continuity.py', 'scripts/recovery.py',
                         'adapters/harness/native-plugin.mjs', 'adapters/harness/automatic-recovery.mjs',
                         'adapters/harness/client-notice/package.json',
                         'adapters/harness/client-notice/index.mjs', 'adapters/harness/client-notice/client.js'):
            copied = self.target / relative
            self.assertEqual(copied.read_bytes(), (ROOT / relative).read_bytes())
            self.assertEqual(copied.stat().st_mode & 0o777, 0o600)
        entries = json.loads((self.target / 'overlay.json').read_text())
        self.assertEqual([item['id'] for item in entries], ['recaloom-native', 'recaloom-notice'])
        self.assertEqual(entries[0]['config']['projectId'], self.project_id)
        self.assertEqual(entries[0]['config']['project'], str(self.project))
        self.assertEqual(self.command('status')['data']['state'], 'staged_not_activated')
        self.assertFalse((self.target / 'settings.yaml').exists())
        self.assertEqual(database.read_bytes(), before)
        self.assertEqual(self.command('install', ok=False)['code'], 'TARGET_EXISTS')
        self.assertEqual(database.read_bytes(), before)

    def test_refuses_shared_writable_sdk_before_creating_bundle(self):
        self.sdk.chmod(0o777)
        self.assertEqual(self.command('install', ok=False)['code'], 'UNSAFE_SDK')
        self.assertFalse(self.target.exists())

    def test_executable_bundle_must_stay_outside_project(self):
        self.target = self.project / 'adapter-bundle'
        self.assertEqual(self.command('install', ok=False)['code'], 'UNSAFE_LOCATION')
        self.assertFalse(self.target.exists())

    def test_status_rejects_a_different_project_recreated_at_same_path(self):
        self.command('install')
        self.project.rename(self.base / 'preserved original project')
        self.project.mkdir(mode=0o700)
        subprocess.run([sys.executable, str(ROOT / 'scripts/continuity.py'), '--project',
                        str(self.project), 'init', '--name', '另一个项目'], check=True,
                       capture_output=True)
        self.assertEqual(self.command('status', ok=False)['code'], 'PROJECT_MISMATCH')

    def test_modified_file_is_rejected_and_left_intact(self):
        self.command('install')
        file = self.target / 'overlay.json'
        file.write_text('[]\n')
        self.assertEqual(self.command('status', ok=False)['code'], 'BUNDLE_CHANGED')
        self.assertEqual(file.read_text(), '[]\n')

    def test_relocated_bundle_is_rejected_without_rewriting_absolute_bindings(self):
        self.command('install')
        original = (self.target / 'overlay.json').read_bytes()
        moved = self.base / 'moved bundle'
        self.target.rename(moved)
        self.target = moved
        self.assertEqual(self.command('status', ok=False)['code'], 'BUNDLE_MOVED')
        self.assertEqual((moved / 'overlay.json').read_bytes(), original)

    def test_bundle_preserves_the_invoking_python_environment(self):
        self.command('install')
        overlay = json.loads((self.target / 'overlay.json').read_text())
        self.assertEqual(overlay[0]['config']['python'], str(Path(sys.executable).absolute()))

    def test_path_resolution_loop_returns_json_not_traceback(self):
        loop = self.base / 'loop'
        loop.symlink_to(loop)
        self.target = loop / 'bundle'
        for action in ('status', 'preflight', 'install'):
            with self.subTest(action=action):
                self.assertEqual(self.command(action, ok=False)['code'], 'IO_ERROR')

    def test_unsupported_sdk_and_wrong_project_do_not_create_bundle(self):
        self.assertEqual(self.command('install', ok=False, extra=('--project-id', 'wrong'))['code'],
                         'PROJECT_MISMATCH')
        package = self.sdk / '@deepseek-ai/dsh/package.json'
        package.write_text(json.dumps({'name': '@deepseek-ai/dsh', 'version': '99.0.0'}))
        self.assertEqual(self.command('install', ok=False)['code'], 'UNSUPPORTED_SDK')
        self.assertFalse(self.target.exists())

    def test_bundle_file_links_are_not_followed(self):
        self.command('install')
        file = self.target / 'overlay.json'
        original = self.base / 'saved overlay.json'
        file.rename(original)
        file.symlink_to(original)
        self.assertEqual(self.command('status', ok=False)['code'], 'UNSAFE_FILE')
        file.unlink()
        os.link(original, file)
        self.assertEqual(self.command('status', ok=False)['code'], 'UNSAFE_FILE')

    def test_partial_installation_is_not_repaired_or_reported_ready(self):
        self.target.mkdir(mode=0o700)
        partial = self.target / 'overlay.json'
        partial.write_text('preserve me')
        self.assertEqual(self.command('status', ok=False)['code'], 'IO_ERROR')
        self.assertEqual(self.command('install', ok=False)['code'], 'TARGET_EXISTS')
        self.assertEqual(partial.read_text(), 'preserve me')

    def test_preflight_does_not_run_selected_sdk_code(self):
        package = self.sdk / '@deepseek-ai/dsh/package.json'
        info = json.loads(package.read_text())
        marker = self.base / 'must-not-exist'
        payload = 'require("node:fs").writeFileSync(' + json.dumps(str(marker)) + ', "executed")'
        info['main'] = 'malicious.cjs'
        info['scripts'] = {'postinstall': 'node malicious.cjs'}
        package.write_text(json.dumps(info))
        (package.parent / 'malicious.cjs').write_text(payload)
        self.command('preflight')
        self.assertFalse(marker.exists())
        self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
