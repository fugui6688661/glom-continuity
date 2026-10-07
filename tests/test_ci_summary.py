"""Check the published workflow's summary contract, not Windows execution."""
import ast
from pathlib import Path
import re
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
CASE = ('test_runtime_env.RuntimeEnvironment.'
        'test_timed_out_pip_stops_its_same_group_child_and_retains_environment')
REASON = 'POSIX process-group cleanup; Windows tree cleanup not yet verified'


class WorkflowSummary(unittest.TestCase):
    def contract(self):
        # Inspect only the self-contained report functions of the trusted local
        # workflow. Never run its package download, runner setup or upload steps.
        workflow = (ROOT / '.github/workflows/verify.yml').read_text(encoding='utf-8')
        start = workflow.index('          def identifier(')
        end = workflow.index('          root = Path.cwd()', start)
        contract = ast.parse(textwrap.dedent(workflow[start:end]))
        self.assertTrue(all(isinstance(item, ast.FunctionDef) for item in contract.body))
        namespace = {'re': re}
        exec(compile(contract, '<workflow summary contract>', 'exec'), namespace)
        return namespace

    def evaluate(self, output, windows):
        return self.contract()['test_summary'](output, windows)

    def output(self, case=CASE, reason=REASON, extra=''):
        method = case.rsplit('.', 1)[1]
        return (f'test_baseline (test_example.Example.test_baseline) ... ok\n'
                f'{method} ({case}) ... skipped {reason!r}\n'
                f'{extra}\nRan 2 tests in 0.001s\n\nOK (skipped=1)\n')

    def test_only_the_named_windows_limitation_is_an_allowed_skip(self):
        report = self.evaluate(self.output(), True)
        self.assertTrue(report['acceptance_valid'], report)
        self.assertEqual(report['counts']['skipped'], 1)
        self.assertEqual(report['skipped'], [{
            'test': CASE, 'allowed': True, 'reason_code': 'runtime_posix_cleanup_unverified'
        }])
        # This is an explicitly unsupported platform case, not a general skip
        # exemption for missing MCP, wrong runtimes, errors or new test names.
        for output, windows in (
            (self.output(), False),
            (self.output(reason='Missing MCP SDK'), True),
            (self.output(case=CASE + '_other'), True),
            (self.output().replace('OK (skipped=1)', 'FAILED (failures=1, skipped=1)'), True),
            (self.output().replace('Ran 2 tests', 'Ran 1 test'), True),
        ):
            with self.subTest(windows=windows, output=output):
                self.assertFalse(self.evaluate(output, windows)['acceptance_valid'])

    def test_incomplete_run_reports_only_structured_progress_and_never_passes(self):
        output = ('test_one (test_example.Example.test_one) ... ok\n'
                  'test_two (test_example.Example.test_two) ... skipped "PRIVATE REASON"\n'
                  'test_three (test_example.Example.test_three) ... FAIL\n'
                  'PRIVATE DIAGNOSTIC /private/fixture credential=synthetic-only\n'
                  'test_four (test_example.Example.test_four) ... ')
        report = self.evaluate(output, False)
        self.assertFalse(report['acceptance_valid'])
        self.assertIsNone(report['tests_run'])
        self.assertEqual(report['progress'], {
            'started': 4, 'completed': 3,
            'outcomes': {'ok': 1, 'FAIL': 1, 'ERROR': 0, 'skipped': 1},
            'last_started': 'test_example.Example.test_four',
        })
        self.assertNotIn('PRIVATE', str(report['progress']))
        progress = self.contract()['test_progress']
        self.assertEqual(progress(output.encode()), report['progress'])
        self.assertEqual(progress(None), {
            'started': 0, 'completed': 0,
            'outcomes': {'ok': 0, 'FAIL': 0, 'ERROR': 0, 'skipped': 0},
            'last_started': None,
        })


if __name__ == '__main__':
    unittest.main()
