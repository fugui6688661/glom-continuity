"""Required installed-Harness CI checks; missing coverage is never success."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

if __package__:
    from .harness_install import PEERS
else:
    from harness_install import PEERS

ROOT = Path(__file__).resolve().parents[1]
NETWORK_POLICY = ('(version 1)(allow default)(deny network*)'
                  '(allow network-inbound (local ip "localhost:*"))'
                  '(allow network-outbound (remote ip "localhost:*"))'
                  '(allow network-inbound (local unix-socket))'
                  '(allow network-outbound (remote unix-socket))')


def reconcile_hosts(scratch, env):
    """Stop only synthetic homes under this runner's private temporary root.

    Use the controller's home/run identity and ownership lock, never kill a PID
    read from disk. An unresponsive home is retained and reported unverified.
    """
    deadline = time.monotonic() + 35
    homes = list(Path(scratch).glob('recaloom-host-*/host'))
    for home in homes:
        if home.is_symlink() or home.parent.is_symlink() or time.monotonic() >= deadline:
            return False
        try:
            result = subprocess.run(['/usr/bin/sandbox-exec', '-p', NETWORK_POLICY,
                                     sys.executable, '-B', str(ROOT / 'scripts/harness_host.py'),
                                     'stop', '--home', str(home)], env=env,
                                    capture_output=True, text=True,
                                    timeout=max(.1, deadline - time.monotonic()))
            receipt = json.loads(result.stdout)
            if (result.returncode != 0 or receipt.get('ok') is not True
                    or receipt.get('data', {}).get('state') != 'stopped'):
                return False
        except (OSError, ValueError, TypeError, AttributeError, subprocess.SubprocessError):
            return False
    return True


def run_required(report, anchor, node, host_timeout):
    env = {key: os.environ[key] for key in ('PATH', 'SystemRoot', 'WINDIR') if key in os.environ}
    inventory = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ci_plan.py'),
                                'check', '--root', str(ROOT)], env=env,
                               capture_output=True, text=True, timeout=10)
    if inventory.returncode:
        report['reason'] = 'COVERAGE_INVENTORY_INVALID'
        return
    plan = json.loads((ROOT / 'ci/test-plan.json').read_text(encoding='utf-8'))
    if not plan['harness_node'] or not plan['harness_py']:
        report['reason'] = 'REQUIRED_SUITES_MISSING'
        return
    # Fail closed rather than silently running a real host without containment.
    if sys.platform != 'darwin' or not Path('/usr/bin/sandbox-exec').is_file():
        report['reason'] = 'MACOS_NETWORK_SANDBOX_REQUIRED'
        return
    if not node or not Path(node).is_file() or not os.access(node, os.X_OK):
        report['reason'] = 'NODE_REQUIRED'
        return
    version = subprocess.run([node, '--version'], env=env, capture_output=True,
                             text=True, timeout=10)
    match = re.fullmatch(r'v(\d+)\.\d+\.\d+\s*', version.stdout)
    if version.returncode or not match or int(match[1]) < 24:
        report['reason'] = 'NODE_VERSION_UNSUPPORTED'
        return
    report.update(node=version.stdout.strip(), sdk_version=PEERS['dsh'],
                  network_policy='macos-loopback-and-unix-only',
                  plan_sha256=hashlib.sha256((ROOT / 'ci/test-plan.json').read_bytes()).hexdigest())
    scratch = tempfile.mkdtemp(prefix='recaloom-ci-', dir='/tmp')
    cleanup_verified = False
    try:
        env.update(HOME=scratch, USERPROFILE=scratch, TMPDIR=scratch, TMP=scratch, TEMP=scratch,
                   PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
                   PIP_CONFIG_FILE=os.devnull, CONTINUITY_DSH_PACKAGE=str(anchor),
                   CONTINUITY_TEST_NODE=node, CONTINUITY_TEST_PYTHON=sys.executable,
                   CONTINUITY_CI_SCRATCH=scratch)
        suites = [(file, 'node', [node, '--test', '--test-reporter=tap', str(ROOT / file)])
                  for file in plan['harness_node']]
        suites += [(file, 'python', [sys.executable, '-B', '-m', 'unittest', 'discover',
                                    '-s', str(ROOT / 'tests'), '-p', Path(file).name, '-v'])
                   for file in plan['harness_py']]
        for file, format, command in suites:
            started = time.monotonic()
            entry = {'file': file, 'format': format,
                     'source_sha256': hashlib.sha256((ROOT / file).read_bytes()).hexdigest()}
            # Interrupt the Python test itself first, so its finally block can
            # safely stop independently sessioned launchers/hosts.
            process = subprocess.Popen(['/usr/bin/sandbox-exec', '-p', NETWORK_POLICY, *command],
                                       cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                stdout, stderr = process.communicate(timeout=host_timeout if format == 'python' else 60)
                entry.update(check_result(stdout if format == 'node' else stderr,
                                          format, process.returncode), exit_code=process.returncode)
            except subprocess.TimeoutExpired:
                if process.poll() is None:
                    process.send_signal(signal.SIGINT)
                try:
                    process.communicate(timeout=40)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    try:
                        process.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.stdout.close()
                        process.stderr.close()
                entry.update(accepted=False, reason='SUITE_TIMEOUT', exit_code=None,
                             child_cleanup_verified=False)
            entry['seconds'] = round(time.monotonic() - started, 3)
            report['suites'].append(entry)
            if not entry['accepted']:
                report['reason'] = 'REQUIRED_SUITE_FAILED'
                return
    finally:
        cleanup_verified = reconcile_hosts(scratch, env)
        report['managed_home_cleanup_verified'] = cleanup_verified
        if cleanup_verified:
            shutil.rmtree(scratch)
        else:
            report.update(reason='MANAGED_HOME_CLEANUP_UNVERIFIED', retained_scratch_id=Path(scratch).name)
    if not cleanup_verified:
        return
    report.update(state='passed', reason='OK', host_verified=True,
                  real_model_quality_verified=False, ui_verified=False)


def check_result(text, format, return_code):
    counts = {}
    if format == 'node':
        for name in ('tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo'):
            values = re.findall(r'^# ' + name + r' (\d+)$', text, re.M)
            if len(values) == 1:
                counts[name] = int(values[0])
        accepted = (len(counts) == 6 and counts['tests'] > 0
                    and counts['pass'] == counts['tests']
                    and not any(counts[k] for k in ('fail', 'cancelled', 'skipped', 'todo')))
    else:
        totals = re.findall(r'^Ran (\d+) tests? in [0-9.]+s$', text, re.M)
        endings = re.findall(r'^(OK|FAILED)(?: \(([^\n]*)\))?\s*$', text, re.M)
        if len(totals) == 1:
            counts['tests'] = int(totals[0])
        accepted = (counts.get('tests', 0) > 0 and len(endings) == 1
                    and endings[0] == ('OK', '')
                    and not re.search(r'^(FAIL|ERROR):|\.\.\. skipped ', text, re.M))
    accepted = bool(accepted and return_code == 0)
    return {'accepted': accepted, 'counts': counts,
            'reason': 'OK' if accepted else 'INCOMPLETE_TEST_COVERAGE'}


def main():
    if sys.argv[1:2] == ['check-result']:
        checker = argparse.ArgumentParser()
        checker.add_argument('--format', choices=('node', 'python'), required=True)
        checker.add_argument('--return-code', type=int, required=True)
        args = checker.parse_args(sys.argv[2:])
        report = check_result(sys.stdin.read(4 * 1024 * 1024), args.format, args.return_code)
        print(json.dumps(report))
        return 0 if report['accepted'] else 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk-package')
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--host-timeout-seconds', type=int, default=180,
                        help='Bound a host suite to 1..180 seconds; timeout always fails')
    args = parser.parse_args()
    report = {'format': 'recaloom-harness-ci-v1', 'state': 'failed',
              'reason': 'SDK_REQUIRED' if not args.sdk_package else 'NOT_VALIDATED',
              'suites': [], 'host_verified': False, 'publication_authorized': False}
    if not 1 <= args.host_timeout_seconds <= 180:
        report['reason'] = 'INVALID_HOST_TIMEOUT'
        print(json.dumps(report))
        return 1
    if args.sdk_package:
        try:
            anchor = Path(args.sdk_package).resolve(strict=True)
            if anchor.name != 'package.json' or anchor.parent.name != 'dsh':
                raise ValueError('Wrong SDK anchor')
            scope = anchor.parent.parent
            for name, version in PEERS.items():
                info = json.loads((scope / name / 'package.json').read_text(encoding='utf-8'))
                if (not isinstance(info, dict) or info.get('name') != '@deepseek-ai/' + name
                        or info.get('version') != version):
                    raise ValueError('Unsupported SDK')
        except (OSError, ValueError, TypeError, KeyError, RecursionError):
            report['reason'] = 'SDK_INVALID'
        else:
            try:
                run_required(report, anchor, args.node, args.host_timeout_seconds)
            except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError) as exc:
                report.update(reason='CI_INFRASTRUCTURE_ERROR', error_type=type(exc).__name__)
    print(json.dumps(report))
    return 0 if report['state'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
