"""Required-host CI runner: public process result, no installed SDK needed here."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RequiredHarnessCI(unittest.TestCase):
    def test_required_runner_rejects_an_inventory_with_no_host_suites(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir()
            (root / 'ci').mkdir()
            (root / 'tests').mkdir()
            for name in ('ci_harness.py', 'ci_plan.py', 'harness_install.py', 'continuity.py'):
                shutil.copyfile(ROOT / 'scripts' / name, root / 'scripts' / name)
            (root / 'tests/test_fixture.py').write_text('', encoding='utf-8')
            plan = {'schema_version': 1, 'portable_py': ['tests/test_fixture.py'],
                    'harness_py': [], 'harness_node': [], 'exclusions': []}
            (root / 'ci/test-plan.json').write_text(json.dumps(plan), encoding='utf-8')
            peers = {'dsh': '0.1.5-rc.1', 'cordis': '4.0.2', 'schemastery': '3.18.2',
                     'dsh-llm': '0.1.5-rc.1', 'dsh-client-ui-commands': '0.1.5-rc.1',
                     'dsh-api-session-controller': '0.1.5-rc.1',
                     'dsh-client-ui-conversation': '0.1.5-rc.1'}
            for name, version in peers.items():
                folder = root / 'node_modules/@deepseek-ai' / name
                folder.mkdir(parents=True)
                (folder / 'package.json').write_text(json.dumps(
                    {'name': '@deepseek-ai/' + name, 'version': version}), encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', str(root / 'scripts/ci_harness.py'),
                                     '--sdk-package', str(root / 'node_modules/@deepseek-ai/dsh/package.json')],
                                    capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['reason'], 'REQUIRED_SUITES_MISSING')
        self.assertEqual(report['suites'], [])
        self.assertFalse(report['host_verified'])

    def test_invalid_sdk_metadata_is_rejected_without_echoing_its_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            package = Path(directory) / '@deepseek-ai/dsh/package.json'
            package.parent.mkdir(parents=True)
            for content in ('{"name":"wrong-package","version":"PRIVATE-MARKER"}',
                            '[]', 'null', '[' * 20000 + '0' + ']' * 20000):
                with self.subTest(content_type=content[:20]):
                    package.write_text(content, encoding='utf-8')
                    result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ci_harness.py'),
                                             '--sdk-package', str(package)], capture_output=True,
                                            text=True, timeout=10)
                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(result.stderr, '')
                    self.assertEqual(json.loads(result.stdout)['reason'], 'SDK_INVALID')
                    self.assertNotIn('PRIVATE-MARKER', result.stdout + result.stderr)

    def test_actual_passing_python_summary_is_accepted(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ci_harness.py'),
                                 'check-result', '--format', 'python', '--return-code', '0'],
                                input='test_a (fixture.Checks.test_a) ... ok\n\nRan 1 test in 0.123s\n\nOK\n',
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)['accepted'])

    def test_invalid_required_results_stay_failed_and_do_not_echo_test_output(self):
        transcripts = [
            ('python', 0, 'PRIVATE-MARKER\nRan 0 tests in 0.000s\nOK\n'),
            ('python', 0, 'PRIVATE-MARKER\nRan 1 test in 0.001s\nOK (skipped=1)\n'),
            ('python', 1, 'PRIVATE-MARKER\nRan 1 test in 0.001s\nOK\n'),
            ('node', 0, 'PRIVATE-MARKER\n# tests 0\n# pass 0\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n'),
            ('node', 0, '# tests 3\n# pass 1\n# fail 0\n# cancelled 0\n# skipped 2\n# todo 0\n'),
            ('node', 0, '# tests 1\n# tests 2\n# pass 1\n# fail 0\n# cancelled 0\n# skipped 0\n# todo 0\n'),
        ]
        for format, code, transcript in transcripts:
            with self.subTest(format=format, code=code):
                result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ci_harness.py'),
                                         'check-result', '--format', format, '--return-code', str(code)],
                                        input=transcript, capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertFalse(json.loads(result.stdout)['accepted'])
                self.assertNotIn('PRIVATE-MARKER', result.stdout + result.stderr)

    def test_node_success_exit_with_skipped_required_test_is_not_coverage(self):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ci_harness.py'),
                                 'check-result', '--format', 'node', '--return-code', '0'],
                                input='TAP version 13\n1..1\n# tests 1\n# suites 0\n# pass 0\n# fail 0\n# cancelled 0\n# skipped 1\n# todo 0\n',
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertFalse(report['accepted'])
        self.assertEqual(report['reason'], 'INCOMPLETE_TEST_COVERAGE')

    def test_missing_explicit_sdk_fails_instead_of_reporting_skipped_success(self):
        env = {key: os.environ[key] for key in ('PATH', 'SystemRoot', 'WINDIR')
               if key in os.environ}
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/ci_harness.py')],
                                env=env, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['state'], 'failed')
        self.assertEqual(report['reason'], 'SDK_REQUIRED')
        self.assertEqual(report['suites'], [])
        self.assertFalse(report['host_verified'])


if __name__ == '__main__':
    unittest.main()
