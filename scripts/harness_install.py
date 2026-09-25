"""Prepare a private Harness adapter bundle; never activate a host implicitly."""
from __future__ import annotations

import argparse
import hashlib
from importlib import resources
import os
from pathlib import Path
import sqlite3
import stat
import sys

if __package__:
    from . import continuity as core
else:
    import continuity as core

SUPPORTED_SDK = '0.1.5-rc.1'
PEERS = {
    'dsh': SUPPORTED_SDK, 'cordis': '4.0.2', 'schemastery': '3.18.2',
    'dsh-llm': SUPPORTED_SDK, 'dsh-client-ui-commands': SUPPORTED_SDK,
    'dsh-api-session-controller': SUPPORTED_SDK, 'dsh-client-ui-conversation': SUPPORTED_SDK,
}
ASSETS = (
    'scripts/continuity.py', 'scripts/recovery.py',
    'adapters/harness/native-plugin.mjs', 'adapters/harness/automatic-recovery.mjs',
    'adapters/harness/managed-host.mjs',
    'adapters/harness/client-notice/package.json', 'adapters/harness/client-notice/index.mjs',
    'adapters/harness/client-notice/client.js',
)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def asset_bytes(relative):
    if __package__:
        prefix = 'adapters/harness/'
        package = 'glom_continuity.harness' if relative.startswith(prefix) else 'glom_continuity'
        name = relative[len(prefix):] if relative.startswith(prefix) else relative[len('scripts/'):]
        return resources.files(package).joinpath(*name.split('/')).read_bytes()
    return (Path(__file__).resolve().parents[1] / relative).read_bytes()


def write_new(path, data):
    # No replacing an older file, and a crash leaves an inspectable partial bundle.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def json_bytes(value):
    return (core.wire(value) + '\n').encode('utf-8')


def read_json(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > 131072:
        raise core.Fault('UNSAFE_FILE', 'Expected a bounded regular JSON file; no code was executed')
    return core.strict_json(path.read_text(encoding='utf-8'))


def private_directory(path):
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077):
        raise core.Fault('UNSAFE_DIRECTORY', 'Choose a private directory owned by the current user (mode 0700)')


def new_target(value):
    raw = Path(value).expanduser().absolute()
    target = raw.parent.resolve(strict=True) / raw.name
    private_directory(target.parent)
    if os.path.lexists(target):
        raise core.Fault('TARGET_EXISTS', 'Destination already exists. It was not replaced or repaired')
    return target


def check_sdk(value):
    sdk = Path(value).expanduser().resolve(strict=True)
    if not sdk.is_dir():
        raise core.Fault('INVALID_SDK', 'Expected the explicitly selected SDK node_modules directory')
    def trusted(path, directory):
        info = path.lstat()
        expected_type = stat.S_ISDIR if directory else stat.S_ISREG
        if (not expected_type(info.st_mode) or info.st_uid not in (0, os.getuid())
                or info.st_mode & 0o022 or (not directory and info.st_nlink != 1)):
            raise core.Fault('UNSAFE_SDK', 'SDK metadata must not be symlinked, shared-writable or owned by another user')
    trusted(sdk, True)
    trusted(sdk / '@deepseek-ai', True)
    # Metadata only: do not import JS, boot profiles, inspect keys, or run npm.
    for name, version in PEERS.items():
        folder = sdk / '@deepseek-ai' / name
        trusted(folder, True)
        trusted(folder / 'package.json', False)
        package = read_json(folder / 'package.json')
        if not isinstance(package, dict) or (package.get('name'), package.get('version')) != ('@deepseek-ai/' + name, version):
            raise core.Fault('UNSUPPORTED_SDK', 'SDK or public peer version differs from the verified compatibility baseline')
    return sdk


def preflight(args):
    if os.name != 'posix':
        raise core.Fault('UNSUPPORTED_PLATFORM', 'This installer currently verifies private POSIX directories only')
    target = new_target(args.directory)
    project = core.project_root(args.project)
    if target.is_relative_to(project):
        raise core.Fault('UNSAFE_LOCATION', 'Keep executable adapter files outside the project being read')
    observed = core.execute(argparse.Namespace(command='doctor', project=str(project)))['storage']
    if not observed.get('compatible'):
        raise core.Fault('PROJECT_NOT_READY', 'Initialize and inspect the selected Continuity project first; no project data was changed')
    if observed['project_id'] != args.project_id:
        raise core.Fault('PROJECT_MISMATCH', 'The selected project ID does not match; no project data was changed')
    sdk = check_sdk(args.sdk_node_modules)
    if target.is_relative_to(sdk):
        raise core.Fault('UNSAFE_LOCATION', 'Do not install an adapter inside the existing SDK')
    return {'state': 'ready_to_stage', 'directory': str(target), 'project': str(project),
            'project_id': observed['project_id'], 'sdk_node_modules': str(sdk),
            'sdk_version': SUPPORTED_SDK, 'host_state': 'not_inspected',
            'model_called': False, 'profile_changed': False,
            'note': 'Compatibility metadata checked, not publisher authentication or live host activation.'}


def stage(args):
    checked = preflight(args)
    target = Path(checked['directory'])
    payloads = {relative: asset_bytes(relative) for relative in ASSETS}
    payloads['overlay.json'] = json_bytes([
        {'id': 'recaloom-native', 'name': str(target / 'adapters/harness/native-plugin.mjs'),
         'config': {'python': str(Path(sys.executable).absolute()),
                    'recovery': str(target / 'scripts/recovery.py'),
                    'project': checked['project'], 'projectId': checked['project_id']}},
        {'id': 'recaloom-notice', 'name': str(target / 'adapters/harness/client-notice/index.mjs')},
    ])
    # This is a private adapter bundle, NOT a host profile. Never initialize, launch,
    # overwrite or infer activation from a profile/settings file in this operation.
    target.mkdir(mode=0o700)
    for relative, data in payloads.items():
        destination = target / relative
        directory = target
        for part in destination.relative_to(target).parts[:-1]:
            directory = directory / part
            directory.mkdir(mode=0o700, exist_ok=True)
            private_directory(directory)
        write_new(destination, data)
    (target / 'node_modules').symlink_to(checked['sdk_node_modules'], target_is_directory=True)
    manifest = {'format': 'recaloom-harness-bundle-v1', 'version': core.VERSION, 'directory': str(target),
                'project': checked['project'], 'project_id': checked['project_id'],
                'sdk_node_modules': checked['sdk_node_modules'], 'sdk_version': SUPPORTED_SDK,
                'files': {relative: sha256(data) for relative, data in payloads.items()}}
    # Last file is the completion marker. A partial installation never reports ready.
    write_new(target / 'installation.json', json_bytes(manifest))
    return inspect_bundle(target)


def private_file(path):
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1
            or stat.S_IMODE(info.st_mode) != 0o600):
        raise core.Fault('UNSAFE_FILE', 'Bundle files must be private, owned, regular and not hard-linked')


def inspect_bundle(target):
    raw = Path(target).expanduser().absolute()
    target = raw.parent.resolve(strict=True) / raw.name
    private_directory(target)
    private_file(target / 'installation.json')
    manifest = read_json(target / 'installation.json')
    if (not isinstance(manifest, dict) or manifest.get('format') != 'recaloom-harness-bundle-v1'
            or not isinstance(manifest.get('files'), dict)
            or set(manifest['files']) != set(ASSETS) | {'overlay.json'}):
        raise core.Fault('INVALID_BUNDLE', 'Installation metadata is incomplete or not this bundle format')
    if manifest.get('directory') != str(target):
        raise core.Fault('BUNDLE_MOVED', 'This bundle moved; its absolute paths were not rewritten. Stage a fresh bundle instead')
    # Fixed allowlist: never trust a manifest to supply arbitrary paths to read.
    for relative in (*ASSETS, 'overlay.json'):
        directory = target
        for part in Path(relative).parts[:-1]:
            directory = directory / part
            private_directory(directory)
        path = target / relative
        private_file(path)
        if sha256(path.read_bytes()) != manifest['files'][relative]:
            raise core.Fault('BUNDLE_CHANGED', 'Installed files differ from their staging snapshot; no repair was attempted')
    sdk = check_sdk(manifest['sdk_node_modules'])
    if (not (target / 'node_modules').is_symlink()
            or (target / 'node_modules').resolve(strict=True) != sdk):
        raise core.Fault('SDK_CHANGED', 'The installed SDK link no longer matches its explicit binding')
    current = core.execute(argparse.Namespace(command='doctor', project=manifest['project']))['storage']
    if not current.get('compatible') or current.get('project_id') != manifest['project_id']:
        raise core.Fault('PROJECT_MISMATCH', 'The bound project is missing or has changed identity; no host was activated')
    return {'state': 'staged_not_activated', 'directory': str(target),
            'project': manifest['project'], 'project_id': manifest['project_id'],
            'sdk_version': manifest['sdk_version'], 'host_state': 'not_inspected',
            'model_called': False, 'profile_changed': False,
            'note': 'Files verified, not live activation or publisher authentication. A separately managed host must explicitly mount this bundle.'}


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest='command', required=True)
    for name, help_text in (('preflight', 'Read-only project and SDK metadata checks'),
                            ('install', 'Stage a private adapter bundle; does not activate a host')):
        check = commands.add_parser(name, help=help_text)
        check.add_argument('--directory', required=True, help='New bundle under an existing private (0700) parent')
        check.add_argument('--project', required=True)
        check.add_argument('--project-id', required=True)
        check.add_argument('--sdk-node-modules', required=True)
    status = commands.add_parser('status', help='Verify staged files; does not infer whether a host has enabled them')
    status.add_argument('--directory', required=True)
    return result


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    args = parser().parse_args()
    try:
        data = (preflight(args) if args.command == 'preflight' else
                stage(args) if args.command == 'install' else inspect_bundle(args.directory))
        print(core.wire({'ok': True, 'code': 'OK', 'data': data}))
        return 0
    except core.Fault as exc:
        print(core.wire({'ok': False, 'code': exc.code, 'data': None, 'error': exc.message}))
        return 2
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, RuntimeError):
        print(core.wire({'ok': False, 'code': 'IO_ERROR', 'data': None,
                         'error': 'Installer could not verify this target; no host was activated'}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
