"""The public environment entry must yield a runnable, isolated installation target."""
import json
from contextlib import ExitStack
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import venv

if os.name == 'posix':
    import fcntl

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/runtime_env.py'


class RuntimeEnvironment(unittest.TestCase):
    def command(self, *args):
        env = {key: os.environ[key] for key in ('PATH', 'SystemRoot', 'WINDIR') if key in os.environ}
        env['PIP_CONFIG_FILE'] = os.devnull
        return subprocess.run([sys.executable, '-I', '-B', str(CLI), *args],
                              env=env, capture_output=True, text=True, timeout=90)

    def test_create_yields_a_runnable_environment_without_changing_the_base(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch).resolve() / '中文 environment'
            result = self.command('create', '--directory', str(target))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual(response['code'], 'RUNTIME_READY')
            self.assertFalse(response['data']['host_integrated'])
            self.assertFalse(response['data']['tool_installed'])
            python = response['data']['python_executable']
            verified = subprocess.run([python, '-I', '-B', '-c',
                'import json, sys, sqlite3; print(json.dumps({"prefix":sys.prefix,"base":sys.base_prefix}))'],
                cwd=Path(scratch), capture_output=True, text=True, timeout=10)
            self.assertEqual(verified.returncode, 0, verified.stderr)
            runtime = json.loads(verified.stdout)
            self.assertEqual(Path(runtime['prefix']).resolve(), target)
            self.assertNotEqual(runtime['prefix'], runtime['base'])
            pip = subprocess.run([python, '-I', '-B', '-m', 'pip', '--version'],
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(pip.returncode, 0, pip.stderr)

    def test_check_reports_the_selected_environment_without_writing_it(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch).resolve() / 'runtime'
            created = self.command('create', '--directory', str(target))
            self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
            def snapshot():
                return {str(p.relative_to(target)): (p.lstat().st_mode, p.lstat().st_mtime_ns,
                            p.readlink().as_posix() if p.is_symlink() else p.read_bytes())
                        for p in target.rglob('*') if p.is_file() or p.is_symlink()}
            before = snapshot()
            checked = self.command('check', '--directory', str(target))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            report = json.loads(checked.stdout)
            self.assertEqual(report['code'], 'RUNTIME_READY')
            self.assertFalse(report['data']['tool_installation_checked'])
            self.assertFalse(report['data']['host_configuration_checked'])
            self.assertEqual(snapshot(), before)

    def test_create_refuses_existing_paths_without_replacing_them(self):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch).resolve()
            folder = base / 'old environment'
            folder.mkdir()
            sentinel = folder / 'keep.txt'
            sentinel.write_bytes(b'existing installation and project')
            existing = base / 'file'
            existing.write_bytes(b'do not replace')
            paths = [folder, existing]
            if os.name != 'nt':
                link = base / 'dangling'
                link.symlink_to(base / 'absent')
                paths.append(link)
            for path in paths:
                with self.subTest(kind=path.name):
                    identity = path.lstat()
                    refused = self.command('create', '--directory', str(path))
                    self.assertEqual(refused.returncode, 1, refused.stderr)
                    data = json.loads(refused.stdout)
                    self.assertEqual(data['code'], 'TARGET_EXISTS')
                    self.assertFalse(data['data']['created'])
                    self.assertEqual(path.lstat(), identity)
            self.assertEqual(sentinel.read_bytes(), b'existing installation and project')
            self.assertEqual(existing.read_bytes(), b'do not replace')

    def test_check_missing_pip_reports_incomplete_without_installing_it(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch).resolve() / 'without-pip'
            venv.EnvBuilder(with_pip=False, symlinks=os.name != 'nt').create(target)
            result = self.command('check', '--directory', str(target))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertEqual(data['code'], 'PIP_UNAVAILABLE')
            self.assertEqual(data['data']['phase'], 'pip_probe')
            self.assertFalse(data['data']['created'])
            self.assertFalse(list(target.rglob('pip-*.dist-info')))

    def test_missing_directory_is_not_created_by_check(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch).resolve() / 'absent'
            result = self.command('check', '--directory', str(target))
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertFalse(json.loads(result.stdout)['data']['created'])
            self.assertFalse(target.exists())

    def test_unsupported_path_separator_is_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch).resolve() / ('not' + os.pathsep + 'a-runtime')
            result = self.command('create', '--directory', str(target))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertEqual(json.loads(result.stdout)['code'], 'INVALID_DIRECTORY')
            self.assertFalse(target.exists())

    def test_requested_link_mode_never_falls_back_to_copy_silently(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch).resolve() / 'link-refused'
            if os.name == 'nt':
                result = self.command('create', '--directory', str(target))
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['data']['creation_mode'], 'copies')
                return
            wrapper = '''import os, runpy, sys
original = os.symlink
def deny_python_link(src, dst, *args, **kwargs):
    if os.path.basename(os.path.dirname(dst)) == 'bin' and os.path.basename(dst).startswith('python'):
        raise OSError('synthetic filesystem does not permit interpreter symlinks')
    return original(src, dst, *args, **kwargs)
os.symlink = deny_python_link
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', wrapper, str(CLI),
                                     'create', '--directory', str(target)],
                                    capture_output=True, text=True, timeout=90)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            response = json.loads(result.stdout)
            self.assertEqual(response['code'], 'RUNTIME_MODE_UNAVAILABLE')
            self.assertTrue(response['data']['partial_environment_retained'])
            self.assertFalse((target / 'bin/python').exists())
            self.assertFalse(list(target.rglob('pip-*.dist-info')))

    def test_mismatched_prefix_preserves_observed_runtime_identity(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch).resolve()
            # Inject only the OS process reply. Exercise the unchanged public check entry.
            wrapper = '''import json, runpy, subprocess, sys
reply = json.dumps({
    'prefix': '/other-runtime', 'base_prefix': '/base-python', 'python_version': [3, 13, 12],
    'sqlite_version': '3.50.4', 'pip_available': False})
class ProcessReply:
    returncode = 0
    def __init__(self, *args, **kwargs): pass
    def communicate(self, **kwargs): return reply, ''
subprocess.Popen = ProcessReply
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', wrapper, str(CLI),
                                     'check', '--directory', str(target)],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['code'], 'RUNTIME_IDENTITY_MISMATCH')
            self.assertEqual(report['data']['exit_code'], 0)
            observed = report['data']['runtime']
            self.assertEqual(observed['prefix'], '/other-runtime')
            self.assertFalse(observed['pip_available'])
            self.assertEqual(Path(observed['python_executable']),
                             target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python'))

    def test_broken_pip_is_a_probe_failure_not_a_bootstrap_attempt(self):
        with tempfile.TemporaryDirectory() as scratch:
            target = Path(scratch).resolve() / 'runtime'
            venv.EnvBuilder(with_pip=False, symlinks=os.name != 'nt').create(target)
            python = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
            result = subprocess.run([str(python), '-I', '-B', '-c',
                                     'import sysconfig; print(sysconfig.get_path("purelib"))'],
                                    capture_output=True, text=True, timeout=10, check=True)
            package = Path(result.stdout.strip()) / 'pip'
            self.assertTrue(package.resolve().is_relative_to(target))
            package.mkdir()
            (package / '__init__.py').write_text('')
            (package / '__main__.py').write_text('import sys; print("PRIVATE_PROBE_MARKER"); sys.exit(23)')
            checked = self.command('check', '--directory', str(target))
            self.assertEqual(checked.returncode, 1, checked.stderr)
            report = json.loads(checked.stdout)
            self.assertEqual(report['code'], 'PIP_UNAVAILABLE')
            self.assertEqual(report['data']['phase'], 'pip_probe')
            self.assertEqual(report['data']['exit_code'], 23)
            self.assertFalse(report['data']['created'])
            runtime = report['data']['runtime']
            self.assertEqual(Path(runtime['prefix']), target)
            self.assertNotEqual(runtime['base_prefix'], runtime['prefix'])
            self.assertEqual(runtime['python_version'], list(sys.version_info[:3]))
            self.assertTrue(runtime['pip_available'])
            self.assertTrue(runtime['sqlite_version'])
            self.assertNotIn('PRIVATE_PROBE_MARKER', checked.stdout + checked.stderr)

    def test_interrupt_does_not_signal_a_group_after_the_child_was_reaped(self):
        with tempfile.TemporaryDirectory() as scratch:
            # Model the documented OS subprocess boundary: communicate may
            # reap a child during its KeyboardInterrupt handling. Never issue
            # a real signal to a made-up numeric ID in this fault injection.
            wrapper = '''import os, runpy, subprocess, sys
class ReapedProcess:
    returncode = None
    pid = 999999
    stdout = stderr = None
    def __init__(self, *args, **kwargs): pass
    def communicate(self, **kwargs):
        self.returncode = 0
        raise KeyboardInterrupt()
    def kill(self): raise AssertionError('must not signal a reaped process')
def refuse_signal(*args): raise AssertionError('must not signal a reaped group')
os.killpg = refuse_signal
subprocess.Popen = ReapedProcess
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', wrapper, str(CLI),
                                     'check', '--directory', str(Path(scratch).resolve())],
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['code'], 'RUNTIME_INTERRUPTED')
            cleanup = report['data']['child_cleanup']
            self.assertTrue(cleanup['ownership_released_before_cleanup'])
            self.assertTrue(cleanup['leader_reaped'])
            self.assertFalse(cleanup['signal_sent'])

    @unittest.skipUnless(os.name == 'posix', 'POSIX process-group cleanup; Windows tree cleanup not yet verified')
    def test_timed_out_pip_stops_its_same_group_child_and_retains_environment(self):
        with ExitStack() as cleanup:
            base = Path(tempfile.mkdtemp(prefix='recaloom-runtime-timeout-')).resolve()
            target = base / 'runtime'
            venv.EnvBuilder(with_pip=False, symlinks=True).create(target)
            python = target / 'bin/python'
            site = subprocess.check_output([str(python), '-I', '-B', '-c',
                'import sysconfig; print(sysconfig.get_path("purelib"))'], text=True).strip()
            package = Path(site) / 'pip'
            self.assertTrue(package.resolve().is_relative_to(target))
            package.mkdir()
            (package / '__init__.py').write_text('')
            lock = base / 'child.lock'
            leader_lock = base / 'leader.lock'
            ready = base / 'ready'
            child = ('import fcntl, signal, time\nfrom pathlib import Path\n'
                     'signal.signal(signal.SIGTERM, signal.SIG_IGN)\n'
                     f'with open({str(lock)!r}, "w") as f:\n'
                     '    fcntl.flock(f, fcntl.LOCK_EX)\n'
                     f'    Path({str(ready)!r}).write_text("ready")\n'
                     '    time.sleep(17)\n')
            (package / '__main__.py').write_text('import fcntl, subprocess, sys, time\n'
                f'with open({str(leader_lock)!r}, "w") as leader:\n'
                '    fcntl.flock(leader, fcntl.LOCK_EX)\n'
                f'    subprocess.Popen([sys.executable, "-I", "-B", "-c", {child!r}], '
                'stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n'
                '    time.sleep(30)\n')
            before = (package / '__main__.py').read_bytes()
            result = self.command('check', '--directory', str(target))
            self.assertTrue(ready.exists(), 'Fixture must establish actual child ownership')
            with lock.open('r') as child_handle, leader_lock.open('r') as leader_handle:
                def unlocked():
                    for handle in (child_handle, leader_handle):
                        try:
                            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            fcntl.flock(handle, fcntl.LOCK_UN)
                        except BlockingIOError:
                            return False
                    return True
                stopped_at_return = unlocked()
                # The original bug must not leave our fixture running after a red test.
                deadline = time.monotonic() + 20
                while not unlocked() and time.monotonic() < deadline:
                    time.sleep(.05)
                self.assertTrue(unlocked(), f'Retained fixture; process ownership not released: {base}')
            self.assertTrue(stopped_at_return, f'Retained fixture; process still owned a lock at timeout: {base}')
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['code'], 'RUNTIME_TIMEOUT')
            self.assertEqual(report['data']['phase'], 'pip_probe')
            self.assertEqual(Path(report['data']['runtime']['prefix']), target)
            self.assertEqual(report['data']['child_cleanup']['scope'], 'posix_process_group')
            self.assertTrue(report['data']['child_cleanup']['leader_reaped'])
            self.assertEqual((package / '__main__.py').read_bytes(), before)
            # Failure evidence stays even after the bounded fixtures finish.
            # Register deletion only once both ownership and all assertions pass.
            cleanup.callback(shutil.rmtree, base)


if __name__ == '__main__':
    unittest.main()
