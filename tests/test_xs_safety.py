"""Public CLI regressions for the XS input and first-use boundary."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CLI = Path(__file__).resolve().parents[1] / 'scripts' / 'continuity.py'


class XSSafetyTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='recaloom-xs-')
        self.addCleanup(tmp.cleanup)
        self.project = Path(tmp.name) / '项目 XS'
        self.project.mkdir()

    def run_cli(self, *args):
        result = subprocess.run([sys.executable, '-B', str(CLI), '--project',
                                 str(self.project), *args], capture_output=True,
                                encoding='utf-8', timeout=15)
        return result, json.loads(result.stdout)

    def draft(self, text):
        path = self.project / 'draft.json'
        path.write_text(json.dumps({'objective': text, 'next_action': 'Review the plan',
                                   'constraints': [], 'decisions': [], 'unresolved': [],
                                   'evidence': []}, ensure_ascii=True), encoding='utf-8')
        return str(path)

    def test_new_checkpoint_rejects_del_and_c1_without_advancing_project(self):
        self.assertEqual(self.run_cli('init', '--name', 'XS input')[0].returncode, 0)
        for codepoint in range(0x7f, 0xa0):
            with self.subTest(codepoint=hex(codepoint)):
                revision = self.run_cli('status')[1]['data']['revision']
                result, data = self.run_cli('checkpoint', '--from-file', self.draft('Plan'+chr(codepoint)),
                                            '--expect-revision', str(revision))
                self.assertEqual(result.returncode, 2)
                self.assertEqual(data['code'], 'INVALID_INPUT')
                self.assertNotIn(chr(codepoint), result.stdout)
        self.assertEqual(self.run_cli('status')[1]['data']['revision'], 0)

    def test_new_checkpoint_preserves_chinese_emoji_newline_and_tab(self):
        self.run_cli('init', '--name', 'XS input')
        text = '中文计划\n保留\t缩进 🙂'
        result, data = self.run_cli('checkpoint', '--from-file', self.draft(text), '--expect-revision', '0')
        self.assertEqual(result.returncode, 0, data)
        self.assertEqual(self.run_cli('status')[1]['data']['checkpoint']['objective'], text)

    def test_context_query_is_validated_before_optional_memory_branches(self):
        self.run_cli('init', '--name', 'Query validation')
        path = self.draft('Plan')
        self.run_cli('checkpoint', '--from-file', path, '--expect-revision', '0')
        for scenario in ('no_memory', 'memory_current', 'memory_changed'):
            if scenario == 'memory_current':
                memory = {'format': 'continuity-memory-v1', 'items': []}
                (self.project / 'memory.json').write_text(json.dumps(memory), encoding='utf-8')
                draft = json.loads(Path(path).read_text())
                draft['evidence'] = [{'path': 'memory.json', 'role': 'memory'}]
                Path(path).write_text(json.dumps(draft), encoding='utf-8')
                self.run_cli('checkpoint', '--from-file', path, '--expect-revision', '1')
            elif scenario == 'memory_changed':
                (self.project / 'memory.json').write_text('{}', encoding='utf-8')
            before = (self.project / '.continuity/state.sqlite3').read_bytes()
            for command in ('context', 'resume'):
                for cp in (127, 159):
                    with self.subTest(scenario=scenario, command=command, cp=cp):
                        result, data = self.run_cli(command, '--query', 'bad' + chr(cp))
                        self.assertEqual(data['code'], 'INVALID_INPUT')
                        self.assertEqual(result.returncode, 2)
                        self.assertIsNone(data['data'])
            self.assertEqual((self.project / '.continuity/state.sqlite3').read_bytes(), before)

    def storage_fault(self, fault):
        # The only injected boundary is the OS mkdir outcome, not Core logic.
        # A competing creator may win after the preliminary existence check.
        program = '''
from pathlib import Path
import runpy, sys
original = Path.mkdir
fault = sys.argv[3]
def mkdir(path, *args, **kwargs):
    if path.name == '.continuity':
        if fault == 'denied':
            raise PermissionError('synthetic disk permission failure')
        original(path, *args, **kwargs)
        (path / 'other-owner.txt').write_text('preserve this', encoding='utf-8')
    return original(path, *args, **kwargs)
Path.mkdir = mkdir
cli, project = sys.argv[1:3]
sys.argv = [cli, '--project', project, 'init', '--name', 'XS contender']
raise SystemExit(runpy.run_path(cli)['main']())
'''
        result = subprocess.run([sys.executable, '-B', '-c', program, str(CLI),
                                 str(self.project), fault], capture_output=True,
                                encoding='utf-8', timeout=15)
        return result, json.loads(result.stdout)

    def test_competing_storage_creator_is_not_reported_as_generic_io_failure(self):
        result, data = self.storage_fault('exists')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data['code'], 'ALREADY_INITIALIZED')
        self.assertEqual((self.project / '.continuity' / 'other-owner.txt').read_text(), 'preserve this')
        self.assertFalse((self.project / '.continuity' / 'state.sqlite3').exists())

    def test_real_storage_permission_failure_is_not_disguised_as_already_initialized(self):
        result, data = self.storage_fault('denied')
        self.assertEqual(result.returncode, 2)
        self.assertEqual(data['code'], 'IO_ERROR')
        self.assertFalse((self.project / '.continuity').exists())


if __name__ == '__main__':
    unittest.main()
