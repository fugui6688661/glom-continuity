"""CI inventory acceptance through its public CLI, using isolated fixtures only."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'scripts/ci_plan.py'


class CIPlan(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ci-plan-private-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'tests').mkdir()
        (self.root / 'ci').mkdir()
        self.plan = {
            'schema_version': 1,
            'portable_py': ['tests/test_example.py'],
            'harness_py': [], 'harness_node': [], 'exclusions': [],
        }
        (self.root / 'tests/test_example.py').write_text(
            'import unittest\nclass Example(unittest.TestCase):\n'
            '    def test_pass(self):\n        self.assertTrue(True)\n', encoding='utf-8')
        self.save_plan()

    def save_plan(self):
        (self.root / 'ci/test-plan.json').write_text(json.dumps(self.plan), encoding='utf-8')

    def invoke(self, action='check', root=None, env=None):
        return subprocess.run([sys.executable, '-B', str(CLI), action,
                               '--root', str(root or self.root)],
                              env=env, capture_output=True, text=True, encoding='utf-8', timeout=20)

    def assert_failure(self, result, reason):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['state'], 'failed')
        self.assertEqual(report['reason'], reason)
        self.assertEqual(result.stderr, '')
        self.assertNotIn(str(self.root), result.stdout)
        self.assertNotIn('test_example.py', result.stdout)
        return report

    def test_unknown_test_is_rejected_without_disclosing_its_name(self):
        (self.root / 'tests/test_secret_fixture.py').write_text('', encoding='utf-8')
        result = self.invoke()
        self.assert_failure(result, 'UNASSIGNED_TESTS')
        self.assertNotIn('secret_fixture', result.stdout)

    def test_duplicate_assignment_within_or_across_lanes_or_exclusions_is_rejected(self):
        for target in ('portable_py', 'harness_py', 'exclusions'):
            with self.subTest(target=target):
                item = ({'file': 'tests/test_example.py', 'reason': 'Duplicate fixture'}
                        if target == 'exclusions' else 'tests/test_example.py')
                self.plan[target].append(item)
                self.save_plan()
                try:
                    self.assert_failure(self.invoke(), 'DUPLICATE_TESTS')
                finally:
                    self.plan[target].pop()

    def test_assigned_but_missing_test_is_rejected(self):
        self.plan['portable_py'].append('tests/test_missing.py')
        self.save_plan()
        self.assert_failure(self.invoke(), 'MISSING_TESTS')

    def test_manifest_schema_and_json_mistakes_are_sanitized_failures(self):
        valid = json.dumps(self.plan)
        variants = [
            ('not-json', '{private-invalid-json'),
            ('excessive-nesting', '[' * 20000 + '0' + ']' * 20000),
            ('root-list', '[]'),
            ('duplicate-key', valid.replace('"schema_version": 1',
                                            '"schema_version": 9, "schema_version": 1')),
        ]
        for key, value in [('schema_version', True), ('schema_version', 2),
                           ('portable_py', 'tests/test_example.py'),
                           ('harness_node', ['tests/test_example.py']),
                           ('portable_py', [None]), ('unexpected', 'private-schema-value'),
                           ('exclusions', [{'file': 'tests/test_unused.py', 'reason': ''}]),
                           ('exclusions', [{'file': 'tests/test_unused.py', 'reason': 'ok', 'extra': 1}])]:
            candidate = json.loads(valid)
            candidate[key] = value
            variants.append((key, json.dumps(candidate)))
        candidate = json.loads(valid)
        del candidate['harness_py']
        variants.append(('missing-lane', json.dumps(candidate)))
        for name in ('../test_escape.py', '/tmp/test_escape.py',
                     'tests/test_*.py', 'tests/test_x;echo_secret.py'):
            candidate = json.loads(valid)
            candidate['portable_py'] = [name]
            variants.append(('unsafe-name', json.dumps(candidate)))
        for label, content in variants:
            with self.subTest(label=label):
                (self.root / 'ci/test-plan.json').write_text(content, encoding='utf-8')
                result = self.invoke()
                self.assert_failure(result, 'INVALID_MANIFEST')
                self.assertNotIn('private-', result.stdout)
                self.assertNotIn('escape', result.stdout)

    def test_symlinked_test_targets_and_test_directory_are_rejected(self):
        target = self.root / 'outside.py'
        target.write_text('raise RuntimeError("must not import")\n', encoding='utf-8')
        original = self.root / 'tests/test_example.py'
        original.unlink()
        original.symlink_to(target)
        self.assert_failure(self.invoke(), 'UNSAFE_TEST_TARGET')
        original.unlink()
        original.symlink_to(self.root / 'absent.py')
        self.assert_failure(self.invoke(), 'UNSAFE_TEST_TARGET')
        original.unlink()
        target_directory = self.root / 'outside-tests'
        (self.root / 'tests').rename(target_directory)
        (self.root / 'tests').symlink_to(target_directory, target_is_directory=True)
        self.assert_failure(self.invoke(), 'UNSAFE_TEST_TARGET')

    def test_real_inventory_and_default_root_match_the_agreed_lanes(self):
        explicit = self.invoke(root=ROOT)
        self.assertEqual(explicit.returncode, 0, explicit.stdout + explicit.stderr)
        report = json.loads(explicit.stdout)
        self.assertEqual(report['state'], 'passed')
        default = subprocess.run([sys.executable, '-B', str(CLI), 'check'], cwd=self.root,
                                 capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(default.returncode, 0, default.stdout + default.stderr)
        self.assertEqual(json.loads(default.stdout), report)
        self.assertNotIn(str(ROOT), default.stdout)
        plan = json.loads((ROOT / 'ci/test-plan.json').read_text(encoding='utf-8'))
        self.assertEqual(plan['harness_py'], ['tests/test_managed_host.py'])
        self.assertEqual(set(plan['harness_node']), {
            'tests/test_dsh_client_notice.mjs', 'tests/test_dsh_desktop_plugin.mjs',
            'tests/test_dsh_native_races.mjs', 'tests/test_dsh_recovery.mjs',
            'tests/test_dsh_runtime.mjs', 'tests/test_managed_control.mjs',
        })
        self.assertEqual([item['file'] for item in plan['exclusions']], ['tests/test_dsh_adapter.py'])
        self.assertIn('test_dsh_recovery.mjs', plan['exclusions'][0]['reason'])
        self.assertIn('tests/test_ci_harness.py', plan['portable_py'])
        self.assertIn('tests/test_ci_plan.py', plan['portable_py'])
        self.assertTrue(all(name.endswith('.py') for name in plan['portable_py']))

    def test_portable_runs_only_its_list_at_verbosity_two_and_inherits_environment(self):
        secret = 'synthetic-private-ci-value'
        (self.root / 'tests/test_example.py').write_text(
            'import os, unittest\nclass Example(unittest.TestCase):\n'
            '    def test_normal_environment(self):\n'
            '        self.assertTrue(os.environ.get("CI_PLAN_TEST_SECRET") == '
            + repr(secret) + ')\n', encoding='utf-8')
        for lane, filename in [('harness_py', 'tests/test_host.py'),
                               ('harness_node', 'tests/test_host.mjs')]:
            self.plan[lane] = [filename]
            (self.root / filename).write_text('raise RuntimeError("HOST_MUST_NOT_RUN")\n', encoding='utf-8')
        self.plan['exclusions'] = [{'file': 'tests/test_wrapper.py', 'reason': 'Synthetic exclusion'}]
        (self.root / 'tests/test_wrapper.py').write_text('raise RuntimeError("WRAPPER_MUST_NOT_RUN")\n',
                                                        encoding='utf-8')
        self.save_plan()
        result = self.invoke('portable', env={**os.environ, 'CI_PLAN_TEST_SECRET': secret})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('test_normal_environment', result.stderr)
        self.assertIn('Ran 1 test', result.stderr)
        self.assertIn('OK', result.stderr)
        self.assertEqual(result.stdout, '')
        self.assertNotIn(secret, result.stderr)

    def test_portable_rejects_a_zero_test_suite(self):
        (self.root / 'tests/test_example.py').write_text('', encoding='utf-8')
        self.assert_failure(self.invoke('portable'), 'EMPTY_PORTABLE_SUITE')

    def test_portable_validation_happens_before_importing_tests(self):
        (self.root / 'tests/test_example.py').write_text(
            'raise RuntimeError("TEST_IMPORTED_BEFORE_VALIDATION")\n', encoding='utf-8')
        (self.root / 'tests/test_unknown.py').write_text('', encoding='utf-8')
        self.assert_failure(self.invoke('portable'), 'UNASSIGNED_TESTS')

    def test_portable_propagates_unittest_failure(self):
        (self.root / 'tests/test_example.py').write_text(
            'import unittest\nclass Example(unittest.TestCase):\n'
            '    def test_failure(self):\n        self.fail("synthetic failure")\n', encoding='utf-8')
        result = self.invoke('portable')
        self.assertEqual(result.returncode, 1)
        self.assertIn('test_failure', result.stderr)
        self.assertIn('FAILED (failures=1)', result.stderr)

    def test_invalid_arguments_do_not_echo_private_paths_or_values(self):
        result = subprocess.run([sys.executable, '-B', str(CLI), 'check',
                                 '--private-invalid-argument', str(self.root)],
                                capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assert_failure(result, 'INVALID_ARGUMENTS')
        self.assertNotIn('private-invalid', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
