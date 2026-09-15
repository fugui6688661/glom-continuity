"""Single-call recovery through public CLI processes only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Resume(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'selected-project'
        self.project.mkdir()

    def cli(self, *args, ok=True):
        p = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
                            '--project', str(self.project), *args],
                           capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(p.returncode, 0 if ok else 2, p.stdout + p.stderr)
        result = json.loads(p.stdout)
        self.assertEqual(result['ok'], ok)
        return result

    def test_first_visit_explains_missing_memory_without_creating_storage(self):
        data = self.cli('resume')['data']
        self.assertEqual(data['recovery_state'], 'not_initialized')
        self.assertIsNone(data['project_id'])
        self.assertEqual(data['instruction_authority'], 'none')
        self.assertFalse(data['check']['semantic_completion_verified'])
        self.assertFalse((self.project / '.continuity').exists())

    def test_initialized_project_without_checkpoint_is_not_fake_memory(self):
        initial = self.cli('init', '--name', 'Selected project')['data']
        data = self.cli('resume')['data']
        self.assertEqual(data['recovery_state'], 'no_checkpoint')
        self.assertEqual(data['project_id'], initial['project_id'])
        self.assertIsNone(data['checkpoint_id'])
        self.assertEqual(data['revision'], 0)
        self.assertEqual(data['check']['state'], 'no_checkpoint')
        self.assertEqual(self.cli('status')['data']['revision'], 0)

    def save(self):
        self.cli('init', '--name', 'Lunar Paper project')
        (self.project / 'brief.txt').write_text('Only prepare a draft. Price is unknown.', encoding='utf-8')
        note = dict(id='review-video', kind='workflow', title='Review', body='Listen before delivery.',
                    when=['video'], status='active', source='Synthetic user request', expires_at=None)
        (self.project / 'habits.json').write_text(json.dumps({'format': 'continuity-memory-v1', 'items': [note]}), encoding='utf-8')
        self.draft = dict(objective='Prepare a product video', next_action='Review permitted assets',
                          constraints=['No publishing'], decisions=['Landscape format'],
                          unresolved=['Price unknown'], evidence=[{'path': 'brief.txt', 'role': 'input'},
                                                                   {'path': 'habits.json', 'role': 'memory'}])
        (self.project / 'draft.json').write_text(json.dumps(self.draft), encoding='utf-8')
        return self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '0')['data']

    def test_one_call_recovers_context_and_leaves_handoff_unaccepted(self):
        saved = self.save()
        handoff = self.cli('handoff', '--recipient', 'next', '--expect-revision', '1')['data']
        data = self.cli('resume', '--query', 'VIDEO', '--max-chars', '10000')['data']
        self.assertEqual(data['recovery_state'], 'restored')
        self.assertEqual(data['project_id'], saved['project_id'])
        self.assertEqual(data['checkpoint_id'], saved['checkpoint_id'])
        self.assertEqual(data['revision'], 1)
        self.assertEqual(data['check']['state'], 'references_current')
        self.assertFalse(data['check']['semantic_completion_verified'])
        self.assertEqual(data['memory']['selected'][0]['body'], 'Listen before delivery.')
        self.assertIn('No publishing', data['text'])
        self.assertIn('Price unknown', data['text'])
        self.assertEqual(data['pending_handoffs'][0]['id'], handoff['handoff_id'])
        self.assertEqual(self.cli('receipt', '--id', handoff['handoff_id'])['data']['state'], 'open')
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    def test_invalid_query_is_rejected_even_without_saved_memory(self):
        self.assertEqual(self.cli('resume', '--query', 'x' * 2001, ok=False)['code'], 'INVALID_INPUT')
        self.assertFalse((self.project / '.continuity').exists())

    def test_changed_input_withholds_memory_and_never_revalidates_next_step(self):
        self.save()
        (self.project / 'brief.txt').write_text('New goal; do not follow the old plan.', encoding='utf-8')
        data = self.cli('resume', '--query', 'video')['data']
        self.assertEqual(data['recovery_state'], 'needs_review')
        self.assertEqual(data['next_action_status'], 'requires_reference_review')
        self.assertEqual(data['memory']['selected'], [])
        self.assertEqual(data['instruction_authority'], 'none')
        self.assertIn('No publishing', data['text'])
        self.assertIn('Price unknown', data['text'])

    def test_budget_rejects_whole_response_in_first_save_and_restore_states(self):
        for setup in (None, lambda: self.cli('init', '--name', 'Empty project')):
            if setup:
                setup()
            result = self.cli('resume', '--max-chars', '10', ok=False)
            self.assertEqual(result['code'], 'BUDGET_TOO_SMALL')
            self.assertIsNone(result['data'])

    def test_unreferenced_planning_is_not_verified_work(self):
        self.save()
        self.draft['evidence'] = []
        (self.project / 'draft.json').write_text(json.dumps(self.draft), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '1')
        data = self.cli('resume')['data']
        self.assertEqual(data['recovery_state'], 'no_references')
        self.assertFalse(data['check']['semantic_completion_verified'])
        self.assertEqual(data['next_action_status'], 'recorded_unverified')


if __name__ == '__main__':
    unittest.main()
