"""Authorized progress through public CLI, not simulated host lifecycle events."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import sqlite3
import os
import shutil
from contextlib import closing, ExitStack
import tempfile
import time
import unittest

CLI = Path(__file__).resolve().parents[1] / 'scripts/continuity.py'

# Observe SQLite's public trace boundary without replacing its transactions.
# This does not model a torn write, a power failure, or physical disk exhaustion.
TRACE_COMMIT_WORKER = r'''
import runpy, sqlite3, sys
from pathlib import Path
marker = sys.argv.pop(1)
original_connect = sqlite3.connect
def connect(*args, **kwargs):
    db = original_connect(*args, **kwargs)
    def trace(statement):
        if statement.strip().upper() == 'COMMIT':
            if marker != '-':
                with Path(marker).open('x') as output:
                    output.write('SQLITE_COMMIT_ENTERED')
            print('SQLITE_COMMIT_ENTERED', file=sys.stderr, flush=True)
    db.set_trace_callback(trace)
    return db
sqlite3.connect = connect
sys.argv = sys.argv[1:]
runpy.run_path(sys.argv[0], run_name='__main__')
'''


class AuthorizedSave(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='recaloom-authorized-save-'))
        self.retain_fixture = False
        def cleanup():
            if self.retain_fixture:
                print('Unreaped owned process; fixture retained: ' + str(self.root), file=sys.stderr)
            else:
                shutil.rmtree(self.root)
        self.addCleanup(cleanup)
        self.identity = self.call('init', '--name', 'Synthetic project')['project_id']
        (self.root / 'brief.txt').write_text('Do not publish the synthetic result.', encoding='utf-8')
        self.draft = {'objective': 'Prepare a summary', 'next_action': 'Draft the summary',
                      'constraints': ['No publication'], 'decisions': [], 'unresolved': ['Reviewer unknown'],
                      'evidence': [{'path': 'brief.txt', 'role': 'input'}]}
        self.write()
        self.call('checkpoint', '--from-file', str(self.root / 'draft.json'), '--expect-revision', '0')

    def command(self, *args):
        return [sys.executable, '-B', str(CLI), '--project', str(self.root), *args]

    def call(self, *args, code='OK'):
        result = subprocess.run(self.command(*args), capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0 if code == 'OK' else 2, result.stdout + result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response['code'], code, response)
        return response['data']

    def write(self):
        (self.root / 'draft.json').write_text(json.dumps(self.draft), encoding='utf-8')

    def enable(self, previous='none', ttl='3600'):
        return self.call('save-policy', 'enable', '--session-id', 'session-a',
                         '--expect-generation', previous, '--draft-path', 'draft.json',
                         '--ttl-seconds', ttl, '--expect-revision', str(self.call('status')['revision']),
                         '--expect-project-id', self.identity)

    def prepare(self, generation, event='stop-1', revision='1', code='OK'):
        return self.call('save', 'prepare', '--session-id', 'session-a', '--generation', generation,
                         '--event-id', event, '--expect-revision', revision,
                         '--expect-project-id', self.identity, code=code)

    def commit(self, generation, candidate, code='OK'):
        return self.call('save', 'commit', '--session-id', 'session-a', '--generation', generation,
                         '--candidate-id', candidate, '--expect-project-id', self.identity, code=code)

    def tree(self):
        return {str(p.relative_to(self.root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.root.rglob('*') if p.is_file()}

    def test_prepared_progress_commits_once_and_recovers_through_existing_resume(self):
        policy = self.enable()
        self.assertFalse(policy['host_automation_verified'])
        generation = policy['generation']
        self.draft['next_action'] = 'Review the summary'
        self.draft['decisions'] = ['Use the selected brief']
        self.write()
        prepared = self.prepare(generation)
        self.assertEqual(prepared['state'], 'prepared')
        self.assertEqual(self.call('status')['revision'], 1)
        saved = self.commit(generation, prepared['candidate_id'])
        self.assertEqual((saved['state'], saved['revision'], saved['replayed']), ('saved', 2, False))
        self.assertFalse(saved['semantic_completion_verified'])
        before = self.tree()
        replay = self.commit(generation, prepared['candidate_id'])
        self.assertEqual((replay['revision'], replay['replayed']), (2, True))
        self.assertEqual(self.tree(), before)
        again = self.prepare(generation)
        self.assertEqual(again['candidate_id'], prepared['candidate_id'])
        self.assertEqual(self.call('status')['revision'], 2)
        restored = self.call('resume', '--expect-project-id', self.identity)
        self.assertIn('Review the summary', restored['text'])
        self.assertEqual(restored['check']['state'], 'references_current')

    def test_revoke_fences_pending_commit_and_old_generation_cannot_revive(self):
        generation = self.enable()['generation']
        candidate = self.prepare(generation)['candidate_id']
        self.call('save-policy', 'revoke', '--session-id', 'session-a', '--generation', generation,
                  '--expect-project-id', self.identity)
        before = self.tree()
        self.commit(generation, candidate, code='SAVE_NOT_AUTHORIZED')
        self.assertEqual(self.tree(), before)
        replacement = self.enable(generation)['generation']
        self.assertNotEqual(replacement, generation)
        self.commit(generation, candidate, code='SAVE_GENERATION_CHANGED')
        self.commit(replacement, candidate, code='SAVE_CANDIDATE_NOT_FOUND')
        self.assertEqual(self.call('status')['revision'], 1)

    def test_unchanged_content_does_not_create_a_revision_and_expiry_blocks_replay(self):
        generation = self.enable(ttl='2')['generation']
        candidate = self.prepare(generation)['candidate_id']
        result = self.commit(generation, candidate)
        self.assertEqual((result['state'], result['revision']), ('unchanged', 1))
        time.sleep(2.05)
        before = self.tree()
        self.commit(generation, candidate, code='SAVE_EXPIRED')
        self.assertEqual(self.tree(), before)

    def test_event_reuse_with_changed_content_is_rejected_and_candidate_is_immutable(self):
        generation = self.enable()['generation']
        candidate = self.prepare(generation)['candidate_id']
        self.draft['next_action'] = 'Different proposed action'
        self.write()
        before = self.tree()
        self.prepare(generation, code='SAVE_EVENT_CONFLICT')
        self.assertEqual(self.tree(), before)
        result = self.commit(generation, candidate)
        self.assertEqual(result['state'], 'unchanged')
        self.assertIn('Draft the summary', self.call('resume')['text'])

    def test_changed_reference_and_removed_constraints_require_explicit_review(self):
        generation = self.enable()['generation']
        candidate = self.prepare(generation)['candidate_id']
        (self.root / 'brief.txt').write_text('Changed input', encoding='utf-8')
        before = self.tree()
        self.commit(generation, candidate, code='EVIDENCE_CHANGED')
        self.assertEqual(self.tree(), before)
        self.prepare(generation, event='new-event', code='SAVE_REVIEW_REQUIRED')
        (self.root / 'brief.txt').write_text('Do not publish the synthetic result.', encoding='utf-8')
        self.draft['constraints'] = []
        self.write()
        self.prepare(generation, event='new-event', code='SAVE_REVIEW_REQUIRED')
        self.assertEqual(self.call('status')['revision'], 1)

    def test_unconfirmed_habit_is_stored_as_candidate_not_recalled_as_active(self):
        generation = self.enable()['generation']
        memory = {'format': 'continuity-memory-v1', 'items': [
            {'id': 'style', 'kind': 'preference', 'title': 'Possible preference',
             'body': 'Might prefer short answers', 'when': ['*'], 'status': 'active',
             'source': 'Inferred from a synthetic task', 'expires_at': None}]}
        path = self.root / 'habits.json'
        path.write_text(json.dumps(memory), encoding='utf-8')
        self.draft['evidence'].append({'path': 'habits.json', 'role': 'memory'})
        self.write()
        self.prepare(generation, code='SAVE_REVIEW_REQUIRED')
        memory['items'][0]['status'] = 'candidate'
        path.write_text(json.dumps(memory), encoding='utf-8')
        candidate = self.prepare(generation)['candidate_id']
        self.commit(generation, candidate)
        recalled = self.call('resume')['memory']
        self.assertEqual(recalled['selected'], [])
        self.assertEqual(recalled['omitted'][0]['reason'], 'candidate')

    def test_concurrent_callbacks_share_one_candidate_and_one_checkpoint(self):
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Review concurrent result'
        self.write()
        args = ['save', 'prepare', '--session-id', 'session-a', '--generation', generation,
                '--event-id', 'parallel', '--expect-revision', '1', '--expect-project-id', self.identity]
        processes = [subprocess.Popen(self.command(*args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True) for _ in range(4)]
        prepared = []
        for process in processes:
            output, error = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, output + error)
            prepared.append(json.loads(output)['data'])
        self.assertEqual(len({p['candidate_id'] for p in prepared}), 1)
        args = ['save', 'commit', '--session-id', 'session-a', '--generation', generation,
                '--candidate-id', prepared[0]['candidate_id'], '--expect-project-id', self.identity]
        processes = [subprocess.Popen(self.command(*args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      text=True) for _ in range(4)]
        saved = []
        for process in processes:
            output, error = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, output + error)
            saved.append(json.loads(output)['data'])
        self.assertEqual(sum(not p['replayed'] for p in saved), 1)
        self.assertEqual(self.call('status')['revision'], 2)

    def test_stale_candidate_cannot_overwrite_another_writer(self):
        generation = self.enable()['generation']
        candidate = self.prepare(generation)['candidate_id']
        self.draft['next_action'] = 'Manually reviewed later state'
        self.write()
        self.call('checkpoint', '--from-file', str(self.root / 'draft.json'), '--expect-revision', '1')
        before = self.tree()
        self.commit(generation, candidate, code='REVISION_CONFLICT')
        self.assertEqual(self.tree(), before)

    def test_pending_work_can_be_inspected_after_revocation_and_explicitly_discarded(self):
        generation = self.enable()['generation']
        candidate = self.prepare(generation)['candidate_id']
        args = ['--session-id', 'session-a', '--generation', generation,
                '--candidate-id', candidate, '--expect-project-id', self.identity]
        self.call('save-policy', 'revoke', '--session-id', 'session-a', '--generation', generation,
                  '--expect-project-id', self.identity)
        before = self.tree()
        pending = self.call('save-policy', 'status', '--session-id', 'session-a',
                            '--expect-project-id', self.identity)['pending']
        self.assertEqual([p['candidate_id'] for p in pending], [candidate])
        shown = self.call('save', 'show', *args)
        self.assertTrue(shown['read_only'])
        self.assertEqual(shown['payload']['objective'], self.draft['objective'])
        self.assertEqual(self.tree(), before)
        discarded = self.call('save', 'discard', *args)
        self.assertEqual(discarded['state'], 'discarded')
        self.assertEqual(self.call('status')['revision'], 1)

    def test_automatic_progress_must_not_drop_inherited_handoff_references(self):
        handoff = self.call('handoff', '--recipient', 'worker', '--expect-revision', '1')['handoff_id']
        self.call('accept', '--id', handoff, '--recipient', 'worker')
        (self.root / 'result.md').write_text('Synthetic reviewed result', encoding='utf-8')
        self.draft['evidence'] = [{'path': 'result.md', 'role': 'artifact'}]
        self.write()
        self.call('return-work', '--id', handoff, '--recipient', 'worker',
                  '--from-file', str(self.root / 'draft.json'), '--expect-revision', '1')
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Follow up after result'
        self.write()
        before = self.tree()
        self.prepare(generation, revision='2', code='SAVE_REVIEW_REQUIRED')
        self.assertEqual(self.tree(), before)
        self.draft['evidence'].append({'path': 'brief.txt', 'role': 'input'})
        self.write()
        candidate = self.prepare(generation, revision='2')['candidate_id']
        self.commit(generation, candidate)
        (self.root / 'brief.txt').write_text('Changed after automatic progress', encoding='utf-8')
        self.assertEqual(self.call('resume')['check']['state'], 'needs_review')

    def test_wrong_project_identity_and_wrong_session_cannot_write(self):
        generation = self.enable()['generation']
        candidate = self.prepare(generation)['candidate_id']
        before = self.tree()
        self.call('save', 'commit', '--session-id', 'session-a', '--generation', generation,
                  '--candidate-id', candidate, '--expect-project-id', 'not-the-bound-project', code='PROJECT_MISMATCH')
        self.call('save', 'commit', '--session-id', 'session-b', '--generation', generation,
                  '--candidate-id', candidate, '--expect-project-id', self.identity, code='SAVE_NOT_AUTHORIZED')
        self.assertEqual(self.tree(), before)

    def test_discard_blocks_future_commit_and_does_not_remove_already_saved_work(self):
        generation = self.enable()['generation']
        candidate = self.prepare(generation)['candidate_id']
        args = ['--session-id', 'session-a', '--generation', generation,
                '--candidate-id', candidate, '--expect-project-id', self.identity]
        self.call('save', 'discard', *args)
        before = self.tree()
        self.commit(generation, candidate, code='SAVE_DISCARDED')
        self.assertEqual(self.tree(), before)
        candidate = self.prepare(generation, event='second-event')['candidate_id']
        self.commit(generation, candidate)
        self.call('save', 'discard', '--session-id', 'session-a', '--generation', generation,
                  '--candidate-id', candidate, '--expect-project-id', self.identity, code='SAVE_ALREADY_COMMITTED')

    def test_lost_reply_is_inspectable_and_does_not_repeat_the_save(self):
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Review persisted progress'
        self.write()
        candidate = self.prepare(generation)['candidate_id']
        args = ['--session-id', 'session-a', '--generation', generation,
                '--candidate-id', candidate, '--expect-project-id', self.identity]
        # A real separate process commits while its caller does not retain stdout.
        # This models acknowledgment loss, not a process kill or power failure.
        result = subprocess.run(self.command('save', 'commit', *args), stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.tree()
        restored = self.call('save', 'show', *args)
        replay = self.commit(generation, candidate)
        self.assertEqual((restored['state'], replay['revision'], replay['replayed']), ('saved', 2, True))
        self.assertEqual(self.tree(), before)
        self.call('save-policy', 'revoke', '--session-id', 'session-a', '--generation', generation,
                  '--expect-project-id', self.identity)
        self.assertEqual(self.call('save', 'show', *args)['state'], 'saved')

    def test_unknown_policy_read_does_not_create_tables_or_implicitly_enable(self):
        before = self.tree()
        status = self.call('save-policy', 'status', '--session-id', 'session-a',
                           '--expect-project-id', self.identity)
        self.assertFalse(status['effective'])
        self.assertEqual(status['pending'], [])
        self.prepare('unapproved', code='SAVE_NOT_AUTHORIZED')
        self.assertEqual(self.tree(), before)

    def test_commit_busy_preserves_old_progress_and_explains_receipt_reconciliation(self):
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Review after the occupied database is released'
        self.write()
        candidate = self.prepare(generation)['candidate_id']
        scope = ['--session-id', 'session-a', '--generation', generation,
                 '--candidate-id', candidate, '--expect-project-id', self.identity]
        command = self.command('save', 'commit', *scope)
        # An external reader prevents COMMIT, not BEGIN IMMEDIATE. Only SQLite
        # schema is read to acquire that lock; outcomes use the public CLI.
        with closing(sqlite3.connect(self.root / '.continuity/state.sqlite3')) as reader:
            reader.execute('BEGIN')
            reader.execute('SELECT name FROM sqlite_schema').fetchall()
            try:
                failed = subprocess.run([sys.executable, '-I', '-B', '-c', TRACE_COMMIT_WORKER,
                                         '-', *command[2:]], capture_output=True, text=True, timeout=15)
            finally:
                reader.rollback()
        self.assertEqual(failed.returncode, 2, failed.stdout + failed.stderr)
        self.assertEqual(failed.stderr.strip(), 'SQLITE_COMMIT_ENTERED')
        response = json.loads(failed.stdout)
        self.assertEqual(response['code'], 'IO_ERROR', response)
        self.assertFalse(response['ok'])
        self.assertIsNone(response['data'])
        before = self.tree()
        self.assertEqual(self.call('save', 'show', *scope)['state'], 'prepared')
        restored = self.call('resume', '--expect-project-id', self.identity)
        self.assertEqual(restored['revision'], 1)
        self.assertIn('Recorded next step (not revalidated): Draft the summary', restored['text'])
        self.assertEqual(self.tree(), before)
        # The diagnostic must help a user without claiming an unobserved outcome
        # or directing a host to blindly repeat work after any local I/O error.
        self.assertIn('save show', response['error'])
        self.assertIn('same candidate', response['error'])
        self.assertIn('Do not automatically retry', response['error'])
        saved = self.commit(generation, candidate)
        self.assertEqual((saved['state'], saved['revision']), ('saved', 2))
        self.assertTrue(self.commit(generation, candidate)['replayed'])

    def test_terminated_commit_request_is_reconciled_without_losing_old_progress(self):
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Review after the interrupted save'
        self.write()
        candidate = self.prepare(generation)['candidate_id']
        scope = ['--session-id', 'session-a', '--generation', generation,
                 '--candidate-id', candidate, '--expect-project-id', self.identity]
        command = self.command('save', 'commit', *scope)
        # Retain by default on exceptional cleanup. ExitStack closes each owned
        # handle independently; marker polling needs no blocked reader thread.
        self.retain_fixture = True
        marker = self.root / 'commit-entered.txt'
        with ExitStack() as resources:
            reader = resources.enter_context(closing(sqlite3.connect(self.root / '.continuity/state.sqlite3')))
            reader.execute('BEGIN')
            reader.execute('SELECT name FROM sqlite_schema').fetchall()
            process = subprocess.Popen([sys.executable, '-I', '-B', '-c', TRACE_COMMIT_WORKER,
                                        str(marker), *command[2:]], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True)
            resources.callback(process.stdout.close)
            resources.callback(process.stderr.close)
            try:
                deadline = time.monotonic() + 10
                while not marker.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(.01)
                self.assertEqual(marker.read_text(), 'SQLITE_COMMIT_ENTERED')
                self.assertIsNone(process.poll(), 'Commit finished despite the external reader')
                # Terminate only our owned subprocess after SQLite reported
                # COMMIT entry. No page-write/flush timing is claimed.
                process.terminate()
                output, error = process.communicate(timeout=10)
                self.assertNotEqual(process.returncode, 0)
                self.assertEqual(output, '', output + error)
            finally:
                if process.poll() is None:
                    try:
                        process.terminate()
                        process.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate(timeout=2)
                self.assertIsNotNone(process.poll(), 'Owned child exit is unconfirmed')
        self.retain_fixture = False
        before = self.tree()
        self.assertEqual(self.call('save', 'show', *scope)['state'], 'prepared')
        restored = self.call('resume', '--expect-project-id', self.identity)
        self.assertEqual(restored['revision'], 1)
        self.assertIn('Recorded next step (not revalidated): Draft the summary', restored['text'])
        self.assertEqual(self.tree(), before)
        saved = self.commit(generation, candidate)
        self.assertEqual(saved['revision'], 2)
        self.assertTrue(self.commit(generation, candidate)['replayed'])

    def test_broken_receipt_pipe_does_not_mean_the_save_failed(self):
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Review after the reply channel disappeared'
        self.write()
        candidate = self.prepare(generation)['candidate_id']
        scope = ['--session-id', 'session-a', '--generation', generation,
                 '--candidate-id', candidate, '--expect-project-id', self.identity]
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        try:
            lost = subprocess.run(self.command('save', 'commit', *scope), stdout=write_fd,
                                  stderr=subprocess.PIPE, text=True, timeout=15)
        finally:
            os.close(write_fd)
        self.assertNotEqual(lost.returncode, 0, lost.stderr)
        diagnostic = json.loads(lost.stderr)
        self.assertEqual(diagnostic['code'], 'OUTPUT_UNAVAILABLE')
        self.assertFalse(diagnostic['ok'])
        self.assertIsNone(diagnostic['data'])
        self.assertIn('save show', diagnostic['error'])
        self.assertIn('same candidate', diagnostic['error'])
        self.assertIn('Do not automatically retry', diagnostic['error'])
        self.assertNotIn(str(self.root), lost.stderr)
        # Nonzero exit on a broken response pipe cannot be treated as rollback.
        before = self.tree()
        shown = self.call('save', 'show', *scope)
        self.assertEqual((shown['state'], shown['revision']), ('saved', 2))
        replayed = self.commit(generation, candidate)
        self.assertEqual((replayed['revision'], replayed['replayed']), (2, True))
        self.assertEqual(self.call('resume')['revision'], 2)
        self.assertEqual(self.tree(), before)
        self.call('save-policy', 'revoke', '--session-id', 'session-a', '--generation', generation,
                  '--expect-project-id', self.identity)
        self.assertEqual(self.call('save', 'show', *scope)['revision'], 2)
        self.commit(generation, candidate, code='SAVE_NOT_AUTHORIZED')

    def test_both_reply_channels_missing_still_allow_same_candidate_reconciliation(self):
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Review using a new working response channel'
        self.write()
        candidate = self.prepare(generation)['candidate_id']
        scope = ['--session-id', 'session-a', '--generation', generation,
                 '--candidate-id', candidate, '--expect-project-id', self.identity]
        read_fd, write_fd = os.pipe()
        os.close(read_fd)
        try:
            lost = subprocess.run(self.command('save', 'commit', *scope), stdout=write_fd,
                                  stderr=write_fd, timeout=15)
        finally:
            os.close(write_fd)
        self.assertEqual(lost.returncode, 2)
        before = self.tree()
        shown = self.call('save', 'show', *scope)
        self.assertEqual((shown['state'], shown['revision']), ('saved', 2))
        self.assertEqual(self.call('resume')['revision'], 2)
        self.assertTrue(self.commit(generation, candidate)['replayed'])
        self.assertEqual(self.tree(), before)

    def test_reviewed_retirement_fences_old_queue_handoff_and_restored_old_file(self):
        memory = {'format': 'continuity-memory-v1', 'items': [
            {'id': 'old-style', 'kind': 'preference', 'title': 'Old synthetic style',
             'body': 'Use the obsolete blue template', 'when': ['*'], 'status': 'active',
             'source': 'Synthetic owner instruction', 'expires_at': None}]}
        path = self.root / 'habits.json'
        original = json.dumps(memory).encode('utf-8')
        path.write_bytes(original)
        self.draft['evidence'].append({'path': 'habits.json', 'role': 'memory'})
        self.write()
        self.call('checkpoint', '--from-file', str(self.root / 'draft.json'), '--expect-revision', '1')
        generation = self.enable()['generation']
        self.draft['next_action'] = 'Queued before the owner changed the preference'
        self.write()
        candidate = self.prepare(generation, revision='2')['candidate_id']
        handoff = self.call('handoff', '--recipient', 'next-worker', '--expect-revision', '2')['handoff_id']
        memory['items'][0]['status'] = 'retired'
        retired = json.dumps(memory).encode('utf-8')
        path.write_bytes(retired)
        self.draft['next_action'] = 'Continue without the old style'
        self.write()
        self.call('checkpoint', '--from-file', str(self.root / 'draft.json'), '--expect-revision', '2')
        before = self.tree()
        recovered = self.call('resume')
        self.assertEqual(recovered['memory']['selected'], [])
        self.assertEqual(recovered['memory']['omitted'],
                         [{'path': 'habits.json', 'id': 'old-style', 'reason': 'retired'}])
        self.assertNotIn('Use the obsolete blue template', recovered['text'])
        self.commit(generation, candidate, code='EVIDENCE_CHANGED')
        self.call('accept', '--id', handoff, '--recipient', 'next-worker', code='STALE_HANDOFF')
        self.assertEqual(self.tree(), before)

        # A delayed file copy restores the old bytes, but not the reviewed revision.
        path.write_bytes(original)
        before = self.tree()
        self.commit(generation, candidate, code='REVISION_CONFLICT')
        recovered = self.call('resume')
        self.assertEqual(recovered['recovery_state'], 'needs_review')
        self.assertEqual(recovered['memory']['selected'], [])
        self.assertNotIn('Use the obsolete blue template', recovered['text'])
        self.assertEqual(self.tree(), before)
        path.write_bytes(retired)
        self.assertEqual(self.call('resume')['revision'], 3)
        self.assertEqual(self.call('resume')['memory']['selected'], [])

    def test_exact_inherited_confirmed_memory_is_not_a_new_inference(self):
        memory = {'format': 'continuity-memory-v1', 'items': [
            {'id': 'confirmed-style', 'kind': 'preference', 'title': 'Reviewed preference',
             'body': 'Use concise output', 'when': ['*'], 'status': 'active',
             'source': 'Explicitly reviewed in this synthetic project', 'expires_at': None}]}
        path = self.root / 'habits.json'
        path.write_text(json.dumps(memory), encoding='utf-8')
        self.draft['evidence'].append({'path': 'habits.json', 'role': 'memory'})
        self.write()
        self.call('checkpoint', '--from-file', str(self.root / 'draft.json'), '--expect-revision', '1')
        handoff = self.call('handoff', '--recipient', 'worker', '--expect-revision', '2')['handoff_id']
        self.call('accept', '--id', handoff, '--recipient', 'worker')
        (self.root / 'result.md').write_text('Synthetic artifact', encoding='utf-8')
        self.draft['evidence'] = [{'path': 'result.md', 'role': 'artifact'}]
        self.write()
        self.call('return-work', '--id', handoff, '--recipient', 'worker',
                  '--from-file', str(self.root / 'draft.json'), '--expect-revision', '2')
        generation = self.enable()['generation']
        self.draft['evidence'] += [{'path': 'brief.txt', 'role': 'input'}, {'path': 'habits.json', 'role': 'memory'}]
        self.write()
        candidate = self.prepare(generation, revision='3')['candidate_id']
        self.commit(generation, candidate)
        selected = self.call('resume')['memory']['selected']
        self.assertEqual([p['id'] for p in selected], ['confirmed-style'])
        # Same path and ID do not bless different content or an explicit retirement.
        memory['items'][0]['status'] = 'retired'
        path.write_text(json.dumps(memory), encoding='utf-8')
        self.prepare(generation, event='after-retirement', revision='4', code='SAVE_REVIEW_REQUIRED')
        self.assertEqual(self.call('resume')['memory']['selected'], [])


if __name__ == '__main__':
    unittest.main()
