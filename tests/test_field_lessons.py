"""Synthetic workflow lifecycle through separate public CLI processes, no model."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FieldLessons(unittest.TestCase):
    def test_reviewed_workflow_does_not_survive_changed_registered_evidence_or_retirement(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / 'project'
            project.mkdir()

            def cli(*args):
                run = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
                                      '--project', str(project), *args], capture_output=True,
                                     text=True, encoding='utf-8', timeout=10)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                result = json.loads(run.stdout)
                self.assertTrue(result['ok'])
                return result['data']

            def write(name, value):
                (project / name).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

            def recover():
                return cli('resume', '--query', 'report', '--max-chars', '12000')

            def save(revision):
                return cli('checkpoint', '--from-file', str(project / 'draft.json'),
                           '--expect-revision', str(revision))

            def preserved(data, revision):
                self.assertEqual(data['revision'], revision)
                self.assertIn('Never publish the report', data['text'])
                self.assertIn('Currency not confirmed', data['text'])
                self.assertEqual(data['instruction_authority'], 'none')
                self.assertFalse(data['check']['semantic_completion_verified'])
                self.assertEqual(cli('status')['revision'], revision)

            cli('init', '--name', 'Synthetic review')
            note = dict(id='check-totals', kind='workflow', title='Check report totals',
                        body='Compare quantity times price against each subtotal.', when=['report'],
                        status='candidate', source='Synthetic hypothesis; not user approval', expires_at=None)
            memory = dict(format='continuity-memory-v1', items=[note])
            (project / 'verification.txt').write_text('Synthetic trial: positive and negative cases observed.', encoding='utf-8')
            write('memory.json', memory)
            write('draft.json', dict(objective='Prepare a report', next_action='Confirm currency',
                                     constraints=['Never publish the report'], decisions=[],
                                     unresolved=['Currency not confirmed'], evidence=[
                                         {'path': 'memory.json', 'role': 'memory'},
                                         {'path': 'verification.txt', 'role': 'input'}]))
            save(0)
            candidate = recover()
            preserved(candidate, 1)
            self.assertEqual(candidate['memory']['selected'], [])
            self.assertEqual(candidate['memory']['omitted'][0]['reason'], 'candidate')

            # An explicit test-fixture author decision, not automatic promotion.
            note.update(status='active', source='Synthetic project-specific confirmation')
            write('memory.json', memory)
            unsaved = recover()
            preserved(unsaved, 1)
            self.assertEqual(unsaved['recovery_state'], 'needs_review')
            self.assertEqual(unsaved['memory']['selected'], [])
            save(1)
            active = recover()
            preserved(active, 2)
            self.assertEqual(active['memory']['selected'][0]['id'], 'check-totals')

            (project / 'verification.txt').write_text('Synthetic later failure: subtotal rule needs review.', encoding='utf-8')
            changed = recover()
            preserved(changed, 2)
            self.assertEqual(changed['recovery_state'], 'needs_review')
            self.assertEqual(changed['memory']['selected'], [])
            self.assertTrue(any(item['path'] == 'verification.txt' for item in changed['check']['issues']))

            note.update(status='retired', source='Synthetic user retires the workflow after review')
            write('memory.json', memory)
            save(2)
            retired = recover()
            preserved(retired, 3)
            self.assertEqual(retired['recovery_state'], 'restored')
            self.assertEqual(retired['memory']['selected'], [])
            self.assertEqual(retired['memory']['omitted'][0]['reason'], 'retired')
            self.assertTrue((project / 'verification.txt').is_file())
