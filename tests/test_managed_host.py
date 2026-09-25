"""Opt-in real CLI host lifecycle; caller must restrict network to loopback."""
import json
from contextlib import contextmanager
import os
import shutil
import signal
import socket
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'scripts/harness_host.py'
INSTALLED_BIN = os.environ.get('CONTINUITY_TEST_BIN')
HOST_COMMAND = ([str(Path(INSTALLED_BIN) / 'glom-continuity-host')] if INSTALLED_BIN else [sys.executable, str(HOST)])
INSTALL_COMMAND = ([str(Path(INSTALLED_BIN) / 'glom-continuity-harness')] if INSTALLED_BIN else [sys.executable, str(ROOT / 'scripts/harness_install.py')])
CORE_COMMAND = ([str(Path(INSTALLED_BIN) / 'glom-continuity')] if INSTALLED_BIN else [sys.executable, str(ROOT / 'scripts/continuity.py')])


@contextmanager
def synthetic_directory():
    directory = Path(tempfile.mkdtemp(prefix='recaloom-host-',
                                     dir=os.environ.get('CONTINUITY_CI_SCRATCH', '/tmp'))).resolve()
    try:
        yield directory
    finally:
        home = directory / 'host'
        if home.exists():
            # Keep the control files if shutdown failed. The parent CI runner
            # must still be able to stop this home after a killed test process.
            status = subprocess.run([*HOST_COMMAND, 'status', '--home', str(home)],
                                    capture_output=True, text=True, timeout=20)
            if status.returncode or json.loads(status.stdout).get('data', {}).get('state') != 'stopped':
                raise RuntimeError('Synthetic host cleanup unverified; owned directory retained')
        shutil.rmtree(directory)


@unittest.skipUnless(os.environ.get('CONTINUITY_DSH_PACKAGE'), 'Explicit installed DSH required')
class ManagedHost(unittest.TestCase):
    def test_public_cli_runs_and_stops_the_real_official_profile(self):
        # A required-CI parent can reconcile this exact owned home even if the
        # test process dies before its finally block. Never touch ordinary homes.
        with synthetic_directory() as directory:
            root = Path(directory).resolve()
            project = root / 'project'
            project.mkdir(mode=0o700)
            def core(*args):
                return json.loads(subprocess.check_output([*CORE_COMMAND, '--project', str(project), *args], text=True))
            project_id = core('init', '--name', 'Synthetic public managed lifecycle')['data']['project_id']
            baseline = core('status')
            sdk = Path(os.environ['CONTINUITY_DSH_PACKAGE']).resolve().parents[2]
            bundle = root / 'bundle'
            subprocess.run([*INSTALL_COMMAND, 'install',
                '--directory', str(bundle), '--project', str(project), '--project-id', project_id,
                '--sdk-node-modules', str(sdk)], capture_output=True, check=True)
            home = root / 'host'
            def command(action, *args, ok=True):
                result = subprocess.run([*HOST_COMMAND, action, '--home', str(home), *args],
                    capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
                return json.loads(result.stdout)
            created = command('create', '--bundle', str(bundle), '--node', os.environ.get('CONTINUITY_TEST_NODE') or shutil.which('node'))
            self.assertEqual(created['data']['state'], 'prepared')
            self.assertEqual(command('status')['data']['state'], 'stopped')
            process = subprocess.Popen([*HOST_COMMAND, 'run', '--home', str(home)],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    self.assertIsNone(process.poll(), 'Official host exited before readiness')
                    state = command('status')['data']
                    if state['state'] == 'running':
                        break
                    time.sleep(.1)
                else:
                    self.fail('Managed host never reported ready')
                self.assertFalse(state['memory_enabled'])
                self.assertTrue(state['recovery_attached'])
                self.assertTrue(state['client_notice_attached'])
                self.assertEqual(state.get('workspace_picker'), 'browse',
                                 'Managed Web users need an in-page picker, not an invisible native dialog')
                self.assertGreater(state['port'], 0)
                self.assertNotEqual(os.getsid(state['pid']), os.getsid(process.pid),
                                    'Terminal signals must not bypass the owning launcher')
                with socket.socket(socket.AF_UNIX) as connection:
                    connection.settimeout(2)
                    connection.connect(str(home / 'control.sock'))
                    connection.sendall((json.dumps({'action': 'stop', 'home_id': state['home_id'], 'run_id': 'wrong-run'}) + '\n').encode())
                    refused = json.loads(connection.recv(4096))
                self.assertFalse(refused['ok'])
                self.assertEqual(command('status')['data']['state'], 'running')
                self.assertEqual(command('run', ok=False)['code'], 'HOST_BUSY')
                stopped = command('stop')['data']
                self.assertEqual(stopped['state'], 'stopped')
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, stdout + stderr)
                self.assertEqual(command('status')['data']['state'], 'stopped')
                self.assertEqual(core('status'), baseline)
                self.assertTrue((home / 'dsh-home/profiles/recaloom/package.json').exists())
                # Simulate a terminal Ctrl-C to the foreground wrapper's group.
                process = subprocess.Popen([*HOST_COMMAND, 'run', '--home', str(home)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    self.assertIsNone(process.poll())
                    if command('status')['data']['state'] == 'running':
                        break
                    time.sleep(.1)
                else:
                    self.fail('Interrupted run did not become ready')
                os.killpg(process.pid, signal.SIGINT)
                stdout, stderr = process.communicate(timeout=20)
                self.assertEqual(process.returncode, 0, stdout + stderr)
                self.assertEqual(json.loads(stdout)['data']['state'], 'exited')
                self.assertEqual(command('status')['data']['state'], 'stopped')
                self.assertEqual(command('detach')['data']['state'], 'detached')
                # The official child must retain ownership even if only its
                # launcher dies. Never infer a stopped host from a dead parent.
                process = subprocess.Popen([*HOST_COMMAND, 'run', '--home', str(home)],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    self.assertIsNone(process.poll())
                    state = command('status')['data']
                    if state['state'] == 'running':
                        break
                    time.sleep(.1)
                else:
                    self.fail('Restart did not reach readiness')
                self.assertFalse(state['recovery_attached'])
                self.assertFalse(state['client_notice_attached'])
                process.kill()  # Exact synthetic launcher we just created, never a PID from disk.
                process.communicate(timeout=5)
                self.assertEqual(command('status')['data']['state'], 'running')
                self.assertEqual(command('run', ok=False)['code'], 'HOST_BUSY')
                detached_stop = command('stop')['data']
                self.assertEqual(detached_stop['state'], 'stopped')
                self.assertFalse(detached_stop['persisted_pause'], 'An absent attachment did not persist a pause')
                self.assertEqual(core('status'), baseline)
            finally:
                if command('status')['data']['state'] != 'stopped':
                    command('stop')
                if process.poll() is None:
                    process.communicate(timeout=10)
