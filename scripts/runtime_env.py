"""Create a new offline tool environment, validating its interpreter before pip."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import venv

PROBE = '''import importlib.util, json, sqlite3, sys
print(json.dumps(dict(prefix=sys.prefix, base_prefix=sys.base_prefix,
    python_version=list(sys.version_info[:3]), sqlite_version=sqlite3.sqlite_version,
    pip_available=importlib.util.find_spec("pip") is not None)))
'''


class EnvironmentFault(Exception):
    def __init__(self, code, message, phase, *, exit_code=None, next_step=None, runtime=None, cleanup=None):
        super().__init__(message)
        self.code, self.phase = code, phase
        self.exit_code, self.next_step = exit_code, next_step
        self.runtime = runtime
        self.cleanup = cleanup


class StrictEnvironmentBuilder(venv.EnvBuilder):
    """Keep POSIX interpreter-link refusal from silently choosing copies."""
    def symlink_or_copy(self, src, dst, relative_symlinks_ok=False):
        if not self.symlinks:
            return super().symlink_or_copy(src, dst, relative_symlinks_ok)
        try:
            if not os.path.islink(dst):
                os.symlink(os.path.basename(src) if relative_symlinks_ok else src, dst)
        except OSError:
            raise EnvironmentFault('RUNTIME_MODE_UNAVAILABLE', 'The selected interpreter link mode could not be created.',
                                   'venv_create', next_step='Preserve the partial directory. Choose a link-capable location '
                                   'or explicitly request --copies at a different path and verify that runtime.') from None


def child_env():
    env = {name: os.environ[name] for name in ('PATH', 'SystemRoot', 'WINDIR') if name in os.environ}
    env['PIP_CONFIG_FILE'] = os.devnull
    return env


def stop_owned_child(process):
    """Signal only the new process/group whose unreaped leader we still own.

    No poll/wait is allowed before signaling: retaining the child prevents PID
    reuse from turning a stale identifier into somebody else's process group.
    A descendant that deliberately creates another session is outside this
    trusted-runtime boundary; Windows tree termination is not yet verified.
    """
    group = os.name == 'posix'
    cleanup = dict(scope='posix_process_group' if group else 'direct_child',
                   signal_sent=False, leader_reaped=False, output_drained=False,
                   escaped_descendants_checked=False)
    if process.returncode is not None:
        # communicate() may reap a promptly exiting leader while processing
        # KeyboardInterrupt. Its numeric group ID is no longer ours to signal.
        cleanup.update(leader_reaped=True, ownership_released_before_cleanup=True)
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
        return cleanup
    try:
        if group:
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        cleanup['signal_sent'] = True
    except ProcessLookupError:
        pass
    except OSError:
        cleanup['signal_error'] = True
    try:
        process.communicate(timeout=2)
        cleanup['leader_reaped'] = True
        cleanup['output_drained'] = True
    except subprocess.TimeoutExpired:
        # An escaped descendant can retain inherited pipes. Never wait forever
        # or search by process name/PID to kill an unverified process.
        for pipe in (process.stdout, process.stderr):
            if pipe is not None:
                pipe.close()
        try:
            process.wait(timeout=2)
            cleanup['leader_reaped'] = True
        except subprocess.TimeoutExpired:
            pass
    return cleanup


def run_child(argv, phase, timeout=10):
    try:
        process = subprocess.Popen(argv, env=child_env(), cwd=Path(argv[0]).parent,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding='utf-8', errors='replace',
                                   start_new_session=os.name == 'posix')
    except OSError:
        raise EnvironmentFault('RUNTIME_UNAVAILABLE', 'The selected environment executable could not be started.', phase,
                               runtime={'python_executable': argv[0]},
                               next_step='Use a working base Python to inspect this environment. Do not overwrite it.')
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
        cleanup = stop_owned_child(process)
        timed_out = isinstance(exc, subprocess.TimeoutExpired)
        raise EnvironmentFault('RUNTIME_TIMEOUT' if timed_out else 'RUNTIME_INTERRUPTED',
                               'The selected environment timed out.' if timed_out else 'Environment checking was interrupted.',
                               phase, exit_code=process.returncode, cleanup=cleanup,
                               runtime={'python_executable': argv[0]},
                               next_step='Preserve this directory. Check the reported cleanup scope before retrying; '
                               'Windows process trees and escaped descendants are not certified.') from None
    result = subprocess.CompletedProcess(argv, process.returncode, stdout, stderr)
    if result.returncode:
        hint = ('The copied macOS interpreter cannot locate libpython. Use a working base Python '
                'to create a different environment with the default symlink mode; do not patch loader paths.'
                if 'Library not loaded:' in result.stderr and 'libpython' in result.stderr else
                'Preserve this directory. Check the chosen base Python and its bundled venv/ensurepip support; '
                'create a separate environment after resolving the cause.')
        code = {'runtime_probe': 'RUNTIME_START_FAILED', 'pip_probe': 'PIP_UNAVAILABLE',
                'pip_bootstrap': 'PIP_BOOTSTRAP_FAILED', 'wheel_install': 'WHEEL_INSTALL_FAILED',
                'tool_probe': 'TOOL_CHECK_FAILED'}[phase]
        if phase in ('wheel_install', 'tool_probe'):
            hint = ('Preserve the partial environment. Check the exact trusted wheel, its supplied hash and matching guide. '
                    'Do not overwrite an existing installation or initialize a project to fix this failure.')
        raise EnvironmentFault(code,
                               'The selected installation phase did not complete.', phase,
                               exit_code=result.returncode, next_step=hint, runtime={'python_executable': argv[0]})
    return result.stdout


def inspect_runtime(target):
    python = target / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    output = run_child([str(python), '-I', '-B', '-c', PROBE], 'runtime_probe')
    observed = {'python_executable': str(python)}
    try:
        data = json.loads(output)
        valid = (isinstance(data, dict) and all(isinstance(data[key], str) and len(data[key]) <= 16384
                 and not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in data[key])
                 for key in ('prefix', 'base_prefix', 'sqlite_version'))
                 and len(data['python_version']) == 3
                 and all(type(v) is int for v in data['python_version'])
                 and type(data['pip_available']) is bool)
        if valid:
            observed.update({key: data[key] for key in
                ('prefix', 'base_prefix', 'python_version', 'sqlite_version', 'pip_available')})
            valid = (Path(data['prefix']).resolve() == target and Path(data['base_prefix']).resolve() != target
                     and tuple(data['python_version']) >= (3, 10, 0))
    except (ValueError, TypeError, KeyError, OSError, RecursionError):
        valid = False
    if not valid:
        raise EnvironmentFault('RUNTIME_IDENTITY_MISMATCH',
                               'The interpreter did not identify a supported isolated environment at this path.',
                               'runtime_probe', exit_code=0, runtime=observed,
                               next_step='Preserve this directory and select the correct environment.')
    return observed


def verify_pip(data):
    if not data['pip_available']:
        raise EnvironmentFault('PIP_UNAVAILABLE', 'The interpreter starts but pip is not installed.',
                               'pip_probe', runtime=data,
                               next_step='Keep this environment. Use a working base Python to create a separate environment.')
    try:
        run_child([data['python_executable'], '-I', '-B', '-m', 'pip', '--version'], 'pip_probe')
    except EnvironmentFault as fault:
        fault.runtime = dict(data)
        raise


def verified_wheel(value, expected):
    phase = 'wheel_verify'
    if not value or not expected or not re.fullmatch(r'[0-9a-fA-F]{64}', expected):
        raise EnvironmentFault('INVALID_WHEEL_ARGUMENTS', 'Supply a local wheel and its complete SHA-256 together.', phase)
    wheel = Path(value)
    if (not wheel.is_absolute() or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value)
            or not re.fullmatch(r'glom_continuity-[A-Za-z0-9][A-Za-z0-9_.+!]*-py3-none-any\.whl', wheel.name)
            or not stat.S_ISREG(wheel.lstat().st_mode)):
        raise EnvironmentFault('INVALID_WHEEL', 'Choose a trusted local Recaloom wheel file, not a link or directory.', phase)
    digest = hashlib.sha256()
    descriptor = os.open(wheel, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
                         | getattr(os, 'O_NONBLOCK', 0) | getattr(os, 'O_BINARY', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise EnvironmentFault('INVALID_WHEEL', 'The selected wheel is not a regular file.', phase)
        size = 0
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > 64 * 1024 * 1024:
                raise EnvironmentFault('WHEEL_TOO_LARGE', 'The selected wheel exceeds the 64 MiB installation limit.', phase)
            digest.update(chunk)
    if digest.hexdigest() != expected.lower():
        raise EnvironmentFault('WHEEL_HASH_MISMATCH', 'The wheel does not match the supplied SHA-256; nothing was installed.',
                               phase, next_step='Obtain the exact trusted asset and matching digest. Do not retry with an invented digest.')
    return wheel.resolve(strict=True), expected.lower()


def install_tool(data, wheel, target):
    path, digest = wheel
    python = data['python_executable']
    run_child([python, '-I', '-B', '-m', 'pip', 'install', '--no-index', '--no-deps',
               '--only-binary', ':all:', '--require-hashes', '--no-cache-dir', '--no-input',
               '--disable-pip-version-check', path.as_uri() + '#sha256=' + digest], 'wheel_install', timeout=60)
    output = run_child([python, '-I', '-B', '-m', 'glom_continuity', '--project', str(target), 'doctor'], 'tool_probe')
    try:
        response = json.loads(output)
        tool = response['data']
        valid = (response['ok'] is True and response['code'] == 'OK' and tool['product_id'] == 'glom-continuity'
                 and tool['usage']['state'] == 'available' and tool['runtime']['python_executable'] == python
                 and Path(tool['runtime']['program_path']).resolve(strict=True).is_relative_to(target)
                 and Path(tool['usage']['skill_path']).resolve(strict=True).is_relative_to(target)
                 and tool['storage']['state'] == 'not_initialized')
    except (ValueError, TypeError, KeyError, OSError, RecursionError):
        valid = False
    if not valid:
        raise EnvironmentFault('TOOL_CHECK_FAILED', 'The installed tool or matching bundled guide could not be verified.',
                               'tool_probe', runtime=data, next_step='Preserve the partial installation; obtain a matching '
                               'candidate with its bundled guide. Do not borrow another runtime or initialize a project.')
    data.update(tool_installed=True, host_integrated=False, wheel_sha256=digest,
                cli_argv=[python, '-I', '-B', '-m', 'glom_continuity'], tool=tool)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest='command', required=True)
    create = actions.add_parser('create', help='Create a new environment; never replace an existing path')
    create.add_argument('--directory', required=True, help='New absolute path with an existing parent directory')
    create.add_argument('--copies', action='store_true', help='Explicitly request copies; no automatic fallback')
    create.add_argument('--wheel', help='Optionally install this trusted local absolute Recaloom wheel path')
    create.add_argument('--sha256', help='Required with --wheel: SHA-256 from the selected trusted release or candidate')
    check = actions.add_parser('check', help='Inspect a trusted existing environment without repairing it')
    check.add_argument('--directory', required=True, help='Absolute path to the selected environment')
    args = parser.parse_args(argv)
    target = None
    created = False
    phase = 'destination_check'
    try:
        raw = Path(args.directory)
        if not raw.is_absolute() or any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in args.directory):
            raise EnvironmentFault('INVALID_DIRECTORY', 'Choose an absolute path without control characters.', phase)
        target = raw.parent.resolve(strict=True) / raw.name
        if args.command == 'create' and os.pathsep in str(target):
            raise EnvironmentFault('INVALID_DIRECTORY', 'Python venv cannot use a directory containing the PATH separator.',
                                   phase, next_step='Choose a different new path without the PATH separator.')
        if args.command == 'check':
            if not stat.S_ISDIR(target.lstat().st_mode):
                raise EnvironmentFault('INVALID_DIRECTORY', 'Choose a real environment directory, not a link or file.', phase)
            data = inspect_runtime(target)
            verify_pip(data)
            data.update(directory=str(target), tool_installation_checked=False, host_configuration_checked=False)
            print(json.dumps(dict(ok=True, code='RUNTIME_READY', data=data), ensure_ascii=False))
            return 0
        wheel = None
        if args.wheel is not None or args.sha256 is not None:
            phase = 'wheel_verify'
            wheel = verified_wheel(args.wheel, args.sha256)
        phase = 'destination_check'
        try:
            target.mkdir(mode=0o700)  # Atomic reservation, including refusal of existing/dangling links.
        except FileExistsError:
            raise EnvironmentFault('TARGET_EXISTS', 'The destination already exists and was not changed.', phase,
                                   next_step='Inspect the existing installation, or choose a new directory.')
        created = True
        phase = 'venv_create'
        mode = 'symlinks' if os.name != 'nt' and not args.copies else 'copies'
        StrictEnvironmentBuilder(with_pip=False, system_site_packages=False, symlinks=mode == 'symlinks').create(target)
        data = inspect_runtime(target)
        phase = 'pip_bootstrap'
        run_child([data['python_executable'], '-I', '-B', '-m', 'ensurepip', '--default-pip'], phase, timeout=60)
        data = inspect_runtime(target)
        verify_pip(data)
        data.update(directory=str(target), creation_mode=mode, host_integrated=False, tool_installed=False)
        if wheel is not None:
            phase = 'wheel_install'
            install_tool(data, wheel, target)
        print(json.dumps(dict(ok=True, code='TOOL_READY' if wheel is not None else 'RUNTIME_READY', data=data), ensure_ascii=False))
        return 0
    except (EnvironmentFault, OSError, subprocess.SubprocessError) as exc:
        fault = exc if isinstance(exc, EnvironmentFault) else EnvironmentFault(
            'ENVIRONMENT_IO_ERROR', 'Environment preparation failed; no existing installation was replaced.', phase,
            next_step='Check the parent directory, permissions and base Python. Preserve any partial environment.')
        print(json.dumps(dict(ok=False, code=fault.code, message=str(fault), data=dict(
            phase=fault.phase, directory=str(target) if target else None, created=created,
            partial_environment_retained=created, exit_code=fault.exit_code, next_step=fault.next_step,
            runtime=fault.runtime, child_cleanup=fault.cleanup)), ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
