"""Release CLI rejects mismatched labels before creating a candidate archive."""
import json
import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]


class ReleaseIdentity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='recaloom-release-identity-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'scripts').mkdir()
        (self.root / '.codex-plugin').mkdir()
        shutil.copyfile(ROOT / 'scripts/build_release.py', self.root / 'scripts/build_release.py')
        (self.root / 'scripts/continuity.py').write_text("VERSION = '0.2.0'\n", encoding='utf-8')
        self.plugin_version('0.2.0')
        (self.root / 'release-files.json').write_text(json.dumps([
            'scripts/continuity.py', '.codex-plugin/plugin.json']), encoding='utf-8')
        self.output = self.root / 'candidate.zip'

    def plugin_version(self, version):
        (self.root / '.codex-plugin/plugin.json').write_text(
            json.dumps({'name': 'glom-continuity', 'version': version}), encoding='utf-8')

    def build(self, *options):
        return subprocess.run([sys.executable, '-I', '-B', str(self.root / 'scripts/build_release.py'),
                               '--output', str(self.output), *options], cwd=self.root,
                              capture_output=True, text=True, timeout=15)

    def test_mismatched_plugin_version_is_refused_before_archive_creation(self):
        self.plugin_version('0.1.0-alpha.7')
        result = self.build()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('Release version mismatch', result.stderr)
        self.assertFalse(self.output.exists())

    def test_expected_label_is_recorded_with_the_archived_program_digest(self):
        result = self.build('--expect-version', '0.2.0')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['tool_version'], '0.2.0')
        self.assertFalse(receipt['published'])
        with zipfile.ZipFile(self.output) as archive:
            manifest = json.loads(archive.read('glom-continuity/PACKAGE-MANIFEST.json'))
            self.assertEqual(manifest['tool_version'], '0.2.0')
            self.assertEqual(manifest['program_sha256'], hashlib.sha256(
                archive.read('glom-continuity/scripts/continuity.py')).hexdigest())
            self.assertFalse(manifest['published'])

    def test_wrong_expected_version_does_not_overwrite_an_existing_output(self):
        self.output.write_bytes(b'previous candidate: preserve these bytes')
        result = self.build('--expect-version', '0.3.0')
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('--expect-version', result.stderr)
        self.assertEqual(self.output.read_bytes(), b'previous candidate: preserve these bytes')

    def test_invalid_or_ambiguous_declarations_are_not_evaluated(self):
        for declaration in (
            "VERSION = '0.2.0'\nVERSION = '0.2.0'\n",
            "VERSION = __import__('pathlib').Path('executed').write_text('bad')\n",
            'VERSION = 2\n',
            "VERSION = '0.2.0\\n'\n",
            "VERSION = OTHER = '0.2.0'\n",
        ):
            with self.subTest(declaration=declaration):
                (self.root / 'scripts/continuity.py').write_text(declaration, encoding='utf-8')
                result = self.build()
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse(self.output.exists())
                self.assertFalse((self.root / 'executed').exists())

    def test_missing_packaged_identity_file_is_rejected(self):
        (self.root / 'release-files.json').write_text(
            json.dumps(['scripts/continuity.py']), encoding='utf-8')
        result = self.build()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(self.output.exists())

    def test_additional_typed_or_augmented_version_assignment_is_refused(self):
        for index, extra in enumerate(("VERSION: str = '0.3.0'\n", "VERSION += '-different'\n")):
            with self.subTest(extra=extra):
                self.output = self.root / ('candidate-extra-' + str(index) + '.zip')
                (self.root / 'scripts/continuity.py').write_text(
                    "VERSION = '0.2.0'\n" + extra, encoding='utf-8')
                result = self.build()
                self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
                self.assertFalse(self.output.exists())

    def test_repeated_plugin_version_key_is_refused(self):
        (self.root / '.codex-plugin/plugin.json').write_text(
            '{"name":"glom-continuity","version":"0.3.0","version":"0.2.0"}', encoding='utf-8')
        result = self.build()
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(self.output.exists())

    def test_default_build_reports_labels_without_importing_packaged_code(self):
        (self.root / 'scripts/continuity.py').write_text(
            "VERSION = '0.2.0'\nraise RuntimeError('Do not import during packaging')\n", encoding='utf-8')
        result = self.build()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['tool_version'], '0.2.0')


if __name__ == '__main__':
    unittest.main()
