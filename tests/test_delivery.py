import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
import hashlib

ROOT = Path(__file__).resolve().parents[1]


class Delivery(unittest.TestCase):
    def test_new_user_can_run_a_protocol_demo_without_modifying_an_existing_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'demo'
            cmd = [sys.executable, '-B', str(ROOT / 'scripts/smoke_demo.py'), '--output', str(output)]
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads(result.stdout)
            self.assertEqual(receipt['state'], 'protocol_demo_passed')
            self.assertFalse(receipt['real_model_handoff_verified'])
            report = output / '演示结果.md'
            self.assertTrue(report.is_file())
            before = report.read_bytes()
            again = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(report.read_bytes(), before)

    def test_candidate_package_relocates_and_runs_without_private_state(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            archive = directory / 'candidate.zip'
            build = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/build_release.py'),
                                    '--output', str(archive)], text=True, capture_output=True, timeout=20)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            with zipfile.ZipFile(archive) as package:
                names = package.namelist()
                self.assertTrue(all(name.startswith('glom-continuity/') for name in names))
                self.assertFalse(any('.continuity/' in name or name.endswith('.sqlite3') for name in names))
                manifest = json.loads(package.read('glom-continuity/PACKAGE-MANIFEST.json'))
                for item in manifest['files']:
                    content = package.read('glom-continuity/' + item['path'])
                    self.assertEqual(hashlib.sha256(content).hexdigest(), item['sha256'])
                    self.assertNotRegex(content.decode('utf-8'), r'/Users/[A-Za-z0-9_.-]+/')
                package.extractall(directory / 'unpacked')
            copy = directory / 'unpacked' / 'glom-continuity'
            demo = subprocess.run([sys.executable, '-B', str(copy / 'scripts/smoke_demo.py'),
                                   '--output', str(directory / 'relocated-demo')],
                                  text=True, capture_output=True, timeout=30)
            self.assertEqual(demo.returncode, 0, demo.stdout + demo.stderr)
