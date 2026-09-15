"""Installation diagnosis through public CLI processes; synthetic directories only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Doctor(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / 'selected project'
        self.project.mkdir()

    def cli(self, *args, ok=True):
        run = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
                              '--project', str(self.project), *args],
                             capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(run.returncode, 0 if ok else 2, run.stdout + run.stderr)
        value = json.loads(run.stdout)
        self.assertEqual(value['ok'], ok)
        return value

    def test_diagnosis_identifies_invoked_tool_without_initializing_a_project(self):
        data = self.cli('doctor')['data']
        self.assertEqual(data['product_id'], 'glom-continuity')
        self.assertEqual(data['display_name'], 'Recaloom')
        self.assertEqual(data['storage']['state'], 'not_initialized')
        self.assertFalse(data['storage']['compatible'])
        self.assertFalse(data['publisher_authenticated'])
        self.assertEqual(Path(data['runtime']['program_path']), ROOT / 'scripts/continuity.py')
        self.assertIn('resume', data['capabilities'])
        self.assertFalse((self.project / '.continuity').exists())

    def test_existing_project_is_identified_without_rewriting_its_database(self):
        initial = self.cli('init', '--name', 'My project')['data']
        database = self.project / '.continuity/state.sqlite3'
        before = database.read_bytes()
        data = self.cli('doctor')['data']
        self.assertEqual(data['storage']['state'], 'compatible_v1')
        self.assertTrue(data['storage']['compatible'])
        self.assertEqual(data['storage']['project_id'], initial['project_id'])
        self.assertEqual(data['storage']['revision'], 0)
        self.assertEqual(database.read_bytes(), before)

    def test_foreign_directory_is_not_misreported_as_an_empty_project(self):
        folder = self.project / '.continuity'
        folder.mkdir()
        marker = folder / 'other-tool.json'
        marker.write_text('{"keep":"this belongs to another tool"}', encoding='utf-8')
        before = marker.read_bytes()
        data = self.cli('doctor')['data']
        self.assertEqual(data['storage']['state'], 'UNRECOGNIZED_STORAGE')
        self.assertFalse(data['storage']['compatible'])
        self.assertEqual(self.cli('resume', ok=False)['code'], 'UNRECOGNIZED_STORAGE')
        self.assertEqual(self.cli('init', '--name', 'Do not overwrite', ok=False)['code'], 'ALREADY_INITIALIZED')
        self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['other-tool.json'])


if __name__ == '__main__':
    unittest.main()
