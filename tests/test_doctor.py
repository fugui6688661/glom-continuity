"""Installation diagnosis through public CLI processes; synthetic directories only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Doctor(unittest.TestCase):
    def test_small_entry_response_preserves_host_risk_before_binding_and_after_install(self):
        self.cli('init', '--name', 'Small response, complete diagnosis')
        cases = [('workbuddy', '.codebuddy/CODEBUDDY.md', '😀' * 4000,
                  'ENTRY_HOST_BUDGET_EXCEEDED', '8000 UTF-16'),
                 ('codex', 'AGENTS.md', '界' * 11000,
                  'ENTRY_DEFAULT_BUDGET_EXCEEDED', '32 KiB')]
        for host, relative, padding, code, limit in cases:
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# private-synthetic-sentinel\n' + padding, encoding='utf-8')
            full = self.cli('entry', 'integrate', '--host', host, '--max-chars', '100000')['data']
            for action in ('integrate', 'status'):
                with self.subTest(host=host, action=action):
                    if action == 'status':
                        path.write_bytes((full['upgrade']['content']).encode('utf-8'))
                    before = self.snapshot()
                    result = self.cli('entry', action, '--host', host, '--max-chars', '1000', ok=False)
                    self.assertEqual(result['code'], 'BUDGET_TOO_SMALL')
                    self.assertIn(code, result['error'])
                    self.assertIn(limit, result['error'])
                    self.assertIn('--max-chars', result['error'])
                    self.assertNotIn('private-synthetic-sentinel', result['error'])
                    self.assertLessEqual(len(json.dumps(result, ensure_ascii=False)) + 1, 1000)
                    self.assertEqual(self.snapshot(), before)

    def test_workbuddy_budget_boundary_counts_full_rule_in_utf16_not_utf8(self):
        self.cli('init', '--name', 'Boundary')
        path = self.project / '.codebuddy/CODEBUDDY.md'
        path.parent.mkdir()
        original = '# Rules\n'
        path.write_text(original, encoding='utf-8')
        base = self.cli('entry', 'integrate', '--host', 'workbuddy')['data']['upgrade']['content']
        self.assertTrue(base.isascii())
        for letter in ('x', '界'):
            for size in (8000, 8001):
                with self.subTest(letter=letter, units=size):
                    # Both characters are exactly one UTF-16 unit, but have
                    # different UTF-8 sizes. Expected limit is the host spec.
                    path.write_text(original + letter * (size - len(base)), encoding='utf-8')
                    before = self.snapshot()
                    data = self.cli('entry', 'integrate', '--host', 'workbuddy', '--max-chars', '100000')['data']
                    self.assertEqual(len(data['upgrade']['content']), size)
                    if size == 8000:
                        self.assertNotIn('loading_notice', data)
                    else:
                        self.assertEqual(data['loading_notice']['document_utf16_units'], 8001)
                        self.assertEqual(data['loading_notice']['code'], 'ENTRY_HOST_BUDGET_EXCEEDED')
                    self.assertEqual(self.snapshot(), before)

    def test_workbuddy_default_preview_refusal_keeps_the_budget_diagnostic(self):
        self.cli('init', '--name', 'Short actionable response')
        path = self.project / '.codebuddy/CODEBUDDY.md'
        path.parent.mkdir()
        path.write_text('# User rules\n' + 'private-synthetic-text\n' * 1600, encoding='utf-8')
        before = self.snapshot()
        refused = self.cli('entry', 'integrate', '--host', 'workbuddy', ok=False)
        self.assertEqual(refused['code'], 'BUDGET_TOO_SMALL')
        self.assertIn('ENTRY_HOST_BUDGET_EXCEEDED', refused['error'])
        self.assertIn('8000 UTF-16', refused['error'])
        self.assertIn('--max-chars', refused['error'])
        self.assertNotIn('private-synthetic-text', refused['error'])
        self.assertEqual(self.snapshot(), before)

    def test_workbuddy_long_non_bmp_guidance_warns_without_claiming_host_loading(self):
        self.cli('init', '--name', 'Preserve user guidance')
        path = self.project / '.codebuddy/CODEBUDDY.md'
        path.parent.mkdir()
        path.write_text('# Rules\n' + '😀' * 4000, encoding='utf-8')
        before = self.snapshot()
        preview = self.cli('entry', 'integrate', '--host', 'workbuddy', '--max-chars', '100000')['data']
        content = preview['upgrade']['content']
        self.assertLess(len(content), 8000, 'Fixture must distinguish code points from UTF-16 units')
        self.assertTrue(content.replace('😀', '').isascii())
        notice = preview.get('loading_notice', {})
        self.assertEqual(notice.get('code'), 'ENTRY_HOST_BUDGET_EXCEEDED')
        self.assertEqual(notice['document_utf16_units'], len(content) + 4000)
        self.assertEqual(notice['observed_limit_utf16_units'], 8000)
        self.assertEqual(notice['observed_host_version'], '5.6.2')
        self.assertFalse(notice['current_host_checked'])
        self.assertNotIn('😀', json.dumps(notice, ensure_ascii=False))
        self.assertFalse(preview['host_loading_verified'])
        self.assertEqual(self.snapshot(), before)
        # Diagnostic fixture only; no native host is launched.
        path.write_bytes((content).encode('utf-8'))
        before = self.snapshot()
        for command in (('doctor', '--host', 'workbuddy'), ('entry', 'status', '--host', 'workbuddy')):
            data = self.cli(*command)['data']
            entry = data['host_entry'] if command[0] == 'doctor' else data
            self.assertEqual(entry['loading_notice'], notice)
            self.assertFalse(entry['host_loading_verified'])
            if command[0] == 'doctor':
                self.assertIn('8000 UTF-16', entry['next_step'])
        self.assertEqual(self.snapshot(), before)

    def test_codex_default_preview_budget_refuses_with_actionable_short_warning(self):
        self.cli('init', '--name', 'Do not lose the warning')
        (self.project / 'AGENTS.md').write_text('# Rules\n' + 'private-synthetic-text\n' * 1600)
        before = self.snapshot()
        refusal = self.cli('entry', 'integrate', '--host', 'codex', ok=False)
        self.assertEqual(refusal['code'], 'BUDGET_TOO_SMALL')
        self.assertIsNone(refusal['data'])
        self.assertIn('ENTRY_DEFAULT_BUDGET_EXCEEDED', refusal['error'])
        self.assertIn('--max-chars', refusal['error'])
        self.assertNotIn('private-synthetic-text', refusal['error'])
        self.assertEqual(self.snapshot(), before)

    def test_codex_budget_notice_uses_complete_document_and_does_not_assume_other_hosts(self):
        self.cli('init', '--name', 'Document boundary')
        for host, relative in [('codex', 'AGENTS.md'), ('claude-code', '.claude/rules/recaloom.md'),
                               ('workbuddy', '.codebuddy/CODEBUDDY.md')]:
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            original = '# Keep these user rules\n'
            path.write_text(original, encoding='utf-8')
            preview = self.cli('entry', 'integrate', '--host', host)['data']
            prefix_bytes = len(preview['upgrade']['content'].encode('utf-8'))
            for size in (32768, 32769):
                with self.subTest(host=host, bytes=size):
                    path.write_text(original + 'x' * (size - prefix_bytes), encoding='utf-8')
                    before = self.snapshot()
                    data = self.cli('entry', 'integrate', '--host', host, '--max-chars', '100000')['data']
                    self.assertEqual(len(data['upgrade']['content'].encode('utf-8')), size)
                    if host == 'codex' and size > 32768:
                        self.assertEqual(data['loading_notice']['code'], 'ENTRY_DEFAULT_BUDGET_EXCEEDED')
                    elif host == 'workbuddy':
                        self.assertEqual(data['loading_notice']['code'], 'ENTRY_HOST_BUDGET_EXCEEDED')
                        self.assertEqual(data['loading_notice']['document_utf16_units'], size)
                    else:
                        self.assertNotIn('loading_notice', data)
                    self.assertFalse(data['host_loading_verified'])
                    self.assertEqual(self.snapshot(), before)

    def test_codex_large_rule_reports_default_budget_risk_without_claiming_truncation(self):
        self.cli('init', '--name', 'Keep long user instructions')
        path = self.project / 'AGENTS.md'
        # UTF-8 bytes, not character count, determine the host's documented cap.
        path.write_text('# User instructions\n' + '界' * 11000, encoding='utf-8')
        before = self.snapshot()
        preview = self.cli('entry', 'integrate', '--host', 'codex', '--max-chars', '100000')['data']
        self.assertEqual(self.snapshot(), before)
        notice = preview.get('loading_notice', {})
        self.assertEqual(notice.get('code'), 'ENTRY_DEFAULT_BUDGET_EXCEEDED')
        self.assertEqual(notice['default_limit_bytes'], 32768)
        self.assertIsNone(notice['effective_limit_bytes'])
        self.assertFalse(notice['instruction_chain_checked'])
        self.assertEqual(notice['document_bytes'], len(preview['upgrade']['content'].encode('utf-8')))
        self.assertNotIn('界', json.dumps(notice, ensure_ascii=False))
        # Use the public preview as diagnostic input; this is not a native-host run.
        path.write_bytes((preview['upgrade']['content']).encode('utf-8'))
        before = self.snapshot()
        diagnosis = self.cli('doctor', '--host', 'codex')['data']['host_entry']
        status = self.cli('entry', 'status', '--host', 'codex')['data']
        self.assertEqual(diagnosis['loading_notice'], notice)
        self.assertEqual(status['loading_notice'], notice)
        self.assertFalse(diagnosis['host_loading_verified'])
        self.assertIn('budget', diagnosis['next_step'])
        self.assertEqual(self.snapshot(), before)

    def test_unknown_rule_and_priority_conflict_are_both_reported(self):
        self.cli('init', '--name', 'Combined diagnosis')
        for host, rule, priority in [('codex', 'AGENTS.md', 'AGENTS.override.md'),
                                     ('workbuddy', '.codebuddy/CODEBUDDY.md', 'CODEBUDDY.md')]:
            with self.subTest(host=host):
                path = self.project / rule
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('User-owned rule, not generated by Recaloom\n')
                (self.project / priority).write_text('User-owned higher priority rule\n')
                before = self.snapshot()
                entry = self.cli('doctor', '--host', host)['data']['host_entry']
                self.assertEqual(entry['issue']['code'], 'ENTRY_UNRECOGNIZED')
                self.assertEqual(entry.get('priority_issue', {}).get('code'), 'ENTRY_SHADOWED')
                self.assertEqual(entry['priority_issue']['relative_path'], priority)
                self.assertEqual(self.snapshot(), before)

    def test_missing_guide_never_recommends_initialization_or_setup(self):
        copied = self.project.parent / 'incomplete-package/scripts/continuity.py'
        copied.parent.mkdir(parents=True)
        copied.write_bytes(self.program.read_bytes())
        self.program = copied
        for initialized in (False, True):
            with self.subTest(initialized=initialized):
                if initialized:
                    self.cli('init', '--name', 'Existing memory')
                before = self.snapshot()
                data = self.cli('doctor', '--host', 'codex')['data']
                self.assertEqual(data['usage']['state'], 'unavailable')
                self.assertIn('GUIDE_MISSING', data['usage']['issues'])
                self.assertIn('guide', data['host_entry']['next_step'])
                self.assertNotIn('first save', data['host_entry']['next_step'])
                self.assertNotIn('Review setup', data['host_entry']['next_step'])
                self.assertEqual(self.snapshot(), before)

    def entry_fixture(self, host):
        # Set up diagnostic input, not a successful host installation claim.
        preview = self.cli('setup', '--host', host)['data']['project_entry']
        target = self.project / preview['relative_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(preview['content'].encode('utf-8'))

    def test_host_diagnosis_rejects_linked_or_wrong_project_entry_without_changes(self):
        self.cli('init', '--name', 'Selected')
        self.entry_fixture('codex')
        path = self.project / 'AGENTS.md'
        original = path.read_text()
        project_id = self.cli('status')['data']['project_id']
        path.write_bytes((original.replace(project_id, '00000000-0000-0000-0000-000000000000')).encode('utf-8'))
        before = self.snapshot()
        data = self.cli('doctor', '--host', 'codex')['data']
        self.assertEqual(data['host_entry']['issue']['code'], 'PROJECT_MISMATCH')
        self.assertEqual(self.snapshot(), before)
        # A separate user file remains the same; only fixture setup changes the rule path.
        path.rename(self.project / 'retained-rule')
        try:
            path.symlink_to('retained-rule')
        except OSError:
            if sys.platform == 'win32':
                return  # Some Windows accounts cannot create symlinks.
            raise
        before = self.snapshot()
        data = self.cli('doctor', '--host', 'codex')['data']
        self.assertEqual(data['host_entry']['issue']['code'], 'ENTRY_UNSAFE_PATH')
        self.assertEqual(self.snapshot(), before)

    def test_host_diagnosis_prioritizes_absent_or_foreign_storage_without_initializing(self):
        before = self.snapshot()
        data = self.cli('doctor', '--host', 'workbuddy')['data']
        self.assertEqual(data['storage']['state'], 'not_initialized')
        self.assertIn('first save', data['host_entry']['next_step'])
        self.assertEqual(self.snapshot(), before)
        folder = self.project / '.continuity'
        folder.mkdir()
        (folder / 'keep.json').write_text('{}')
        before = self.snapshot()
        data = self.cli('doctor', '--host', 'workbuddy')['data']
        self.assertEqual(data['storage']['state'], 'UNRECOGNIZED_STORAGE')
        self.assertIn('storage', data['host_entry']['next_step'])
        self.assertNotIn('setup', data['host_entry']['next_step'])
        self.assertEqual(self.snapshot(), before)

    def test_host_diagnosis_does_not_recommend_recovery_past_binding_or_priority_issues(self):
        self.cli('init', '--name', 'Unsafe to continue')
        self.entry_fixture('codex')
        path = self.project / 'AGENTS.md'
        original = path.read_text()
        program_hash = self.cli('doctor')['data']['runtime']['program_sha256']
        path.write_bytes((original.replace(program_hash, '0' * 64)).encode('utf-8'))
        before = self.snapshot()
        mismatched = self.cli('doctor', '--host', 'codex')['data']['host_entry']
        self.assertFalse(mismatched['runtime_binding_matches'])
        self.assertIn('binding', mismatched['next_step'])
        self.assertNotIn('fresh session', mismatched['next_step'])
        self.assertEqual(self.snapshot(), before)
        path.write_bytes((original).encode('utf-8'))
        (self.project / 'AGENTS.override.md').write_text('Higher priority user rule\n')
        before = self.snapshot()
        shadowed = self.cli('doctor', '--host', 'codex')['data']['host_entry']
        self.assertEqual(shadowed['priority_issue']['code'], 'ENTRY_SHADOWED')
        self.assertIn('priority', shadowed['next_step'])
        self.assertEqual(self.snapshot(), before)

    def test_host_diagnosis_keeps_runtime_details_and_preserves_unknown_rule(self):
        self.cli('init', '--name', 'Keep user rules')
        content = 'PRIVATE_SYNTHETIC_RULE_DO_NOT_ECHO\n'
        (self.project / 'AGENTS.md').write_bytes((content).encode('utf-8'))
        before = self.snapshot()
        data = self.cli('doctor', '--host', 'codex')['data']
        self.assertEqual(data['product_id'], 'glom-continuity')
        self.assertTrue(data['storage']['compatible'])
        self.assertEqual(data['host_entry']['state'], 'needs_review')
        self.assertEqual(data['host_entry']['issue']['code'], 'ENTRY_UNRECOGNIZED')
        self.assertFalse(data['host_entry']['host_loading_verified'])
        self.assertIn('Preserve', data['host_entry']['next_step'])
        self.assertNotIn(content.strip(), json.dumps(data))
        self.assertEqual(self.snapshot(), before)

    def test_host_diagnosis_explains_active_and_paused_without_writes(self):
        self.cli('init', '--name', 'Lifecycle diagnosis')
        for host in ('codex', 'claude-code', 'workbuddy'):
            with self.subTest(host=host):
                self.entry_fixture(host)
                before = self.snapshot()
                entry = self.cli('doctor', '--host', host)['data']['host_entry']
                self.assertEqual(entry['state'], 'active')
                self.assertTrue(entry['runtime_binding_matches'])
                self.assertFalse(entry['host_loading_verified'])
                self.assertIn('fresh session', entry['next_step'])
                self.assertEqual(self.snapshot(), before)
                # Portable read-only inspection of a paused-file fixture. Native
                # pause/enable operations have their own lifecycle tests.
                (self.project / entry['active_path']).rename(self.project / entry['paused_path'])
                before = self.snapshot()
                paused = self.cli('doctor', '--host', host)['data']['host_entry']
                self.assertEqual(paused['state'], 'paused')
                self.assertIn('enable', paused['next_step'])
                self.assertFalse(paused['already_loaded_context_revoked'])
                self.assertEqual(self.snapshot(), before)

    def snapshot(self):
        result = {}
        for p in self.project.rglob('*'):
            meta = p.lstat()
            result[str(p.relative_to(self.project))] = (
                meta.st_mode, str(p.readlink()) if p.is_symlink() else
                p.read_bytes() if p.is_file() else None)
        return result

    def test_host_diagnosis_reports_missing_entry_without_installing_it(self):
        self.cli('init', '--name', 'Host diagnosis')
        database = self.project / '.continuity/state.sqlite3'
        before = database.read_bytes()
        plain = self.cli('doctor')['data']
        self.assertNotIn('host_entry', plain)
        for host, relative in [('codex', 'AGENTS.md'), ('claude-code', '.claude/rules/recaloom.md'),
                               ('workbuddy', '.codebuddy/CODEBUDDY.md')]:
            with self.subTest(host=host):
                entry = self.cli('doctor', '--host', host)['data']['host_entry']
                self.assertEqual(entry['state'], 'not_installed')
                self.assertEqual(entry['active_path'], relative)
                self.assertTrue(entry['read_only'])
                self.assertFalse(entry['host_loading_verified'])
                self.assertIn('setup', entry['next_step'])
                self.assertFalse((self.project / relative).exists())
                self.assertEqual(database.read_bytes(), before)

    def setUp(self):
        self.program = ROOT / 'scripts/continuity.py'
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.project = Path(temporary.name) / 'selected project'
        self.project.mkdir()

    def cli(self, *args, ok=True):
        run = subprocess.run([sys.executable, '-B', str(self.program),
                              '--project', str(self.project), *args],
                             capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(run.returncode, 0 if ok else 2, run.stdout + run.stderr)
        value = json.loads(run.stdout)
        self.assertEqual(value['ok'], ok)
        return value

    def test_diagnosis_identifies_invoked_tool_without_initializing_a_project(self):
        data = self.cli('doctor')['data']
        self.assertEqual(data['product_id'], 'glom-continuity')
        self.assertEqual(data['display_name'], 'Recaloom')
        self.assertEqual(data['storage']['state'], 'not_initialized')
        self.assertFalse(data['storage']['compatible'])
        self.assertFalse(data['publisher_authenticated'])
        self.assertEqual(Path(data['runtime']['program_path']), ROOT / 'scripts/continuity.py')
        self.assertIn('resume', data['capabilities'])
        self.assertFalse((self.project / '.continuity').exists())

    def test_source_checkout_discloses_unsealed_guide_instead_of_guessing_another_install(self):
        data = self.cli('doctor')['data']
        self.assertEqual(data['usage']['state'], 'source_unsealed')
        self.assertEqual(Path(data['usage']['skill_path']), ROOT / 'skills/project-continuity/SKILL.md')
        self.assertFalse(data['usage']['publisher_authenticated'])
        self.assertFalse(data['usage']['host_configuration_checked'])
        self.assertFalse((self.project / '.continuity').exists())

    def test_existing_project_is_identified_without_rewriting_its_database(self):
        initial = self.cli('init', '--name', 'My project')['data']
        database = self.project / '.continuity/state.sqlite3'
        before = database.read_bytes()
        data = self.cli('doctor')['data']
        self.assertEqual(data['storage']['state'], 'compatible_v1')
        self.assertTrue(data['storage']['compatible'])
        self.assertEqual(data['storage']['project_id'], initial['project_id'])
        self.assertEqual(data['storage']['revision'], 0)
        self.assertEqual(database.read_bytes(), before)

    def test_foreign_directory_is_not_misreported_as_an_empty_project(self):
        folder = self.project / '.continuity'
        folder.mkdir()
        marker = folder / 'other-tool.json'
        marker.write_text('{"keep":"this belongs to another tool"}', encoding='utf-8')
        before = marker.read_bytes()
        data = self.cli('doctor')['data']
        self.assertEqual(data['storage']['state'], 'UNRECOGNIZED_STORAGE')
        self.assertFalse(data['storage']['compatible'])
        self.assertEqual(self.cli('resume', ok=False)['code'], 'UNRECOGNIZED_STORAGE')
        self.assertEqual(self.cli('init', '--name', 'Do not overwrite', ok=False)['code'], 'ALREADY_INITIALIZED')
        self.assertEqual(marker.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['other-tool.json'])


if __name__ == '__main__':
    unittest.main()
