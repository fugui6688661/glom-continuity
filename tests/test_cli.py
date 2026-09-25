"""Behavioral acceptance at the executable CLI boundary; no private DB assertions."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / 'scripts' / 'continuity.py'


class ContinuityCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / 'project'
        self.project.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args, ok=True, project=None):
        result = subprocess.run(
            [sys.executable, '-B', str(CLI), '--project', str(project or self.project), *args],
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['ok'], ok)
        if ok and '--max-chars' in args:
            self.assertLessEqual(len(result.stdout), int(args[args.index('--max-chars') + 1]))
        return data

    def draft(self):
        (self.project / 'input.csv').write_text('item,amount\nA,10\nB,20\n', encoding='utf-8')
        payload = {
            'objective': '制作汇总表，金额保持不变',
            'next_action': '检查两行金额合计为30，再准备汇总',
            'constraints': ['不得上传原始客户文件'],
            'decisions': ['已否决删除缺失行的方案'],
            'unresolved': ['币种待确认'],
            'evidence': [{'path': 'input.csv', 'role': 'input'}],
        }
        path = self.project / 'draft.json'
        path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
        return path

    def test_new_process_recovers_objective_constraints_and_next_action(self):
        initialized = self.run_cli('init', '--name', '中文演示项目')['data']
        self.assertTrue(initialized['project_id'])
        self.run_cli('checkpoint', '--from-file', str(self.draft()), '--expect-revision', '0')
        state = self.run_cli('status')['data']
        self.assertEqual(state['revision'], 1)
        self.assertEqual(state['checkpoint']['objective'], '制作汇总表，金额保持不变')
        self.assertEqual(state['checkpoint']['constraints'], ['不得上传原始客户文件'])
        self.assertEqual(state['checkpoint']['next_action'], '检查两行金额合计为30，再准备汇总')
        self.assertEqual(self.run_cli('check')['data']['state'], 'references_current')
        self.assertFalse(self.run_cli('check')['data']['semantic_completion_verified'])
        context = self.run_cli('context')['data']
        self.assertEqual(context['next_action_status'], 'recorded_unverified')
        self.assertEqual(context['instruction_authority'], 'none')
        self.assertFalse(context['check']['semantic_completion_verified'])

    def test_storage_recovery_never_initializes_or_replaces_unknown_data(self):
        self.assertEqual(self.run_cli('recover-storage', ok=False)['code'], 'NOT_INITIALIZED')
        self.assertFalse((self.project / '.continuity').exists())
        self.run_cli('init', '--name', 'Synthetic healthy recovery')
        self.run_cli('checkpoint', '--from-file', str(self.draft()), '--expect-revision', '0')
        before = self.run_cli('status')['data']
        self.assertEqual(self.run_cli('recover-storage')['data'], before)
        self.assertEqual(self.run_cli('recover-storage')['data'], before)
        self.assertEqual(self.run_cli('status')['data'], before)
        foreign = self.root / 'unrecognized'
        storage = foreign / '.continuity'
        storage.mkdir(parents=True)
        raw = b'Synthetic unknown storage. Do not replace.'
        database = storage / 'state.sqlite3'
        database.write_bytes(raw)
        refused = self.run_cli('recover-storage', ok=False, project=foreign)
        self.assertEqual(refused['code'], 'IO_ERROR')
        self.assertEqual(database.read_bytes(), raw)
        self.assertEqual(list(storage.iterdir()), [database])

    def test_machine_output_is_utf8_even_with_a_legacy_pipe_encoding(self):
        for encoding in ('ascii', 'cp1252', 'gbk'):
            with self.subTest(encoding=encoding):
                project = self.root / encoding
                project.mkdir()
                env = dict(os.environ, PYTHONIOENCODING=encoding)
                command = [sys.executable, '-B', str(CLI), '--project', str(project)]
                for args in (['init', '--name', '中文项目 café — 灯'], ['status']):
                    result = subprocess.run(command + args, env=env, capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    data = json.loads(result.stdout.decode('utf-8'))
                    self.assertTrue(result.stdout.endswith(b'\n'))
                    self.assertFalse(result.stdout.endswith(b'\r\n'))
                    self.assertEqual(data['data']['name'], '中文项目 café — 灯')
                    self.assertEqual(result.stderr, b'')

    def test_context_has_a_strict_wire_budget_and_never_hides_critical_state(self):
        self.run_cli('init', '--name', '恢复测试')
        self.run_cli('checkpoint', '--from-file', str(self.draft()), '--expect-revision', '0')
        result = self.run_cli('context', '--max-chars', '1500')
        self.assertIn('不得上传原始客户文件', result['data']['text'])
        self.assertIn('检查两行金额合计为30', result['data']['text'])
        self.assertIn('币种待确认', result['data']['text'])
        too_small = self.run_cli('context', '--max-chars', '256', ok=False)
        self.assertEqual(too_small['code'], 'BUDGET_TOO_SMALL')
        (self.project / 'input.csv').write_text('item,amount\nA,999\n', encoding='utf-8')
        self.assertEqual(self.run_cli('check')['data']['state'], 'needs_review')
        self.assertEqual(self.run_cli('context', '--max-chars', '1500')['data']['check']['state'], 'needs_review')

    def test_handoff_is_single_use_scoped_and_rechecked_before_acceptance(self):
        self.run_cli('init', '--name', '接手测试')
        self.run_cli('checkpoint', '--from-file', str(self.draft()), '--expect-revision', '0')
        handoff = self.run_cli('handoff', '--recipient', 'harness', '--expect-revision', '1')['data']
        self.assertEqual(self.run_cli('accept', '--id', handoff['handoff_id'], '--recipient', 'wrong', ok=False)['code'], 'WRONG_RECIPIENT')
        (self.project / 'input.csv').write_text('changed', encoding='utf-8')
        self.assertEqual(self.run_cli('accept', '--id', handoff['handoff_id'], '--recipient', 'harness', ok=False)['code'], 'EVIDENCE_CHANGED')
        self.draft()  # restore exact input; the failed acceptance must not have consumed the handoff
        accepted = self.run_cli('accept', '--id', handoff['handoff_id'], '--recipient', 'harness')['data']
        self.assertEqual(accepted['state'], 'accepted')
        self.assertEqual(accepted['checkpoint']['unresolved'], ['币种待确认'])
        self.assertEqual(self.run_cli('accept', '--id', handoff['handoff_id'], '--recipient', 'harness', ok=False)['code'], 'ALREADY_ACCEPTED')
        other = self.root / 'other'
        other.mkdir()
        self.run_cli('init', '--name', '其他项目', project=other)
        self.assertEqual(self.run_cli('accept', '--id', handoff['handoff_id'], '--recipient', 'harness', ok=False, project=other)['code'], 'HANDOFF_NOT_FOUND')

    def test_changed_input_warns_in_the_handoff_text_without_rewriting_the_checkpoint(self):
        self.run_cli('init', '--name', '旧步骤不能冒充新指令')
        self.run_cli('checkpoint', '--from-file', str(self.draft()), '--expect-revision', '0')
        before = self.run_cli('status')['data']
        (self.project / 'input.csv').write_text('item,amount\nA,999\n', encoding='utf-8')
        result = self.run_cli('context', '--max-chars', '1500')['data']
        self.assertIn('Reference check: needs_review', result['text'])
        self.assertIn('Review changed or unavailable references before using the recorded next step.', result['text'])
        self.assertIn('input.csv', result['text'])
        self.assertIn('Recorded next step (not revalidated): 检查两行金额合计为30，再准备汇总', result['text'])
        self.assertEqual(result['next_action_status'], 'requires_reference_review')
        self.assertEqual(result['instruction_authority'], 'none')
        after = self.run_cli('status')['data']
        self.assertEqual(after, before)

    def test_receipt_can_be_recovered_after_the_receiver_process_exits(self):
        self.run_cli('init', '--name', '回执恢复')
        self.run_cli('checkpoint', '--from-file', str(self.draft()), '--expect-revision', '0')
        handoff = self.run_cli('handoff', '--recipient', 'codex', '--expect-revision', '1')['data']
        self.run_cli('accept', '--id', handoff['handoff_id'], '--recipient', 'codex')
        recovered = self.run_cli('receipt', '--id', handoff['handoff_id'])['data']
        self.assertEqual(recovered['state'], 'accepted')
        self.assertEqual(recovered['revision'], 1)
        self.assertTrue(recovered['accepted_at'])
        self.assertFalse(recovered['external_actions_verified'])

    def test_export_is_explicit_metadata_only_and_never_overwrites(self):
        self.run_cli('init', '--name', '便携任务包')
        self.run_cli('checkpoint', '--from-file', str(self.draft()), '--expect-revision', '0')
        exported = self.run_cli('export', '--output', 'handoff.json')['data']
        self.assertEqual(exported['path'], 'handoff.json')
        contents = (self.project / 'handoff.json').read_text(encoding='utf-8')
        bundle = json.loads(contents)
        self.assertEqual(bundle['format'], 'continuity-review-bundle-v1')
        self.assertEqual(bundle['checkpoint']['unresolved'], ['币种待确认'])
        self.assertFalse(bundle['grants_permission'])
        self.assertNotIn('A,10', contents)
        self.assertNotIn(str(self.root), contents)
        self.assertEqual(self.run_cli('export', '--output', 'handoff.json', ok=False)['code'], 'OUTPUT_EXISTS')
        self.assertEqual(self.run_cli('export', '--output', '../escape.json', ok=False)['code'], 'UNSAFE_PATH')
        self.assertFalse((self.root / 'escape.json').exists())

    def test_checkpoint_without_files_does_not_claim_reference_verification(self):
        self.run_cli('init', '--name', '规划阶段')
        path = self.draft()
        payload = json.loads(path.read_text())
        payload['evidence'] = []
        path.write_text(json.dumps(payload))
        self.run_cli('checkpoint', '--from-file', str(path), '--expect-revision', '0')
        checked = self.run_cli('check')['data']
        self.assertEqual(checked['state'], 'no_references')
        self.assertFalse(checked['semantic_completion_verified'])
        context = self.run_cli('context')['data']
        self.assertEqual(context['next_action_status'], 'recorded_unverified')
        self.assertEqual(context['instruction_authority'], 'none')
        self.assertIn('Reference check: no_references', context['text'])
        self.assertFalse(context['check']['semantic_completion_verified'])

    def test_business_error_has_a_uniform_envelope(self):
        result = self.run_cli('status', ok=False)
        self.assertEqual(result['code'], 'NOT_INITIALIZED')
        self.assertIn('data', result)
        self.assertIsNone(result['data'])

    def test_prefixed_credential_assignments_are_rejected(self):
        self.run_cli('init', '--name', '配置边界')
        for key in ('AWS_SECRET_ACCESS_KEY', 'GOOGLE_CLIENT_SECRET'):
            with self.subTest(key=key):
                draft = self.draft()
                value = json.loads(draft.read_text())
                value['decisions'] = [key + '=synthetic-fixture-not-real']
                draft.write_text(json.dumps(value))
                result = self.run_cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0', ok=False)
                self.assertEqual(result['code'], 'SENSITIVE_CONTENT')
                self.assertEqual(self.run_cli('status')['data']['revision'], 0)


if __name__ == '__main__':
    unittest.main()
