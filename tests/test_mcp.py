"""Optional MCP tests: real stdio, no model/network calls or internal DB reads."""
import importlib.util
import json
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
                                     'continuity_context', 'continuity_receipt'})
            result = await client.call_tool('continuity_status', {})
            self.assertFalse(result.is_error)
            state = result.structured_content
            self.assertEqual(state['data']['project_id'], initial['project_id'])
            self.assertEqual(state['data']['revision'], 0)
            self.assertEqual(state['data']['name'], 'Example project')
        self.assertEqual(self.cli('status')['data']['revision'], 0)

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
            larger = await client.call_tool('continuity_context', {'max_chars': 9000})
            self.assertFalse(larger.is_error)
            encoded = json.dumps(larger.model_dump(by_alias=True, exclude_none=True), ensure_ascii=False, separators=(',', ':'))
            self.assertLessEqual(len(encoded) + 1, 9000)
            self.assertIn('Do not delete', larger.structured_content['data']['text'])
