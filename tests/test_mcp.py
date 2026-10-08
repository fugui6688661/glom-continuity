"""Optional MCP tests: real stdio, no model/network calls or internal DB reads."""
import importlib.util
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MCP_AVAILABLE = importlib.util.find_spec('mcp') is not None
if MCP_AVAILABLE:
    from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(MCP_AVAILABLE, 'Optional MCP SDK not installed; MCP NOT verified by this run')
class MCPIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project'
        self.project.mkdir()

    def cli(self, *args):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
                                 '--project', str(self.project), *args],
                                capture_output=True, text=True, timeout=10)
        return json.loads(result.stdout)

    def client(self, writable=False):
        return Client(StdioServerParameters(command=sys.executable, args=[
            '-B', str(ROOT / 'scripts/mcp_server.py'), '--project', str(self.project),
            *(['--allow-writes'] if writable else [])]), read_timeout_seconds=10)

    async def test_readonly_client_discovers_and_recovers_the_cli_project(self):
        initial = self.cli('init', '--name', 'Example project')['data']
        async with self.client() as client:
            names = {t.name for t in (await client.list_tools()).tools}
            self.assertEqual(names, {'continuity_status', 'continuity_check',
                                     'continuity_context', 'continuity_receipt', 'continuity_resume',
                                     'continuity_doctor', 'continuity_review'})
            diagnosis = await client.call_tool('continuity_doctor', {})
            self.assertFalse(diagnosis.is_error)
            self.assertEqual(diagnosis.structured_content['data']['product_id'], 'glom-continuity')
            self.assertEqual(diagnosis.structured_content['data']['storage']['project_id'], initial['project_id'])
            self.assertFalse(diagnosis.structured_content['data']['write_tools_enabled'])
            result = await client.call_tool('continuity_status', {})
            self.assertFalse(result.is_error)
            state = result.structured_content
            self.assertEqual(state['data']['project_id'], initial['project_id'])
            self.assertEqual(state['data']['revision'], 0)
            self.assertEqual(state['data']['name'], 'Example project')
        self.assertEqual(self.cli('status')['data']['revision'], 0)

    async def test_readonly_review_explains_changes_and_enforces_complete_result_budget(self):
        initial = self.cli('init', '--name', 'Review changes')['data']
        source = self.project / 'brief.txt'
        source.write_text('ORIGINAL_BODY', encoding='utf-8')
        draft = dict(objective='Review', next_action='Recheck input', constraints=[], decisions=[], unresolved=[],
                     evidence=[{'path': 'brief.txt', 'role': 'input'}])
        (self.project / 'draft.json').write_text(json.dumps(draft), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '0')
        source.write_text('NEW_BODY', encoding='utf-8')
        async with self.client() as client:
            result = await client.call_tool('continuity_review', {'expect_project_id': initial['project_id'], 'max_chars': 12000})
            self.assertFalse(result.is_error, str(result.content))
            data = result.structured_content['data']
            self.assertTrue(data['read_only'])
            self.assertEqual(data['references'][0]['state'], 'changed')
            self.assertEqual(data['instruction_authority'], 'none')
            self.assertNotIn('NEW_BODY', str(result.content))
            # The SDK client may add defaults that were not on the wire. Give
            # enough room for the CLI envelope, but not both MCP representations.
            budget = len(json.dumps(result.structured_content, ensure_ascii=False,
                                    sort_keys=True, separators=(',', ':'))) + 1
            self.assertTrue(self.cli('review', '--max-chars', str(budget))['ok'])
            small = await client.call_tool('continuity_review', {'max_chars': budget})
            self.assertTrue(small.is_error)
            self.assertEqual(small.structured_content['code'], 'BUDGET_TOO_SMALL')
            self.assertIsNone(small.structured_content['data'])
            wrong = await client.call_tool('continuity_review', {'expect_project_id': 'another'})
            self.assertTrue(wrong.is_error)
            self.assertEqual(wrong.structured_content['code'], 'PROJECT_MISMATCH')
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    async def test_readonly_resume_handles_first_save_then_recovers_current_project(self):
        async with self.client() as client:
            result = await client.call_tool('continuity_resume', {})
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content['data']['recovery_state'], 'not_initialized')
            self.assertFalse((self.project / '.continuity').exists())
            self.cli('init', '--name', 'One call recovery')
            result = await client.call_tool('continuity_resume', {})
            self.assertEqual(result.structured_content['data']['recovery_state'], 'no_checkpoint')
            draft = dict(objective='Review a draft', next_action='Read the brief',
                         constraints=['Do not publish'], decisions=[], unresolved=['Price unknown'], evidence=[])
            (self.project / 'draft.json').write_text(json.dumps(draft), encoding='utf-8')
            self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '0')
            result = await client.call_tool('continuity_resume', {'max_chars': 6000})
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content['data']['recovery_state'], 'no_references')
            self.assertIn('Price unknown', result.structured_content['data']['text'])
            small = await client.call_tool('continuity_resume', {'max_chars': 1000})
            self.assertTrue(small.is_error)
            self.assertEqual(small.structured_content['code'], 'BUDGET_TOO_SMALL')
            self.assertIsNone(small.structured_content['data'])

    async def test_opt_in_memory_summary_is_readonly_and_keeps_mcp_wire_budget(self):
        self.assertTrue(self.cli('init', '--name', 'Memory summary')['ok'])
        notes = [{'id': f'note-{index}', 'kind': 'preference', 'title': 'Synthetic note',
                  'body': 'Preserve the full current preference.', 'when': ['*'],
                  'status': 'active' if index < 2 else 'retired', 'source': 'Synthetic owner',
                  'expires_at': None} for index in range(32)]
        (self.project / 'memory.json').write_text(json.dumps({'format': 'continuity-memory-v1', 'items': notes}))
        draft = dict(objective='Keep useful memory', next_action='Review', constraints=['Do not publish'],
                     decisions=['Use reviewed input'], unresolved=['Price unknown'], evidence=[{'path': 'memory.json', 'role': 'memory'}])
        (self.project / 'draft.json').write_text(json.dumps(draft))
        self.assertTrue(self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '0')['ok'])
        self.assertTrue(self.cli('handoff', '--recipient', 'next-reviewer', '--expect-revision', '1')['ok'])
        before = {str(path): path.read_bytes() for path in self.project.rglob('*') if path.is_file()}
        async with self.client() as client:
            for tool in ('continuity_context', 'continuity_resume'):
                full = await client.call_tool(tool, {'max_chars': 50000})
                self.assertFalse(full.is_error, str(full.content))
                result = await client.call_tool(tool, {'memory_summary': True, 'max_chars': 6000})
                self.assertFalse(result.is_error, str(result.content))
                data = result.structured_content['data']
                self.assertEqual(data['memory']['selected'], full.structured_content['data']['memory']['selected'])
                self.assertEqual(len(data['memory']['selected']), 2)
                self.assertEqual(data['memory']['omitted_counts'], {'retired': 30})
                self.assertNotIn('omitted', data['memory'])
                self.assertIn('Do not publish', data['text'])
                self.assertIn('Price unknown', data['text'])
                self.assertIn('Use reviewed input', data['text'])
                if tool == 'continuity_resume':
                    self.assertEqual(data['pending_handoffs'], full.structured_content['data']['pending_handoffs'])
                # A budget that fits one envelope but not MCP's two representations must fail.
                budget = len(json.dumps(result.structured_content, ensure_ascii=False, sort_keys=True,
                                        separators=(',', ':'))) + 1
                cli = self.cli(tool.removeprefix('continuity_'), '--memory-summary', '--max-chars', str(budget))
                self.assertTrue(cli['ok'])
                limited = await client.call_tool(tool, {'memory_summary': True, 'max_chars': budget})
                self.assertEqual(limited.structured_content['code'], 'BUDGET_TOO_SMALL')
                self.assertIsNone(limited.structured_content['data'])
                malformed = await client.call_tool(tool, {'memory_summary': 'false', 'max_chars': 50000})
                self.assertTrue(malformed.is_error)
        self.assertEqual({str(path): path.read_bytes() for path in self.project.rglob('*') if path.is_file()}, before)

    async def test_mcp_writer_hands_off_to_cli_and_recovers_its_next_revision(self):
        (self.project / 'input.txt').write_text('source data', encoding='utf-8')
        draft = {'objective': 'Prepare a source-backed note', 'next_action': 'Write note.txt',
                 'constraints': ['Keep the source unchanged'], 'decisions': [], 'unresolved': [],
                 'evidence': [{'path': 'input.txt', 'role': 'input'}]}
        (self.project / 'checkpoint.json').write_text(json.dumps(draft), encoding='utf-8')
        async with self.client(writable=True) as client:
            initialized = await client.call_tool('continuity_init', {'name': 'Mixed interfaces'})
            self.assertFalse(initialized.is_error)
            saved = await client.call_tool('continuity_checkpoint',
                                          {'from_file': str(self.project / 'checkpoint.json'), 'expect_revision': 0})
            self.assertFalse(saved.is_error)
            offered = await client.call_tool('continuity_handoff', {'recipient': 'agent-b', 'expect_revision': 1})
            handoff_id = offered.structured_content['data']['handoff_id']
        self.assertTrue(self.cli('accept', '--id', handoff_id, '--recipient', 'agent-b')['ok'])
        (self.project / 'note.txt').write_text('A note based on source data.', encoding='utf-8')
        draft['next_action'] = 'Review note.txt with the user'
        draft['evidence'].append({'path': 'note.txt', 'role': 'artifact'})
        (self.project / 'next.json').write_text(json.dumps(draft), encoding='utf-8')
        self.assertTrue(self.cli('checkpoint', '--from-file', str(self.project / 'next.json'),
                                 '--expect-revision', '1')['ok'])
        async with self.client() as client:
            context = await client.call_tool('continuity_context', {})
            self.assertEqual(context.structured_content['data']['revision'], 2)
            self.assertIn('Review note.txt with the user', context.structured_content['data']['text'])
            receipt = await client.call_tool('continuity_receipt', {'id': handoff_id})
            self.assertEqual(receipt.structured_content['data']['state'], 'accepted')
            self.assertFalse(receipt.structured_content['data']['external_actions_verified'])

    async def test_checkpoint_identity_guard_is_enforced_by_the_stdio_writer(self):
        identity = self.cli('init', '--name', 'Bound writer')['data']['project_id']
        draft = dict(objective='A reviewed plan', next_action='Review unknowns', constraints=['No publishing'],
                     decisions=[], unresolved=['Schedule unknown'], evidence=[])
        (self.project / 'bound.json').write_text(json.dumps(draft), encoding='utf-8')
        before = (self.project / '.continuity/state.sqlite3').read_bytes()
        async with self.client(writable=True) as client:
            arguments = {'from_file': 'bound.json', 'expect_revision': 0,
                         'expect_project_id': 'another-project'}
            rejected = await client.call_tool('continuity_checkpoint', arguments)
            self.assertTrue(rejected.is_error, str(rejected.content))
            self.assertEqual(rejected.structured_content['code'], 'PROJECT_MISMATCH')
            self.assertIsNone(rejected.structured_content['data'])
            self.assertEqual((self.project / '.continuity/state.sqlite3').read_bytes(), before)
            arguments['expect_project_id'] = identity
            saved = await client.call_tool('continuity_checkpoint', arguments)
            self.assertFalse(saved.is_error, str(saved.content))
            self.assertEqual(saved.structured_content['data']['revision'], 1)
        async with self.client() as readonly:
            self.assertNotIn('continuity_checkpoint', {t.name for t in (await readonly.list_tools()).tools})
            rejected = await readonly.call_tool('continuity_checkpoint', arguments)
            self.assertTrue(rejected.is_error)
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    async def test_mcp_returns_work_for_cli_receipt_and_new_readonly_session(self):
        self.cli('init', '--name', 'Result round trip')
        draft = dict(objective='Write a review', next_action='Prepare note.md',
                     constraints=['Do not publish'], decisions=[], unresolved=['Price unknown'], evidence=[])
        (self.project / 'draft.json').write_text(json.dumps(draft), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '0')
        identifier = self.cli('handoff', '--recipient', 'reviewer', '--expect-revision', '1')['data']['handoff_id']
        self.cli('accept', '--id', identifier, '--recipient', 'reviewer')
        (self.project / 'note.md').write_text('Draft for review. Price unknown.', encoding='utf-8')
        draft['evidence'] = [{'path': 'note.md', 'role': 'artifact'}]
        (self.project / 'result.json').write_text(json.dumps(draft), encoding='utf-8')
        arguments = dict(id=identifier, recipient='reviewer', from_file='result.json', expect_revision=1)
        async with self.client(writable=True) as client:
            result = await client.call_tool('continuity_return_work', arguments)
            self.assertFalse(result.is_error, str(result.content))
            saved = result.structured_content['data']
            self.assertEqual(saved['revision'], 2)
            self.assertFalse(saved['result']['semantic_completion_verified'])
            replay = await client.call_tool('continuity_return_work', arguments)
            self.assertFalse(replay.is_error)
            self.assertTrue(replay.structured_content['data']['replayed'])
            self.assertEqual(replay.structured_content['data']['checkpoint_id'], saved['checkpoint_id'])
        receipt = self.cli('receipt', '--id', identifier)['data']['result']
        self.assertEqual(receipt['revision'], 2)
        self.assertEqual(receipt['artifacts'][0]['path'], 'note.md')
        async with self.client() as client:
            self.assertNotIn('continuity_return_work', {t.name for t in (await client.list_tools()).tools})
            recovered = await client.call_tool('continuity_resume', {'max_chars': 16000})
            self.assertFalse(recovered.is_error)
            self.assertEqual(recovered.structured_content['data']['result']['handoff_id'], identifier)
            rejected = await client.call_tool('continuity_return_work', arguments)
            self.assertTrue(rejected.is_error)
        self.assertEqual(self.cli('status')['data']['revision'], 2)

    async def test_receiver_cannot_accept_changed_inputs_or_export_over_an_existing_file(self):
        self.cli('init', '--name', 'Receiver')
        (self.project / 'input.txt').write_text('original', encoding='utf-8')
        draft = {'objective': 'Review source', 'next_action': 'Read input.txt',
                 'constraints': [], 'decisions': [], 'unresolved': [],
                 'evidence': [{'path': 'input.txt', 'role': 'input'}]}
        (self.project / 'checkpoint.json').write_text(json.dumps(draft), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(self.project / 'checkpoint.json'), '--expect-revision', '0')
        offered = self.cli('handoff', '--recipient', 'reviewer', '--expect-revision', '1')
        identifier = offered['data']['handoff_id']
        (self.project / 'input.txt').write_text('changed', encoding='utf-8')
        async with self.client(writable=True) as client:
            context = await client.call_tool('continuity_context', {})
            self.assertFalse(context.is_error)
            state = context.structured_content['data']
            self.assertEqual(state['next_action_status'], 'requires_reference_review')
            self.assertEqual(state['instruction_authority'], 'none')
            self.assertIn('Reference check: needs_review', state['text'])
            self.assertIn('input.txt', state['text'])
            self.assertIn('Recorded next step (not revalidated): Read input.txt', state['text'])
            self.assertEqual(json.loads(context.content[0].text), context.structured_content)
            rejected = await client.call_tool('continuity_accept', {'id': identifier, 'recipient': 'reviewer'})
            self.assertTrue(rejected.is_error)
            self.assertEqual(rejected.structured_content['code'], 'EVIDENCE_CHANGED')
            receipt = await client.call_tool('continuity_receipt', {'id': identifier})
            self.assertEqual(receipt.structured_content['data']['state'], 'open')
            (self.project / 'input.txt').write_text('original', encoding='utf-8')
            accepted = await client.call_tool('continuity_accept', {'id': identifier, 'recipient': 'reviewer'})
            self.assertFalse(accepted.is_error)
            duplicate = await client.call_tool('continuity_accept', {'id': identifier, 'recipient': 'reviewer'})
            self.assertEqual(duplicate.structured_content['code'], 'ALREADY_ACCEPTED')
            exported = await client.call_tool('continuity_export', {'output': 'review.json'})
            self.assertFalse(exported.is_error)
            original = (self.project / 'review.json').read_bytes()
            again = await client.call_tool('continuity_export', {'output': 'review.json'})
            self.assertTrue(again.is_error)
            self.assertEqual(again.structured_content['code'], 'OUTPUT_EXISTS')
            self.assertEqual((self.project / 'review.json').read_bytes(), original)

    async def test_mcp_budget_counts_the_result_wrapper_not_just_the_inner_text(self):
        self.cli('init', '--name', 'Budget')
        draft = {'objective': '文' * 2200, 'next_action': 'Preserve the source',
                 'constraints': ['Do not delete'], 'decisions': [], 'unresolved': [], 'evidence': []}
        (self.project / 'checkpoint.json').write_text(json.dumps(draft), encoding='utf-8')
        self.cli('checkpoint', '--from-file', str(self.project / 'checkpoint.json'), '--expect-revision', '0')
        async with self.client() as client:
            result = await client.call_tool('continuity_context', {'max_chars': 3500})
            self.assertTrue(result.is_error)
            self.assertEqual(result.structured_content['code'], 'BUDGET_TOO_SMALL')
            hint = re.search(r'required_mcp_chars=(\d+)', result.structured_content['error'])
            self.assertIsNotNone(hint)
            budget = int(hint.group(1))
            self.assertGreater(budget, 3500)
            larger = await client.call_tool('continuity_context', {'max_chars': budget})
            self.assertFalse(larger.is_error)
            # The high-level client adds defaults after receiving the frame.
            # Exact transport sizing is checked by the raw peer regression.
            self.assertIn('Do not delete', larger.structured_content['data']['text'])

    async def test_readonly_context_recalls_task_matched_workflow_with_its_full_budget(self):
        self.cli('init', '--name', 'Personal workflow')
        note = {'id': 'film', 'kind': 'workflow', 'title': 'Film review',
                'body': 'Inspect frames and listen to the audio before delivery.',
                'when': ['video'], 'status': 'active', 'source': 'Synthetic user request',
                'expires_at': None}
        (self.project / 'habits.json').write_text(json.dumps({'format': 'continuity-memory-v1', 'items': [note]}))
        draft = {'objective': 'Produce a video', 'next_action': 'Review assets',
                 'constraints': ['Do not publish'], 'decisions': [], 'unresolved': ['Music rights'],
                 'evidence': [{'path': 'habits.json', 'role': 'memory'}]}
        (self.project / 'draft.json').write_text(json.dumps(draft))
        self.assertTrue(self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'), '--expect-revision', '0')['ok'])
        async with self.client() as client:
            result = await client.call_tool('continuity_context', {'query': 'Make a VIDEO', 'max_chars': 6000})
            self.assertFalse(result.is_error)
            data = result.structured_content['data']
            self.assertEqual([x['id'] for x in data['memory']['selected']], ['film'])
            self.assertIn(note['body'], data['text'])
            small = await client.call_tool('continuity_context', {'query': 'video', 'max_chars': 1800})
            self.assertTrue(small.is_error)
            self.assertEqual(small.structured_content['code'], 'BUDGET_TOO_SMALL')

    async def test_legal_large_memory_can_recover_with_an_explicit_larger_budget(self):
        self.cli('init', '--name', 'Large but legal habits')
        references = []
        for index in range(4):
            items = [dict(id=f'p-{index}-{n}', kind='preference', title='Review',
                          body='x' * 4000, when=['*'], status='active',
                          source='Synthetic user request', expires_at=None) for n in range(16)]
            name = f'habits-{index}.json'
            raw = json.dumps(dict(format='continuity-memory-v1', items=items))
            self.assertLess(len(raw.encode('utf-8')), 128 * 1024)
            (self.project / name).write_text(raw, encoding='utf-8')
            references.append(dict(path=name, role='memory'))
        draft = dict(objective='Review only', next_action='Read current inputs',
                     constraints=['No publishing'], decisions=[], unresolved=['Price unknown'],
                     evidence=references)
        (self.project / 'draft.json').write_text(json.dumps(draft), encoding='utf-8')
        self.assertTrue(self.cli('checkpoint', '--from-file', str(self.project / 'draft.json'),
                                 '--expect-revision', '0')['ok'])
        async with self.client() as client:
            for name in ('continuity_context', 'continuity_resume'):
                small = await client.call_tool(name, {'max_chars': 1000000})
                self.assertTrue(small.is_error)
                self.assertEqual(small.structured_content['code'], 'BUDGET_TOO_SMALL')
                large = await client.call_tool(name, {'max_chars': 2000000})
                self.assertFalse(large.is_error, str(large.content)[:300])
                data = large.structured_content['data']
                self.assertEqual(len(data['memory']['selected']), 64)
                self.assertIn('No publishing', data['text'])
                self.assertFalse(data['check']['semantic_completion_verified'])
                encoded = json.dumps(large.model_dump(by_alias=True, exclude_unset=True),
                                     ensure_ascii=False, separators=(',', ':'))
                self.assertLessEqual(len(encoded) + 1, 2000000)
        self.assertEqual(self.cli('status')['data']['revision'], 1)
