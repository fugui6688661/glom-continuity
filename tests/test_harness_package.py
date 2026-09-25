"""Offline acceptance of Harness resources through the installed wheel only."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
import zipfile


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_FILES = (
    'native-plugin.mjs',
    'automatic-recovery.mjs',
    'managed-host.mjs',
    'client-notice/package.json',
    'client-notice/index.mjs',
    'client-notice/client.js',
)
SDK_PEERS = {
    'dsh': '0.1.5-rc.1', 'cordis': '4.0.2', 'schemastery': '3.18.2',
    'dsh-llm': '0.1.5-rc.1', 'dsh-client-ui-commands': '0.1.5-rc.1',
    'dsh-api-session-controller': '0.1.5-rc.1', 'dsh-client-ui-conversation': '0.1.5-rc.1',
}
HAS_BUILDER = all(importlib.util.find_spec(name) for name in ('pip', 'setuptools', 'wheel'))
RESOURCE_PROBE = r'''
import base64
from importlib import metadata, resources
import json
from pathlib import Path
import sys

import glom_continuity
import glom_continuity.harness

runtime = Path(sys.prefix).resolve()
for package in (glom_continuity, glom_continuity.harness):
    assert Path(package.__file__).resolve().is_relative_to(runtime), package.__file__
root = resources.files('glom_continuity.harness')
payload = {}
for name in json.load(sys.stdin):
    resource = root.joinpath(*name.split('/'))
    assert Path(str(resource)).resolve().is_relative_to(runtime), str(resource)
    payload[name] = base64.b64encode(resource.read_bytes()).decode('ascii')
entrypoints = metadata.distribution('glom-continuity').entry_points
print(json.dumps({
    'resources': payload,
    'sys_path': sys.path,
    'harness_entrypoints': [entry.value for entry in entrypoints
                           if entry.group == 'console_scripts'
                           and entry.name == 'glom-continuity-harness'],
}))
'''


@unittest.skipUnless(HAS_BUILDER, 'Requires locally installed pip, setuptools>=77, wheel')
class HarnessPackage(unittest.TestCase):
    def command(self, args, cwd, input=None):
        # Do not inherit package indexes, Python paths, credentials or user pip config.
        env = {key: os.environ[key] for key in ('PATH', 'SystemRoot', 'WINDIR')
               if key in os.environ}
        env['PIP_CONFIG_FILE'] = os.devnull
        result = subprocess.run(args, cwd=cwd, env=env, input=input,
                                capture_output=True, text=True, encoding='utf-8', timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_release_wheel_resources_and_installer_work_without_source_tree(self):
        expected = {name: (ROOT / 'adapters' / 'harness' / name).read_bytes()
                    for name in RUNTIME_FILES}
        expected_assets = {'adapters/harness/' + name: data for name, data in expected.items()}
        expected_assets.update({name: (ROOT / name).read_bytes()
                                for name in ('scripts/continuity.py', 'scripts/recovery.py')})
        with tempfile.TemporaryDirectory(prefix='continuity-harness-package-') as temp:
            base = Path(temp).resolve() / '中文 打包验收'
            base.mkdir(mode=0o700)
            source = base / 'release source'
            source.mkdir()
            for relative in json.loads((ROOT / 'release-files.json').read_text(encoding='utf-8')):
                destination = source / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, destination)

            wheels = base / 'wheels'
            pip = [sys.executable, '-I', '-B', '-m', 'pip', '--isolated',
                   '--disable-pip-version-check', '--no-cache-dir']
            self.command(pip + ['wheel', '--no-index', '--no-deps', '--no-build-isolation',
                                '--wheel-dir', str(wheels), str(source)], base)
            artifacts = list(wheels.glob('*.whl'))
            self.assertEqual(len(artifacts), 1)

            runtime = base / '隔离 environment'
            venv.EnvBuilder(with_pip=False, system_site_packages=False).create(runtime)
            binaries = runtime / ('Scripts' if os.name == 'nt' else 'bin')
            python = binaries / ('python.exe' if os.name == 'nt' else 'python')
            self.command(pip + ['--python', str(python), 'install', '--no-index', '--no-deps',
                                '--no-compile', str(artifacts[0])], base)

            # The installed consumer has neither the staged source nor the repo on sys.path.
            shutil.rmtree(source)
            unrelated = base / '无关 cwd'
            unrelated.mkdir()
            result = self.command([str(python), '-I', '-B', '-c', RESOURCE_PROBE], unrelated,
                                  input=json.dumps(RUNTIME_FILES))
            observed = json.loads(result.stdout)
            self.assertEqual({name: base64.b64decode(data, validate=True)
                              for name, data in observed['resources'].items()}, expected)
            for path in observed['sys_path']:
                self.assertFalse(Path(path).resolve().is_relative_to(ROOT))
                self.assertFalse(Path(path).resolve().is_relative_to(source))
            self.assertEqual(observed['harness_entrypoints'], ['glom_continuity.harness_install:main'])
            suffix = '.exe' if os.name == 'nt' else ''
            harness_cli = binaries / ('glom-continuity-harness' + suffix)
            self.assertTrue(harness_cli.is_file())
            help_result = self.command([str(harness_cli), '--help'], unrelated)
            for action in ('preflight', 'install', 'status'):
                self.assertIn(action, help_result.stdout)
            if os.name == 'posix':
                host_cli = binaries / ('glom-continuity-host' + suffix)
                host_help = self.command([str(host_cli), '--help'], unrelated)
                for action in ('create', 'run', 'status', 'stop', 'detach'):
                    self.assertIn(action, host_help.stdout)
            # The current installer explicitly supports private POSIX directories only.
            if os.name == 'posix':
                self.check_installed_cli(binaries, harness_cli, base, unrelated, expected_assets)

            with zipfile.ZipFile(artifacts[0]) as archive:
                prefix = 'glom_continuity/harness/'
                packaged = {name[len(prefix):] for name in archive.namelist()
                            if name.startswith(prefix) and not name.endswith('/')}
                self.assertEqual(packaged, {'__init__.py', *RUNTIME_FILES})
                for name in archive.namelist():
                    self.assertTrue(set(Path(name).parts).isdisjoint({'qa', 'profiles', 'docs', 'tests'}), name)

    def check_installed_cli(self, binaries, harness_cli, base, unrelated, expected_assets):
        def response(args):
            result = self.command(args, unrelated)
            envelope = json.loads(result.stdout)
            self.assertIs(envelope['ok'], True)
            self.assertEqual(envelope['code'], 'OK')
            return envelope['data']

        project = base / '中文 project'
        project.mkdir(mode=0o700)
        initialized = response([str(binaries / 'glom-continuity'), '--project', str(project),
                                'init', '--name', '安装项目'])
        project_id = initialized['project_id']
        (project / '保留 note.txt').write_text('Synthetic project evidence; preserve these bytes.\n',
                                             encoding='utf-8')

        def project_snapshot():
            return {str(path.relative_to(project)): path.read_bytes() if path.is_file() else None
                    for path in project.rglob('*')}

        before = project_snapshot()
        sdk = base / '合成 sdk' / 'node_modules'
        for name, version in SDK_PEERS.items():
            directory = sdk / '@deepseek-ai' / name
            directory.mkdir(parents=True, mode=0o700)
            (directory / 'package.json').write_text(
                json.dumps({'name': '@deepseek-ai/' + name, 'version': version}), encoding='utf-8')
        sdk_before = {str(path.relative_to(sdk)): path.read_bytes()
                      for path in sdk.rglob('package.json')}
        target = base / '接入 bundle'
        binding = ['--directory', str(target), '--project', str(project), '--project-id', project_id,
                   '--sdk-node-modules', str(sdk)]
        preflight = response([str(harness_cli), 'preflight', *binding])
        self.assertEqual(preflight['state'], 'ready_to_stage')
        self.assertFalse(target.exists())
        self.assertEqual(project_snapshot(), before)

        installed = response([str(harness_cli), 'install', *binding])
        status = response([str(harness_cli), 'status', '--directory', str(target)])
        for data in (preflight, installed, status):
            self.assertEqual(data['project'], str(project))
            self.assertEqual(data['project_id'], project_id)
            self.assertEqual(data['sdk_version'], '0.1.5-rc.1')
            self.assertEqual(data['host_state'], 'not_inspected')
            self.assertIs(data['model_called'], False)
            self.assertIs(data['profile_changed'], False)
        for data in (installed, status):
            self.assertEqual(data['state'], 'staged_not_activated')
        for name, expected in expected_assets.items():
            path = target / name
            self.assertEqual(path.read_bytes(), expected, name)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600, name)
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)
        self.assertTrue((target / 'node_modules').is_symlink())
        self.assertEqual((target / 'node_modules').resolve(), sdk)
        overlay = json.loads((target / 'overlay.json').read_text(encoding='utf-8'))
        self.assertEqual([row['id'] for row in overlay], ['recaloom-native', 'recaloom-notice'])
        self.assertEqual(overlay[0]['name'], str(target / 'adapters/harness/native-plugin.mjs'))
        self.assertEqual(overlay[1]['name'], str(target / 'adapters/harness/client-notice/index.mjs'))
        self.assertEqual(overlay[0]['config']['project'], str(project))
        self.assertEqual(overlay[0]['config']['projectId'], project_id)
        self.assertEqual(overlay[0]['config']['recovery'], str(target / 'scripts/recovery.py'))
        self.assertTrue((target / 'installation.json').is_file())
        # Do not recurse through the SDK symlink when enumerating the staged payload.
        files = {str((Path(directory) / name).relative_to(target))
                 for directory, _, names in os.walk(target, followlinks=False) for name in names}
        self.assertEqual(files, set(expected_assets) | {'overlay.json', 'installation.json'})
        self.assertEqual(project_snapshot(), before)
        self.assertEqual({str(path.relative_to(sdk)): path.read_bytes()
                          for path in sdk.rglob('package.json')}, sdk_before)


if __name__ == '__main__':
    unittest.main()
