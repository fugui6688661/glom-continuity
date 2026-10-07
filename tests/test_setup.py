"""Public first-use binding and explicitly requested project instructions."""
import json
import hashlib
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Setup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "中文 project ' $draft"
        self.project.mkdir()

    def command(self, argv, ok=True):
        result = subprocess.run(argv, capture_output=True, text=True,
                                encoding='utf-8', timeout=15, cwd=self.temp.name)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stdout + result.stderr)
        response = json.loads(result.stdout)
        self.assertEqual(response['ok'], ok)
        return response

    def cli(self, *args, ok=True):
        return self.command([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
                             '--project', str(self.project), *args], ok=ok)

    def test_generated_entry_line_endings_are_bytes_not_platform_text(self):
        self.cli('init', '--name', 'Exact managed entry')
        preview = self.cli('setup', '--host', 'codex')['data']['project_entry']
        active = self.project / 'AGENTS.md'
        content = preview['content'].encode('utf-8')
        active.write_bytes(content)
        self.assertEqual(self.cli('entry', 'status', '--host', 'codex')['data']['state'], 'active')
        self.assertEqual(active.read_bytes(), content)
        # Text-mode fixture writes on Windows used to alter the approved bytes.
        # This is an edited entry, not permission to silently normalize a rule.
        transformed = content.replace(b'\n', b'\r\n')
        active.write_bytes(transformed)
        refused = self.cli('entry', 'status', '--host', 'codex', ok=False)
        self.assertEqual(refused['code'], 'ENTRY_UNRECOGNIZED')
        self.assertEqual(active.read_bytes(), transformed)
        active.write_bytes(content)
        self.assertEqual(self.cli('entry', 'status', '--host', 'codex')['data']['state'], 'active')

    def test_one_command_returns_real_bound_recovery_without_host_claim(self):
        initial = self.cli('init', '--name', 'An existing project')['data']
        draft = self.project / 'draft.json'
        draft.write_text(json.dumps(dict(objective='Plan an event for 50 people',
            next_action='Compare two venues', constraints=['Budget is 5000; no payment'],
            decisions=[], unresolved=['Venue unknown'], evidence=[])), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
        card = self.cli('setup')['data']
        self.assertEqual(card['setup_state'], 'ready_for_manual_binding')
        self.assertTrue(card['read_only'])
        self.assertFalse(card['host_integrated'])
        self.assertFalse(card['automatic_restore'])
        self.assertFalse(card['automatic_save'])
        binding = card['binding']
        self.assertEqual(binding['project_path'], str(self.project.resolve()))
        self.assertEqual(binding['project_id'], initial['project_id'])
        self.assertEqual(binding['guide_state'], 'source_unsealed')
        self.assertTrue(Path(binding['skill_path']).is_file())
        self.assertIn('--expect-project-id', binding['resume_argv'])
        checked = self.command(binding['doctor_argv'])['data']
        self.assertEqual(checked['runtime']['program_sha256'], binding['program_sha256'])
        restored = self.command(binding['resume_argv'])['data']
        self.assertEqual(restored['project_id'], initial['project_id'])
        self.assertIn('Budget is 5000; no payment', restored['text'])
        self.assertIn('Venue unknown', restored['text'])
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    def test_empty_project_explains_first_save_without_creating_storage(self):
        card = self.cli('setup')['data']
        self.assertEqual(card['setup_state'], 'requires_initialization')
        self.assertIsNone(card['binding'])
        self.assertFalse(card['grants_permission'])
        self.assertEqual(list(self.project.iterdir()), [])

    def test_upgrade_preview_is_read_only_and_binds_the_invoked_new_runtime(self):
        self.cli('init', '--name', 'Upgrade preview')
        old_root = Path(self.temp.name) / 'old-runtime'
        (old_root / 'scripts').mkdir(parents=True)
        (old_root / 'skills/project-continuity').mkdir(parents=True)
        old_program = old_root / 'scripts/continuity.py'
        old_program.write_bytes((ROOT / 'scripts/continuity.py').read_bytes() + b'\n# Old fixture build\n')
        (old_root / 'skills/project-continuity/SKILL.md').write_text('Synthetic old guide', encoding='utf-8')
        old_prefix = [sys.executable, '-B', str(old_program), '--project', str(self.project)]
        old_rule = self.command(old_prefix + ['setup', '--host', 'codex'])['data']['project_entry']
        (self.project / 'AGENTS.md').write_bytes((old_rule['content']).encode('utf-8'))
        before = {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        preview = self.cli('entry', 'upgrade', '--host', 'codex')['data']
        self.assertTrue(preview['read_only'])
        self.assertFalse(preview['host_loading_verified'])
        self.assertEqual(preview['state'], 'active')
        upgrade = preview['upgrade']
        self.assertEqual(upgrade['outcome'], 'preview')
        self.assertEqual(upgrade['old_sha256'], old_rule['sha256'])
        self.assertNotEqual(upgrade['new_sha256'], old_rule['sha256'])
        self.assertEqual(upgrade['new_sha256'], hashlib.sha256(upgrade['content'].encode()).hexdigest())
        self.assertEqual(upgrade['binding']['doctor_argv'][2], str(ROOT / 'scripts/continuity.py'))
        self.assertEqual(self.command(upgrade['binding']['resume_argv'])['data']['project_id'], preview['project_id'])
        self.assertEqual(before, {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob('*') if p.is_file()})

    def test_upgrade_applies_reviewed_binding_preserves_old_bytes_and_paused_state(self):
        old_root = Path(self.temp.name) / 'old-runtime'
        (old_root / 'scripts').mkdir(parents=True)
        (old_root / 'skills/project-continuity').mkdir(parents=True)
        old_program = old_root / 'scripts/continuity.py'
        old_program.write_bytes((ROOT / 'scripts/continuity.py').read_bytes() + b'\n# Old fixture build\n')
        (old_root / 'skills/project-continuity/SKILL.md').write_text('Synthetic old guide', encoding='utf-8')
        for host, relative in [('codex', 'AGENTS.md'), ('claude-code', '.claude/rules/recaloom.md'),
                               ('workbuddy', '.codebuddy/CODEBUDDY.md')]:
            for state in ('active', 'paused'):
                with self.subTest(host=host, state=state):
                    self.project = Path(self.temp.name) / (host + '-' + state)
                    self.project.mkdir()
                    self.cli('init', '--name', 'Keep memory through upgrade')
                    draft = self.project / 'draft.json'
                    draft.write_text(json.dumps(dict(objective='Workshop for 18 people',
                        next_action='Compare rooms', constraints=['Budget 2300; no booking'], decisions=[],
                        unresolved=['Date unknown'], evidence=[])), encoding='utf-8')
                    self.cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
                    old_rule = self.command([sys.executable, '-B', str(old_program), '--project', str(self.project),
                                             'setup', '--host', host])['data']['project_entry']
                    active = self.project / relative
                    active.parent.mkdir(parents=True, exist_ok=True)
                    selected = active if state == 'active' else active.with_name('.recaloom-' + host + '.paused')
                    selected.write_bytes((old_rule['content']).encode('utf-8'))
                    database = self.project / '.continuity/state.sqlite3'
                    original = database.read_bytes()
                    preview = self.cli('entry', 'upgrade', '--host', host)['data']['upgrade']
                    args = ['entry', 'upgrade', '--host', host, '--apply', '--expect-state', state, '--expect-sha256',
                            preview['old_sha256'], '--expect-new-sha256', preview['new_sha256']]
                    if sys.platform not in ('darwin', 'linux'):
                        self.assertEqual(self.cli(*args, ok=False)['code'], 'ENTRY_EXCHANGE_UNSUPPORTED')
                        self.assertEqual(selected.read_text(), old_rule['content'])
                        continue
                    result = self.cli(*args)['data']
                    self.assertEqual(result['upgrade']['outcome'], 'exchange_observed')
                    self.assertEqual(result['state'], state)
                    self.assertTrue(result['runtime_binding_matches'])
                    self.assertEqual(selected.read_text(), preview['content'])
                    retained = self.project / result['upgrade']['retained_path']
                    self.assertEqual(retained.read_text(), old_rule['content'])
                    self.assertNotEqual(retained.suffix, '.md')
                    self.assertEqual(self.cli('entry', 'status', '--host', host)['data']['state'], state)
                    self.assertEqual(active.exists(), state == 'active')
                    self.assertIn('Budget 2300; no booking', self.command(preview['binding']['resume_argv'])['data']['text'])
                    self.assertEqual(database.read_bytes(), original)
                    files = {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
                    same = self.cli('entry', 'upgrade', '--host', host)['data']['upgrade']
                    again = self.cli('entry', 'upgrade', '--host', host, '--apply', '--expect-state', state, '--expect-sha256',
                                     same['old_sha256'], '--expect-new-sha256', same['new_sha256'])['data']
                    self.assertTrue(again['read_only'])
                    self.assertEqual(again['upgrade']['outcome'], 'already_current')
                    self.assertEqual(files, {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()})

    def test_upgrade_requires_both_reviewed_digests_and_refuses_changed_preview(self):
        self.cli('init', '--name', 'Reviewed upgrade only')
        rule = self.cli('setup', '--host', 'codex')['data']['project_entry']
        active = self.project / 'AGENTS.md'
        active.write_bytes((rule['content']).encode('utf-8'))
        preview = self.cli('entry', 'upgrade', '--host', 'codex')['data']['upgrade']
        before = {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        for flags, code in [([], 'ENTRY_EXPECTATION_REQUIRED'),
                            (['--expect-sha256', preview['old_sha256']], 'ENTRY_EXPECTATION_REQUIRED'),
                            (['--expect-sha256', '0'*64, '--expect-new-sha256', preview['new_sha256']], 'ENTRY_CHANGED'),
                            (['--expect-sha256', preview['old_sha256'], '--expect-new-sha256', '0'*64], 'ENTRY_CHANGED'),
                            (['--max-chars', '10'], 'BUDGET_TOO_SMALL')]:
            with self.subTest(code=code, flags=flags):
                self.assertEqual(self.cli('entry', 'upgrade', '--host', 'codex', '--apply', '--expect-state', 'active', *flags, ok=False)['code'], code)
                self.assertEqual(before, {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()})
        # A newly saved checkpoint changes the proposed binding's reviewed revision.
        draft = self.project / 'draft.json'
        draft.write_text(json.dumps(dict(objective='Changed goal', next_action='Review only', constraints=[],
                                         decisions=[], unresolved=[], evidence=[])), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
        self.assertEqual(self.cli('entry', 'upgrade', '--host', 'codex', '--apply', '--expect-state', 'active',
            '--expect-sha256', preview['old_sha256'], '--expect-new-sha256', preview['new_sha256'], ok=False)['code'], 'ENTRY_CHANGED')
        active.write_bytes((rule['content'] + '\nMy personal rule.\n').encode('utf-8'))
        self.assertEqual(self.cli('entry', 'upgrade', '--host', 'codex', ok=False)['code'], 'ENTRY_UNRECOGNIZED')
        self.assertTrue(active.read_text().endswith('My personal rule.\n'))
        self.assertEqual(list(self.project.glob('.recaloom-*.upgrade-*')), [])

    def test_upgrade_retains_staged_file_on_flush_failure_and_reports_no_exchange(self):
        self.cli('init', '--name', 'Upgrade write failure')
        old = self.cli('setup', '--host', 'codex')['data']['project_entry']
        active = self.project / 'AGENTS.md'
        active.write_bytes((old['content']).encode('utf-8'))
        draft = self.project / 'draft.json'
        draft.write_text(json.dumps(dict(objective='New checkpoint', next_action='Review', constraints=[],
                                         decisions=[], unresolved=[], evidence=[])), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
        preview = self.cli('entry', 'upgrade', '--host', 'codex')['data']['upgrade']
        args = ['entry', 'upgrade', '--host', 'codex', '--apply', '--expect-state', 'active', '--expect-sha256', preview['old_sha256'],
                '--expect-new-sha256', preview['new_sha256']]
        if sys.platform not in ('darwin', 'linux'):
            self.assertEqual(self.cli(*args, ok=False)['code'], 'ENTRY_EXCHANGE_UNSUPPORTED')
            return
        # Fail actual filesystem flush through the OS seam, not a product helper.
        script = ('import sys,runpy,errno; from unittest.mock import patch; sys.argv=sys.argv[1:]; '
                  'p=patch("os.fsync",side_effect=OSError(errno.ENOSPC,"fixture disk full")); '
                  'p.start(); runpy.run_path(sys.argv[0],run_name="__main__")')
        failed = self.command([sys.executable, '-I', '-B', '-c', script, str(ROOT / 'scripts/continuity.py'),
                               '--project', str(self.project), *args])['data']
        self.assertEqual(failed['state'], 'needs_review')
        self.assertFalse(failed['read_only'])
        operation = failed['upgrade']
        self.assertEqual(operation['native_result'], 'not_attempted')
        self.assertEqual(operation['stage'], 'writing')
        self.assertEqual(operation['retained_role'], 'partial_or_unknown')
        self.assertEqual(operation['io_errno'], 28)
        self.assertEqual(active.read_text(), old['content'])
        self.assertTrue((self.project / operation['retained_path']).exists())
        self.assertEqual(len(list(self.project.glob('.recaloom-*.upgrade-*'))), 1)

    def test_upgrade_cannot_change_selected_state_after_preview(self):
        self.cli('init', '--name', 'Respect a later pause')
        old = self.cli('setup', '--host', 'codex')['data']['project_entry']
        active = self.project / 'AGENTS.md'
        active.write_bytes((old['content']).encode('utf-8'))
        preview = self.cli('entry', 'upgrade', '--host', 'codex')['data']
        paused = self.project / '.recaloom-codex.paused'
        active.rename(paused)  # External user pause of our owned fixture after preview.
        before = {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}
        refused = self.cli('entry', 'upgrade', '--host', 'codex', '--apply',
            '--expect-state', preview['state'], '--expect-sha256', preview['upgrade']['old_sha256'],
            '--expect-new-sha256', preview['upgrade']['new_sha256'], ok=False)
        self.assertEqual(refused['code'], 'ENTRY_CHANGED')
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.project.rglob('*') if p.is_file()})

    def test_upgrade_interference_after_staging_preserves_both_files_without_exchange(self):
        self.cli('init', '--name', 'Concurrent editor')
        old = self.cli('setup', '--host', 'codex')['data']['project_entry']
        active = self.project / 'AGENTS.md'
        active.write_bytes((old['content']).encode('utf-8'))
        draft = self.project / 'draft.json'
        draft.write_text(json.dumps(dict(objective='Changed checkpoint', next_action='Review', constraints=[],
                                         decisions=[], unresolved=[], evidence=[])), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
        preview = self.cli('entry', 'upgrade', '--host', 'codex')['data']['upgrade']
        args = ['entry', 'upgrade', '--host', 'codex', '--apply', '--expect-state', 'active',
                '--expect-sha256', preview['old_sha256'], '--expect-new-sha256', preview['new_sha256']]
        if sys.platform not in ('darwin', 'linux'):
            self.assertEqual(self.cli(*args, ok=False)['code'], 'ENTRY_EXCHANGE_UNSUPPORTED')
            return
        script = '''import os,sys,runpy
from pathlib import Path
from unittest.mock import patch
sys.argv=sys.argv[1:]
project=Path(sys.argv[sys.argv.index('--project')+1])
original=os.fsync
def concurrent_edit(fd):
    original(fd)
    (project/'AGENTS.md').write_text('A new rule from the user',encoding='utf-8')
with patch('os.fsync',concurrent_edit):
    runpy.run_path(sys.argv[0],run_name='__main__')
'''
        reply = self.command([sys.executable, '-I', '-B', '-c', script, str(ROOT / 'scripts/continuity.py'),
                              '--project', str(self.project), *args])['data']
        self.assertEqual(reply['state'], 'needs_review')
        self.assertEqual(reply['upgrade']['native_result'], 'not_attempted')
        self.assertEqual(reply['upgrade']['stage'], 'staged')
        self.assertEqual(active.read_text(), 'A new rule from the user')
        self.assertEqual((self.project / reply['upgrade']['retained_path']).read_text(), preview['content'])

    def test_upgrade_failure_observations_follow_actual_objects_and_keep_diagnostics(self):
        for mode in ('stage_replaced', 'native_rejected', 'post_changed', 'post_denied'):
            with self.subTest(mode=mode):
                self.project = Path(self.temp.name) / mode
                self.project.mkdir()
                self.cli('init', '--name', 'Failure observations')
                old = self.cli('setup', '--host', 'codex')['data']['project_entry']
                active = self.project / 'AGENTS.md'
                active.write_bytes((old['content']).encode('utf-8'))
                draft = self.project / 'draft.json'
                draft.write_text(json.dumps(dict(objective='New checkpoint', next_action='Review',
                    constraints=[], decisions=[], unresolved=[], evidence=[])), encoding='utf-8')
                self.cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
                preview = self.cli('entry', 'upgrade', '--host', 'codex')['data']['upgrade']
                args = ['entry', 'upgrade', '--host', 'codex', '--apply', '--expect-state', 'active',
                        '--expect-sha256', preview['old_sha256'], '--expect-new-sha256', preview['new_sha256']]
                if sys.platform not in ('darwin', 'linux'):
                    self.assertEqual(self.cli(*args, ok=False)['code'], 'ENTRY_EXCHANGE_UNSUPPORTED')
                    continue
                # Boundary injection only: public CLI, real staging and (except
                # explicit native rejection) real exchange. No product mocks.
                script = '''import ctypes,errno,os,sys,runpy
from pathlib import Path
from unittest.mock import patch
mode=sys.argv[1]
sys.argv=sys.argv[2:]
project=Path(sys.argv[sys.argv.index('--project')+1])
library=ctypes.CDLL(None,use_errno=True)
name='renameatx_np' if sys.platform=='darwin' else 'renameat2'
native=getattr(library,name)
native.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
native.restype=ctypes.c_int
exchanged=False
original_open=os.open
original_fsync=os.fsync
def sync(fd):
    original_fsync(fd)
    if mode=='stage_replaced':
        staged=next(project.glob('.recaloom-*.upgrade-*'))
        staged.rename(project/'approved-candidate.bin')
        with staged.open('x',encoding='utf-8') as f:
            f.write('unrelated replacement')
def exchange(*args):
    global exchanged
    # Inject faults at the real rule exchange, not a same-filesystem canary.
    if args[1] != b'AGENTS.md':
        return native(*args)
    if mode=='native_rejected':
        ctypes.set_errno(errno.EACCES)
        return -1
    result=native(*args)
    exchanged=result==0
    if exchanged and mode=='post_changed':
        (project/'AGENTS.md').write_text('external editor after exchange',encoding='utf-8')
    return result
def opening(path,*args,**kwargs):
    if exchanged and mode=='post_denied' and str(path).startswith('.recaloom-codex.upgrade-'):
        raise OSError(errno.EACCES,'fixture retained read denied')
    return original_open(path,*args,**kwargs)
class Library:
    def __getattr__(self,key):
        return exchange if key==name else getattr(library,key)
with patch('ctypes.CDLL',return_value=Library()), patch('os.fsync',sync), patch('os.open',opening), patch('os.supports_dir_fd',os.supports_dir_fd|{opening}):
    runpy.run_path(sys.argv[0],run_name='__main__')
'''
                reply = self.command([sys.executable, '-I', '-B', '-c', script, mode,
                    str(ROOT / 'scripts/continuity.py'), '--project', str(self.project), *args])['data']
                op = reply['upgrade']
                retained = self.project / op['retained_path']
                self.assertEqual(reply['state'], 'needs_review')
                if mode == 'stage_replaced':
                    self.assertEqual(op['native_result'], 'not_attempted')
                    self.assertEqual(op['retained_role'], 'unknown')
                    self.assertEqual(retained.read_text(), 'unrelated replacement')
                    self.assertEqual((self.project / 'approved-candidate.bin').read_text(), preview['content'])
                    self.assertEqual(active.read_text(), old['content'])
                elif mode == 'native_rejected':
                    self.assertEqual(op['native_result'], 'error')
                    self.assertEqual(op['native_errno'], 13)
                    self.assertEqual(op['error_code'], 'NATIVE_EXCHANGE_ERROR')
                    self.assertTrue(op['requested_paths_current'])
                    self.assertEqual(op['observed_rule_path'], op['rule_path'])
                    self.assertEqual(op['observed_retained_path'], op['retained_path'])
                    self.assertEqual(op['retained_role'], 'candidate')
                    self.assertEqual(active.read_text(), old['content'])
                    self.assertEqual(retained.read_text(), preview['content'])
                else:
                    self.assertEqual(op['native_result'], 'succeeded')
                    self.assertEqual(op['outcome'], 'exchanged_needs_review')
                    self.assertEqual(op['error_code'], 'POSTEXCHANGE_CHECK_FAILED')
                    self.assertEqual(retained.read_text(), old['content'])
                    if mode == 'post_denied':
                        self.assertEqual(op['io_errno'], 13)
                        self.assertIsNone(op['observed_retained_path'])
                        self.assertEqual(active.read_text(), preview['content'])
                    else:
                        self.assertEqual(active.read_text(), 'external editor after exchange')

    def test_concurrent_upgrade_preserves_original_and_all_created_candidates(self):
        self.cli('init', '--name', 'Concurrent upgrade')
        old = self.cli('setup', '--host', 'codex')['data']['project_entry']
        active = self.project / 'AGENTS.md'
        active.write_bytes((old['content']).encode('utf-8'))
        draft = self.project / 'draft.json'
        draft.write_text(json.dumps(dict(objective='Changed checkpoint', next_action='Review', constraints=[],
                                         decisions=[], unresolved=[], evidence=[])), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
        database = self.project / '.continuity/state.sqlite3'
        database_before = database.read_bytes()
        preview = self.cli('entry', 'upgrade', '--host', 'codex')['data']['upgrade']
        args = ['entry', 'upgrade', '--host', 'codex', '--apply', '--expect-state', 'active',
                '--expect-sha256', preview['old_sha256'], '--expect-new-sha256', preview['new_sha256']]
        if sys.platform not in ('darwin', 'linux'):
            self.assertEqual(self.cli(*args, ok=False)['code'], 'ENTRY_EXCHANGE_UNSUPPORTED')
            return
        argv = [sys.executable, '-I', '-B', str(ROOT / 'scripts/continuity.py'), '--project', str(self.project), *args]
        def apply():
            return subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', timeout=15)
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: apply(), range(4)))
        for result in results:
            self.assertIn(result.returncode, (0, 2), result.stdout + result.stderr)
            response = json.loads(result.stdout)
            if not response['ok']:
                self.assertEqual(response['code'], 'ENTRY_CHANGED')
        retained = list(self.project.glob('.recaloom-*.upgrade-*'))
        self.assertGreaterEqual(len(retained), 1)
        self.assertLessEqual(len(retained), 4)
        contents = [p.read_text() for p in retained] + [active.read_text()]
        self.assertIn(old['content'], contents)
        self.assertIn(preview['content'], contents)
        self.assertTrue(all(text in (old['content'], preview['content']) for text in contents))
        self.assertEqual(database.read_bytes(), database_before)

    def test_project_entry_preview_then_explicit_install_recovers_bound_memory(self):
        self.cli('init', '--name', 'Entry test')
        draft = self.project / 'draft.json'
        draft.write_text(json.dumps(dict(objective='Prepare a local workshop',
            next_action='Compare rooms', constraints=['No booking; budget 2300'],
            decisions=[], unresolved=['Date unknown'], evidence=[])), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
        preview = self.cli('setup', '--host', 'codex')['data']
        self.assertTrue(preview['read_only'])
        self.assertFalse((self.project / 'AGENTS.md').exists())
        entry = preview['project_entry']
        self.assertEqual(entry['relative_path'], 'AGENTS.md')
        self.assertEqual(entry['state'], 'preview')
        if os.name != 'posix':
            self.assertEqual(self.cli('setup', '--host', 'codex', '--write-instructions',
                                     ok=False)['code'], 'ENTRY_WRITE_UNSUPPORTED')
            self.assertFalse((self.project / 'AGENTS.md').exists())
            return
        installed = self.cli('setup', '--host', 'codex', '--write-instructions')['data']
        self.assertEqual(installed['project_entry']['state'], 'written_unverified')
        self.assertFalse(installed['read_only'])
        self.assertFalse(installed['host_integrated'])
        self.assertFalse(installed['automatic_save'])
        self.assertEqual((self.project / 'AGENTS.md').read_text(), entry['content'])
        self.assertNotIn('budget 2300', entry['content'])
        self.assertIn('not authorization', entry['content'])
        restored = self.command(installed['binding']['resume_argv'])['data']
        self.assertIn('budget 2300', restored['text'])
        self.assertIn('Date unknown', restored['text'])
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    def test_entry_preview_identifies_existing_rules_without_overwriting(self):
        self.cli('init', '--name', 'Keep my rules')
        for host, relative in [('codex', 'AGENTS.md'),
                               ('claude-code', '.claude/rules/recaloom.md'),
                               ('workbuddy', '.codebuddy/CODEBUDDY.md')]:
            with self.subTest(host=host):
                target = self.project / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                original = b'User instructions: preserve this exactly.\n'
                target.write_bytes(original)
                for extra in [[], ['--write-instructions']]:
                    rejected = self.cli('setup', '--host', host, *extra, ok=False)
                    self.assertEqual(rejected['code'], 'ENTRY_EXISTS')
                    self.assertEqual(target.read_bytes(), original)
        self.assertEqual(self.cli('status')['data']['revision'], 0)

    def test_other_project_entry_locations_preserve_existing_root_rules(self):
        self.cli('init', '--name', 'Other host entry')
        (self.project / 'AGENTS.md').write_text('Existing root rule\n', encoding='utf-8')
        for host, relative in [('claude-code', '.claude/rules/recaloom.md'),
                               ('workbuddy', '.codebuddy/CODEBUDDY.md')]:
            with self.subTest(host=host):
                card = self.cli('setup', '--host', host)['data']
                self.assertEqual(card['project_entry']['relative_path'], relative)
                self.assertFalse((self.project / relative).parent.exists())
                if os.name != 'posix':
                    self.assertEqual(self.cli('setup', '--host', host, '--write-instructions',
                                             ok=False)['code'], 'ENTRY_WRITE_UNSUPPORTED')
                    continue
                written = self.cli('setup', '--host', host, '--write-instructions')['data']
                self.assertEqual((self.project / relative).read_text(), card['project_entry']['content'])
                self.assertFalse(written['automatic_restore'])
                self.assertFalse(written['host_integrated'])
                self.assertEqual(self.command(written['binding']['resume_argv'])['data']['recovery_state'], 'no_checkpoint')
        self.assertEqual((self.project / 'AGENTS.md').read_text(), 'Existing root rule\n')
        self.assertFalse((self.project / 'CLAUDE.md').exists())

    def test_entry_requires_project_host_and_sufficient_budget_before_writing(self):
        self.assertEqual(self.cli('setup', '--host', 'codex', '--write-instructions',
                                 ok=False)['code'], 'PROJECT_REQUIRED')
        self.assertEqual(list(self.project.iterdir()), [])
        self.cli('init', '--name', 'Existing')
        before = self.cli('status')['data']
        self.assertEqual(self.cli('setup', '--write-instructions', ok=False)['code'], 'HOST_REQUIRED')
        self.assertEqual(self.cli('setup', '--host', 'claude-code', '--write-instructions',
                                 '--max-chars', '10', ok=False)['code'], 'BUDGET_TOO_SMALL')
        self.assertFalse((self.project / '.claude').exists())
        self.assertEqual(self.cli('status')['data'], before)

    def test_entry_rejects_priority_override_and_non_directory_parents(self):
        self.cli('init', '--name', 'Existing')
        (self.project / 'AGENTS.override.md').write_text('priority rule', encoding='utf-8')
        for extra in [[], ['--write-instructions']]:
            self.assertEqual(self.cli('setup', '--host', 'codex', *extra, ok=False)['code'], 'ENTRY_SHADOWED')
        self.assertFalse((self.project / 'AGENTS.md').exists())
        (self.project / '.codebuddy').write_text('Not a directory', encoding='utf-8')
        self.assertEqual(self.cli('setup', '--host', 'workbuddy', '--write-instructions',
                                 ok=False)['code'], 'ENTRY_UNSAFE_PATH')
        if os.name == 'posix':
            outside = Path(self.temp.name) / 'outside'
            outside.mkdir()
            (self.project / '.claude').symlink_to(outside, target_is_directory=True)
            self.assertEqual(self.cli('setup', '--host', 'claude-code', '--write-instructions',
                                     ok=False)['code'], 'ENTRY_UNSAFE_PATH')
            self.assertEqual(list(outside.iterdir()), [])

    def test_workbuddy_root_guidance_blocks_new_entry_without_overwrite(self):
        self.cli('init', '--name', 'Existing')
        root_rule = self.project / 'CODEBUDDY.md'
        for content in ('', '# My existing rules\nDo not contact customers.\n'):
            with self.subTest(content=bool(content)):
                root_rule.write_text(content, encoding='utf-8')
                before = {str(p.relative_to(self.project)): p.read_bytes()
                          for p in self.project.rglob('*') if p.is_file()}
                for extra in ([], ['--write-instructions']):
                    result = self.cli('setup', '--host', 'workbuddy', *extra, ok=False)
                    self.assertEqual(result['code'], 'ENTRY_SHADOWED')
                    self.assertIn('CODEBUDDY.md', result['error'])
                    self.assertEqual({str(p.relative_to(self.project)): p.read_bytes()
                                      for p in self.project.rglob('*') if p.is_file()}, before)
                self.assertFalse((self.project / '.codebuddy').exists())

    def test_workbuddy_priority_after_install_is_diagnosed_and_blocks_lifecycle(self):
        self.cli('init', '--name', 'Installed but later shadowed')
        self.cli('setup', '--host', 'workbuddy', '--write-instructions')
        status = self.cli('entry', 'status', '--host', 'workbuddy')['data']
        expected = status['sha256']
        (self.project / 'CODEBUDDY.md').write_text('', encoding='utf-8')
        before = {str(p.relative_to(self.project)): p.read_bytes()
                  for p in self.project.rglob('*') if p.is_file()}
        status = self.cli('entry', 'status', '--host', 'workbuddy')['data']
        self.assertEqual(status['state'], 'active', 'File state is not host loading')
        self.assertFalse(status['host_loading_verified'])
        self.assertEqual(status['priority_issue']['code'], 'ENTRY_SHADOWED')
        self.assertEqual(status['priority_issue']['relative_path'], 'CODEBUDDY.md')
        for action in ('pause', 'enable', 'upgrade'):
            result = self.cli('entry', action, '--host', 'workbuddy', '--expect-sha256', expected, ok=False)
            self.assertEqual(result['code'], 'ENTRY_SHADOWED')
            self.assertEqual({str(p.relative_to(self.project)): p.read_bytes()
                              for p in self.project.rglob('*') if p.is_file()}, before)

    def test_instruction_binding_encodes_path_characters_as_data(self):
        if os.name == 'posix':
            self.project = self.project / 'quotes "\n```\n$() `text`'
            self.project.mkdir()
        self.cli('init', '--name', 'Do not put this name in the rule')
        card = self.cli('setup', '--host', 'codex')['data']
        text = card['project_entry']['content']
        decoded = json.loads(text.split('```json\n', 1)[1].rsplit('\n```', 1)[0])
        self.assertEqual(decoded, card['binding'])
        self.assertNotIn('Do not put this name in the rule', text)
        self.assertEqual(text.splitlines().count('```'), 1)
        self.assertEqual(self.command(decoded['resume_argv'])['data']['recovery_state'], 'no_checkpoint')

    def test_interrupted_instruction_write_has_no_loadable_partial_rule(self):
        self.cli('init', '--name', 'Existing')
        if os.name != 'posix':
            self.assertEqual(self.cli('setup', '--host', 'codex', '--write-instructions',
                                     ok=False)['code'], 'ENTRY_WRITE_UNSUPPORTED')
            return
        # Inject an OS I/O failure at the filesystem seam, not a mocked product helper.
        script = ('import sys, runpy; from unittest.mock import patch; '
                  'sys.argv=sys.argv[1:]; '
                  'p=patch("os.fsync", side_effect=OSError("synthetic fsync failure")); '
                  'p.start(); runpy.run_path(sys.argv[0], run_name="__main__")')
        refused = self.command([sys.executable, '-I', '-B', '-c', script,
                                str(ROOT / 'scripts/continuity.py'), '--project', str(self.project),
                                'setup', '--host', 'codex', '--write-instructions'], ok=False)
        self.assertEqual(refused['code'], 'ENTRY_IO_ERROR')
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertEqual(list(self.project.glob('.recaloom-*.pending')), [])
        self.assertEqual(self.cli('status')['data']['revision'], 0)

    def test_concurrent_instruction_install_has_one_complete_winner(self):
        self.cli('init', '--name', 'Existing')
        if os.name != 'posix':
            self.assertEqual(self.cli('setup', '--host', 'codex', '--write-instructions',
                                     ok=False)['code'], 'ENTRY_WRITE_UNSUPPORTED')
            return
        argv = [sys.executable, '-B', str(ROOT / 'scripts/continuity.py'), '--project',
                str(self.project), 'setup', '--host', 'codex', '--write-instructions']
        def install():
            return subprocess.run(argv, capture_output=True, text=True, encoding='utf-8', timeout=15)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: install(), range(2)))
        self.assertEqual(sorted(r.returncode for r in results), [0, 2])
        replies = [json.loads(r.stdout) for r in results]
        self.assertEqual(sorted(r['code'] for r in replies), ['ENTRY_EXISTS', 'OK'])
        winner = next(r for r in replies if r['ok'])
        self.assertEqual((self.project / 'AGENTS.md').read_text(), winner['data']['project_entry']['content'])
        self.assertEqual(list(self.project.glob('.recaloom-*.pending')), [])

    def test_cannot_create_instruction_temp_file_reports_actionable_failure(self):
        self.cli('init', '--name', 'Existing')
        if os.name != 'posix':
            self.assertEqual(self.cli('setup', '--host', 'codex', '--write-instructions',
                                     ok=False)['code'], 'ENTRY_WRITE_UNSUPPORTED')
            return
        script = '''import os, sys, runpy
from unittest.mock import patch
original = os.open
def fail_temp(path, *args, **kwargs):
    if str(path).endswith('.pending'):
        raise PermissionError('synthetic permission denial')
    return original(path, *args, **kwargs)
sys.argv = sys.argv[1:]
# Preserve capability metadata while injecting only the OS operation failure.
with patch('os.open', fail_temp), patch('os.supports_dir_fd', os.supports_dir_fd | {fail_temp}):
    runpy.run_path(sys.argv[0], run_name='__main__')
'''
        refused = self.command([sys.executable, '-I', '-B', '-c', script,
                                str(ROOT / 'scripts/continuity.py'), '--project', str(self.project),
                                'setup', '--host', 'codex', '--write-instructions'], ok=False)
        self.assertEqual(refused['code'], 'ENTRY_IO_ERROR')
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertEqual(list(self.project.glob('.recaloom-*.pending')), [])

    def test_cleanup_failure_reports_written_rule_without_inviting_reinstallation(self):
        self.cli('init', '--name', 'Existing')
        if os.name != 'posix':
            self.assertEqual(self.cli('setup', '--host', 'codex', '--write-instructions',
                                     ok=False)['code'], 'ENTRY_WRITE_UNSUPPORTED')
            return
        script = '''import os, sys, runpy
from unittest.mock import patch
original = os.unlink
def deny_cleanup(path, *args, **kwargs):
    if str(path).endswith('.pending'):
        raise PermissionError('synthetic cleanup denial')
    return original(path, *args, **kwargs)
sys.argv = sys.argv[1:]
with patch('os.unlink', deny_cleanup), patch('os.supports_dir_fd', os.supports_dir_fd | {deny_cleanup}):
    runpy.run_path(sys.argv[0], run_name='__main__')
'''
        reply = self.command([sys.executable, '-I', '-B', '-c', script,
                              str(ROOT / 'scripts/continuity.py'), '--project', str(self.project),
                              'setup', '--host', 'codex', '--write-instructions'])['data']
        entry = reply['project_entry']
        self.assertEqual(entry['state'], 'written_unverified')
        self.assertEqual(entry['cleanup_state'], 'incomplete')
        self.assertEqual((self.project / 'AGENTS.md').read_text(), entry['content'])
        self.assertEqual((self.project / entry['temporary_path']).read_text(), entry['content'])
        self.assertFalse(reply['host_integrated'])
        self.assertEqual(self.cli('setup', '--host', 'codex', '--write-instructions',
                                 ok=False)['code'], 'ENTRY_EXISTS')

    def test_cleanup_failure_preserves_primary_unpublished_write_error(self):
        self.cli('init', '--name', 'Existing')
        if os.name != 'posix':
            self.assertEqual(self.cli('setup', '--host', 'codex', '--write-instructions',
                                     ok=False)['code'], 'ENTRY_WRITE_UNSUPPORTED')
            return
        script = '''import os, sys, runpy
from unittest.mock import patch
original = os.unlink
def deny_cleanup(path, *args, **kwargs):
    if str(path).endswith('.pending'):
        raise PermissionError('synthetic cleanup denial')
    return original(path, *args, **kwargs)
sys.argv = sys.argv[1:]
with patch('os.unlink', deny_cleanup), patch('os.supports_dir_fd', os.supports_dir_fd | {deny_cleanup}), patch('os.fsync', side_effect=OSError('synthetic sync failure')):
    runpy.run_path(sys.argv[0], run_name='__main__')
'''
        refused = self.command([sys.executable, '-I', '-B', '-c', script,
                                str(ROOT / 'scripts/continuity.py'), '--project', str(self.project),
                                'setup', '--host', 'codex', '--write-instructions'], ok=False)
        self.assertEqual(refused['code'], 'ENTRY_IO_ERROR')
        self.assertIn('cleanup also failed', refused['error'])
        self.assertFalse((self.project / 'AGENTS.md').exists())
        self.assertEqual(len(list(self.project.glob('.recaloom-*.pending'))), 1)

    def test_entry_status_reads_exact_project_rule_without_claiming_host_loaded(self):
        empty = self.cli('entry', 'status', '--host', 'codex')['data']
        self.assertEqual(empty['state'], 'not_installed')
        self.assertEqual(list(self.project.iterdir()), [])
        self.cli('init', '--name', 'Entry lifecycle')
        if os.name != 'posix':
            preview = self.cli('setup', '--host', 'codex')['data']
            (self.project / 'AGENTS.md').write_bytes((preview['project_entry']['content']).encode('utf-8'))
        else:
            self.cli('setup', '--host', 'codex', '--write-instructions')
        status = self.cli('entry', 'status', '--host', 'codex')['data']
        self.assertEqual(status['state'], 'active')
        self.assertTrue(status['read_only'])
        self.assertTrue(status['runtime_binding_matches'])
        self.assertFalse(status['host_loading_verified'])
        self.assertFalse(status['already_loaded_context_revoked'])
        self.assertEqual(status['sha256'], hashlib.sha256((self.project / 'AGENTS.md').read_bytes()).hexdigest())
        self.assertEqual(status['project_id'], self.cli('status')['data']['project_id'])

    def test_entry_pause_and_enable_preserve_exact_rule_and_task_memory(self):
        self.cli('init', '--name', 'Reversible entry')
        memory_before = self.cli('status')['data']
        for host, relative in [('codex', 'AGENTS.md'),
                               ('claude-code', '.claude/rules/recaloom.md'),
                               ('workbuddy', '.codebuddy/CODEBUDDY.md')]:
            with self.subTest(host=host):
                preview = self.cli('setup', '--host', host)['data']
                active = self.project / relative
                active.parent.mkdir(parents=True, exist_ok=True)
                active.write_bytes((preview['project_entry']['content']).encode('utf-8'))
                original = active.read_bytes()
                expected = hashlib.sha256(original).hexdigest()
                if sys.platform not in ('darwin', 'linux'):
                    refused = self.cli('entry', 'pause', '--host', host,
                                       '--expect-sha256', expected, ok=False)
                    self.assertEqual(refused['code'], 'ENTRY_MOVE_UNSUPPORTED')
                    self.assertEqual(active.read_bytes(), original)
                    continue
                paused = active.parent / ('.recaloom-' + host + '.paused')
                result = self.cli('entry', 'pause', '--host', host, '--expect-sha256', expected)['data']
                self.assertEqual(result['state'], 'paused')
                self.assertEqual(result['operation']['outcome'], 'move_observed')
                self.assertFalse(result['read_only'])
                self.assertFalse(result['already_loaded_context_revoked'])
                self.assertFalse(active.exists())
                self.assertEqual(paused.read_bytes(), original)
                self.assertEqual(self.cli('entry', 'status', '--host', host)['data']['state'], 'paused')
                again = self.cli('entry', 'pause', '--host', host, '--expect-sha256', expected)['data']
                self.assertEqual(again['operation']['outcome'], 'already_in_state')
                self.assertTrue(again['read_only'])
                enabled = self.cli('entry', 'enable', '--host', host, '--expect-sha256', expected)['data']
                self.assertEqual(enabled['state'], 'active')
                self.assertEqual(enabled['operation']['outcome'], 'move_observed')
                self.assertEqual(active.read_bytes(), original)
                self.assertFalse(paused.exists())
                self.assertFalse(enabled['host_loading_verified'])
                self.assertEqual(self.cli('entry', 'enable', '--host', host,
                                          '--expect-sha256', expected)['data']['operation']['outcome'], 'already_in_state')
        self.assertEqual(self.cli('status')['data'], memory_before)

    def test_setup_does_not_reinstall_over_a_paused_entry(self):
        self.cli('init', '--name', 'Keep paused entry')
        for host, relative in [('codex', 'AGENTS.md'),
                               ('claude-code', '.claude/rules/recaloom.md'),
                               ('workbuddy', '.codebuddy/CODEBUDDY.md')]:
            with self.subTest(host=host):
                preview = self.cli('setup', '--host', host)['data']['project_entry']['content']
                active = self.project / relative
                active.parent.mkdir(parents=True, exist_ok=True)
                paused = active.parent / ('.recaloom-' + host + '.paused')
                paused.write_bytes((preview).encode('utf-8'))
                for options in [[], ['--write-instructions']]:
                    refused = self.cli('setup', '--host', host, *options, ok=False)
                    self.assertEqual(refused['code'], 'ENTRY_PAUSED')
                    self.assertEqual(paused.read_text(), preview)
                    self.assertFalse(active.exists())

    def test_entry_requires_reviewed_digest_and_preserves_edited_rules(self):
        self.cli('init', '--name', 'No unreviewed changes')
        content = self.cli('setup', '--host', 'codex')['data']['project_entry']['content']
        active = self.project / 'AGENTS.md'
        active.write_bytes((content).encode('utf-8'))
        expected = hashlib.sha256(active.read_bytes()).hexdigest()
        cases = [([], 'ENTRY_EXPECTATION_REQUIRED'),
                 (['--expect-sha256', 'not-a-digest'], 'ENTRY_EXPECTATION_REQUIRED'),
                 (['--expect-sha256', '0' * 64], 'ENTRY_CHANGED'),
                 (['--expect-sha256', expected, '--max-chars', '1'], 'BUDGET_TOO_SMALL')]
        for options, code in cases:
            with self.subTest(code=code):
                self.assertEqual(self.cli('entry', 'pause', '--host', 'codex', *options, ok=False)['code'], code)
                self.assertEqual(active.read_text(), content)
                self.assertFalse((self.project / '.recaloom-codex.paused').exists())
        active.write_text(content + '\nUser-authored additional rule.\n', encoding='utf-8')
        edited = active.read_bytes()
        self.assertEqual(self.cli('entry', 'pause', '--host', 'codex',
                                  '--expect-sha256', hashlib.sha256(edited).hexdigest(), ok=False)['code'], 'ENTRY_UNRECOGNIZED')
        self.assertEqual(active.read_bytes(), edited)

    def test_entry_conflicts_and_copied_project_never_change_files(self):
        self.cli('init', '--name', 'Bound rule only')
        content = self.cli('setup', '--host', 'codex')['data']['project_entry']['content']
        active = self.project / 'AGENTS.md'
        active.write_bytes((content).encode('utf-8'))
        expected = hashlib.sha256(active.read_bytes()).hexdigest()
        other = Path(self.temp.name) / 'copied-project'
        shutil.copytree(self.project, other)
        self.assertEqual(self.command([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
            '--project', str(other), 'entry', 'pause', '--host', 'codex', '--expect-sha256', expected], ok=False)['code'],
            'PROJECT_MISMATCH')
        self.assertEqual((other / 'AGENTS.md').read_text(), content)
        override = self.project / 'AGENTS.override.md'
        override.write_text('User priority rule', encoding='utf-8')
        self.assertEqual(self.cli('entry', 'pause', '--host', 'codex', '--expect-sha256', expected, ok=False)['code'], 'ENTRY_SHADOWED')
        self.assertEqual(override.read_text(), 'User priority rule')
        paused = self.project / '.recaloom-codex.paused'
        paused.write_text('Keep this too', encoding='utf-8')
        self.assertEqual(self.cli('entry', 'status', '--host', 'codex', ok=False)['code'], 'ENTRY_CONFLICT')
        self.assertEqual(active.read_text(), content)
        self.assertEqual(paused.read_text(), 'Keep this too')

    def test_entry_stale_runtime_can_pause_but_cannot_enable(self):
        self.cli('init', '--name', 'Retired runtime')
        preview = self.cli('setup', '--host', 'codex')['data']
        content = preview['project_entry']['content'].replace(preview['binding']['program_sha256'], '0' * 64)
        active = self.project / 'AGENTS.md'
        active.write_bytes((content).encode('utf-8'))
        expected = hashlib.sha256(active.read_bytes()).hexdigest()
        self.assertFalse(self.cli('entry', 'status', '--host', 'codex')['data']['runtime_binding_matches'])
        if sys.platform not in ('darwin', 'linux'):
            self.assertEqual(self.cli('entry', 'pause', '--host', 'codex', '--expect-sha256', expected,
                                     ok=False)['code'], 'ENTRY_MOVE_UNSUPPORTED')
            return
        self.assertEqual(self.cli('entry', 'pause', '--host', 'codex', '--expect-sha256', expected)['data']['state'], 'paused')
        self.assertEqual(self.cli('entry', 'enable', '--host', 'codex', '--expect-sha256', expected,
                                 ok=False)['code'], 'ENTRY_RUNTIME_MISMATCH')
        self.assertFalse(active.exists())
        self.assertEqual((self.project / '.recaloom-codex.paused').read_text(), content)

    def test_entry_native_collision_and_post_move_interference_preserve_observed_files(self):
        self.cli('init', '--name', 'Native boundary')
        if sys.platform not in ('darwin', 'linux'):
            self.assertEqual(self.cli('entry', 'status', '--host', 'codex')['data']['state'], 'not_installed')
            return  # Native mutation is deliberately unsupported, not certified here.
        script = r'''
import ctypes, errno, os, pathlib, runpy, sys, types
from unittest.mock import patch
mode = sys.argv.pop(1)
sys.argv = sys.argv[1:]
library = ctypes.CDLL(None, use_errno=True)
name = 'renameatx_np' if sys.platform == 'darwin' else 'renameat2'
native = getattr(library, name)
root = pathlib.Path(sys.argv[sys.argv.index('--project') + 1])
def injected(fd, src, target_fd, dst, flags):
    source, target = root / os.fsdecode(src), root / os.fsdecode(dst)
    if mode == 'collision':
        target.write_bytes(b'Competing target; preserve me')
    if mode == 'source-replaced':
        source.rename(root / 'retained-selected-rule')
        source.write_bytes(b'Unrelated replacement; preserve me')
    if mode == 'native-error':
        ctypes.set_errno(errno.EIO)
        return -1
    result = native(fd, src, target_fd, dst, flags)
    if result == 0 and mode == 'post-write':
        target.write_bytes(b'Edited after native move; preserve me')
    if result == 0 and mode == 'source-recreated':
        source.write_bytes(b'New active rule; preserve me')
    return result
with patch('ctypes.CDLL', return_value=types.SimpleNamespace(**{name: injected})):
    runpy.run_path(sys.argv[0], run_name='__main__')
'''
        for mode in ['collision', 'source-replaced', 'post-write', 'source-recreated', 'native-error']:
            with self.subTest(mode=mode):
                selected = self.project / mode
                selected.mkdir()
                prefix = [sys.executable, '-B', str(ROOT / 'scripts/continuity.py'), '--project', str(selected)]
                self.command(prefix + ['init', '--name', mode])
                content = self.command(prefix + ['setup', '--host', 'codex'])['data']['project_entry']['content']
                active, paused = selected / 'AGENTS.md', selected / '.recaloom-codex.paused'
                active.write_bytes((content).encode('utf-8'))
                expected = hashlib.sha256(active.read_bytes()).hexdigest()
                result = self.command([sys.executable, '-I', '-B', '-c', script, mode, *prefix[2:],
                    'entry', 'pause', '--host', 'codex', '--expect-sha256', expected], ok=mode != 'collision')
                if mode == 'collision':
                    self.assertEqual(result['code'], 'ENTRY_CONFLICT')
                    self.assertEqual(active.read_text(), content)
                    self.assertEqual(paused.read_bytes(), b'Competing target; preserve me')
                    continue
                data = result['data']
                self.assertEqual(data['state'], 'needs_review')
                self.assertFalse(data['read_only'])
                if mode == 'native-error':
                    self.assertEqual(data['operation']['outcome'], 'outcome_unknown')
                    self.assertEqual(active.read_text(), content)
                    self.assertFalse(paused.exists())
                else:
                    self.assertEqual(data['operation']['outcome'], 'moved_needs_review')
                    self.assertEqual(data['operation']['native_result'], 'succeeded')
                    if mode == 'source-replaced':
                        self.assertEqual(paused.read_bytes(), b'Unrelated replacement; preserve me')
                        self.assertEqual((selected / 'retained-selected-rule').read_text(), content)
                    elif mode == 'post-write':
                        self.assertEqual(paused.read_bytes(), b'Edited after native move; preserve me')
                    else:
                        self.assertEqual(active.read_bytes(), b'New active rule; preserve me')
                        self.assertEqual(paused.read_text(), content)

    def test_entry_competing_pauses_keep_one_complete_recoverable_rule(self):
        self.cli('init', '--name', 'Competing pause')
        content = self.cli('setup', '--host', 'codex')['data']['project_entry']['content']
        active = self.project / 'AGENTS.md'
        active.write_bytes((content).encode('utf-8'))
        expected = hashlib.sha256(active.read_bytes()).hexdigest()
        argv = [sys.executable, '-B', str(ROOT / 'scripts/continuity.py'), '--project', str(self.project),
                'entry', 'pause', '--host', 'codex', '--expect-sha256', expected]
        with ThreadPoolExecutor(max_workers=4) as workers:
            results = list(workers.map(lambda _: subprocess.run(argv, capture_output=True, text=True, timeout=15), range(4)))
        if sys.platform not in ('darwin', 'linux'):
            self.assertTrue(all(json.loads(r.stdout)['code'] == 'ENTRY_MOVE_UNSUPPORTED' for r in results))
            self.assertEqual(active.read_text(), content)
            return
        self.assertTrue(any(r.returncode == 0 for r in results), [r.stdout + r.stderr for r in results])
        self.assertTrue(all(r.returncode in (0, 2) for r in results))
        self.assertFalse(active.exists())
        self.assertEqual((self.project / '.recaloom-codex.paused').read_text(), content)
        self.assertEqual(self.cli('entry', 'status', '--host', 'codex')['data']['state'], 'paused')
        self.assertEqual(self.cli('entry', 'enable', '--host', 'codex', '--expect-sha256', expected)['data']['state'], 'active')
        self.assertEqual(active.read_text(), content)

    def test_entry_links_and_oversize_rules_are_refused_without_touching_targets(self):
        self.cli('init', '--name', 'Path boundary')
        active = self.project / 'AGENTS.md'
        active.write_bytes(b'x' * 65537)
        self.assertEqual(self.cli('entry', 'status', '--host', 'codex', ok=False)['code'], 'ENTRY_UNSAFE_PATH')
        self.assertEqual(active.stat().st_size, 65537)
        if os.name != 'posix':
            return  # Link capabilities are not certified by the non-POSIX fixture.
        active.unlink()  # Only the oversized synthetic fixture created above.
        outside = Path(self.temp.name) / 'outside-rule'
        outside.write_text('User data outside selected project', encoding='utf-8')
        active.symlink_to(outside)
        self.assertEqual(self.cli('entry', 'status', '--host', 'codex', ok=False)['code'], 'ENTRY_UNSAFE_PATH')
        self.assertEqual(outside.read_text(), 'User data outside selected project')
        outside_dir = Path(self.temp.name) / 'outside-directory'
        outside_dir.mkdir()
        (self.project / '.claude').symlink_to(outside_dir, target_is_directory=True)
        self.assertEqual(self.cli('entry', 'status', '--host', 'claude-code', ok=False)['code'], 'ENTRY_UNSAFE_PATH')
        self.assertEqual(list(outside_dir.iterdir()), [])

    def test_entry_status_and_noop_refuse_hardlink_aliases_consistently(self):
        self.cli('init', '--name', 'Alias consistency')
        for host, relative in [('codex', 'AGENTS.md'),
                               ('claude-code', '.claude/rules/recaloom.md'),
                               ('workbuddy', '.codebuddy/CODEBUDDY.md')]:
            with self.subTest(host=host):
                content = self.cli('setup', '--host', host)['data']['project_entry']['content']
                active = self.project / relative
                active.parent.mkdir(parents=True, exist_ok=True)
                active.write_bytes((content).encode('utf-8'))
                alias = self.project / ('retained-' + host)
                os.link(active, alias)
                expected = hashlib.sha256(active.read_bytes()).hexdigest()
                self.assertEqual(self.cli('entry', 'status', '--host', host, ok=False)['code'], 'ENTRY_UNSAFE_PATH')
                self.assertEqual(self.cli('entry', 'enable', '--host', host, '--expect-sha256', expected,
                                         ok=False)['code'], 'ENTRY_UNSAFE_PATH')
                paused = active.parent / ('.recaloom-' + host + '.paused')
                active.rename(paused)  # Move only this test fixture; retain its second link.
                self.assertEqual(self.cli('entry', 'status', '--host', host, ok=False)['code'], 'ENTRY_UNSAFE_PATH')
                self.assertEqual(self.cli('entry', 'pause', '--host', host, '--expect-sha256', expected,
                                         ok=False)['code'], 'ENTRY_UNSAFE_PATH')
                self.assertEqual(alias.read_text(), content)
                self.assertEqual(paused.read_text(), content)

    def test_entry_parent_drift_marks_requested_paths_stale_not_preserved_location(self):
        self.cli('init', '--name', 'Relocated parent')
        if sys.platform not in ('darwin', 'linux'):
            self.assertEqual(self.cli('entry', 'status', '--host', 'claude-code')['data']['state'], 'not_installed')
            return
        content = self.cli('setup', '--host', 'claude-code')['data']['project_entry']['content']
        active = self.project / '.claude/rules/recaloom.md'
        active.parent.mkdir(parents=True)
        active.write_bytes((content).encode('utf-8'))
        expected = hashlib.sha256(active.read_bytes()).hexdigest()
        script = r'''
import ctypes, pathlib, runpy, sys, types
from unittest.mock import patch
sys.argv = sys.argv[1:]
name = 'renameatx_np' if sys.platform == 'darwin' else 'renameat2'
native = getattr(ctypes.CDLL(None, use_errno=True), name)
root = pathlib.Path(sys.argv[sys.argv.index('--project') + 1])
def injected(*args):
    (root / '.claude/rules').rename(root / 'retained-rules')
    return native(*args)
with patch('ctypes.CDLL', return_value=types.SimpleNamespace(**{name: injected})):
    runpy.run_path(sys.argv[0], run_name='__main__')
'''
        data = self.command([sys.executable, '-I', '-B', '-c', script,
            str(ROOT / 'scripts/continuity.py'), '--project', str(self.project), 'entry', 'pause',
            '--host', 'claude-code', '--expect-sha256', expected])['data']
        self.assertEqual(data['state'], 'needs_review')
        self.assertEqual(data['operation']['outcome'], 'moved_needs_review')
        self.assertIs(data['operation']['requested_paths_current'], False)
        self.assertIsNone(data['operation']['observed_target_path'])
        self.assertIn('unknown', data['operation']['location_note'])
        self.assertFalse((self.project / data['operation']['target_path']).exists())
        self.assertEqual((self.project / 'retained-rules/.recaloom-claude-code.paused').read_text(), content)
        # A later path-only status cannot rediscover an externally renamed parent.
        self.assertEqual(self.cli('entry', 'status', '--host', 'claude-code')['data']['state'], 'not_installed')

    def test_old_binding_rejects_replaced_project_instead_of_rebinding(self):
        self.cli('init', '--name', 'Original')
        card = self.cli('setup')['data']['binding']
        (self.project / '.continuity').rename(self.project / 'retained-original')
        different = self.cli('init', '--name', 'Replacement')['data']
        self.assertNotEqual(different['project_id'], card['project_id'])
        refused = self.command(card['resume_argv'], ok=False)
        self.assertEqual(refused['code'], 'PROJECT_MISMATCH')
        self.assertIsNone(refused['data'])

    def test_unrecognized_storage_is_preserved_and_never_bound(self):
        folder = self.project / '.continuity'
        folder.mkdir()
        database = folder / 'state.db'
        original = b'Not a Recaloom database; preserve this file.'
        database.write_bytes(original)
        refused = self.cli('setup', ok=False)
        self.assertEqual(refused['code'], 'UNRECOGNIZED_STORAGE')
        self.assertIsNone(refused['data'])
        self.assertEqual(database.read_bytes(), original)

    def test_damaged_database_is_preserved_and_never_bound(self):
        self.cli('init', '--name', 'Existing')
        database = self.project / '.continuity' / 'state.sqlite3'
        self.assertTrue(database.is_file())
        damaged = b'Damaged database in this synthetic project; preserve it.'
        database.write_bytes(damaged)
        refused = self.cli('setup', ok=False)
        self.assertEqual(refused['code'], 'IO_ERROR')
        self.assertIsNone(refused['data'])
        self.assertEqual(database.read_bytes(), damaged)

    def test_missing_matching_skill_withholds_binding_without_source_repair(self):
        self.cli('init', '--name', 'Existing')
        isolated = Path(self.temp.name) / 'other-tool' / 'scripts'
        isolated.mkdir(parents=True)
        program = isolated / 'continuity.py'
        shutil.copyfile(ROOT / 'scripts/continuity.py', program)
        refused = self.command([sys.executable, '-B', str(program),
                                '--project', str(self.project), 'setup'], ok=False)
        self.assertEqual(refused['code'], 'GUIDE_UNAVAILABLE')
        self.assertIsNone(refused['data'])
        self.assertFalse((isolated.parent / 'skills').exists())
        self.assertEqual(self.cli('status')['data']['revision'], 0)

    def test_small_budget_never_emits_partial_card_or_modifies_project(self):
        self.cli('init', '--name', 'Existing')
        before = {str(p.relative_to(self.project)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.project.rglob('*') if p.is_file()}
        result = self.cli('setup', '--max-chars', '10', ok=False)
        self.assertEqual(result['code'], 'BUDGET_TOO_SMALL')
        self.assertIsNone(result['data'])
        after = {str(p.relative_to(self.project)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.project.rglob('*') if p.is_file()}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
