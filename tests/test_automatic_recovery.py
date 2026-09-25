"""Host-neutral lifecycle boundary, exercised as CLI subprocesses, never DB internals."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AutomaticRecovery(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name).resolve() / 'Studio'
        self.project.mkdir()
        self.identity = self.cli('init', '--name', 'Studio')['data']['project_id']
        (self.project / 'brief.txt').write_text('Synthetic brief. Keep budget under 5000.', encoding='utf-8')
        self.draft = dict(objective='Prepare an internal event for 50 people',
                          next_action='Compare venues; do not book', constraints=['Budget 5000', 'No purchases'],
                          decisions=['50 people'], unresolved=['Venue unknown'],
                          evidence=[{'path': 'brief.txt', 'role': 'input'}])
        self.save(0)

    def cli(self, *args):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/continuity.py'),
                                 '--project', str(self.project), *args],
                                capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def save(self, revision):
        path = self.project / 'draft.json'
        path.write_text(json.dumps(self.draft), encoding='utf-8')
        return self.cli('checkpoint', '--from-file', str(path), '--expect-revision', str(revision))

    def event(self, **overrides):
        return {**dict(event='session_start', cwd=str(self.project), session_id='session-A',
                       generation='generation-1', query=''), **overrides}

    def recovery(self, command, payload, *, ok=True, session='session-A', generation='generation-1',
                 project_id=None, budget=10000, input_encoding='utf-8'):
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/recovery.py'),
                                 '--project', str(self.project), '--project-id', project_id or self.identity,
                                 '--session-id', session, '--generation', generation, '--max-chars', str(budget), command],
                                input=json.dumps(payload).encode(input_encoding), capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0 if ok else 2, result.stdout + result.stderr)
        self.assertTrue(result.stdout, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['ok'], ok)
        return value

    def test_prepare_and_deliver_restores_bound_context_without_claiming_completion(self):
        before = self.cli('status')['data']
        prepared = self.recovery('prepare', self.event())['data']
        self.assertNotIn('Budget 5000', json.dumps(prepared))
        delivered = self.recovery('deliver', prepared['receipt'])['data']
        self.assertEqual(delivered['target']['project_id'], self.identity)
        self.assertEqual(delivered['target']['session_id'], 'session-A')
        self.assertEqual(delivered['target']['generation'], 'generation-1')
        self.assertEqual(delivered['delivery_state'], 'ready')
        self.assertIn('Budget 5000', delivered['context']['text'])
        self.assertIn('Venue unknown', delivered['context']['text'])
        self.assertFalse(delivered['context']['check']['semantic_completion_verified'])
        self.assertEqual(delivered['context']['instruction_authority'], 'none')
        self.assertEqual(self.cli('status')['data'], before)

    def test_reference_change_between_prepare_and_deliver_withholds_old_plan(self):
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        (self.project / 'brief.txt').write_text('New brief: event cancelled.', encoding='utf-8')
        denied = self.recovery('deliver', receipt, ok=False)
        self.assertEqual(denied['code'], 'EVIDENCE_CHANGED')
        self.assertIsNone(denied['data'])
        self.assertNotIn('Compare venues', json.dumps(denied))

    def test_context_is_not_returned_to_new_session_or_revoked_binding_epoch(self):
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        for arguments in ({'session': 'session-B'}, {'generation': 'generation-2'}):
            with self.subTest(arguments=arguments):
                denied = self.recovery('deliver', receipt, ok=False, **arguments)
                self.assertEqual(denied['code'], 'TARGET_MISMATCH')
                self.assertIsNone(denied['data'])
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    def test_new_checkpoint_invalidates_prepared_result(self):
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        self.draft['unresolved'] = ['Budget approval withdrawn']
        self.save(1)
        denied = self.recovery('deliver', receipt, ok=False)
        self.assertEqual(denied['code'], 'STALE_RECOVERY')
        self.assertIsNone(denied['data'])

    def test_wrong_project_identity_and_cwd_are_not_disclosed(self):
        denied = self.recovery('prepare', self.event(), project_id='different-id', ok=False)
        self.assertEqual(denied['code'], 'PROJECT_MISMATCH')
        other = self.project.parent / 'Other'
        other.mkdir()
        denied = self.recovery('prepare', self.event(cwd=str(other)), ok=False)
        self.assertEqual(denied['code'], 'TARGET_MISMATCH')
        self.assertIsNone(denied['data'])
        self.assertFalse((other / '.continuity').exists())

    def test_short_budget_has_no_partial_memory(self):
        denied = self.recovery('prepare', self.event(), budget=100, ok=False)
        self.assertEqual(denied['code'], 'BUDGET_TOO_SMALL')
        self.assertIsNone(denied['data'])
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        denied = self.recovery('deliver', receipt, budget=100, ok=False)
        self.assertEqual(denied['code'], 'BUDGET_TOO_SMALL')

    def test_lifecycle_stop_is_not_an_authorized_checkpoint(self):
        before = self.cli('status')['data']
        denied = self.recovery('prepare', self.event(event='stop'), ok=False)
        self.assertEqual(denied['code'], 'INVALID_EVENT')
        self.assertEqual(self.cli('status')['data'], before)

    def test_old_delivery_and_changed_runtime_are_rejected(self):
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        self.assertIn('issued_at', receipt)
        stale = {**receipt, 'issued_at': (datetime.now(timezone.utc) - timedelta(minutes=2)).isoformat()}
        self.assertEqual(self.recovery('deliver', stale, ok=False)['code'], 'EXPIRED_RECOVERY')
        changed = {**receipt, 'runtime': {**receipt['runtime'], 'source_sha256': '0' * 64}}
        self.assertEqual(self.recovery('deliver', changed, ok=False)['code'], 'RUNTIME_CHANGED')

    def test_boolean_revision_is_not_treated_as_revision_one(self):
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        receipt['revision'] = True
        self.assertEqual(self.recovery('deliver', receipt, ok=False)['code'], 'INVALID_INPUT')

    def test_memory_expiring_after_prepare_is_not_returned_from_a_cache(self):
        expiry = datetime.now(timezone.utc) + timedelta(seconds=2)
        memory = {'format': 'continuity-memory-v1', 'items': [dict(
            id='brief-review', kind='preference', title='Temporary preference',
            body='Use the amber mockup for this trial.', when=['*'], status='active',
            source='Synthetic request', expires_at=expiry.isoformat())]}
        (self.project / 'memory.json').write_text(json.dumps(memory), encoding='utf-8')
        self.draft['evidence'].append({'path': 'memory.json', 'role': 'memory'})
        self.save(1)
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        time.sleep(max(0, (expiry - datetime.now(timezone.utc)).total_seconds()) + .05)
        delivered = self.recovery('deliver', receipt)['data']['context']
        self.assertEqual(delivered['memory']['selected'], [])
        self.assertEqual(delivered['memory']['omitted'][0]['reason'], 'expired')
        self.assertNotIn('amber mockup', json.dumps(delivered))

    def test_duplicate_read_events_do_not_consume_handoffs_or_add_revisions(self):
        handoff = self.cli('handoff', '--recipient', 'reviewer', '--expect-revision', '1')['data']['handoff_id']
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        for _ in range(2):
            context = self.recovery('deliver', receipt)['data']['context']
            self.assertEqual(context['pending_handoffs'][0]['id'], handoff)
        self.assertEqual(self.cli('receipt', '--id', handoff)['data']['state'], 'open')
        self.assertEqual(self.cli('status')['data']['revision'], 1)

    def test_new_bound_project_reports_empty_not_restored_memory(self):
        empty = self.project.parent / 'Fresh'
        empty.mkdir()
        self.project = empty
        self.identity = self.cli('init', '--name', 'Fresh')['data']['project_id']
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        delivered = self.recovery('deliver', receipt)['data']
        self.assertEqual(delivered['delivery_state'], 'empty')
        self.assertEqual(delivered['context']['recovery_state'], 'no_checkpoint')
        self.assertEqual(self.cli('status')['data']['revision'], 0)

    def test_lifecycle_input_accepts_only_the_documented_utf8_encoding(self):
        receipt = self.recovery('prepare', self.event())['data']['receipt']
        for encoding in ('utf-16', 'utf-32'):
            for command, payload in (('prepare', self.event()), ('deliver', receipt)):
                with self.subTest(encoding=encoding, command=command):
                    rejected = self.recovery(command, payload, ok=False, input_encoding=encoding)
                    self.assertEqual(rejected['code'], 'INVALID_INPUT')
                    self.assertIsNone(rejected['data'])


if __name__ == '__main__':
    unittest.main()
