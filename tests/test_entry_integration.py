"""Public CLI integration preserves user-owned project guidance."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HOSTS = [('codex', 'AGENTS.md'), ('claude-code', '.claude/rules/recaloom.md'),
         ('workbuddy', '.codebuddy/CODEBUDDY.md')]


class Integration(unittest.TestCase):
    def test_detach_does_not_claim_success_if_an_active_entry_reappears_during_move(self):
        if sys.platform not in ('darwin', 'linux'):
            return  # Safe no-replace move refusal is checked in the standalone test.
        self.cli('setup', '--host', 'codex', '--write-instructions')
        active = self.project / 'AGENTS.md'
        original = active.read_bytes()
        state = self.cli('entry', 'status', '--host', 'codex')['data']
        self.cli('entry', 'pause', '--host', 'codex', '--expect-sha256', state['sha256'])
        preview = self.cli('entry', 'detach', '--host', 'codex')['data']
        # The external filesystem races the public command; no internal helpers are mocked.
        script = '''import ctypes,os,runpy,sys
from unittest.mock import patch
library=ctypes.CDLL(None,use_errno=True)
name='renameatx_np' if sys.platform=='darwin' else 'renameat2'
native=getattr(library,name)
native.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
native.restype=ctypes.c_int
def racing_move(srcfd,src,dstfd,dst,flags):
    with os.fdopen(os.open(src,os.O_RDONLY,dir_fd=srcfd),'rb') as stream:
        old=stream.read()
    result=native(srcfd,src,dstfd,dst,flags)
    if result==0:
        fd=os.open('AGENTS.md',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=srcfd)
        with os.fdopen(fd,'wb') as stream: stream.write(old)
    return result
class Library:
    def __getattr__(self,key): return racing_move if key==name else getattr(library,key)
sys.argv=sys.argv[1:]
with patch('ctypes.CDLL',return_value=Library()): runpy.run_path(sys.argv[0],run_name='__main__')
'''
        reply = subprocess.run([sys.executable, '-I', '-B', '-c', script,
            str(ROOT / 'scripts/continuity.py'), '--project', str(self.project),
            'entry', 'detach', '--host', 'codex', '--apply', '--expect-state', 'paused',
            '--expect-sha256', preview['sha256']], capture_output=True, text=True, timeout=15)
        self.assertEqual(reply.returncode, 0, reply.stdout + reply.stderr)
        data = json.loads(reply.stdout)['data']
        self.assertEqual(data['state'], 'needs_review')
        self.assertEqual(active.read_bytes(), original, 'Never erase the concurrently added entry')
        self.assertEqual((self.project / data['removal']['retained_path']).read_bytes(), original)

    def test_detach_standalone_entry_retains_file_outside_host_discovery(self):
        for host, relative in HOSTS:
            for state in ('active', 'paused'):
                with self.subTest(host=host, state=state):
                    self.project = Path(self.temp.name) / (host + '-' + state)
                    self.project.mkdir()
                    self.cli('init', '--name', 'Standalone detach')
                    if sys.platform not in ('darwin', 'linux'):
                        # Supply a valid, explicitly prepared preview as a user can;
                        # automatic writing is separately refused on unsupported OSes.
                        card = self.cli('setup', '--host', host)['data']
                        self.fixture(relative, card['project_entry']['content'].encode())
                    else:
                        self.cli('setup', '--host', host, '--write-instructions')
                    initial = self.cli('entry', 'status', '--host', host)['data']
                    if state == 'paused':
                        if sys.platform not in ('darwin', 'linux'):
                            continue  # Existing lifecycle tests cover pause refusal.
                        self.cli('entry', 'pause', '--host', host, '--expect-sha256', initial['sha256'])
                    before = self.snapshot()
                    preview = self.cli('entry', 'detach', '--host', host)['data']
                    self.assertEqual(self.snapshot(), before)
                    self.assertIsNone(preview['removal']['content'])
                    if sys.platform not in ('darwin', 'linux'):
                        refused = self.cli('entry', 'detach', '--host', host, '--apply',
                            '--expect-sha256', preview['sha256'], '--expect-state', state, ok=False)
                        self.assertEqual(refused['code'], 'ENTRY_MOVE_UNSUPPORTED')
                        self.assertEqual(self.snapshot(), before)
                        continue
                    memory = self.cli('status')
                    result = self.cli('entry', 'detach', '--host', host, '--apply',
                        '--expect-sha256', preview['sha256'], '--expect-state', state)['data']
                    self.assertEqual(result['state'], 'detached')
                    self.assertEqual(result['removal']['outcome'], 'move_observed')
                    retained = self.project / result['removal']['retained_path']
                    self.assertEqual(hashlib.sha256(retained.read_bytes()).hexdigest(), preview['sha256'])
                    self.assertFalse((self.project / relative).exists())
                    self.assertFalse((self.project / relative).with_name('.recaloom-' + host + '.paused').exists())
                    self.assertEqual(self.cli('entry', 'status', '--host', host)['data']['state'], 'not_installed')
                    self.assertEqual(self.cli('status'), memory)

    def test_detach_paused_embedded_rules_across_hosts_keeps_current_user_edits(self):
        for host, relative in HOSTS:
            with self.subTest(host=host):
                original = b'\xef\xbb\xbf---\r\npaths: src/**\r\n---\r\n# User rules\r\n'
                file = self.fixture(relative, original)
                proposal = self.cli('entry', 'integrate', '--host', host)['data']
                if self.apply_native_or_check_refusal(host, proposal) is None:
                    continue
                status = self.cli('entry', 'status', '--host', host)['data']
                self.cli('entry', 'pause', '--host', host, '--expect-sha256', status['sha256'])
                file.write_bytes(file.read_bytes() + b'New user instruction.\r\n')
                before = self.snapshot()
                preview = self.cli('entry', 'detach', '--host', host)['data']
                self.assertEqual(preview['state'], 'paused')
                self.assertEqual(self.snapshot(), before)
                result = self.cli('entry', 'detach', '--host', host, '--apply',
                                  '--expect-sha256', preview['sha256'], '--expect-state', 'paused')['data']
                self.assertEqual(result['state'], 'detached')
                self.assertEqual(file.read_bytes(), original + b'New user instruction.\r\n')

    def test_detach_refuses_stale_preview_and_small_budget_without_writing(self):
        for embedded in (False, True):
            with self.subTest(embedded=embedded):
                self.project = Path(self.temp.name) / ('rejected-' + str(embedded))
                self.project.mkdir()
                self.cli('init', '--name', 'Rejected detach')
                if embedded:
                    self.fixture('AGENTS.md', b'# User rules\n')
                    proposal = self.cli('entry', 'integrate', '--host', 'codex')['data']
                    if self.apply_native_or_check_refusal('codex', proposal) is None:
                        continue
                else:
                    card = self.cli('setup', '--host', 'codex')['data']
                    self.fixture('AGENTS.md', card['project_entry']['content'].encode())
                preview = self.cli('entry', 'detach', '--host', 'codex')['data']
                before = self.snapshot()
                for extras, expected in [
                    (['--max-chars', '256'], 'BUDGET_TOO_SMALL'),
                    (['--apply'], 'ENTRY_EXPECTATION_REQUIRED'),
                    (['--apply', '--expect-state', 'paused', '--expect-sha256', preview['sha256']], 'ENTRY_CHANGED'),
                    (['--apply', '--expect-state', 'active', '--expect-sha256', '0' * 64], 'ENTRY_CHANGED'),
                    (['--apply', '--expect-state', 'active', '--expect-sha256', preview['sha256'],
                      '--max-chars', '256'], 'BUDGET_TOO_SMALL')]:
                    refused = self.cli('entry', 'detach', '--host', 'codex', *extras, ok=False)
                    self.assertEqual(refused['code'], expected)
                    self.assertEqual(self.snapshot(), before)
                file = self.project / 'AGENTS.md'
                file.write_bytes(file.read_bytes().replace(b'Recaloom project continuity', b'Edited project continuity'))
                before = self.snapshot()
                refused = self.cli('entry', 'detach', '--host', 'codex', '--apply',
                    '--expect-state', 'active', '--expect-sha256', preview['sha256'], ok=False)
                self.assertEqual(refused['code'], 'ENTRY_UNRECOGNIZED')
                self.assertEqual(self.snapshot(), before)

    def test_detach_restores_exact_user_rules_and_keeps_project_memory(self):
        original = b'\xef\xbb\xbf---\r\npaths: src/**\r\n---\r\n# User rules\r\nNever disclose client data.\r\n'
        active = self.fixture('AGENTS.md', original)
        integrated = self.cli('entry', 'integrate', '--host', 'codex')['data']
        if self.apply_native_or_check_refusal('codex', integrated) is None:
            return
        managed = active.read_bytes()
        memory = self.cli('status')
        before = self.snapshot()
        preview = self.cli('entry', 'detach', '--host', 'codex')['data']
        self.assertEqual(self.snapshot(), before, 'Removal preview must not write')
        self.assertEqual(preview['removal']['content'].encode(), original)
        result = self.cli('entry', 'detach', '--host', 'codex', '--apply',
                          '--expect-state', preview['state'],
                          '--expect-sha256', preview['sha256'])['data']
        self.assertEqual(result['state'], 'detached')
        self.assertEqual(active.read_bytes(), original)
        self.assertEqual((self.project / result['removal']['retained_path']).read_bytes(), managed)
        self.assertEqual(self.cli('status'), memory)
        self.assertFalse(result['already_loaded_context_revoked'])

    def test_filesystem_lying_about_exchange_keeps_user_rules_in_place(self):
        original = b'# User rules\nNever disclose client data.\n'
        active = self.fixture('AGENTS.md', original)
        preview = self.cli('entry', 'integrate', '--host', 'codex')['data']
        if sys.platform not in ('darwin', 'linux'):
            self.apply_native_or_check_refusal('codex', preview)
            return
        script = '''import ctypes,os,runpy,sys
from unittest.mock import patch
library=ctypes.CDLL(None,use_errno=True)
name='renameatx_np' if sys.platform=='darwin' else 'renameat2'
def lying_exchange(srcfd,src,dstfd,dst,flags):
    os.replace(src,dst,src_dir_fd=srcfd,dst_dir_fd=dstfd)
    return 0
class Library:
    def __getattr__(self,key):
        return lying_exchange if key==name else getattr(library,key)
sys.argv=sys.argv[1:]
with patch('ctypes.CDLL',return_value=Library()):
    runpy.run_path(sys.argv[0],run_name='__main__')
'''
        command = [sys.executable, '-I', '-B', '-c', script, str(ROOT / 'scripts/continuity.py'),
                   '--project', str(self.project), 'entry', 'integrate', '--host', 'codex', '--apply',
                   '--expect-state', 'active', '--expect-sha256', preview['sha256'],
                   '--expect-new-sha256', preview['upgrade']['new_sha256']]
        reply = subprocess.run(command, capture_output=True, text=True, timeout=15)
        self.assertEqual(reply.returncode, 0, reply.stdout + reply.stderr)
        data = json.loads(reply.stdout)['data']
        self.assertTrue(active.exists(), 'User rule disappeared despite failed integration')
        self.assertEqual(active.read_bytes(), original)
        self.assertEqual(data['state'], 'needs_review')
        self.assertEqual(data['upgrade']['native_result'], 'not_attempted')
        self.assertEqual(data['upgrade']['error_code'], 'ENTRY_EXCHANGE_UNRELIABLE')

    def test_probe_errors_keep_errno_and_phase_without_touching_user_rules(self):
        if sys.platform not in ('darwin', 'linux'):
            return  # Unsupported-platform refusal is covered by integration above.
        for mode, expected_errno, expected_phase in [('space', 28, 'exchange'), ('permission', 13, 'cleanup')]:
            with self.subTest(mode=mode):
                original = b'# Private user rules\n'
                active = self.fixture('AGENTS.md', original)
                preview = self.cli('entry', 'integrate', '--host', 'codex')['data']
                script = '''import ctypes,errno,os,runpy,sys
from unittest.mock import patch
mode=sys.argv[1]
sys.argv=sys.argv[2:]
library=ctypes.CDLL(None,use_errno=True)
name='renameatx_np' if sys.platform=='darwin' else 'renameat2'
native=getattr(library,name)
native.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
native.restype=ctypes.c_int
original_unlink=os.unlink
def exchange(*args):
    if mode=='space':
        ctypes.set_errno(errno.ENOSPC)
        return -1
    return native(*args)
def unlink(path,*args,**kwargs):
    if mode=='permission' and path=='left' and 'dir_fd' in kwargs:
        raise OSError(errno.EACCES,'Probe cleanup refused')
    return original_unlink(path,*args,**kwargs)
class Library:
    def __getattr__(self,key):
        return exchange if key==name else getattr(library,key)
with patch('ctypes.CDLL',return_value=Library()), patch('os.unlink',unlink):
    runpy.run_path(sys.argv[0],run_name='__main__')
'''
                command = [sys.executable, '-I', '-B', '-c', script, mode, str(ROOT / 'scripts/continuity.py'),
                           '--project', str(self.project), 'entry', 'integrate', '--host', 'codex', '--apply',
                           '--expect-state', 'active', '--expect-sha256', preview['sha256'],
                           '--expect-new-sha256', preview['upgrade']['new_sha256']]
                reply = subprocess.run(command, capture_output=True, text=True, timeout=15)
                self.assertEqual(reply.returncode, 0, reply.stdout + reply.stderr)
                data = json.loads(reply.stdout)['data']
                self.assertEqual(active.read_bytes(), original)
                self.assertEqual(data['state'], 'needs_review')
                op = data['upgrade']
                self.assertEqual(op['native_result'], 'not_attempted')
                self.assertEqual(op.get('probe_errno'), expected_errno)
                self.assertEqual(op.get('probe_phase'), expected_phase)
                self.assertEqual(op['probe_state'], 'cleanup_failed' if mode == 'permission' else 'unreliable_or_unavailable')

    def test_loading_notice_is_not_a_yaml_scope_parser(self):
        for content in (b'---\n---\nUser rules.\n',
                        b'---\ndescription: local rules\n...\nUser rules.\n',
                        b'---\n"paths": ["src/**"]\n---\nUser rules.\n'):
            with self.subTest(content=content):
                self.fixture('.claude/rules/recaloom.md', content)
                before = self.snapshot()
                data = self.cli('entry', 'integrate', '--host', 'claude-code')['data']
                self.assertEqual(data['loading_notice']['code'], 'ENTRY_FRONTMATTER_SCOPE_UNVERIFIED')
                self.assertFalse(data['loading_notice']['path_scope_inferred'])
                self.assertFalse(data['host_loading_verified'])
                self.assertEqual(self.snapshot(), before)

    def test_loading_notice_does_not_infer_other_hosts_or_plain_text(self):
        for host, relative in HOSTS:
            examples = [b'# Rules\n', b'\xef\xbb\xbf# Rules\n', b'\xef\xbb\xbf',
                        b'# Rules\n---\npaths: src/**\n---\n']
            if host != 'claude-code':
                examples.append(b'---\npaths: src/**\n---\n# Rules\n')
            for content in examples:
                with self.subTest(host=host, content=content):
                    self.fixture(relative, content)
                    before = self.snapshot()
                    data = self.cli('entry', 'integrate', '--host', host)['data']
                    self.assertNotIn('loading_notice', data)
                    self.assertFalse(data['host_loading_verified'])
                    self.assertEqual(self.snapshot(), before)

    def test_loading_notice_preserves_budget_refusal_and_standalone_state(self):
        if sys.platform not in ('darwin', 'linux'):
            before = self.snapshot()
            refused = self.cli('setup', '--host', 'claude-code', '--write-instructions', ok=False)
            self.assertEqual(refused['code'], 'ENTRY_WRITE_UNSUPPORTED')
            self.assertEqual(self.snapshot(), before)
            preview = self.cli('setup', '--host', 'claude-code')['data']['project_entry']
            # Diagnostic input only, not a claim that automatic writing worked.
            self.fixture('.claude/rules/recaloom.md', preview['content'].encode('utf-8'))
        else:
            self.cli('setup', '--host', 'claude-code', '--write-instructions')
        standalone = self.cli('entry', 'status', '--host', 'claude-code')['data']
        self.assertNotIn('loading_notice', standalone)
        self.assertFalse(standalone['host_loading_verified'])
        self.fixture('.claude/rules/recaloom.md', b'---\npaths: src/**\n---\n# My rules\n')
        preview = self.cli('entry', 'integrate', '--host', 'claude-code')['data']
        before = self.snapshot()
        refused = self.cli('entry', 'integrate', '--host', 'claude-code', '--apply',
                           '--expect-state', 'active', '--expect-sha256', preview['sha256'],
                           '--expect-new-sha256', preview['upgrade']['new_sha256'],
                           '--max-chars', '256', ok=False)
        self.assertEqual(refused['code'], 'BUDGET_TOO_SMALL')
        self.assertEqual(self.snapshot(), before)
        if self.apply_native_or_check_refusal('claude-code', preview) is None:
            return
        before = self.snapshot()
        refused = self.cli('entry', 'status', '--host', 'claude-code', '--max-chars', '256', ok=False)
        self.assertEqual(refused['code'], 'BUDGET_TOO_SMALL')
        self.assertEqual(self.snapshot(), before)

    def test_claude_frontmatter_notice_preserves_scope_through_lifecycle(self):
        original = b'\xef\xbb\xbf---\r\npaths:\r\n  - "src/**"\r\n---\r\n# My rules\r\nKeep data private.\r\n'
        file = self.fixture('.claude/rules/recaloom.md', original)
        before = self.snapshot()
        preview = self.cli('entry', 'integrate', '--host', 'claude-code')['data']
        notice = preview['loading_notice']
        self.assertEqual(notice['code'], 'ENTRY_FRONTMATTER_SCOPE_UNVERIFIED')
        self.assertFalse(notice['path_scope_inferred'])
        self.assertIn('fresh session', notice['message'])
        self.assertEqual(self.snapshot(), before)
        applied = self.apply_native_or_check_refusal('claude-code', preview)
        if applied is None:
            return
        self.assertEqual(applied['loading_notice'], notice)
        before = self.snapshot()
        diagnosed = self.cli('doctor', '--host', 'claude-code')['data']['host_entry']
        self.assertEqual(diagnosed['loading_notice'], notice)
        self.assertFalse(diagnosed['host_loading_verified'])
        self.assertEqual(self.snapshot(), before)
        for action, desired in [('pause', 'paused'), ('enable', 'active')]:
            status = self.cli('entry', 'status', '--host', 'claude-code')['data']
            self.assertEqual(status['loading_notice'], notice)
            changed = self.cli('entry', action, '--host', 'claude-code',
                               '--expect-sha256', status['sha256'])['data']
            self.assertEqual(changed['loading_notice'], notice)
            self.assertEqual(changed['state'], desired)
        before = self.snapshot()
        upgraded = self.cli('entry', 'upgrade', '--host', 'claude-code')['data']
        self.assertEqual(upgraded['loading_notice'], notice)
        self.assertFalse(upgraded['host_loading_verified'])
        self.assertEqual(self.snapshot(), before)
        self.assertTrue(file.read_bytes().startswith(original.split(b'# My rules')[0]))
        self.assertTrue(file.read_bytes().endswith(b'# My rules\r\nKeep data private.\r\n'))

    def test_workbuddy_root_guidance_appearing_after_preview_blocks_apply(self):
        file = self.fixture('.codebuddy/CODEBUDDY.md', b'# My rules\nKeep reports private.\n')
        preview = self.cli('entry', 'integrate', '--host', 'workbuddy')['data']
        priority = self.fixture('CODEBUDDY.md', b'')
        before = self.snapshot()
        refused = self.cli('entry', 'integrate', '--host', 'workbuddy', '--apply',
            '--expect-state', 'active', '--expect-sha256', preview['sha256'],
            '--expect-new-sha256', preview['upgrade']['new_sha256'], ok=False)
        self.assertEqual(refused['code'], 'ENTRY_SHADOWED')
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(priority.read_bytes(), b'')
        self.assertEqual(file.read_bytes(), b'# My rules\nKeep reports private.\n')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project'
        self.project.mkdir()
        self.cli('init', '--name', 'User guidance coexists')

    def cli(self, *args, ok=True):
        proc = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'scripts/continuity.py'),
            '--project', str(self.project), *args], capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0 if ok else 2, proc.stdout + proc.stderr)
        value = json.loads(proc.stdout)
        self.assertEqual(value['ok'], ok)
        return value

    def fixture(self, relative, content):
        file = self.project / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content)
        return file

    def snapshot(self):
        return {str(p.relative_to(self.project)): p.read_bytes() for p in self.project.rglob('*') if p.is_file()}

    def apply(self, host, preview, action='integrate', ok=True):
        return self.cli('entry', action, '--host', host, '--apply',
                        '--expect-state', preview['state'], '--expect-sha256', preview['sha256'],
                        '--expect-new-sha256', preview['upgrade']['new_sha256'], ok=ok)

    def apply_native_or_check_refusal(self, host, preview):
        if sys.platform in ('darwin', 'linux'):
            return self.apply(host, preview)['data']
        before = self.snapshot()
        self.assertEqual(self.apply(host, preview, ok=False)['code'], 'ENTRY_EXCHANGE_UNSUPPORTED')
        self.assertEqual(self.snapshot(), before)
        return None

    def test_apply_recognizes_embedded_rule_and_retains_original(self):
        original = b'\xef\xbb\xbf---\r\npaths: src/**\r\n---\r\n# My rules\r\nNever send customer data.\r\n'
        memory = self.cli('status')['data']
        for host, relative in HOSTS:
            with self.subTest(host=host):
                file = self.fixture(relative, original)
                preview = self.cli('entry', 'integrate', '--host', host)['data']
                applied = self.apply_native_or_check_refusal(host, preview)
                if applied is None:
                    continue
                self.assertEqual(applied['upgrade']['outcome'], 'exchange_observed')
                self.assertEqual(file.read_bytes(), preview['upgrade']['content'].encode())
                self.assertEqual((self.project / applied['upgrade']['retained_path']).read_bytes(), original)
                status = self.cli('entry', 'status', '--host', host)['data']
                self.assertEqual(status['layout'], 'embedded')
                self.assertEqual(status['state'], 'active')
                self.assertEqual(status['user_content_sha256'], hashlib.sha256(original).hexdigest())
                self.assertTrue(status['runtime_binding_matches'])
                self.assertFalse(status['host_loading_verified'])
        self.assertEqual(self.cli('status')['data'], memory)

    def test_preview_keeps_existing_rules_and_frontmatter_without_writes(self):
        original = b'\xef\xbb\xbf---\r\npaths: src/**\r\n---\r\n# My project\r\n\r\nNever send customer data.\r\n```text\r\nunfinished code fence'
        for host, relative in HOSTS:
            with self.subTest(host=host):
                file = self.fixture(relative, original)
                before = self.snapshot()
                data = self.cli('entry', 'integrate', '--host', host)['data']
                proposal = data['upgrade']
                self.assertTrue(data['read_only'])
                self.assertFalse(data['host_loading_verified'])
                self.assertEqual(data['user_content_sha256'], hashlib.sha256(original).hexdigest())
                self.assertEqual(proposal['old_sha256'], hashlib.sha256(original).hexdigest())
                self.assertTrue(proposal['content'].encode().startswith(b'\xef\xbb\xbf---\r\npaths: src/**\r\n---\r\n'))
                self.assertTrue(proposal['content'].endswith('# My project\r\n\r\nNever send customer data.\r\n```text\r\nunfinished code fence'))
                self.assertIn('Run doctor_argv', proposal['content'])
                self.assertEqual(self.snapshot(), before)
                self.assertEqual(file.read_bytes(), original)

    def test_pause_enable_keeps_user_guidance_at_original_path(self):
        original = b'# User rules\r\nUse British English. Never publish without permission.\r\n'
        for host, relative in HOSTS:
            with self.subTest(host=host):
                file = self.fixture(relative, original)
                preview = self.cli('entry', 'integrate', '--host', host)['data']
                if self.apply_native_or_check_refusal(host, preview) is None:
                    continue
                active = file.read_bytes()
                for action, desired in [('pause', 'paused'), ('enable', 'active')]:
                    current = self.cli('entry', 'status', '--host', host)['data']
                    changed = self.cli('entry', action, '--host', host,
                                       '--expect-sha256', current['sha256'])['data']
                    self.assertTrue(file.is_file(), 'Pausing must not move user rules out of discovery')
                    self.assertTrue(file.read_bytes().endswith(original))
                    self.assertEqual(changed['state'], desired)
                    self.assertFalse((file.parent / ('.recaloom-' + host + '.paused')).exists())
                    state = self.cli('entry', 'status', '--host', host)['data']
                    self.assertEqual(state['state'], desired)
                    self.assertEqual(state['user_content_sha256'], hashlib.sha256(original).hexdigest())
                    if desired == 'paused':
                        self.assertNotIn(b'Run doctor_argv', file.read_bytes())
                        self.assertIn(b'recovery is paused', file.read_bytes())
                    else:
                        self.assertEqual(file.read_bytes(), active)

    def test_upgrade_keeps_outside_edits_and_does_not_enable_paused_block(self):
        original = b'# User rules\nAsk before publishing.\n'
        for host, relative in HOSTS:
            for state in ('active', 'paused'):
                with self.subTest(host=host, state=state):
                    # A fresh project avoids overwriting an earlier managed entry.
                    self.project = Path(self.temp.name) / (host + '-' + state)
                    self.project.mkdir()
                    self.cli('init', '--name', 'Existing user text')
                    file = self.fixture(relative, original)
                    preview = self.cli('entry', 'integrate', '--host', host)['data']
                    if self.apply_native_or_check_refusal(host, preview) is None:
                        continue
                    if state == 'paused':
                        status = self.cli('entry', 'status', '--host', host)['data']
                        self.cli('entry', 'pause', '--host', host, '--expect-sha256', status['sha256'])
                    extra = b'Use metric units.\n'
                    file.write_bytes(file.read_bytes() + extra)
                    old = file.read_bytes()
                    preview = self.cli('entry', 'upgrade', '--host', host)['data']
                    self.assertEqual(preview['state'], state)
                    self.assertTrue(preview['upgrade']['content'].encode().endswith(original + extra))
                    self.apply(host, preview, 'upgrade')
                    self.assertEqual(file.read_bytes(), old, 'No-op upgrade must not remove user text')
                    status = self.cli('entry', 'status', '--host', host)['data']
                    self.assertEqual(status['state'], state)
                    self.assertEqual(status['user_content_sha256'], hashlib.sha256(original + extra).hexdigest())
                    draft = self.fixture('draft.json', json.dumps(dict(objective='Workshop for 18 people',
                        next_action='Compare rooms', constraints=['Budget 2300; no booking'],
                        decisions=[], unresolved=['Date unknown'], evidence=[])).encode())
                    self.cli('checkpoint', '--from-file', str(draft), '--expect-revision', '0')
                    preview = self.cli('entry', 'upgrade', '--host', host)['data']
                    result = self.apply(host, preview, 'upgrade')['data']
                    self.assertEqual(result['upgrade']['outcome'], 'exchange_observed')
                    self.assertEqual((self.project / result['upgrade']['retained_path']).read_bytes(), old)
                    self.assertTrue(file.read_bytes().endswith(original + extra))
                    self.assertEqual(self.cli('entry', 'status', '--host', host)['data']['state'], state)

    def test_lifecycle_rejects_unsafe_user_text_after_integration(self):
        file = self.fixture('AGENTS.md', b'# User rules\nNo public uploads.\n')
        preview = self.cli('entry', 'integrate', '--host', 'codex')['data']
        if self.apply_native_or_check_refusal('codex', preview) is None:
            return
        original = file.read_bytes()
        for append in (b'\x00', b'\x7f', '\u0085'.encode()):
            with self.subTest(append=append):
                file.write_bytes(original + append)
                before = self.snapshot()
                result = self.cli('entry', 'status', '--host', 'codex', ok=False)
                self.assertEqual(result['code'], 'ENTRY_UNRECOGNIZED')
                self.assertEqual(self.snapshot(), before)

    def test_invalid_rules_and_changed_confirmation_refuse_without_writes(self):
        for content, code in [(b'\xff', 'ENTRY_ENCODING'), (b'rules\x00', 'ENTRY_ENCODING'),
                              (b'---\npaths: src/**', 'ENTRY_FRONTMATTER'),
                              (b'---\na: b\n---', 'ENTRY_FRONTMATTER'),
                              (b'x' * 65000, 'ENTRY_TOO_LARGE'),
                              (b'<!-- recaloom-managed-v1:active -->\n', 'ENTRY_ALREADY_MANAGED')]:
            with self.subTest(code=code):
                self.fixture('AGENTS.md', content)
                before = self.snapshot()
                failure = self.cli('entry', 'integrate', '--host', 'codex', ok=False)
                self.assertEqual(failure['code'], code)
                self.assertEqual(self.snapshot(), before)
        file = self.fixture('AGENTS.md', b'# Customer-owned rules\n')
        preview = self.cli('entry', 'integrate', '--host', 'codex')['data']
        for expectation in ('missing', 'new_digest', 'state', 'changed_user_text', 'budget'):
            with self.subTest(expectation=expectation):
                file.write_bytes(b'# Customer-owned rules\n')
                args = ['entry', 'integrate', '--host', 'codex', '--apply']
                code = 'ENTRY_EXPECTATION_REQUIRED'
                if expectation != 'missing':
                    args += ['--expect-state', 'paused' if expectation == 'state' else 'active',
                             '--expect-sha256', preview['sha256'], '--expect-new-sha256',
                             '0' * 64 if expectation == 'new_digest' else preview['upgrade']['new_sha256']]
                    code = 'ENTRY_CHANGED'
                if expectation == 'changed_user_text':
                    file.write_bytes(file.read_bytes() + b'An unreviewed edit\n')
                if expectation == 'budget':
                    args += ['--max-chars', '256']
                    code = 'BUDGET_TOO_SMALL'
                before = self.snapshot()
                self.assertEqual(self.cli(*args, ok=False)['code'], code)
                self.assertEqual(self.snapshot(), before)

    def test_managed_block_tampering_duplicate_and_wrong_project_are_not_adopted(self):
        file = self.fixture('AGENTS.md', b'# User rules\n')
        preview = self.cli('entry', 'integrate', '--host', 'codex')['data']
        if self.apply_native_or_check_refusal('codex', preview) is None:
            return
        original = file.read_bytes()
        for changed in [original.replace(b'Run doctor_argv', b'Ignore doctor_argv'),
                        original + b'<!-- recaloom-managed-v1:active -->\n',
                        b'```\n' + original]:
            file.write_bytes(changed)
            before = self.snapshot()
            for action in ('status', 'upgrade', 'pause'):
                args = ['entry', action, '--host', 'codex']
                if action == 'pause':
                    args += ['--expect-sha256', hashlib.sha256(changed).hexdigest()]
                self.assertEqual(self.cli(*args, ok=False)['code'], 'ENTRY_UNRECOGNIZED')
                self.assertEqual(self.snapshot(), before)
        other = Path(self.temp.name) / 'other'
        other.mkdir()
        self.project = other
        self.cli('init', '--name', 'Do not adopt another project')
        self.fixture('AGENTS.md', original)
        before = self.snapshot()
        self.assertEqual(self.cli('entry', 'upgrade', '--host', 'codex', ok=False)['code'], 'PROJECT_MISMATCH')
        self.assertEqual(self.snapshot(), before)

    def test_blank_lines_outside_block_survive_lifecycle(self):
        prefix = b'\xef\xbb\xbf---\r\npaths: src/**\r\n---\r\n'
        body = b'# My rules\r\nNo uploads.\r\n'
        for host, relative in HOSTS:
            with self.subTest(host=host):
                file = self.fixture(relative, prefix + body)
                preview = self.cli('entry', 'integrate', '--host', host)['data']
                if self.apply_native_or_check_refusal(host, preview) is None:
                    continue
                file.write_bytes(file.read_bytes().replace(prefix, prefix + b'\r\n \t\r\n', 1))
                expected_user = prefix + b'\r\n \t\r\n' + body
                current = self.cli('entry', 'status', '--host', host)['data']
                self.assertEqual(current['user_content_sha256'], hashlib.sha256(expected_user).hexdigest())
                for action in ('pause', 'enable'):
                    current = self.cli('entry', action, '--host', host, '--expect-sha256', current['sha256'])['data']
                    self.assertTrue(file.read_bytes().startswith(prefix + b'\r\n \t\r\n<!-- recaloom-managed-v1:'))
                    self.assertTrue(file.read_bytes().endswith(body))
                preview = self.cli('entry', 'upgrade', '--host', host)['data']
                unchanged = file.read_bytes()
                self.apply(host, preview, 'upgrade')
                self.assertEqual(file.read_bytes(), unchanged)

    def test_marker_text_in_path_does_not_break_legacy_or_embedded_rules(self):
        if sys.platform not in ('darwin', 'linux'):
            return  # This pathname is invalid on Windows; not a Windows runtime claim.
        for layout in ('standalone', 'embedded'):
            with self.subTest(layout=layout):
                self.project = Path(self.temp.name) / (layout + ' <!-- recaloom-managed-v1:active -->')
                self.project.mkdir()
                self.cli('init', '--name', 'Delimiter text is path data')
                if layout == 'standalone':
                    self.cli('setup', '--host', 'codex', '--write-instructions')
                else:
                    self.fixture('AGENTS.md', b'# My rules\n')
                    preview = self.cli('entry', 'integrate', '--host', 'codex')['data']
                    self.apply('codex', preview)
                active = self.cli('entry', 'status', '--host', 'codex')['data']
                self.assertEqual(active['state'], 'active')
                paused = self.cli('entry', 'pause', '--host', 'codex', '--expect-sha256', active['sha256'])['data']
                self.assertEqual(paused['state'], 'paused')
                preview = self.cli('entry', 'upgrade', '--host', 'codex')['data']
                self.apply('codex', preview, 'upgrade')

    def test_ordinary_prefix_heading_is_preserved_without_moving_the_block(self):
        for host, relative in HOSTS:
            with self.subTest(host=host):
                original = b'# Original user guidance\n'
                file = self.fixture(relative, original)
                preview = self.cli('entry', 'integrate', '--host', host)['data']
                if self.apply_native_or_check_refusal(host, preview) is None:
                    continue
                prefix = b'# Local note\nNever email customer files.\n\n'
                file.write_bytes(prefix + file.read_bytes())
                status = self.cli('entry', 'status', '--host', host)['data']
                self.assertEqual(status['user_content_sha256'], hashlib.sha256(prefix + original).hexdigest())
                paused = self.cli('entry', 'pause', '--host', host, '--expect-sha256', status['sha256'])['data']
                self.assertEqual(paused['state'], 'paused')
                self.assertTrue(file.read_bytes().startswith(prefix + b'<!-- recaloom-managed-v1:paused -->\n'))
                self.assertTrue(file.read_bytes().endswith(original))
                preview = self.cli('entry', 'upgrade', '--host', host)['data']
                self.apply(host, preview, 'upgrade')

    def test_failed_staging_does_not_claim_embedded_layout(self):
        file = self.fixture('AGENTS.md', b'# Unchanged personal rules\n')
        original = file.read_bytes()
        preview = self.cli('entry', 'integrate', '--host', 'codex')['data']
        if sys.platform not in ('darwin', 'linux'):
            self.apply_native_or_check_refusal('codex', preview)
            return
        import resource
        import signal

        def file_limit():
            signal.signal(signal.SIGXFSZ, signal.SIG_IGN)
            resource.setrlimit(resource.RLIMIT_FSIZE, (1, 1))

        command = [sys.executable, '-I', '-B', str(ROOT / 'scripts/continuity.py'), '--project', str(self.project),
                   'entry', 'integrate', '--host', 'codex', '--apply', '--expect-state', 'active',
                   '--expect-sha256', preview['sha256'], '--expect-new-sha256', preview['upgrade']['new_sha256']]
        result = subprocess.run(command, capture_output=True, text=True, timeout=15, preexec_fn=file_limit)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        data = json.loads(result.stdout)['data']
        self.assertEqual(data['state'], 'needs_review')
        self.assertEqual(data['layout'], 'unknown')
        self.assertEqual(data['proposed_layout'], 'embedded')
        self.assertEqual(data['upgrade']['native_result'], 'not_attempted')
        self.assertEqual(file.read_bytes(), original)
        retained = self.project / data['upgrade']['retained_path']
        self.assertEqual(retained.stat().st_size, 1)


if __name__ == '__main__':
    unittest.main()
