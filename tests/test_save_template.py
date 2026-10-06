"""Draft continuity through the public CLI; no database internals."""
import json
import subprocess
import unittest

import test_authorized_save as base


class SaveTemplate(unittest.TestCase):
    setUp = base.AuthorizedSave.setUp
    command = base.AuthorizedSave.command
    call = base.AuthorizedSave.call
    write = base.AuthorizedSave.write
    tree = base.AuthorizedSave.tree
    enable = base.AuthorizedSave.enable
    prepare = base.AuthorizedSave.prepare
    commit = base.AuthorizedSave.commit

    def template(self, revision='1', **kwargs):
        return self.call('save', 'template', '--expect-project-id', self.identity,
                         '--expect-revision', revision, **kwargs)

    def test_reviewed_base_becomes_editable_draft_without_saving_or_enabling(self):
        before = self.tree()
        result = self.template()
        self.assertEqual(result['draft'], self.draft)
        self.assertEqual((result['project_id'], result['base_revision']), (self.identity, 1))
        self.assertTrue(result['read_only'])
        self.assertEqual(result['instruction_authority'], 'none')
        self.assertFalse(result['semantic_completion_verified'])
        self.assertEqual(result['check']['state'], 'references_current')
        self.assertEqual(self.tree(), before)
        self.assertIsNone(self.call('save-policy', 'status', '--expect-project-id', self.identity,
                                    '--session-id', 'session-a')['policy'])
        self.draft = result['draft']
        self.draft['next_action'] = 'Review the actual work, not this baseline'
        self.write()
        generation = self.enable()['generation']
        candidate = self.prepare(generation, event='review-node-1')['candidate_id']
        self.assertEqual(self.commit(generation, candidate)['revision'], 2)
        self.assertIn('Review the actual work, not this baseline', self.call('resume')['text'])

    def test_returned_work_template_preserves_inherited_inputs(self):
        handoff = self.call('handoff', '--recipient', 'worker', '--expect-revision', '1')['handoff_id']
        self.call('accept', '--id', handoff, '--recipient', 'worker')
        (self.root / 'result.md').write_text('Reviewed result with an unknown reviewer', encoding='utf-8')
        self.draft['evidence'] = [{'path': 'result.md', 'role': 'artifact'}]
        self.write()
        self.call('return-work', '--id', handoff, '--recipient', 'worker',
                  '--from-file', str(self.root / 'draft.json'), '--expect-revision', '1')
        before = self.tree()
        result = self.template('2')
        self.assertEqual(result['draft']['evidence'], [
            {'path': 'result.md', 'role': 'artifact'}, {'path': 'brief.txt', 'role': 'input'}])
        self.assertEqual(result['draft']['unresolved'], ['Reviewer unknown'])
        self.assertEqual(self.tree(), before)
        self.draft = result['draft']
        self.draft['next_action'] = 'Confirm reviewer after handoff'
        self.write()
        generation = self.enable()['generation']
        candidate = self.prepare(generation, event='after-handoff', revision='2')['candidate_id']
        self.assertEqual(self.commit(generation, candidate)['revision'], 3)
        (self.root / 'brief.txt').write_text('Changed original input', encoding='utf-8')
        self.assertEqual(self.call('resume')['check']['state'], 'needs_review')

    def test_conflicting_inherited_roles_are_not_silently_chosen(self):
        handoff = self.call('handoff', '--recipient', 'worker', '--expect-revision', '1')['handoff_id']
        self.call('accept', '--id', handoff, '--recipient', 'worker')
        self.draft['evidence'] = [{'path': 'brief.txt', 'role': 'artifact'}]
        self.write()
        self.call('return-work', '--id', handoff, '--recipient', 'worker',
                  '--from-file', str(self.root / 'draft.json'), '--expect-revision', '1')
        before = self.tree()
        self.template('2', code='SAVE_REVIEW_REQUIRED')
        self.assertEqual(self.tree(), before)

    def test_draft_budget_refuses_instead_of_dropping_constraints(self):
        args = ['save', 'template', '--expect-project-id', self.identity, '--expect-revision', '1']
        before = self.tree()
        self.call(*args, '--max-chars', '100', code='BUDGET_TOO_SMALL')
        result = subprocess.run(self.command(*args, '--max-chars', '4000'), capture_output=True,
                                text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertLessEqual(len(result.stdout), 4000)
        self.assertEqual(json.loads(result.stdout)['data']['draft']['constraints'], ['No publication'])
        self.assertEqual(self.tree(), before)

    def test_wrong_scope_stale_revision_and_changed_inputs_return_no_draft(self):
        before = self.tree()
        self.call('save', 'template', '--expect-project-id', 'another-project',
                  '--expect-revision', '1', code='PROJECT_MISMATCH')
        self.template('0', code='REVISION_CONFLICT')
        self.assertEqual(self.tree(), before)
        (self.root / 'brief.txt').write_text('New requirements must be reviewed', encoding='utf-8')
        before = self.tree()
        self.assertIsNone(self.template(code='SAVE_REVIEW_REQUIRED'))
        self.assertEqual(self.tree(), before)

    def test_inherited_reference_union_over_limit_requires_review(self):
        self.draft['evidence'] = []
        for index in range(64):
            name = f'input-{index}.txt'
            (self.root / name).write_text('Selected input', encoding='utf-8')
            self.draft['evidence'].append({'path': name, 'role': 'input'})
        self.write()
        self.call('checkpoint', '--from-file', str(self.root / 'draft.json'), '--expect-revision', '1')
        handoff = self.call('handoff', '--recipient', 'worker', '--expect-revision', '2')['handoff_id']
        self.call('accept', '--id', handoff, '--recipient', 'worker')
        (self.root / 'result.md').write_text('Additional output', encoding='utf-8')
        self.draft['evidence'] = [{'path': 'result.md', 'role': 'artifact'}]
        self.write()
        self.call('return-work', '--id', handoff, '--recipient', 'worker',
                  '--from-file', str(self.root / 'draft.json'), '--expect-revision', '2')
        before = self.tree()
        self.template('3', code='SAVE_REVIEW_REQUIRED')
        self.assertEqual(self.tree(), before)

    def test_duplicate_memory_ids_across_return_chain_require_review(self):
        for name in ('a.json', 'b.json'):
            memory = {'format': 'continuity-memory-v1', 'items': [{
                'id': 'same-id', 'kind': 'preference', 'title': 'Selected style',
                'body': 'Use concise explanations', 'when': ['*'], 'status': 'active',
                'source': 'Explicit synthetic requirement', 'expires_at': None}]}
            (self.root / name).write_text(json.dumps(memory), encoding='utf-8')
        self.draft['evidence'] = [{'path': 'a.json', 'role': 'memory'}]
        self.write()
        self.call('checkpoint', '--from-file', str(self.root / 'draft.json'), '--expect-revision', '1')
        (self.root / 'result.md').write_text('Reviewed output', encoding='utf-8')
        for revision, evidence in ((2, [{'path': 'b.json', 'role': 'memory'}, {'path': 'result.md', 'role': 'artifact'}]),
                                   (3, [{'path': 'result.md', 'role': 'artifact'}])):
            handoff = self.call('handoff', '--recipient', 'worker', '--expect-revision', str(revision))['handoff_id']
            self.call('accept', '--id', handoff, '--recipient', 'worker')
            self.draft['evidence'] = evidence
            self.write()
            self.call('return-work', '--id', handoff, '--recipient', 'worker',
                      '--from-file', str(self.root / 'draft.json'), '--expect-revision', str(revision))
        before = self.tree()
        self.template('4', code='MEMORY_CONFLICT')
        self.assertEqual(self.tree(), before)

    def test_combined_draft_byte_limit_is_separate_from_response_budget(self):
        folder = self.root / ('a' * 200) / ('b' * 200)
        folder.mkdir(parents=True)
        self.draft['evidence'] = []
        for index in range(12):
            path = folder / (str(index) + 'c' * 90 + '.txt')
            path.write_text('Input', encoding='utf-8')
            self.draft['evidence'].append({'path': path.relative_to(self.root).as_posix(), 'role': 'input'})
        self.write()
        self.call('checkpoint', '--from-file', str(self.root / 'draft.json'), '--expect-revision', '1')
        handoff = self.call('handoff', '--recipient', 'worker', '--expect-revision', '2')['handoff_id']
        self.call('accept', '--id', handoff, '--recipient', 'worker')
        (self.root / 'result.md').write_text('Reviewed output', encoding='utf-8')
        self.draft['evidence'] = [{'path': 'result.md', 'role': 'artifact'}]
        self.draft['decisions'] = ['x' * 7900] * 15
        self.draft['next_action'] = 'y' * 7900
        self.write()
        self.call('return-work', '--id', handoff, '--recipient', 'worker',
                  '--from-file', str(self.root / 'draft.json'), '--expect-revision', '2')
        before = self.tree()
        self.call('save', 'template', '--expect-project-id', self.identity, '--expect-revision', '3',
                  '--max-chars', '500000', code='SAVE_REVIEW_REQUIRED')
        self.assertEqual(self.tree(), before)


if __name__ == '__main__':
    unittest.main()
