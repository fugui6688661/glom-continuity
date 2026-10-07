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
HOST_OWNER = 'test_host_diagnostics.HostDiagnostics'
HOST_REASON = 'Managed homes currently support POSIX only'


class WorkflowSummary(unittest.TestCase):
    def test_failure_summary_keeps_install_stage_codes_not_private_payloads(self):
        summarize = self.contract()['failure_detail']
        codes = ('INVALID_DIRECTORY', 'ENVIRONMENT_IO_ERROR', 'RUNTIME_UNAVAILABLE',
                 'RUNTIME_START_FAILED', 'RUNTIME_IDENTITY_MISMATCH', 'PIP_BOOTSTRAP_FAILED',
                 'PIP_UNAVAILABLE', 'WHEEL_INSTALL_FAILED', 'TOOL_CHECK_FAILED', 'RUNTIME_TIMEOUT',
                 'RUNTIME_MODE_UNAVAILABLE', 'RUNTIME_INTERRUPTED', 'ENTRY_WRITE_UNSUPPORTED')
        for code in codes:
            with self.subTest(code=code):
                text = ('File "/PRIVATE/project/test_runtime_env.py", line 43, in test_create\n'
                        'AssertionError: 1 != 0 : {"ok": false, "code": "' + code + '", '
                        '"data":{"directory":"PRIVATE_PROJECT", "message":"PRIVATE_TOKEN"}}\n')
                detail = summarize(text)
                self.assertEqual(detail['error_codes'], [code])
                self.assertEqual(detail['scalar_comparison'], '1 != 0')
                self.assertEqual(detail['test_location'], 'test_runtime_env.py:43')
                self.assertNotIn('PRIVATE', str(detail))
        unknown = summarize('AssertionError: {"code":"PRIVATE_UNKNOWN_CODE"}\n')
        self.assertEqual(unknown['error_codes'], ['AssertionError'])

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

    def host_diagnostic_cases(self):
        # Read the real declarations without importing or running host fixtures.
        module = ast.parse((ROOT / 'tests/test_host_diagnostics.py').read_text(encoding='utf-8'))
        classes = [item for item in module.body
                   if isinstance(item, ast.ClassDef) and item.name == 'HostDiagnostics']
        self.assertEqual(len(classes), 1)
        host = classes[0]
        decorator = ast.parse(
            "unittest.skipUnless(os.name == 'posix', 'Managed homes currently support POSIX only')",
            mode='eval').body
        self.assertEqual([ast.dump(item) for item in host.decorator_list], [ast.dump(decorator)])
        methods = [item for item in host.body
                   if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and item.name.startswith('test_')]
        self.assertEqual(len(methods), 19, 'Changed host coverage requires explicit platform review')
        self.assertEqual(len({item.name for item in methods}), 19)
        self.assertTrue(all(not item.decorator_list for item in methods),
                        'Review any method-specific change to the class-level skip boundary')
        return [HOST_OWNER + '.' + item.name for item in methods]

    def test_windows_host_diagnostics_classifies_all_19_ast_methods_exactly(self):
        cases = self.host_diagnostic_cases()
        output = ('test_baseline (test_example.Example.test_baseline) ... ok\n' + ''.join(
            f'{case.rsplit(".", 1)[1]} ({case}) ... skipped {HOST_REASON!r}\n' for case in cases)
            + '\nRan 20 tests in 0.001s\n\nOK (skipped=19)\n')
        report = self.evaluate(output, True)
        self.assertTrue(report['acceptance_valid'], report)
        self.assertEqual(report['tests_run'], 20)
        self.assertEqual(report['counts']['skipped'], 19)
        self.assertEqual(report['skipped'], [
            {'test': case, 'allowed': True, 'reason_code': 'managed_host_posix_only'} for case in cases])

    def test_host_diagnostic_skip_requires_windows_exact_method_and_exact_reason(self):
        for case in self.host_diagnostic_cases():
            for boundary, output, windows in (
                ('Linux', self.output(case, HOST_REASON), False),
                ('macOS', self.output(case, HOST_REASON), False),
                ('new method', self.output(case + '_new', HOST_REASON), True),
                ('different class', self.output(case.replace(HOST_OWNER, HOST_OWNER + 'Other'), HOST_REASON), True),
                ('changed reason', self.output(case, HOST_REASON + '.'), True),
                ('missing MCP', self.output(case, 'Optional MCP SDK missing: this run does NOT verify MCP'), True),
            ):
                with self.subTest(case=case, boundary=boundary):
                    report = self.evaluate(output, windows)
                    self.assertFalse(report['acceptance_valid'], report)
                    self.assertEqual(len(report['skipped']), 1)
                    self.assertIs(report['skipped'][0]['allowed'], False)
                    self.assertEqual(report['skipped'][0]['reason_code'], 'unexpected_skip')

    def test_host_platform_skips_do_not_excuse_all_skip_missing_mcp_or_incomplete_results(self):
        cases = self.host_diagnostic_cases()
        skipped = ''.join(f'{case.rsplit(".", 1)[1]} ({case}) ... skipped {HOST_REASON!r}\n'
                          for case in cases)
        all_skipped = skipped + '\nRan 19 tests in 0.001s\n\nOK (skipped=19)\n'
        report = self.evaluate(all_skipped, True)
        self.assertTrue(all(item['allowed'] for item in report['skipped']))
        self.assertFalse(report['acceptance_valid'], report)
        baseline = 'test_baseline (test_example.Example.test_baseline) ... ok\n'
        for boundary, output in (
            ('missing final summary', baseline + skipped),
            ('skip count mismatch', baseline + skipped + '\nRan 20 tests in 0.001s\n\nOK (skipped=18)\n'),
            ('failed', baseline + skipped + '\nRan 20 tests in 0.001s\n\nFAILED (failures=1, skipped=19)\n'),
        ):
            with self.subTest(boundary=boundary):
                self.assertFalse(self.evaluate(output, True)['acceptance_valid'])
        # Even a normally permitted FIFO method is not allowed to skip because
        # the SDK is missing; its class-level SDK guard takes precedence.
        mcp_case = ('test_mcp_independent.IndependentMCPAcceptance.'
                    'test_19_nonregular_draft_should_not_leave_cli_or_mcp_save_hung')
        mcp_reason = 'Optional MCP SDK missing: this run does NOT verify MCP'
        output = (baseline + skipped + f'{mcp_case.rsplit(".", 1)[1]} ({mcp_case}) ... skipped {mcp_reason!r}\n'
                  + '\nRan 21 tests in 0.001s\n\nOK (skipped=20)\n')
        report = self.evaluate(output, True)
        self.assertFalse(report['acceptance_valid'], report)
        self.assertEqual(report['skipped'][-1],
                         {'test': mcp_case, 'allowed': False, 'reason_code': 'unexpected_skip'})

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

    def test_progress_line_counts_are_not_final_test_coverage(self):
        output = ('test_one (test_example.Example.test_one) ... ok\n'
                  'test_documented (test_example.Example.test_documented)\n'
                  'First docstring line ... ok\n'
                  'test_logged (test_example.Example.test_logged) ... PRIVATE fixture output\n'
                  'ok\n\nRan 3 tests in 0.001s\n\nOK\n')
        report = self.evaluate(output, False)
        self.assertTrue(report['acceptance_valid'], report)
        self.assertEqual(report['tests_run'], 3)
        self.assertEqual(report['progress'], {
            'started': 2, 'completed': 1,
            'outcomes': {'ok': 1, 'FAIL': 0, 'ERROR': 0, 'skipped': 0},
            'last_started': 'test_example.Example.test_logged',
        })
        self.assertNotIn('PRIVATE', str(report['progress']))


if __name__ == '__main__':
    unittest.main()
