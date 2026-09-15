"""Project habits/workflows through fresh CLI processes; no DB side channels."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProjectMemory(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / '项目'
        self.project.mkdir()
        self.cli('init', '--name', '单助手长期项目')

    def cli(self, *args, ok=True):
        p = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
                            '--project', str(self.project), *args],
                           capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(p.returncode, 0 if ok else 2, p.stdout + p.stderr)
        value = json.loads(p.stdout)
        self.assertEqual(value['ok'], ok)
        return value

    def note(self, identifier, kind='preference', when=None, **overrides):
        result = dict(id=identifier, kind=kind, title=identifier,
                    body='用中文解释，并区分已完成和未验证。',
                    when=['*'] if when is None else when, status='active',
                    source='用户明确要求，测试用虚构记录', expires_at=None)
        result.update(overrides)
        return result

    def save(self, items, revision=0, ok=True):
        self.memory = {'format': 'continuity-memory-v1', 'items': items}
        (self.project / 'habits.json').write_text(json.dumps(self.memory, ensure_ascii=False), encoding='utf-8')
        self.draft = dict(objective='制作品牌说明', next_action='继续整理材料',
                          constraints=['未经许可不发布'], decisions=[], unresolved=['标价待确认'],
                          evidence=[{'path': 'habits.json', 'role': 'memory'}])
        (self.project / 'checkpoint.json').write_text(json.dumps(self.draft, ensure_ascii=False), encoding='utf-8')
        return self.cli('checkpoint', '--from-file', str(self.project / 'checkpoint.json'),
                        '--expect-revision', str(revision), ok=ok)

    def test_new_process_recalls_habits_and_only_the_relevant_workflow(self):
        self.save([self.note('plain-language'), self.note('film', 'workflow', ['视频', 'video']),
                   self.note('data', 'workflow', ['表格'])])
        data = self.cli('context', '--query', '制作一个VIDEO视频', '--max-chars', '6000')['data']
        self.assertEqual([x['id'] for x in data['memory']['selected']], ['plain-language', 'film'])
        self.assertEqual(data['memory']['omitted'], [{'path': 'habits.json', 'id': 'data', 'reason': 'not_matched'}])
        self.assertIn('未经许可不发布', data['text'])
        self.assertIn('标价待确认', data['text'])
        self.assertIn('用中文解释', data['text'])
        self.assertEqual(data['instruction_authority'], 'none')
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    def test_candidates_retired_and_expired_notes_never_enter_recommended_context(self):
        self.save([self.note('current'), self.note('candidate', status='candidate', body='未经确认的猜测'),
                   self.note('old', status='retired', body='已经否定的旧习惯'),
                   self.note('temporary', expires_at='2001-01-01T08:00:00+08:00', body='已过期的临时流程')])
        data = self.cli('context')['data']
        self.assertEqual([x['id'] for x in data['memory']['selected']], ['current'])
        self.assertEqual({x['id']: x['reason'] for x in data['memory']['omitted']},
                         {'candidate': 'candidate', 'old': 'retired', 'temporary': 'expired'})
        for body in ('未经确认的猜测', '已经否定的旧习惯', '已过期的临时流程'):
            self.assertNotIn(body, data['text'])

    def test_changed_habit_requires_review_and_new_checkpoint_before_reuse(self):
        self.save([self.note('style', body='采用旧版风格')])
        handoff = self.cli('handoff', '--recipient', 'next-session', '--expect-revision', '1')['data']
        self.memory['items'][0]['body'] = '采用经过重新确认的新风格'
        (self.project / 'habits.json').write_text(json.dumps(self.memory, ensure_ascii=False), encoding='utf-8')
        data = self.cli('context')['data']
        self.assertEqual(data['check']['state'], 'needs_review')
        self.assertEqual(data['memory']['state'], 'requires_reference_review')
        self.assertEqual(data['memory']['selected'], [])
        self.assertNotIn('采用经过重新确认的新风格', data['text'])
        self.assertEqual(self.cli('status')['data']['revision'], 1)
        self.assertEqual(self.cli('accept', '--id', handoff['handoff_id'], '--recipient', 'next-session', ok=False)['code'], 'EVIDENCE_CHANGED')
        self.cli('checkpoint', '--from-file', str(self.project / 'checkpoint.json'), '--expect-revision', '1')
        refreshed = self.cli('context')['data']
        self.assertEqual(refreshed['revision'], 2)
        self.assertIn('采用经过重新确认的新风格', refreshed['text'])
        self.assertNotIn('采用旧版风格', refreshed['text'])
        self.assertEqual(self.cli('accept', '--id', handoff['handoff_id'], '--recipient', 'next-session', ok=False)['code'], 'STALE_HANDOFF')

    def test_duplicate_identity_across_memory_files_is_not_silently_merged(self):
        self.save([self.note('style', body='采用浅色主题')])
        other = {'format': 'continuity-memory-v1', 'items': [self.note('style', body='采用深色主题')]}
        (self.project / 'other.json').write_text(json.dumps(other), encoding='utf-8')
        self.draft['evidence'].append({'path': 'other.json', 'role': 'memory'})
        (self.project / 'checkpoint.json').write_text(json.dumps(self.draft), encoding='utf-8')
        result = self.cli('checkpoint', '--from-file', str(self.project / 'checkpoint.json'), '--expect-revision', '1', ok=False)
        self.assertEqual(result['code'], 'MEMORY_CONFLICT')
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    def test_without_query_only_general_preferences_are_loaded(self):
        self.save([self.note('common'), self.note('video-only', when=['视频']),
                   self.note('workflow', 'workflow', ['视频'])])
        (self.project / 'unregistered.json').write_text('This unregistered file must not be read.', encoding='utf-8')
        data = self.cli('context')['data']
        self.assertEqual([x['id'] for x in data['memory']['selected']], ['common'])
        self.assertNotIn('unregistered', json.dumps(data))

    def test_keyword_matching_is_literal_not_regex(self):
        self.save([self.note('literal', 'workflow', ['[A-Z]'])])
        data = self.cli('context', '--query', 'XYZ')['data']
        self.assertEqual(data['memory']['selected'], [])
        self.assertEqual(self.cli('context', '--query', '[a-z]')['data']['memory']['selected'][0]['id'], 'literal')

    def test_too_small_budget_returns_no_partial_memory_or_constraints(self):
        self.save([self.note('long', body='完整要求' * 500)])
        result = self.cli('context', '--max-chars', '1000', ok=False)
        self.assertEqual(result['code'], 'BUDGET_TOO_SMALL')
        self.assertIsNone(result['data'])
        full = self.cli('context', '--max-chars', '12000')['data']
        self.assertEqual(full['memory']['selected'][0]['body'], '完整要求' * 500)

    def test_invalid_note_never_advances_checkpoint(self):
        for override in ({'expires_at': '2030-01-01'}, {'status': 'confirmed-by-model'},
                         {'when': []}, {'kind': 'workflow', 'when': ['*']},
                         {'id': '../escape'}, {'body': ''}, {'unknown_field': 'value'}):
            with self.subTest(override=override):
                result = self.save([self.note('invalid', **override)], ok=False)
                self.assertEqual(result['code'], 'INVALID_INPUT')
                self.assertEqual(self.cli('status')['data']['revision'], 0)

    def test_sensitive_body_is_not_saved_or_echoed(self):
        value = 'password=synthetic-secret-not-real'
        result = self.save([self.note('secret', body=value)], ok=False)
        self.assertEqual(result['code'], 'SENSITIVE_CONTENT')
        self.assertNotIn(value, json.dumps(result))
        self.assertEqual(self.cli('status')['data']['revision'], 0)

    def test_unpaired_surrogates_are_rejected_before_replacing_good_checkpoint(self):
        self.save([self.note('good', body='已确认的旧要求')])
        draft = dict(self.draft, evidence=[{'path': 'bad-memory.json', 'role': 'memory'}])
        (self.project / 'bad-checkpoint.json').write_text(json.dumps(draft), encoding='utf-8')
        for scalar in ('\ud800', '\udc00'):
            for field in ('title', 'body', 'source', 'when'):
                with self.subTest(scalar=repr(scalar), field=field):
                    value = ['video' + scalar] if field == 'when' else 'Synthetic ' + scalar
                    document = {'format': 'continuity-memory-v1', 'items': [self.note('bad', **{field: value})]}
                    # JSON escapes are valid UTF-8 bytes but may decode into lone surrogates.
                    (self.project / 'bad-memory.json').write_text(json.dumps(document, ensure_ascii=True), encoding='utf-8')
                    rejected = self.cli('checkpoint', '--from-file', str(self.project / 'bad-checkpoint.json'),
                                        '--expect-revision', '1', ok=False)
                    self.assertEqual(rejected['code'], 'INVALID_INPUT')
                    self.assertIn('memory.' + field, rejected['error'])
                    self.assertEqual(self.cli('status')['data']['revision'], 1)
                    self.assertEqual(self.cli('context')['data']['memory']['selected'][0]['body'], '已确认的旧要求')

    def test_valid_unicode_scalars_round_trip_from_escaped_json(self):
        self.save([self.note('unicode', body='中文🌙𠮷é')])
        (self.project / 'habits.json').write_text(json.dumps(self.memory, ensure_ascii=True), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(self.project / 'checkpoint.json'), '--expect-revision', '1')
        self.assertEqual(self.cli('context')['data']['memory']['selected'][0]['body'], '中文🌙𠮷é')

    def test_missing_memory_preserves_checkpoint_and_reports_review(self):
        self.save([self.note('common')])
        (self.project / 'habits.json').rename(self.project / 'removed-by-user.json')
        data = self.cli('context')['data']
        self.assertEqual(data['memory']['selected'], [])
        self.assertEqual(data['check']['state'], 'needs_review')
        self.assertEqual(data['check']['issues'], [{'path': 'habits.json', 'code': 'MISSING_FILE'}])

    def test_ordinary_input_changes_also_withhold_workflows(self):
        self.save([self.note('workflow', 'workflow', ['video'])])
        (self.project / 'input.txt').write_text('old input')
        self.draft['evidence'].append({'path': 'input.txt', 'role': 'input'})
        (self.project / 'checkpoint.json').write_text(json.dumps(self.draft))
        self.cli('checkpoint', '--from-file', str(self.project / 'checkpoint.json'), '--expect-revision', '1')
        (self.project / 'input.txt').write_text('changed input')
        data = self.cli('context', '--query', 'video')['data']
        self.assertEqual(data['memory']['selected'], [])
        self.assertEqual(data['next_action_status'], 'requires_reference_review')

    def test_oversize_memory_and_wrong_encoding_are_rejected(self):
        self.save([self.note('common')])
        for raw, code in ((b' ' * (128 * 1024 + 1), 'FILE_TOO_LARGE'),
                          (json.dumps(self.memory).encode('utf-16'), 'INVALID_INPUT')):
            with self.subTest(code=code):
                (self.project / 'habits.json').write_bytes(raw)
                result = self.cli('checkpoint', '--from-file', str(self.project / 'checkpoint.json'), '--expect-revision', '1', ok=False)
                self.assertEqual(result['code'], code)
                self.assertEqual(self.cli('status')['data']['revision'], 1)

    def test_symlinked_memory_cannot_load_another_project(self):
        if sys.platform == 'win32':
            self.skipTest('POSIX symlink fixture; Windows requires separate privilege handling')
        self.save([self.note('common')])
        original = self.project / 'habits.json'
        outside = Path(self.temp.name) / 'outside.json'
        original.rename(outside)
        original.symlink_to(outside)
        data = self.cli('context')['data']
        self.assertEqual(data['memory']['selected'], [])
        self.assertEqual(data['check']['issues'][0]['code'], 'UNSAFE_PATH')

    def test_new_user_can_run_single_assistant_memory_demo(self):
        output = self.project / 'demo'
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/memory_demo.py'),
                                 '--output', str(output)], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['state'], 'memory_demo_passed')
        self.assertFalse(receipt['real_model_verified'])
        self.assertTrue((output / '演示结果.md').is_file())
        original = (output / '演示结果.md').read_bytes()
        again = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/memory_demo.py'),
                                '--output', str(output)], capture_output=True, text=True, timeout=20)
        self.assertNotEqual(again.returncode, 0)
        self.assertEqual((output / '演示结果.md').read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
