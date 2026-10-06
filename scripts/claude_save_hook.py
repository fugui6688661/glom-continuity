"""Opt-in Claude event adapter; the sibling core remains the sole save authority."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

MAX_EVENT = 256 * 1024
EVENTS = ('Stop', 'PreCompact', 'SessionEnd')


class HookError(Exception):
    pass


class HookParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's usual exit 2 means "block" to Claude hooks. Configuration
        # mistakes must not force a continuation or echo arbitrary arguments.
        self.exit(1, 'Recaloom hook configuration invalid (HOOK_ARGUMENT_INVALID). Check the generated session settings.\n')


def parse_event(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate field')
            result[key] = value
        return result
    if len(raw) > MAX_EVENT:
        raise HookError('HOOK_INPUT_TOO_LARGE')
    try:
        event = json.loads(raw, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise HookError('HOOK_INVALID_INPUT') from None
    if not isinstance(event, dict):
        raise HookError('HOOK_INVALID_INPUT')
    return event


def main():
    parser = HookParser(description=__doc__)
    for field in ('project', 'expect-project-id', 'session-id', 'generation', 'program-sha256'):
        parser.add_argument('--' + field, required=True)
    parser.add_argument('--print-settings', action='store_true', help='Preview session-scoped hooks; writes no configuration')
    args = parser.parse_args()
    try:
        core = Path(__file__).resolve().with_name('continuity.py')
        if not re.fullmatch('[0-9a-f]{64}', args.program_sha256) or hashlib.sha256(core.read_bytes()).hexdigest() != args.program_sha256:
            raise HookError('HOOK_PROGRAM_MISMATCH')
        root = Path(args.project)
        if not root.is_absolute() or not root.is_dir():
            raise HookError('HOOK_PROJECT_MISMATCH')
        for value in (args.expect_project_id, args.session_id, args.generation):
            if not re.fullmatch('[A-Za-z0-9_.:-]{1,80}', value):
                raise HookError('HOOK_INVALID_BINDING')
        if args.print_settings:
            if sys.platform == 'win32':
                raise HookError('HOOK_SETTINGS_PLATFORM_UNVERIFIED')
            argv = [sys.executable, '-I', '-B', str(Path(__file__).resolve()), '--project', str(root),
                    '--expect-project-id', args.expect_project_id, '--session-id', args.session_id,
                    '--generation', args.generation, '--program-sha256', args.program_sha256]
            print(json.dumps({'hooks': {name: [{'hooks': [{'type': 'command', 'command': shlex.join(argv),
                                'timeout': 10 if name != 'SessionEnd' else 1}]}] for name in EVENTS}}))
            return 0
        event = parse_event(sys.stdin.buffer.read(MAX_EVENT + 1))
        if event.get('session_id') != args.session_id:
            raise HookError('HOOK_SESSION_MISMATCH')
        cwd = event.get('cwd')
        if not isinstance(cwd, str) or not Path(cwd).is_absolute() or Path(cwd).resolve(strict=True) != root.resolve(strict=True):
            raise HookError('HOOK_PROJECT_MISMATCH')
        name = event.get('hook_event_name')
        if name not in EVENTS:
            raise HookError('HOOK_EVENT_UNSUPPORTED')
        # Only a deadline for these owned CLI children. Input delivery and the
        # host's own hook deadline remain outside this process's guarantee.
        deadline = time.monotonic() + (0.7 if name == 'SessionEnd' else 8)

        def call(*command):
            timeout = deadline - time.monotonic()
            if timeout <= 0:
                raise HookError('HOOK_TIMEOUT_OUTCOME_UNKNOWN')
            try:
                result = subprocess.run([sys.executable, '-I', '-B', str(core), '--project', str(root), *command,
                    '--expect-project-id', args.expect_project_id, '--session-id', args.session_id],
                    capture_output=True, timeout=timeout)
            except subprocess.TimeoutExpired:
                raise HookError('HOOK_TIMEOUT_OUTCOME_UNKNOWN') from None
            try:
                response = json.loads(result.stdout)
            except (ValueError, UnicodeError):
                raise HookError('HOOK_CORE_RESPONSE_INVALID') from None
            if not isinstance(response, dict):
                raise HookError('HOOK_CORE_RESPONSE_INVALID')
            if result.returncode or response.get('ok') is not True or response.get('code') != 'OK':
                code = response.get('code', '')
                raise HookError(code if isinstance(code, str) and re.fullmatch('[A-Z_]{1,80}', code)
                                else 'HOOK_CORE_RESPONSE_INVALID')
            return response['data']

        if name == 'SessionEnd':
            call('save-policy', 'revoke', '--generation', args.generation)
            print(json.dumps({'systemMessage': 'Recaloom: session save permission revoked; existing progress retained.'}))
            return 0
        state = call('save-policy', 'status')
        policy = state.get('policy')
        if not policy or policy['generation'] != args.generation:
            raise HookError('SAVE_GENERATION_CHANGED')
        if not state['effective']:
            raise HookError('SAVE_NOT_AUTHORIZED')
        pending = [item for item in state['pending'] if item['generation'] == args.generation]
        if len(pending) > 1:
            raise HookError('HOOK_AMBIGUOUS_PENDING')
        if not pending:
            return 0
        # The operation identity and immutable snapshot already exist in core.
        # Never derive a new draft/operation from response text or event timing.
        saved = call('save', 'commit', '--generation', args.generation, '--candidate-id', pending[0]['candidate_id'])
        if saved['state'] not in ('saved', 'unchanged'):
            raise HookError('HOOK_CORE_RESPONSE_INVALID')
        print(json.dumps({'systemMessage': f"Recaloom: prepared progress {saved['state']} (revision {saved['revision']}); task completion not assessed."}))
        return 0
    except HookError as exc:
        # Exit 1 is a non-blocking hook failure. Never use exit 2 to force model
        # continuation, or echo host input, transcript paths or private drafts.
        print(f'Recaloom save not confirmed ({exc}). Inspect save-policy status and the candidate before retrying.', file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError):
        print('Recaloom save not confirmed (HOOK_LOCAL_ERROR). Inspect the policy and candidate; no automatic retry.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
