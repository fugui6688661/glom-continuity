"""A saved revision belongs to a project, not merely to a directory name."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'scripts' / 'continuity.py'


class CheckpointBinding(unittest.TestCase):
    def setUp(self):
        self.owned = tempfile.TemporaryDirectory(prefix='recaloom-save-binding-')
        self.addCleanup(self.owned.cleanup)
        self.root = Path(self.owned.name)

    def call(self, project, *args, code='OK'):
        result = subprocess.run([sys.executable, '-B', str(CLI), '--project', str(project), *args],
                                capture_output=True, encoding='utf-8', timeout=15)
        self.assertEqual(result.returncode, 0 if code == 'OK' else 2, result.stdout + result.stderr)
        self.assertTrue(result.stdout.strip(), result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response['code'], code, response)
        return response

    def create(self, name):
        project = self.root / name
        project.mkdir()
        identity = self.call(project, 'init', '--name', name)['data']['project_id']
        (project / 'brief.txt').write_text('Synthetic input only.', encoding='utf-8')
        draft = {'objective': 'Prepare a local summary', 'next_action': 'Review the summary',
                 'constraints': ['Do not publish'], 'decisions': [], 'unresolved': ['Reviewer unknown'],
                 'evidence': [{'path': 'brief.txt', 'role': 'input'}]}
        (project / 'draft.json').write_text(json.dumps(draft), encoding='utf-8')
        return project, identity

    def tree(self, project):
        return {str(file.relative_to(project)): hashlib.sha256(file.read_bytes()).hexdigest()
                for file in project.rglob('*') if file.is_file()}

    def test_wrong_project_with_the_same_revision_cannot_receive_a_checkpoint(self):
        project_a, identity_a = self.create('A')
        project_b, identity_b = self.create('B')
        self.assertNotEqual(identity_a, identity_b)
        before = self.tree(project_b)
        rejected = self.call(project_b, 'checkpoint', '--from-file', str(project_b / 'draft.json'),
                             '--expect-revision', '0', '--expect-project-id', identity_a,
                             code='PROJECT_MISMATCH')
        self.assertIsNone(rejected['data'])
        self.assertEqual(self.tree(project_b), before)
        self.assertEqual(self.call(project_b, 'status')['data']['revision'], 0)
        self.assertEqual(self.call(project_a, 'status')['data']['revision'], 0)

    def test_matching_identity_saves_and_does_not_disable_revision_conflicts(self):
        project, identity = self.create('Expected')
        args = ['checkpoint', '--from-file', str(project / 'draft.json'),
                '--expect-revision', '0', '--expect-project-id', identity]
        saved = self.call(project, *args)['data']
        self.assertEqual(saved['project_id'], identity)
        self.assertEqual(saved['revision'], 1)
        self.assertEqual(saved['checkpoint']['constraints'], ['Do not publish'])
        before = self.tree(project)
        self.call(project, *args, code='REVISION_CONFLICT')
        self.assertEqual(self.tree(project), before)
        recovered = self.call(project, 'resume', '--expect-project-id', identity)['data']
        self.assertEqual(recovered['revision'], 1)
        self.assertEqual(recovered['check']['state'], 'references_current')

    def test_replaced_directory_does_not_rebind_the_previous_project_identity(self):
        original, identity = self.create('Selected')
        replacement, other_identity = self.create('Replacement')
        original.rename(self.root / 'Preserved-original')
        replacement.rename(original)
        before = self.tree(original)
        self.call(original, 'checkpoint', '--from-file', str(original / 'missing-draft.json'),
                  '--expect-revision', '0', '--expect-project-id', identity, code='PROJECT_MISMATCH')
        self.assertEqual(self.tree(original), before)
        self.assertEqual(self.call(original, 'status')['data']['project_id'], other_identity)

    def test_legacy_manual_save_still_works_without_claiming_identity_protection(self):
        project, identity = self.create('Legacy')
        saved = self.call(project, 'checkpoint', '--from-file', str(project / 'draft.json'),
                          '--expect-revision', '0')['data']
        self.assertEqual((saved['project_id'], saved['revision']), (identity, 1))


if __name__ == '__main__':
    unittest.main()
