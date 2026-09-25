"""Explicitly owned Harness profile: create, foreground run, status and safe stop."""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import re
import signal
import socket
import stat
import subprocess
import sys
import time
import uuid

if __package__:
    from . import harness_install as install
else:
    import harness_install as install
core = install.core


def create(args):
    checked = install.inspect_bundle(args.bundle)
    home = install.new_target(args.home)
    if home.is_relative_to(Path(checked['project'])) or home.is_relative_to(Path(checked['directory'])):
        raise core.Fault('UNSAFE_LOCATION', 'Keep the managed home outside its project and executable bundle')
    if len(os.fsencode(str(home / 'control.sock'))) > 100:
        raise core.Fault('SOCKET_PATH_TOO_LONG', 'Choose a shorter private home path for the local control socket')
    node = Path(args.node).expanduser().resolve(strict=True)
    info = node.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.getuid()) or info.st_mode & 0o022:
        raise core.Fault('UNSAFE_NODE', 'Select a trusted, non-shared-writable Node executable')
    version = subprocess.check_output([str(node), '--version'], env={'PATH': '/usr/bin:/bin'}, text=True, timeout=10).strip()
    if not re.fullmatch(r'v\d+\.\d+\.\d+', version) or int(version[1:].split('.')[0]) < 24:
        raise core.Fault('UNSUPPORTED_NODE', 'This managed launcher requires Node 24 or newer')
    home_id = str(uuid.uuid4())
    rows = install.read_json(Path(checked['directory']) / 'overlay.json')
    home.mkdir(mode=0o700)
    (home / 'dsh-home').mkdir(mode=0o700)
    files = {}
    for name, opened, attached in (('closed.json', False, True), ('open.json', True, True),
                                  ('detached-closed.json', False, False), ('detached-open.json', True, False)):
        controller = {'id': 'recaloom-managed-host', 'name': str(Path(checked['directory']) / 'adapters/harness/managed-host.mjs'),
                      'config': {'homeId': home_id, 'socket': str(home / 'control.sock'), 'attached': attached}}
        patch = install.json_bytes([
            {'id': 'web-runtime', 'config': {'openBrowser': opened, 'printUrl': False, 'surfaceContext': True, 'trustedHosts': []}},
            # Web users must see the chooser in their authenticated page;
            # a host-native modal can be invisible to a remote/headless client.
            {'id': 'directory-picker', 'name': '@deepseek-ai/dsh-host-directory-picker-auto', 'disabled': True},
            {'insert': [
                {'id': 'recaloom-directory-picker', 'name': '@deepseek-ai/dsh-host-directory-picker-browse'},
                {'id': 'recaloom-directory-picker-ui', 'name': '@deepseek-ai/dsh-client-ui-directory-picker-browse'},
                *(rows if attached else []), controller]},
        ])
        install.write_new(home / name, patch)
        files[name] = install.sha256(patch)
    install.write_new(home / 'owner.lock', b'')
    install.write_new(home / 'managed.json', install.json_bytes({
        'format': 'recaloom-managed-host-v1', 'home': str(home), 'home_id': home_id,
        'bundle': checked['directory'], 'node': str(node), 'node_version': version, 'files': files,
    }))
    return {'state': 'prepared', 'home': str(home), 'home_id': home_id, 'model_called': False}


def inspect(home):
    raw = Path(home).expanduser().absolute()
    root = raw.parent.resolve(strict=True) / raw.name
    install.private_directory(root)
    install.private_file(root / 'managed.json')
    metadata = install.read_json(root / 'managed.json')
    if metadata.get('format') != 'recaloom-managed-host-v1' or metadata.get('home') != str(root):
        raise core.Fault('INVALID_MANAGED_HOME', 'Not this managed home or it has moved')
    if set(metadata.get('files', {})) != {'open.json', 'closed.json', 'detached-open.json', 'detached-closed.json'}:
        raise core.Fault('INVALID_MANAGED_HOME', 'Incomplete managed composition')
    for name, digest in metadata['files'].items():
        install.private_file(root / name)
        if install.sha256((root / name).read_bytes()) != digest:
            raise core.Fault('MANAGED_HOME_CHANGED', 'Managed composition changed; not silently repaired')
    return root, metadata


def is_detached(root, metadata):
    path = root / 'detached.json'
    if not os.path.lexists(path):
        return False
    install.private_file(path)
    if install.read_json(path) != {'home_id': metadata['home_id'], 'attached': False}:
        raise core.Fault('INVALID_ATTACHMENT_STATE', 'Detached marker does not belong to this home')
    return True


def detach(args):
    stop(args)
    root, metadata = inspect(args.home)
    fd = lock(root)
    if fd is None:
        raise core.Fault('HOST_BUSY', 'Another run started; no attachment state was changed')
    try:
        if not is_detached(root, metadata):
            install.write_new(root / 'detached.json', install.json_bytes({'home_id': metadata['home_id'], 'attached': False}))
        return {'state': 'detached', 'home_id': metadata['home_id'], 'data_deleted': False,
                'note': 'Future runs omit recovery and its notice. Host controller, chats and project data are retained.'}
    finally:
        os.close(fd)


def lock(root):
    install.private_file(root / 'owner.lock')
    fd = os.open(root / 'owner.lock', os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return fd


def control(root, metadata, action):
    install.private_file(root / 'run.json')
    run = install.read_json(root / 'run.json')
    info = (root / 'control.sock').lstat()
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise core.Fault('UNSAFE_SOCKET', 'Expected the private local control socket')
    with socket.socket(socket.AF_UNIX) as connection:
        connection.settimeout(15)
        connection.connect(str(root / 'control.sock'))
        request = {'action': action, 'home_id': metadata['home_id'], 'run_id': run['run_id']}
        connection.sendall(install.json_bytes(request))
        response = b''
        while b'\n' not in response:
            part = connection.recv(1024)
            if not part or len(response) + len(part) > 8192:
                raise core.Fault('CONTROL_RESPONSE_INVALID', 'Host response was missing or oversized')
            response += part
    value = core.strict_json(response.decode('utf-8'))
    if value.get('home_id') != request['home_id'] or value.get('run_id') != request['run_id']:
        raise core.Fault('HOST_IDENTITY_MISMATCH', 'The control response is not from this run')
    if value.get('ok') is not True:
        raise core.Fault('HOST_CONTROL_REFUSED', 'Host did not confirm this control operation')
    return value


def status(args):
    root, metadata = inspect(args.home)
    fd = lock(root)
    if fd is not None:
        os.close(fd)
        return {'state': 'stopped', 'home_id': metadata['home_id']}
    try:
        return control(root, metadata, 'status')
    except (OSError, core.Fault):
        return {'state': 'starting_or_unresponsive', 'home_id': metadata['home_id'],
                'note': 'Ownership lock is held. Do not start a replacement based only on this observation.'}


def stop(args):
    root, metadata = inspect(args.home)
    fd = lock(root)
    if fd is not None:
        os.close(fd)
        return {'state': 'stopped', 'home_id': metadata['home_id']}
    receipt = control(root, metadata, 'stop')
    if receipt.get('persisted_pause') is not True and receipt.get('recovery_attached') is not False:
        raise core.Fault('PAUSE_NOT_SAVED', 'Do not remove this host; persistent pause was not confirmed')
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        fd = lock(root)
        if fd is not None:
            os.close(fd)
            return {'state': 'stopped', 'home_id': metadata['home_id'],
                    'persisted_pause': receipt.get('persisted_pause') is True}
        time.sleep(.05)
    raise core.Fault('STOP_PENDING', 'Host still owns its lock. Do not remove files or start a replacement')


def run(args):
    root, metadata = inspect(args.home)
    checked = install.inspect_bundle(metadata['bundle'])
    install.private_directory(root / 'dsh-home')
    if (root / '.env').exists() or (root / 'dsh-home/.env').exists():
        raise core.Fault('UNREVIEWED_ENVIRONMENT', 'This launcher does not load an unreviewed environment file')
    fd = lock(root)
    if fd is None:
        raise core.Fault('HOST_BUSY', 'This home already has an owner; inspect its status instead')
    try:
        sock = root / 'control.sock'
        if os.path.lexists(sock):
            info = sock.lstat()
            if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                raise core.Fault('UNSAFE_SOCKET', 'Unexpected object at the control path; not removed')
            with socket.socket(socket.AF_UNIX) as probe:
                try:
                    probe.settimeout(.5)
                    probe.connect(str(sock))
                except ConnectionRefusedError:
                    sock.unlink()  # Only this owned, refused, stale socket, while holding its lock.
                else:
                    raise core.Fault('HOST_IDENTITY_MISMATCH', 'A control server is live without the expected lock')
        record = root / 'run.json'
        if record.exists():
            install.private_file(record)
        temporary = root / ('run-' + uuid.uuid4().hex + '.json')
        run_id = str(uuid.uuid4())
        install.write_new(temporary, install.json_bytes({'run_id': run_id, 'home_id': metadata['home_id']}))
        os.replace(temporary, record)
        env = {'PATH': str(Path(metadata['node']).parent) + ':/usr/bin:/bin', 'LANG': 'en_US.UTF-8',
               'DSH_HOME': str(root / 'dsh-home'), 'DSH_TELEMETRY_DISABLED': '1',
               'RECALOOM_MANAGED_RUN_ID': run_id, 'RECALOOM_MANAGED_LOCK_FD': str(fd)}
        first = not (root / 'dsh-home/profiles/recaloom/package.json').exists()
        command = [metadata['node'], str(Path(checked['directory']) / 'node_modules/@deepseek-ai/dsh/lib/bin.js'),
                   '--profile', 'recaloom']
        if first:
            command += ['--from-default-profile', 'web']
        patch_name = ('detached-' if is_detached(root, metadata) else '') + ('open.json' if args.open else 'closed.json')
        command += ['--patch', str(root / patch_name),
                    '--host', '127.0.0.1', '--port', '0']
        if not args.open:
            command += ['--no-open']
        stop_requested = False
        def request_stop(_signal, _frame):
            nonlocal stop_requested
            stop_requested = True
        previous_interrupt = signal.signal(signal.SIGINT, request_stop)
        try:
            # Terminal SIGINT must reach the owner, never bypass the persistent
            # pause barrier by triggering the SDK's direct signal disposal.
            child = subprocess.Popen(command, cwd=root, env=env, stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                     pass_fds=(fd,), start_new_session=True)
            deadline = None
            acknowledged = False
            while child.poll() is None:
                if stop_requested:
                    if deadline is None:
                        deadline = time.monotonic() + 30
                    if time.monotonic() >= deadline:
                        raise core.Fault('STOP_PENDING', 'Safe stop was not confirmed; inspect this home and retry stop, do not remove it')
                    if not acknowledged:
                        try:
                            state = control(root, metadata, 'status')
                        except OSError:
                            state = {'state': 'starting'}
                        if state['state'] in ('running', 'stopping'):
                            receipt = control(root, metadata, 'stop')
                            if receipt.get('persisted_pause') is not True and receipt.get('recovery_attached') is not False:
                                raise core.Fault('PAUSE_NOT_SAVED', 'Safe pause was not confirmed; host was not forcibly stopped')
                            acknowledged = True
                            deadline = time.monotonic() + 15
                time.sleep(.05)
            code = child.returncode
        finally:
            signal.signal(signal.SIGINT, previous_interrupt)
        if code:
            raise core.Fault('HOST_EXIT_FAILED', 'Official host did not exit cleanly; no successful lifecycle claim')
        return {'state': 'exited', 'exit_code': code, 'home_id': metadata['home_id']}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('create', 'run', 'status', 'stop', 'detach'):
        item = commands.add_parser(name)
        item.add_argument('--home', required=True)
        if name == 'create':
            item.add_argument('--bundle', required=True)
            item.add_argument('--node', required=True)
        if name == 'run':
            item.add_argument('--open', action='store_true', help='Open the official authenticated browser entry without printing its URL')
    args = parser.parse_args()
    try:
        result = {'create': create, 'run': run, 'status': status, 'stop': stop, 'detach': detach}[args.command](args)
        print(core.wire({'ok': True, 'code': 'OK', 'data': result}))
        return 0
    except core.Fault as error:
        print(core.wire({'ok': False, 'code': error.code, 'data': None, 'error': error.message}))
        return 2
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError):
        print(core.wire({'ok': False, 'code': 'HOST_IO_ERROR', 'data': None,
                         'error': 'Managed host operation could not be verified; no other process was stopped'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
