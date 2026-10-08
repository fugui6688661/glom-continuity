"""Public launcher CLI against a synthetic external process, not DSH evidence."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

if os.name == 'posix':
    import fcntl


ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / 'scripts/harness_host.py'
INSTALL = ROOT / 'scripts/harness_install.py'
PEERS = {
    'dsh': '0.1.5-rc.1', 'cordis': '4.0.2', 'schemastery': '3.18.2',
    'dsh-llm': '0.1.5-rc.1', 'dsh-client-ui-commands': '0.1.5-rc.1',
    'dsh-api-session-controller': '0.1.5-rc.1', 'dsh-client-ui-conversation': '0.1.5-rc.1',
}
SECRET = 'synthetic-secret-do-not-save'
CONTROLLED_HOST = r'''
import json, os, select, socket
settings = json.loads((root / 'controlled').read_text())
home = Path.cwd()
rows = json.loads(Path(sys.argv[sys.argv.index('--patch') + 1]).read_text())
controller = next(item for row in rows for item in row.get('insert', [])
                  if item['id'] == 'recaloom-managed-host')['config']
with socket.socket(socket.AF_UNIX) as server:
    server.bind(controller['socket'])
    os.chmod(controller['socket'], 0o600)
    server.listen()
    deadline = time.monotonic() + settings.get('lifetime', 10)
    while time.monotonic() < deadline and not (root / 'release').exists():
        if not select.select([server], [], [], .05)[0]:
            continue
        with server.accept()[0] as connection:
            request = json.loads(connection.makefile('rb').readline())
            reply = {'ok': True,
                     'state': 'stopping' if request['action'] == 'stop' else settings.get('status_state', 'running'),
                     'home_id': controller['homeId'],
                     'run_id': 'other-run' if settings.get('wrong_identity') else os.environ['RECALOOM_MANAGED_RUN_ID'],
                     'persisted_pause': settings.get('persisted_pause', True), 'recovery_attached': True}
            if request['action'] == 'stop' and settings.get('refuse_stop'):
                reply.update(ok=False, code='PAUSE_NOT_SAVED')
            reply.update(settings.get('reply_updates', {}))
            if settings.get('omit_state'):
                reply.pop('state')
            output = (bytes.fromhex(settings['raw_response']) if 'raw_response' in settings
                      else (json.dumps(reply) + '\n').encode())
            connection.sendall(output)
        if (request['action'] == 'stop' and not settings.get('wrong_identity')
                and settings.get('persisted_pause', True) is True
                and not settings.get('hold_stop') and not settings.get('refuse_stop')
                and 'raw_response' not in settings and 'reply_updates' not in settings
                and not settings.get('omit_state')):
            break
Path(controller['socket']).unlink()
raise SystemExit(0)
'''


@unittest.skipUnless(os.name == 'posix', 'Managed homes currently support POSIX only')
class HostDiagnostics(unittest.TestCase):
    def setUp(self):
        # No TemporaryDirectory finalizer: a surviving child can outlive both
        # its launcher and the TestCase. Only ownership release permits deletion.
        self.root = Path(tempfile.mkdtemp(prefix='rec-diag-', dir='/tmp')).resolve()
        self.home = self.root / 'host'
        self.addCleanup(self.cleanup_home)
        self.project = self.root / 'project'
        self.project.mkdir(mode=0o700)
        init = self.call(ROOT / 'scripts/continuity.py', '--project', str(self.project),
                         'init', '--name', 'Synthetic diagnostic test')
        self.project_id = init['data']['project_id']
        self.sdk = self.root / 'sdk/node_modules'
        for name, version in PEERS.items():
            path = self.sdk / '@deepseek-ai' / name
            path.mkdir(parents=True, mode=0o700)
            (path / 'package.json').write_text(json.dumps({'name': '@deepseek-ai/' + name, 'version': version}))
        self.bundle = self.root / 'bundle'
        self.call(INSTALL, 'install', '--directory', str(self.bundle), '--project', str(self.project),
                  '--project-id', self.project_id, '--sdk-node-modules', str(self.sdk))
        # A process-boundary double: never loads model keys, contacts a host or uses real DSH.
        self.node = self.root / 'synthetic-node'
        self.node.write_text('#!' + sys.executable + '\nimport sys\n'
                             'if sys.argv[1:] == ["--version"]:\n'
                             '    print("v24.15.0"); raise SystemExit(0)\n'
                             'from pathlib import Path\nimport time\n'
                             'root = Path(' + repr(str(self.root)) + ')\n'
                             'if (root / "quiet").exists():\n'
                             '    deadline = time.monotonic() + 8\n'
                             '    while not (root / "release").exists() and time.monotonic() < deadline:\n'
                             '        time.sleep(.05)\n'
                             '    raise SystemExit(0)\n'
                             'if (root / "controlled").exists():\n' +
                             textwrap.indent(CONTROLLED_HOST, '    ') + '\n' +
                             'print("https://localhost:1234/?token=' + SECRET + '")\n'
                             'print("private failure ' + SECRET + '", file=sys.stderr)\n'
                             'raise SystemExit(23)\n')
        self.node.chmod(0o700)
        self.home = self.root / 'host'
        self.created = self.call(HOST, 'create', '--home', str(self.home), '--bundle', str(self.bundle),
                                 '--node', str(self.node))

    def cleanup_home(self):
        if not self.root.exists():
            return
        owner = None
        try:
            owner = os.open(self.home / 'owner.lock', os.O_RDONLY | os.O_NOFOLLOW)
            info = os.fstat(owner)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
                raise OSError('Unsafe fixture ownership file')
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Keep the acquired lock until deletion finishes; reaping a launcher
            # or observing a free lock and then releasing it is not sufficient.
            shutil.rmtree(self.root)
        except OSError:
            print('Retained synthetic home; ownership release unconfirmed: ' + str(self.home), file=sys.stderr)
        finally:
            if owner is not None:
                os.close(owner)

    def call(self, script, *args, ok=True):
        result = subprocess.run([sys.executable, '-B', str(script), *args], cwd=self.root,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        return json.loads(result.stdout)

    @contextmanager
    def live_host(self, settings):
        (self.root / 'release').unlink(missing_ok=True)
        (self.root / 'controlled').write_text(json.dumps(settings))
        process = subprocess.Popen([sys.executable, '-B', str(HOST), 'run', '--home', str(self.home)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 3
            while not (self.home / 'control.sock').exists() and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertTrue((self.home / 'control.sock').exists(), 'Synthetic control socket did not start')
            yield process
        finally:
            (self.root / 'release').touch()
            process.communicate(timeout=12)
            owner = os.open(self.home / 'owner.lock', os.O_RDONLY | os.O_NOFOLLOW)
            try:
                deadline = time.monotonic() + 12
                while True:
                    try:
                        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            self.fail('Synthetic child remains owned; fixture home must be retained')
                        time.sleep(.05)
            finally:
                os.close(owner)

    def test_unconfirmed_pause_receipt_keeps_diagnostic_and_live_ownership(self):
        with self.live_host({'persisted_pause': False}) as process:
            state = self.call(HOST, 'status', '--home', str(self.home))['data']
            failed = self.call(HOST, 'stop', '--home', str(self.home), ok=False)
            self.assertEqual(failed['code'], 'PAUSE_NOT_SAVED')
            self.assertIsInstance(failed['data'], dict, 'Safe-stop refusal must retain its diagnostic')
            self.assertEqual(failed['data']['diagnostic']['run_id'], state['run_id'])
            self.assertEqual(failed['data']['diagnostic']['stage'], 'process_spawned')
            self.assertIsNone(process.poll())
            self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')

    def test_interrupt_refusals_include_diagnostic_without_releasing_child_ownership(self):
        for settings, code in (({'refuse_stop': True}, 'HOST_CONTROL_REFUSED'),
                               ({'persisted_pause': False}, 'PAUSE_NOT_SAVED'),
                               ({'wrong_identity': True}, 'HOST_IDENTITY_MISMATCH')):
            with self.subTest(code=code), self.live_host(settings) as process:
                process.send_signal(signal.SIGINT)
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 2, stdout + stderr)
                self.assertNotIn(SECRET, stdout + stderr)
                failed = json.loads(stdout)
                self.assertEqual(failed['code'], code)
                self.assertIsInstance(failed['data'], dict, 'Interrupted safe stop must retain its diagnostic')
                self.assertEqual(failed['data']['diagnostic']['stage'], 'process_spawned')
                self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')
                state = self.call(HOST, 'status', '--home', str(self.home))['data']
                self.assertNotEqual(state['state'], 'stopped')

    def test_malformed_control_replies_are_bounded_diagnosed_and_never_echoed(self):
        replies = {'array': b'[]\n', 'null': b'null\n', 'number': b'42\n',
                   'string': json.dumps(SECRET).encode() + b'\n',
                   'invalid_utf8': b'\xff' + SECRET.encode() + b'\n',
                   'invalid_json': b'{"private":' + SECRET.encode() + b'}\n',
                   'duplicate_field': b'{"ok":true,"ok":false}\n',
                   'nonfinite': b'{"ok":NaN}\n'}
        for label, raw in replies.items():
            with self.subTest(reply=label), self.live_host({'raw_response': raw.hex()}) as process:
                for action in ('status', 'stop'):
                    with self.subTest(action=action):
                        result = self.call(HOST, action, '--home', str(self.home), ok=action == 'status')
                        if action == 'status':
                            state = result['data']
                            self.assertEqual(state['state'], 'starting_or_unresponsive')
                            self.assertEqual(state['process_state'], 'unknown')
                            self.assertFalse(state['control_verified'])
                            self.assertEqual(state['control_reason'], 'CONTROL_RESPONSE_INVALID')
                            self.assertIn('next_action', state)
                        else:
                            self.assertEqual(result['code'], 'CONTROL_RESPONSE_INVALID')
                        self.assertEqual(result['data']['diagnostic']['stage'], 'process_spawned')
                        self.assertEqual(result['data']['diagnostic']['output_capture'], 'not_collected')
                self.assertIsNone(process.poll())
                self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')

    def test_invalid_control_object_cannot_claim_state_or_authorize_stop(self):
        settings_cases = [{'omit_state': True}, *({'reply_updates': change} for change in (
            {'state': []}, {'state': SECRET}, {'state': 'control_ready'}, {'ok': 1},
            {'persisted_pause': 'true'}, {'recovery_attached': []}))]
        for settings in settings_cases:
            with self.subTest(fields=settings), self.live_host(settings) as process:
                for action in ('status', 'stop'):
                    with self.subTest(action=action):
                        result = self.call(HOST, action, '--home', str(self.home), ok=action == 'status')
                        if action == 'status':
                            self.assertEqual(result['data']['state'], 'starting_or_unresponsive')
                            self.assertFalse(result['data']['control_verified'])
                            self.assertEqual(result['data']['control_reason'], 'CONTROL_RESPONSE_INVALID')
                        else:
                            self.assertEqual(result['code'], 'CONTROL_RESPONSE_INVALID')
                        self.assertEqual(result['data']['diagnostic']['stage'], 'process_spawned')
                self.assertIsNone(process.poll())
                self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')

    def test_reachable_starting_control_explains_wait_without_claiming_running(self):
        with self.live_host({'status_state': 'starting', 'refuse_stop': True}) as process:
            baseline = {path.name: path.read_bytes() for path in self.home.iterdir() if path.is_file()}
            state = self.call(HOST, 'status', '--home', str(self.home))['data']
            self.assertEqual(state['state'], 'starting')
            self.assertIn('diagnostic', state, 'Reachable control does not complete startup diagnostics')
            self.assertTrue(state['control_verified'])
            self.assertEqual(state['diagnostic']['run_id'], state['run_id'])
            self.assertEqual(state['diagnostic']['stage'], 'process_spawned')
            self.assertEqual(state['diagnostic']['output_capture'], 'not_collected')
            self.assertIn('not collected', state['next_action'])
            self.assertEqual({path.name: path.read_bytes() for path in self.home.iterdir() if path.is_file()}, baseline)
            self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')
            self.assertEqual(self.call(HOST, 'stop', '--home', str(self.home), ok=False)['code'], 'HOST_CONTROL_REFUSED')
            self.assertIsNone(process.poll())

    def test_stop_timeout_includes_diagnostic_and_retains_live_ownership(self):
        with self.live_host({'hold_stop': True, 'lifetime': 45}) as process:
            failed = self.call(HOST, 'stop', '--home', str(self.home), ok=False)
            self.assertEqual(failed['code'], 'STOP_PENDING')
            self.assertEqual(failed['data']['diagnostic']['stage'], 'process_spawned')
            self.assertIsNone(process.poll())
            self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')

    def test_interrupt_timeouts_keep_diagnostic_before_and_after_stop_acknowledgement(self):
        for settings in ({'status_state': 'starting', 'lifetime': 45},
                         {'hold_stop': True, 'lifetime': 45}):
            with self.subTest(settings=settings), self.live_host(settings) as process:
                process.send_signal(signal.SIGINT)
                stdout, stderr = process.communicate(timeout=35)
                self.assertEqual(process.returncode, 2, stdout + stderr)
                failed = json.loads(stdout)
                self.assertEqual(failed['code'], 'STOP_PENDING')
                self.assertEqual(failed['data']['diagnostic']['stage'], 'process_spawned')
                self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')

    def test_interrupt_malformed_control_is_bounded_and_keeps_diagnostic(self):
        with self.live_host({'raw_response': (b'\xff' + SECRET.encode() + b'\n').hex()}) as process:
            process.send_signal(signal.SIGINT)
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 2, stdout + stderr)
            self.assertNotIn(SECRET, stdout + stderr)
            failed = json.loads(stdout)
            self.assertEqual(failed['code'], 'CONTROL_RESPONSE_INVALID')
            self.assertEqual(failed['data']['diagnostic']['stage'], 'process_spawned')
            self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')

    def test_unavailable_diagnostic_cannot_bypass_pause_refusal(self):
        with self.live_host({'persisted_pause': False}) as process:
            (self.home / 'diagnostic.json').write_text('{"raw_output":' + json.dumps(SECRET) + '}')
            failed = self.call(HOST, 'stop', '--home', str(self.home), ok=False)
            self.assertEqual(failed['code'], 'PAUSE_NOT_SAVED')
            self.assertEqual(failed['data']['diagnostic'], {'availability': 'unavailable'})
            self.assertIsNone(process.poll())
            self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')

    def test_corrupt_run_identity_keeps_control_and_interrupt_failures_diagnosed(self):
        for raw in (b'[]', b'{}', b'\xff', b'{', b'{"run_id":null,"home_id":null}'):
            with self.subTest(record=raw.hex()), self.live_host({}) as process:
                (self.home / 'run.json').write_bytes(raw)
                for action in ('status', 'stop'):
                    with self.subTest(action=action):
                        result = self.call(HOST, action, '--home', str(self.home), ok=action == 'status')
                        if action == 'status':
                            self.assertEqual(result['data']['state'], 'starting_or_unresponsive')
                            self.assertEqual(result['data']['control_reason'], 'CONTROL_INVALID')
                            self.assertFalse(result['data']['control_verified'])
                        else:
                            self.assertEqual(result['code'], 'CONTROL_INVALID')
                        self.assertEqual(result['data']['diagnostic'], {'availability': 'unavailable'})
                process.send_signal(signal.SIGINT)
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 2, stdout + stderr)
                failed = json.loads(stdout)
                self.assertEqual(failed['code'], 'CONTROL_INVALID')
                self.assertEqual(failed['data']['diagnostic'], {'availability': 'unavailable'})
                self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')

    def test_failed_child_exit_is_explained_after_restart_without_recording_output(self):
        baseline = self.call(ROOT / 'scripts/continuity.py', '--project', str(self.project), 'status')
        failed = self.call(HOST, 'run', '--home', str(self.home), ok=False)
        self.assertEqual(failed['code'], 'HOST_EXIT_FAILED')
        state = self.call(HOST, 'status', '--home', str(self.home))['data']
        self.assertEqual(state['state'], 'stopped')
        diagnostic = state['diagnostic']
        self.assertEqual(diagnostic['stage'], 'process_exited')
        self.assertEqual(diagnostic['exit_code'], 23)
        self.assertEqual(diagnostic['home_id'], self.created['data']['home_id'])
        self.assertEqual(failed['data']['diagnostic']['run_id'], diagnostic['run_id'])
        self.assertEqual(diagnostic['output_capture'], 'not_collected')
        self.assertIn('next_action', state)
        # Public privacy contract: host-owned diagnostic files must contain no raw output.
        for path in self.home.rglob('*'):
            if path.is_file():
                self.assertNotIn(SECRET.encode(), path.read_bytes(), str(path))
        self.assertEqual(self.call(ROOT / 'scripts/continuity.py', '--project', str(self.project), 'status'), baseline)

    def test_fixture_retains_home_after_launcher_exit_while_child_owns_lock(self):
        (self.root / 'controlled').write_text('{}')
        process = subprocess.Popen([sys.executable, '-B', str(HOST), 'run', '--home', str(self.home)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        owner = os.open(self.home / 'owner.lock', os.O_RDONLY | os.O_NOFOLLOW)
        try:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                state = self.call(HOST, 'status', '--home', str(self.home))['data']
                if state['state'] == 'running':
                    break
                time.sleep(.05)
            self.assertEqual(state['state'], 'running')
            # Only our exact launcher is terminated. The bounded synthetic child
            # intentionally retains the inherited lock and control socket.
            process.terminate()
            process.communicate(timeout=3)
            with self.assertRaises(BlockingIOError):
                fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.doCleanups()
            self.assertTrue(self.home.exists(), 'Cleanup must retain a live child home after reaping its launcher')
            self.assertEqual(self.call(HOST, 'status', '--home', str(self.home))['data']['state'], 'running')
        finally:
            if self.root.exists():
                (self.root / 'release').touch()
            if process.poll() is None:
                process.communicate(timeout=12)
            deadline = time.monotonic() + 12
            while True:
                try:
                    fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        self.fail('Synthetic child retained its original lock; do not delete its home')
                    time.sleep(.05)
            os.close(owner)
            # A retained home may be removed only after the original lock releases.
            if self.root.exists():
                self.cleanup_home()

    def test_unconfirmed_control_explains_last_observation_without_ready_or_force_stop(self):
        (self.root / 'quiet').touch()
        process = subprocess.Popen([sys.executable, '-B', str(HOST), 'run', '--home', str(self.home)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                state = self.call(HOST, 'status', '--home', str(self.home))['data']
                if state.get('diagnostic', {}).get('stage') == 'process_spawned':
                    break
                time.sleep(.1)
            self.assertEqual(state['state'], 'starting_or_unresponsive')
            self.assertEqual(state['diagnostic']['stage'], 'process_spawned')
            self.assertIsNone(state['diagnostic']['exit_code'])
            self.assertEqual(state['process_state'], 'unknown')
            self.assertFalse(state['control_verified'])
            self.assertEqual(state['control_reason'], 'CONTROL_UNREACHABLE')
            self.assertIn('next_action', state)
            self.assertEqual(self.call(HOST, 'run', '--home', str(self.home), ok=False)['code'], 'HOST_BUSY')
            self.assertEqual(self.call(HOST, 'stop', '--home', str(self.home), ok=False)['code'], 'HOST_IO_ERROR')
            self.assertIsNone(process.poll(), 'Failed stop must not force-kill the owned process')
        finally:
            (self.root / 'release').touch()
            stdout, stderr = process.communicate(timeout=12)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        ended = self.call(HOST, 'status', '--home', str(self.home))['data']
        self.assertEqual(ended['state'], 'stopped')
        self.assertEqual(ended['diagnostic']['exit_code'], 0)

    def test_os_spawn_refusal_is_not_misreported_as_a_child_exit(self):
        self.node.chmod(0o600)
        failed = self.call(HOST, 'run', '--home', str(self.home), ok=False)
        self.assertEqual(failed['code'], 'HOST_START_FAILED')
        state = self.call(HOST, 'status', '--home', str(self.home))['data']
        self.assertEqual(state['state'], 'stopped')
        self.assertEqual(state['diagnostic']['stage'], 'spawn_failed')
        self.assertIsNone(state['diagnostic']['exit_code'])
        self.assertIn('Node', state['next_action'])

    def test_unsafe_diagnostic_destination_refuses_before_spawning(self):
        marker = self.root / 'unexpected-execution'
        self.node.write_text('#!' + sys.executable + '\nfrom pathlib import Path\n'
                             'Path(' + repr(str(marker)) + ').touch()\n')
        outside = self.root / 'preserve.txt'
        outside.write_text('untouched')
        (self.home / 'diagnostic.json').symlink_to(outside)
        failed = self.call(HOST, 'run', '--home', str(self.home), ok=False)
        self.assertEqual(failed['code'], 'UNSAFE_FILE')
        # An incorrect implementation may return before the accidentally launched child.
        deadline = time.monotonic() + .3
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertFalse(marker.exists(), 'Diagnostic preflight must precede external execution')
        self.assertEqual(outside.read_text(), 'untouched')

    def test_wrong_run_control_is_explained_without_stopping_or_claiming_ready(self):
        (self.root / 'controlled').write_text(json.dumps({'wrong_identity': True}))
        process = subprocess.Popen([sys.executable, '-B', str(HOST), 'run', '--home', str(self.home)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                state = self.call(HOST, 'status', '--home', str(self.home))['data']
                if state.get('control_reason') == 'HOST_IDENTITY_MISMATCH':
                    break
                time.sleep(.1)
            self.assertEqual(state['state'], 'starting_or_unresponsive')
            self.assertFalse(state['control_verified'])
            self.assertEqual(state['control_reason'], 'HOST_IDENTITY_MISMATCH')
            failed = self.call(HOST, 'stop', '--home', str(self.home), ok=False)
            self.assertEqual(failed['code'], 'HOST_IDENTITY_MISMATCH')
            self.assertEqual(failed['data']['diagnostic']['run_id'], state['diagnostic']['run_id'])
            self.assertIsNone(process.poll())
        finally:
            (self.root / 'release').touch()
            stdout, stderr = process.communicate(timeout=12)
            self.assertEqual(process.returncode, 0, stdout + stderr)

    def test_verified_control_and_persistent_pause_still_govern_normal_stop(self):
        (self.root / 'controlled').write_text('{}')
        process = subprocess.Popen([sys.executable, '-B', str(HOST), 'run', '--home', str(self.home)],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                state = self.call(HOST, 'status', '--home', str(self.home))['data']
                if state['state'] == 'running':
                    break
                time.sleep(.1)
            self.assertEqual(state['state'], 'running')
            stopped = self.call(HOST, 'stop', '--home', str(self.home))['data']
            self.assertEqual(stopped['state'], 'stopped')
            self.assertTrue(stopped['persisted_pause'])
        finally:
            (self.root / 'release').touch()
            stdout, stderr = process.communicate(timeout=12)
            self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertEqual(self.call(HOST, 'status', '--home', str(self.home))['data']['diagnostic']['exit_code'], 0)

    def test_stale_or_extra_diagnostic_fields_are_unavailable_not_echoed(self):
        self.call(HOST, 'run', '--home', str(self.home), ok=False)
        path = self.home / 'diagnostic.json'
        original = path.read_bytes()
        for change in ({'run_id': '11111111-1111-4111-8111-111111111111'},
                       {'raw_output': SECRET}, {'stage': SECRET}, {'exit_code': SECRET}):
            with self.subTest(change=list(change)):
                value = json.loads(original)
                value.update(change)
                path.write_text(json.dumps(value))
                result = self.call(HOST, 'status', '--home', str(self.home))['data']
                self.assertEqual(result['state'], 'stopped')
                self.assertEqual(result['diagnostic'], {'availability': 'unavailable'})

    def test_signal_termination_is_not_an_exit_code(self):
        self.node.write_text('#!' + sys.executable + '\nimport os, signal\n'
                             'os.kill(os.getpid(), signal.SIGTERM)\n')
        self.call(HOST, 'run', '--home', str(self.home), ok=False)
        diagnostic = self.call(HOST, 'status', '--home', str(self.home))['data']['diagnostic']
        self.assertEqual(diagnostic['stage'], 'process_exited')
        self.assertIsNone(diagnostic['exit_code'])
        self.assertEqual(diagnostic['termination_signal'], 15)


if __name__ == '__main__':
    unittest.main()
