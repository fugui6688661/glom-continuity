"""First installation through the public CLI, not private installer functions."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/runtime_env.py'


class RuntimeInstall(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix='recaloom-wheel-fixture-')
        cls.addClassCleanup(cls.fixture.cleanup)
        base = Path(cls.fixture.name).resolve()
        source = base / 'source'
        source.mkdir()
        for name in json.loads((ROOT / 'release-files.json').read_text()):
            dest = source / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, dest)
        build = subprocess.run([sys.executable, '-I', '-B', '-m', 'pip', 'wheel', '--no-index', '--no-deps',
                                '--no-build-isolation', '--no-cache-dir', '--disable-pip-version-check', '--wheel-dir', str(base / 'wheels'),
                                str(source)], capture_output=True, text=True, timeout=90)
        if build.returncode:
            raise AssertionError(build.stdout + build.stderr)
        cls.wheel, = (base / 'wheels').glob('*.whl')
        cls.wheel_sha256 = hashlib.sha256(cls.wheel.read_bytes()).hexdigest()

    def command(self, *args, stdout_encoding=None):
        entry = [str(CLI)]
        if stdout_encoding is not None:
            # Change only the output boundary; -I ignores encoding env vars.
            wrapper = '''import runpy, sys
sys.stdout.reconfigure(encoding=sys.argv.pop(1), errors='strict')
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
            entry = ['-c', wrapper, stdout_encoding, str(CLI)]
        return subprocess.run([sys.executable, '-I', '-B', *entry, *args],
                              capture_output=True, text=True, timeout=90)

    def test_wrong_wheel_digest_is_rejected_before_creating_environment(self):
        with tempfile.TemporaryDirectory(prefix='recaloom-install-') as scratch:
            base = Path(scratch).resolve()
            wheel = base / 'glom_continuity-0.1.0a7-py3-none-any.whl'
            wheel.write_bytes(b'synthetic file, not an executable package')
            target = base / 'new environment'
            before = wheel.read_bytes()
            result = self.command('create', '--directory', str(target),
                                  '--wheel', str(wheel), '--sha256', '0' * 64)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual(response['code'], 'WHEEL_HASH_MISMATCH')
            self.assertFalse(response['data']['created'])
            self.assertFalse(target.exists())
            self.assertEqual(wheel.read_bytes(), before)

    def test_one_command_installs_the_selected_wheel_and_returns_a_working_prefix(self):
        with tempfile.TemporaryDirectory(prefix='recaloom-install-') as scratch:
            base = Path(scratch).resolve()
            target = base / '中文 café 🚀 environment'
            project = base / 'untouched project'
            project.mkdir()
            (project / 'AGENTS.md').write_bytes(b'Existing personal project instructions.\n')
            (project / 'glom_continuity.py').write_text('raise SystemExit(42)\n')
            before = {p.name: p.read_bytes() for p in project.iterdir()}
            result = self.command('create', '--directory', str(target),
                                  '--wheel', str(self.wheel), '--sha256', self.wheel_sha256,
                                  stdout_encoding='cp1252')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(result.stderr, '')
            self.assertTrue(result.stdout.isascii())
            response = json.loads(result.stdout)
            self.assertEqual(response['code'], 'TOOL_READY')
            data = response['data']
            self.assertEqual(data['directory'], str(target))
            self.assertEqual(Path(data['prefix']).resolve(), target)
            self.assertEqual(data['python_executable'],
                             str(target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')))
            self.assertTrue(data['tool_installed'])
            self.assertFalse(data['host_integrated'])
            self.assertEqual(data['wheel_sha256'], self.wheel_sha256)
            self.assertEqual(data['tool']['usage']['state'], 'available')
            checked = subprocess.run([*data['cli_argv'], '--project', str(project), 'doctor'],
                                     cwd=project, capture_output=True, text=True, timeout=10)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(data['cli_argv'], [data['python_executable'], '-I', '-B', '-m', 'glom_continuity'])
            observed = json.loads(checked.stdout)['data']
            self.assertEqual(observed['storage']['state'], 'not_initialized')
            self.assertEqual(observed['usage']['state'], 'available')
            self.assertEqual({p.name: p.read_bytes() for p in project.iterdir()}, before)
            self.assertFalse((target / '.continuity').exists())
            installer = target / ('Scripts/glom-continuity-env.exe' if os.name == 'nt' else 'bin/glom-continuity-env')
            help_result = subprocess.run([str(installer), 'create', '--help'],
                                         cwd=project, capture_output=True, text=True, timeout=10)
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            self.assertIn('--wheel', help_result.stdout)
            self.assertIn('--sha256', help_result.stdout)
            # This installed console entry has no -I flag: constrain its actual
            # inherited stream without changing machine/user configuration.
            env = {key: os.environ[key] for key in ('PATH', 'SystemRoot', 'WINDIR') if key in os.environ}
            env.update(PYTHONIOENCODING='ascii:strict', PYTHONDONTWRITEBYTECODE='1', PIP_CONFIG_FILE=os.devnull)
            installed_check = subprocess.run([str(installer), 'check', '--directory', str(target)],
                                             cwd=project, env=env, capture_output=True, text=True, timeout=20)
            self.assertEqual(installed_check.returncode, 0, installed_check.stdout + installed_check.stderr)
            self.assertEqual(installed_check.stderr, '')
            self.assertTrue(installed_check.stdout.isascii())
            installed_report = json.loads(installed_check.stdout)
            self.assertEqual(installed_report['code'], 'RUNTIME_READY')
            self.assertEqual(installed_report['data']['directory'], str(target))
            self.assertEqual(Path(installed_report['data']['prefix']).resolve(), target)
            self.assertEqual({p.name: p.read_bytes() for p in project.iterdir()}, before)
            self.assertFalse((target / '.continuity').exists())

    def test_incomplete_pair_and_invalid_digest_have_no_side_effects(self):
        with tempfile.TemporaryDirectory(prefix='recaloom-install-') as scratch:
            target = Path(scratch).resolve() / 'absent'
            for options in (['--wheel', str(self.wheel)], ['--sha256', self.wheel_sha256],
                            ['--wheel', str(self.wheel), '--sha256', 'not-a-digest']):
                with self.subTest(options=options):
                    result = self.command('create', '--directory', str(target), *options)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertEqual(json.loads(result.stdout)['code'], 'INVALID_WHEEL_ARGUMENTS')
                    self.assertFalse(target.exists())

    def test_invalid_local_wheel_paths_are_rejected_without_creating_environment(self):
        with tempfile.TemporaryDirectory(prefix='recaloom-install-') as scratch:
            base = Path(scratch).resolve()
            folder = base / self.wheel.name
            folder.mkdir()
            choices = [folder, Path(self.wheel.name), 'https://invalid.example/' + self.wheel.name]
            if os.name == 'posix':
                links = base / 'links'
                links.mkdir()
                link = links / self.wheel.name
                link.symlink_to(self.wheel)
                choices.append(link)
            for choice in choices:
                with self.subTest(choice=str(choice)):
                    target = base / 'absent'
                    result = self.command('create', '--directory', str(target), '--wheel', str(choice),
                                          '--sha256', self.wheel_sha256)
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    response = json.loads(result.stdout)
                    self.assertEqual(response['code'], 'INVALID_WHEEL')
                    self.assertFalse(response['data']['created'])
                    self.assertFalse(target.exists())

    def test_existing_destination_is_not_used_as_an_upgrade_target(self):
        with tempfile.TemporaryDirectory(prefix='recaloom-install-') as scratch:
            target = Path(scratch).resolve() / 'existing'
            target.mkdir()
            sentinel = target / 'keep.txt'
            sentinel.write_bytes(b'Existing installation and memory must stay intact.\n')
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            result = self.command('create', '--directory', str(target), '--wheel', str(self.wheel),
                                  '--sha256', self.wheel_sha256)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual(response['code'], 'TARGET_EXISTS')
            self.assertFalse(response['data']['created'])
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)

    def test_matching_digest_does_not_make_a_broken_wheel_installable(self):
        with tempfile.TemporaryDirectory(prefix='recaloom-install-') as scratch:
            base = Path(scratch).resolve()
            wheel = base / self.wheel.name
            wheel.write_bytes(b'not a wheel even though the supplied digest matches')
            target = base / 'partial'
            result = self.command('create', '--directory', str(target), '--wheel', str(wheel),
                                  '--sha256', hashlib.sha256(wheel.read_bytes()).hexdigest())
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual(response['code'], 'WHEEL_INSTALL_FAILED')
            self.assertEqual(response['data']['phase'], 'wheel_install')
            self.assertTrue(response['data']['created'])
            self.assertTrue(response['data']['partial_environment_retained'])
            self.assertTrue(target.is_dir())
            self.assertEqual(result.stderr, '')

    def test_installed_wheel_without_matching_guide_is_not_reported_ready(self):
        with tempfile.TemporaryDirectory(prefix='recaloom-install-') as scratch:
            base = Path(scratch).resolve()
            wheel = base / self.wheel.name
            with zipfile.ZipFile(self.wheel) as source, zipfile.ZipFile(wheel, 'x') as out:
                for info in source.infolist():
                    if info.filename != 'glom_continuity/_guide/GUIDE-MANIFEST.json':
                        out.writestr(info, source.read(info))
            target = base / 'partial'
            result = self.command('create', '--directory', str(target), '--wheel', str(wheel),
                                  '--sha256', hashlib.sha256(wheel.read_bytes()).hexdigest())
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual(response['code'], 'TOOL_CHECK_FAILED')
            self.assertEqual(response['data']['phase'], 'tool_probe')
            self.assertTrue(response['data']['partial_environment_retained'])
            self.assertTrue(target.is_dir())
            self.assertFalse((target / '.continuity').exists())


if __name__ == '__main__':
    unittest.main()
