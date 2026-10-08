"""Public hook process -> real core -> recovery, without a real Claude host."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_authorized_save as base

HOOK = Path(__file__).resolve().parents[1] / 'scripts/claude_save_hook.py'
CORE = HOOK.with_name('continuity.py')


class ClaudeSaveHook(unittest.TestCase):
    setUp = base.AuthorizedSave.setUp
    command = base.AuthorizedSave.command
    call = base.AuthorizedSave.call
    write = base.AuthorizedSave.write
    enable = base.AuthorizedSave.enable
    prepare = base.AuthorizedSave.prepare
    tree = base.AuthorizedSave.tree

    def hook_command(self, generation):
        return [sys.executable, '-I', '-B', str(HOOK), '--project', str(self.root),
                '--expect-project-id', self.identity, '--session-id', 'session-a',
                '--generation', generation, '--program-sha256', hashlib.sha256(CORE.read_bytes()).hexdigest()]

    def hook(self, generation, event='Stop', *, code=None, **extra):
        payload = dict(session_id='session-a', cwd=str(self.root), hook_event_name=event,
                       transcript_path='/must/not/read/private.jsonl', last_assistant_message='NOT A DRAFT')
        payload.update(extra)
        result = subprocess.run(self.hook_command(generation), input=json.dumps(payload),
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1 if code else 0, result.stdout+result.stderr)
        if code:
            self.assertIn(code, result.stderr)
        self.assertNotIn('NOT A DRAFT', result.stdout+result.stderr)
        return result

    def test_stop_saves_prepared_draft_once_and_a_new_process_recovers_it(self):
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Review the summary with the owner'
        self.write()
        self.prepare(generation, event='milestone-1')
        result = self.hook(generation)
        self.assertIn('revision 2', json.loads(result.stdout)['systemMessage'])
        before = self.tree()
        self.assertEqual(self.hook(generation, 'PreCompact').stdout, '')
        self.assertEqual(self.tree(), before)
        restored = self.call('resume')
        self.assertEqual(restored['revision'], 2)
        self.assertIn('Review the summary with the owner', restored['text'])
        self.assertEqual(restored['check']['state'], 'references_current')

    def test_exit_revokes_without_saving_and_late_event_cannot_write(self):
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Unsaved proposal'
        self.write()
        candidate = self.prepare(generation)['candidate_id']
        self.hook(generation, 'SessionEnd')
        before = self.tree()
        self.hook(generation, code='SAVE_NOT_AUTHORIZED')
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.call('status')['revision'], 1)
        shown = self.call('save', 'show', '--session-id', 'session-a', '--generation', generation,
                          '--candidate-id', candidate, '--expect-project-id', self.identity)
        self.assertEqual(shown['state'], 'prepared')

    def test_old_generation_exit_does_not_revoke_replacement(self):
        old = self.enable()['generation']
        current = self.enable(old)['generation']
        before = self.tree()
        self.hook(old, 'SessionEnd', code='SAVE_GENERATION_CHANGED')
        self.assertEqual(self.tree(), before)
        self.draft['next_action'] = 'New generation progress'
        self.write()
        self.prepare(current)
        self.hook(current)
        self.assertEqual(self.call('status')['revision'], 2)

    def test_wrong_session_project_event_and_program_do_not_mutate(self):
        generation = self.enable()['generation']
        self.prepare(generation)
        before = self.tree()
        self.hook(generation, session_id='session-b', code='HOOK_SESSION_MISMATCH')
        self.hook(generation, cwd=str(self.root.parent), code='HOOK_PROJECT_MISMATCH')
        self.hook(generation, 'SessionStart', code='HOOK_EVENT_UNSUPPORTED')
        argv = self.hook_command(generation)
        argv[-1] = '0' * 64
        result = subprocess.run(argv, input='{}', capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1)
        self.assertIn('HOOK_PROGRAM_MISMATCH', result.stderr)
        self.assertEqual(self.tree(), before)

    def test_ambiguous_pending_is_not_arbitrarily_selected(self):
        generation = self.enable()['generation']
        self.prepare(generation, event='first')
        self.draft['next_action'] = 'A competing proposal'
        self.write()
        self.prepare(generation, event='second')
        before = self.tree()
        self.hook(generation, code='HOOK_AMBIGUOUS_PENDING')
        self.assertEqual(self.tree(), before)

    def test_changed_reference_is_visible_and_retains_pending_candidate(self):
        generation = self.enable()['generation']
        candidate = self.prepare(generation)['candidate_id']
        (self.root / 'brief.txt').write_text('Changed after preparation', encoding='utf-8')
        before = self.tree()
        self.hook(generation, code='EVIDENCE_CHANGED')
        self.assertEqual(self.tree(), before)
        state = self.call('save-policy', 'status', '--session-id', 'session-a', '--expect-project-id', self.identity)
        self.assertEqual(state['pending'][0]['candidate_id'], candidate)

    def test_concurrent_stop_and_compact_commit_a_single_prepared_operation(self):
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Review parallel save'
        self.write()
        self.prepare(generation)
        jobs = []
        for event in ['Stop', 'PreCompact', 'Stop', 'PreCompact']:
            process = subprocess.Popen(self.hook_command(generation), stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            process.stdin.write(json.dumps(dict(session_id='session-a', cwd=str(self.root), hook_event_name=event)))
            process.stdin.close()
            process.stdin = None
            jobs.append(process)
        for process in jobs:
            out, err = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, out+err)
        self.assertEqual(self.call('status')['revision'], 2)

    def test_bounded_malformed_event_and_no_prepared_work_do_not_change_project(self):
        generation = self.enable()['generation']
        before = self.tree()
        self.assertEqual(self.hook(generation).stdout, '')
        for raw, code in [('[]', 'HOOK_INVALID_INPUT'), ('{"cwd":1,"cwd":2}', 'HOOK_INVALID_INPUT'),
                          ('x' * (256 * 1024 + 1), 'HOOK_INPUT_TOO_LARGE')]:
            result = subprocess.run(self.hook_command(generation), input=raw, text=True,
                                    capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 1)
            self.assertIn(code, result.stderr)
        self.assertEqual(self.tree(), before)

    def test_missing_hook_argument_is_nonblocking_and_does_not_echo_values(self):
        generation = self.enable()['generation']
        before = self.tree()
        result = subprocess.run(self.hook_command(generation)[:-2], input='{}', text=True,
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('HOOK_ARGUMENT_INVALID', result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertEqual(self.tree(), before)

    def test_idle_lifecycle_events_and_recovery_do_not_accumulate_receipts(self):
        generation = self.enable()['generation']
        before = self.tree()
        for _ in range(8):
            self.assertEqual(self.hook(generation, 'Stop').stdout, '')
            self.assertEqual(self.hook(generation, 'PreCompact').stdout, '')
            restored = self.call('resume')
            self.assertEqual(restored['revision'], 1)
            self.assertIn('No publication', restored['text'])
            template = self.call('save', 'template', '--expect-project-id', self.identity,
                                 '--expect-revision', '1', '--max-chars', '32000')
            self.assertEqual(template['draft'], self.draft)
        state = self.call('save-policy', 'status', '--session-id', 'session-a',
                          '--expect-project-id', self.identity)
        self.assertEqual(state['pending'], [])
        self.assertEqual(self.tree(), before)

    def test_settings_preview_is_read_only_and_uses_fixed_explicit_scope(self):
        generation = self.enable()['generation']
        before = self.tree()
        result = subprocess.run(self.hook_command(generation) + ['--print-settings'],
                                capture_output=True, text=True, timeout=15)
        if sys.platform == 'win32':
            self.assertEqual(result.returncode, 1)
            self.assertIn('HOOK_SETTINGS_PLATFORM_UNVERIFIED', result.stderr)
            self.assertEqual(self.tree(), before)
            return
        self.assertEqual(result.returncode, 0, result.stderr)
        settings = json.loads(result.stdout)
        self.assertEqual(set(settings['hooks']), {'Stop', 'PreCompact', 'SessionEnd'})
        import shlex
        for event, handlers in settings['hooks'].items():
            self.assertEqual(shlex.split(handlers[0]['hooks'][0]['command']), self.hook_command(generation))
            self.assertNotIn('async', handlers[0]['hooks'][0])
        self.assertEqual(self.tree(), before)


if __name__ == '__main__':
    unittest.main()
