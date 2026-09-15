"""A user can save a received task's result and recover its linkage in a new process."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReturnWork(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name)
        self.cli('init', '--name', 'Activity plan')
        (self.project / 'brief.txt').write_text('Budget 5000 CNY; 50 people; location unknown.', encoding='utf-8')
        self.draft = dict(objective='Prepare an activity plan', next_action='Write a draft',
                          constraints=['Budget 5000 CNY', '50 people'], decisions=[],
                          unresolved=['Location unknown'], evidence=[{'path': 'brief.txt', 'role': 'input'}])
        self.write_draft()
        self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '0')
        self.identifier = self.cli('handoff', '--recipient', 'worker', '--expect-revision', '1')['data']['handoff_id']

    def cli(self, *args, ok=True):
        run = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
                              '--project', str(self.project), *args],
                             capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(run.returncode, 0 if ok else 2, run.stdout + run.stderr)
        data = json.loads(run.stdout)
        self.assertEqual(data['ok'], ok)
        return data

    def write_draft(self):
        (self.project / 'draft.json').write_text(json.dumps(self.draft), encoding='utf-8')

    def prepare_result(self):
        (self.project / 'plan.md').write_text('Draft: 100 CNY per person. Location remains unknown.', encoding='utf-8')
        self.draft['evidence'].append({'path': 'plan.md', 'role': 'artifact'})
        self.draft['next_action'] = 'Review plan.md; do not book a venue'
        self.write_draft()

    def return_result(self, **changes):
        ok = changes.pop('ok', True)
        options = dict(id=self.identifier, recipient='worker', from_file=str(self.project / 'draft.json'), expect_revision='1')
        options.update(changes)
        args = ['return-work']
        for key, value in options.items():
            args.extend(['--' + key.replace('_', '-'), value])
        return self.cli(*args, ok=ok)

    def test_accepted_work_is_saved_and_linked_for_the_next_assistant(self):
        self.cli('accept', '--id', self.identifier, '--recipient', 'worker')
        self.prepare_result()
        saved = self.return_result()['data']
        self.assertEqual(saved['revision'], 2)
        self.assertEqual(saved['result']['state'], 'saved')
        self.assertEqual(saved['result']['handoff_id'], self.identifier)
        self.assertFalse(saved['result']['semantic_completion_verified'])
        receipt = self.cli('receipt', '--id', self.identifier)['data']
        self.assertEqual(receipt['state'], 'accepted')
        self.assertEqual(receipt['result']['checkpoint_id'], saved['checkpoint_id'])
        self.assertEqual(receipt['result']['revision'], 2)
        self.assertEqual(receipt['result']['artifacts'][0]['path'], 'plan.md')
        self.assertEqual(receipt['result']['check']['state'], 'references_current')
        restored = self.cli('resume', '--max-chars', '12000')['data']
        self.assertEqual(restored['revision'], 2)
        self.assertEqual(restored['result']['handoff_id'], self.identifier)
        self.assertIn('Location unknown', restored['text'])

    def test_lost_response_replay_keeps_one_version_and_rejects_changed_result(self):
        self.cli('accept', '--id', self.identifier, '--recipient', 'worker')
        self.prepare_result()
        first = self.return_result()['data']
        repeated = self.return_result()['data']
        self.assertTrue(repeated['replayed'])
        self.assertEqual(repeated['project_id'], first['project_id'])
        self.assertEqual(repeated['checkpoint_id'], first['checkpoint_id'])
        self.assertEqual(self.cli('status')['data']['revision'], 2)
        (self.project / 'plan.md').write_text('Changed result; not the saved output.', encoding='utf-8')
        self.assertEqual(self.return_result(ok=False)['code'], 'RETURN_CONFLICT')
        receipt = self.cli('receipt', '--id', self.identifier)['data']
        self.assertEqual(receipt['result']['state'], 'saved')
        self.assertEqual(receipt['result']['check']['state'], 'needs_review')
        self.assertEqual(receipt['result']['check']['issues'], [{'path': 'plan.md', 'code': 'CONTENT_CHANGED'}])
        self.assertEqual(self.cli('status')['data']['revision'], 2)

    def test_unaccepted_or_wrong_label_cannot_record_a_result(self):
        self.prepare_result()
        self.assertEqual(self.return_result(ok=False)['code'], 'HANDOFF_NOT_ACCEPTED')
        self.cli('accept', '--id', self.identifier, '--recipient', 'worker')
        self.assertEqual(self.return_result(recipient='someone-else', ok=False)['code'], 'WRONG_RECIPIENT')
        self.assertEqual(self.cli('receipt', '--id', self.identifier)['data']['result']['state'], 'not_recorded')
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    def test_simultaneous_identical_returns_create_only_one_revision(self):
        self.cli('accept', '--id', self.identifier, '--recipient', 'worker')
        self.prepare_result()
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(self.return_result) for _ in range(2)]
            results = [job.result()['data'] for job in jobs]
        self.assertEqual(sorted(item['replayed'] for item in results), [False, True])
        self.assertEqual(len({item['checkpoint_id'] for item in results}), 1)
        self.assertEqual(self.cli('status')['data']['revision'], 2)
        receipt = self.cli('receipt', '--id', self.identifier)['data']['result']
        self.assertEqual(receipt['revision'], 2)
        self.assertEqual(receipt['checkpoint_id'], results[0]['checkpoint_id'])

    def test_changed_original_input_prevents_return_even_if_new_draft_omits_it(self):
        self.cli('accept', '--id', self.identifier, '--recipient', 'worker')
        self.prepare_result()
        (self.project / 'brief.txt').write_text('Now 80 people.', encoding='utf-8')
        self.draft['evidence'] = [{'path': 'plan.md', 'role': 'artifact'}]
        self.write_draft()
        self.assertEqual(self.return_result(ok=False)['code'], 'EVIDENCE_CHANGED')
        self.assertEqual(self.cli('status')['data']['revision'], 1)
        self.assertEqual(self.cli('receipt', '--id', self.identifier)['data']['result']['state'], 'not_recorded')

    def test_plain_checkpoint_is_not_misattributed_as_the_handoff_result(self):
        self.cli('accept', '--id', self.identifier, '--recipient', 'worker')
        self.prepare_result()
        self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '1')
        self.assertEqual(self.cli('receipt', '--id', self.identifier)['data']['result']['state'], 'not_recorded')
        self.assertEqual(self.return_result(ok=False)['code'], 'REVISION_CONFLICT')
        self.assertEqual(self.return_result(expect_revision='2', ok=False)['code'], 'STALE_HANDOFF')
        self.assertEqual(self.cli('status')['data']['revision'], 2)

    def test_omitted_original_input_is_still_checked_after_return_and_on_history(self):
        self.cli('accept', '--id', self.identifier, '--recipient', 'worker')
        self.prepare_result()
        self.draft['evidence'] = [{'path': 'plan.md', 'role': 'artifact'}]
        self.write_draft()
        self.return_result()
        (self.project / 'brief.txt').write_text('Now 80 people.', encoding='utf-8')
        for command in ('check', 'context', 'resume'):
            recovered = self.cli(command)['data']
            checked = recovered if command == 'check' else recovered['check']
            self.assertEqual(checked['state'], 'needs_review')
            self.assertIn({'path': 'brief.txt', 'code': 'CONTENT_CHANGED'}, checked['issues'])
        self.assertEqual(self.cli('handoff', '--recipient', 'next', '--expect-revision', '2', ok=False)['code'], 'EVIDENCE_CHANGED')
        self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '2')
        receipt = self.cli('receipt', '--id', self.identifier)['data']['result']
        self.assertEqual(receipt['check']['state'], 'needs_review')
        replay = self.return_result()['data']
        self.assertTrue(replay['replayed'])
        self.assertEqual(replay['result']['check']['state'], 'needs_review')

    def test_successive_linked_results_preserve_transitive_reference_checks(self):
        self.cli('accept', '--id', self.identifier, '--recipient', 'worker')
        self.prepare_result()
        self.draft['evidence'] = [{'path': 'plan.md', 'role': 'artifact'}]
        self.write_draft()
        self.return_result()
        next_id = self.cli('handoff', '--recipient', 'worker', '--expect-revision', '2')['data']['handoff_id']
        self.cli('accept', '--id', next_id, '--recipient', 'worker')
        (self.project / 'review.md').write_text('A review draft.', encoding='utf-8')
        self.draft['evidence'] = [{'path': 'review.md', 'role': 'artifact'}]
        self.write_draft()
        self.return_result(id=next_id, expect_revision='2')
        (self.project / 'brief.txt').write_text('Changed after both returns.', encoding='utf-8')
        result = self.cli('resume', '--max-chars', '16000')['data']
        self.assertEqual(result['recovery_state'], 'needs_review')
        self.assertIn({'path': 'brief.txt', 'code': 'CONTENT_CHANGED'}, result['check']['issues'])
        self.assertEqual(result['result']['check']['state'], 'needs_review')

    def test_result_needs_an_artifact_and_keeps_its_history_after_later_work(self):
        self.cli('accept', '--id', self.identifier, '--recipient', 'worker')
        self.assertEqual(self.return_result(ok=False)['code'], 'NO_ARTIFACT')
        self.prepare_result()
        first = self.return_result()['data']
        self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '2')
        repeated = self.return_result()['data']
        self.assertEqual(repeated['revision'], 2)
        self.assertEqual(repeated['current_revision'], 3)
        self.assertEqual(repeated['checkpoint_id'], first['checkpoint_id'])
        self.assertEqual(self.cli('status')['data']['revision'], 3)
        self.assertNotIn('result', self.cli('resume', '--max-chars', '12000')['data'])


if __name__ == '__main__':
    unittest.main()
