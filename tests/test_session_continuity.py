"""Cooperative user journeys across public CLI processes, not native host claims."""
import json
from pathlib import Path
import subprocess
import sys
import unittest

import test_authorized_save as base
import test_claude_save_hook as hook_base

RECOVERY = Path(__file__).resolve().parents[1] / 'scripts/recovery.py'


class SessionContinuity(unittest.TestCase):
    setUp = base.AuthorizedSave.setUp
    command = base.AuthorizedSave.command
    call = base.AuthorizedSave.call
    write = base.AuthorizedSave.write
    enable = base.AuthorizedSave.enable
    prepare = base.AuthorizedSave.prepare
    commit = base.AuthorizedSave.commit
    tree = base.AuthorizedSave.tree
    hook_command = hook_base.ClaudeSaveHook.hook_command
    hook = hook_base.ClaudeSaveHook.hook

    def recover(self, action, payload=None, *, epoch='view-1', session='window-a', code='OK'):
        if payload is None:
            payload = dict(event='resume', cwd=str(self.root), session_id=session,
                           generation=epoch, query='')
        run = subprocess.run([sys.executable, '-B', str(RECOVERY), '--project', str(self.root),
                              '--project-id', self.identity, '--session-id', session,
                              '--generation', epoch, '--max-chars', '16000', action],
                             input=json.dumps(payload), text=True, capture_output=True, timeout=15)
        self.assertEqual(run.returncode, 0 if code == 'OK' else 2, run.stdout + run.stderr)
        envelope = json.loads(run.stdout)
        self.assertEqual(envelope['code'], code, envelope)
        if code != 'OK':
            self.assertIsNone(envelope['data'])
        return envelope['data']

    def test_second_assistant_return_survives_first_windows_late_save_and_recovery(self):
        generation = self.enable()['generation']
        self.draft['decisions'].append('Use one-page text, no generated illustrations')
        self.draft['next_action'] = 'Ask a reviewer to inspect the outline'
        self.write()
        saved = self.commit(generation, self.prepare(generation)['candidate_id'])
        self.assertEqual(saved['revision'], 2)
        offer = self.call('handoff', '--recipient', 'reviewer', '--expect-revision', '2')['handoff_id']
        # Window A queues work, but has not committed it when B takes over.
        receipt = self.recover('prepare')['receipt']
        self.draft['next_action'] = 'OUTDATED: finish the outline without the review'
        self.write()
        late = self.prepare(generation, event='a-late', revision='2')['candidate_id']
        view_b = self.recover('deliver', self.recover('prepare', session='window-b')['receipt'], session='window-b')
        self.assertEqual(view_b['context']['pending_handoffs'][0]['id'], offer)
        self.assertIn('No publication', view_b['context']['text'])
        self.call('accept', '--id', offer, '--recipient', 'reviewer')
        template = self.call('save', 'template', '--expect-project-id', self.identity,
                             '--expect-revision', '2', '--max-chars', '32000')['draft']
        self.assertEqual(template['decisions'], ['Use one-page text, no generated illustrations'])
        self.assertEqual(template['unresolved'], ['Reviewer unknown'])
        (self.root / 'review.md').write_text('Outline reviewed; publication remains forbidden.', encoding='utf-8')
        self.draft = template
        self.draft['evidence'].append({'path': 'review.md', 'role': 'artifact'})
        self.draft['next_action'] = 'Read the reviewer artifact before accepting the work'
        self.write()
        returned = self.call('return-work', '--id', offer, '--recipient', 'reviewer',
                             '--from-file', str(self.root / 'draft.json'), '--expect-revision', '2')
        self.assertEqual(returned['revision'], 3)
        before = self.tree()
        self.commit(generation, late, code='REVISION_CONFLICT')
        self.recover('deliver', receipt, code='STALE_RECOVERY')
        self.assertEqual(self.tree(), before)
        resumed = self.call('resume', '--expect-project-id', self.identity, '--max-chars', '16000')
        self.assertEqual(resumed['revision'], 3)
        self.assertEqual(resumed['result']['handoff_id'], offer)
        self.assertFalse(resumed['result']['semantic_completion_verified'])
        self.assertIn('Reviewer unknown', resumed['text'])
        self.assertNotIn('OUTDATED:', resumed['text'])
        # B continues from the returned checkpoint, preserving its input chain.
        self.draft = self.call('save', 'template', '--expect-project-id', self.identity,
                               '--expect-revision', '3', '--max-chars', '32000')['draft']
        self.draft['decisions'].append('Reviewer artifact read; publication still not authorized')
        self.write()
        policy_b = self.call('save-policy', 'enable', '--expect-project-id', self.identity,
                             '--session-id', 'session-b', '--expect-generation', 'none',
                             '--expect-revision', '3', '--draft-path', 'draft.json', '--ttl-seconds', '3600')
        bound = ['--expect-project-id', self.identity, '--session-id', 'session-b', '--generation', policy_b['generation']]
        candidate_b = self.call('save', 'prepare', *bound, '--expect-revision', '3', '--event-id', 'b-review')['candidate_id']
        self.assertEqual(self.call('save', 'commit', *bound, '--candidate-id', candidate_b)['revision'], 4)
        fresh = self.recover('deliver', self.recover('prepare', session='window-c')['receipt'], session='window-c')['context']
        self.assertEqual(fresh['revision'], 4)
        for required in ('No publication', 'Reviewer unknown', 'one-page text', 'Reviewer artifact read'):
            self.assertIn(required, fresh['text'])
        self.assertEqual(self.call('receipt', '--id', offer)['result']['revision'], 3)

    def test_pause_reenable_and_late_exit_cannot_restore_old_write_permission(self):
        old = self.enable()['generation']
        old_view = self.recover('prepare')['receipt']
        self.draft['next_action'] = 'OLD: unsaved work before pause'
        self.write()
        old_candidate = self.prepare(old)['candidate_id']
        self.call('save-policy', 'revoke', '--expect-project-id', self.identity,
                  '--session-id', 'session-a', '--generation', old)
        before = self.tree()
        self.hook(old, code='SAVE_NOT_AUTHORIZED')
        self.recover('deliver', old_view, epoch='view-2', code='TARGET_MISMATCH')
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.call('resume')['revision'], 1)
        current = self.enable(old)['generation']
        before = self.tree()
        self.hook(old, 'SessionEnd', code='SAVE_GENERATION_CHANGED')
        self.hook(old, code='SAVE_GENERATION_CHANGED')
        self.assertEqual(self.tree(), before)
        self.draft['next_action'] = 'NEW: review explicitly resumed work'
        self.write()
        candidate = self.prepare(current, event='resumed-work')['candidate_id']
        self.hook(current, 'PreCompact')
        before = self.tree()
        self.hook(current, 'Stop')  # a second event is not a second save
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.call('save', 'show', '--expect-project-id', self.identity,
                                   '--session-id', 'session-a', '--generation', old,
                                   '--candidate-id', old_candidate)['state'], 'prepared')
        self.assertEqual(self.call('save', 'show', '--expect-project-id', self.identity,
                                   '--session-id', 'session-a', '--generation', current,
                                   '--candidate-id', candidate)['state'], 'saved')
        fresh = self.recover('deliver', self.recover('prepare', epoch='view-2')['receipt'], epoch='view-2')['context']
        self.assertEqual(fresh['revision'], 2)
        self.assertIn('NEW: review explicitly resumed work', fresh['text'])
        self.assertNotIn('OLD:', fresh['text'])
        self.assertIn('Reviewer unknown', fresh['text'])
        self.assertEqual(self.call('save-policy', 'status', '--expect-project-id', self.identity,
                                   '--session-id', 'session-a')['policy']['generation'], current)


if __name__ == '__main__':
    unittest.main()
