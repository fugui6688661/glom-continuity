"""Review changes through the public read-only CLI, without a model."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Review(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='recaloom-review-')
        self.addCleanup(tmp.cleanup)
        self.project = Path(tmp.name)

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
                                 '--project', str(self.project), *args], capture_output=True,
                                encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def save(self):
        self.cli('init', '--name', 'XS changes')
        (self.project / 'brief.txt').write_text('ORIGINAL_SOURCE_DO_NOT_EXPORT', encoding='utf-8')
        (self.project / 'result.txt').write_text('UNCHANGED_RESULT_BODY', encoding='utf-8')
        self.draft = dict(objective='Review this plan', next_action='Confirm the changed requirements',
                          constraints=['Do not publish'], decisions=[], unresolved=['Budget unknown'],
                          evidence=[{'path': 'brief.txt', 'role': 'input'},
                                    {'path': 'result.txt', 'role': 'artifact'}])
        return self.checkpoint(0)

    def checkpoint(self, revision):
        path = self.project / 'draft.json'
        path.write_text(json.dumps(self.draft), encoding='utf-8')
        return self.cli('checkpoint', '--from-file', str(path), '--expect-revision', str(revision))['data']

    def test_changed_reference_and_unchanged_artifact_are_distinguished_without_rewriting_memory(self):
        saved = self.save()
        original = saved['checkpoint']['evidence'][0]
        (self.project / 'brief.txt').write_text('NEW_SOURCE_DO_NOT_EXPORT', encoding='utf-8')
        db = self.project / '.continuity' / 'state.sqlite3'
        before = db.read_bytes()
        data = self.cli('review', '--expect-project-id', saved['project_id'])['data']
        self.assertTrue(data['read_only'])
        self.assertEqual(data['revision'], 1)
        self.assertEqual(data['review_state'], 'needs_review')
        self.assertEqual(data['instruction_authority'], 'none')
        self.assertFalse(data['semantic_completion_verified'])
        self.assertEqual(data['impact_status'], 'not_inferred')
        changed, unchanged = data['references']
        self.assertEqual((changed['path'], changed['role'], changed['state']), ('brief.txt', 'input', 'changed'))
        self.assertEqual(changed['recorded']['sha256'], original['sha256'])
        self.assertEqual(changed['observed']['sha256'], hashlib.sha256(b'NEW_SOURCE_DO_NOT_EXPORT').hexdigest())
        self.assertEqual((unchanged['path'], unchanged['state']), ('result.txt', 'unchanged'))
        self.assertIn('review_changed_references', data['next_steps'])
        self.assertEqual(db.read_bytes(), before)
        self.assertEqual(self.cli('status')['data']['revision'], 1)
        for marker in ('ORIGINAL_SOURCE_DO_NOT_EXPORT', 'NEW_SOURCE_DO_NOT_EXPORT', 'UNCHANGED_RESULT_BODY'):
            self.assertNotIn(marker, json.dumps(data))

    def test_review_preserves_pending_handoff_and_reports_missing_reference(self):
        self.save()
        identifier = self.cli('handoff', '--recipient', 'reviewer-b', '--expect-revision', '1')['data']['handoff_id']
        (self.project / 'brief.txt').unlink()
        data = self.cli('review')['data']
        missing = data['references'][0]
        self.assertEqual(missing['state'], 'missing')
        self.assertEqual(missing['code'], 'MISSING_FILE')
        self.assertIsNone(missing['observed'])
        self.assertEqual(self.cli('receipt', '--id', identifier)['data']['state'], 'open')
        self.assertEqual(self.cli('accept', '--id', identifier, '--recipient', 'reviewer-b', ok=False)['code'], 'EVIDENCE_CHANGED')

    def test_review_includes_accepted_source_omitted_from_returned_draft(self):
        self.save()
        identifier = self.cli('handoff', '--recipient', 'b', '--expect-revision', '1')['data']['handoff_id']
        self.cli('accept', '--id', identifier, '--recipient', 'b')
        self.draft['evidence'] = [{'path': 'result.txt', 'role': 'artifact'}]
        path = self.project / 'return.json'
        path.write_text(json.dumps(self.draft), encoding='utf-8')
        self.cli('return-work', '--id', identifier, '--recipient', 'b', '--from-file', str(path), '--expect-revision', '1')
        (self.project / 'brief.txt').write_text('CHANGED_BASE', encoding='utf-8')
        data = self.cli('review')['data']
        self.assertEqual(data['revision'], 2)
        self.assertEqual(data['review_state'], 'needs_review')
        self.assertIn(('brief.txt', 1, 'changed'), [(r['path'], r['source_revision'], r['state']) for r in data['references']])
        self.assertIn(('result.txt', 2, 'unchanged'), [(r['path'], r['source_revision'], r['state']) for r in data['references']])

    def test_wrong_project_and_small_budget_return_no_partial_reference_information(self):
        self.save()
        for arguments, code in ((('--expect-project-id', 'another'), 'PROJECT_MISMATCH'),
                                (('--max-chars', '10'), 'BUDGET_TOO_SMALL')):
            with self.subTest(code=code):
                result = self.cli('review', *arguments, ok=False)
                self.assertEqual(result['code'], code)
                self.assertIsNone(result['data'])
                self.assertNotIn('brief.txt', json.dumps(result))

    def test_no_checkpoint_and_no_references_do_not_claim_verified_memory(self):
        self.cli('init', '--name', 'Empty')
        data = self.cli('review')['data']
        self.assertEqual(data['review_state'], 'no_checkpoint')
        self.assertEqual(data['references'], [])
        self.assertEqual(data['next_steps'], ['save_first_checkpoint'])
        self.draft = dict(objective='Plan', next_action='Review', constraints=[], decisions=[], unresolved=[], evidence=[])
        self.checkpoint(0)
        data = self.cli('review')['data']
        self.assertEqual(data['review_state'], 'no_references')
        self.assertFalse(data['semantic_completion_verified'])

    def test_review_never_initializes_an_untracked_project(self):
        result = self.cli('review', ok=False)
        self.assertEqual(result['code'], 'NOT_INITIALIZED')
        self.assertFalse((self.project / '.continuity').exists())

    def test_wal_readers_refuse_before_touching_shared_memory(self):
        self.save()
        # Real SQLite WAL, with committed data and an abruptly exited writer.
        # No extra tables, fake database methods or mutable product imports.
        program = '''
import os, sqlite3, sys
c = sqlite3.connect(sys.argv[1])
assert c.execute('PRAGMA journal_mode=WAL').fetchone()[0] == 'wal'
c.execute('PRAGMA wal_autocheckpoint=0')
c.execute("UPDATE project SET name='WAL test only'")
c.commit()
os._exit(73)
'''
        storage = self.project / '.continuity'
        result = subprocess.run([sys.executable, '-B', '-c', program,
                                 str(storage / 'state.sqlite3')], timeout=15)
        self.assertEqual(result.returncode, 73)
        def snapshot():
            return {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                    for p in storage.iterdir() if p.is_file()}
        before = snapshot()
        self.assertIn('state.sqlite3-wal', before)
        self.assertIn('state.sqlite3-shm', before)
        for command in ('review', 'resume', 'context', 'check', 'status', 'doctor'):
            with self.subTest(command=command):
                data = self.cli(command, ok=command == 'doctor')
                if command == 'doctor':
                    self.assertEqual(data['data']['storage']['state'], 'READONLY_WAL_UNSUPPORTED')
                    self.assertFalse(data['data']['storage']['compatible'])
                else:
                    self.assertEqual(data['code'], 'READONLY_WAL_UNSUPPORTED')
                    self.assertIsNone(data['data'])
                self.assertEqual(snapshot(), before)


if __name__ == '__main__':
    unittest.main()
