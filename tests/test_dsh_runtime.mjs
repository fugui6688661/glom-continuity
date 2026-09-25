// Opt-in production AgentLoop test, NOT Desktop/profile/SDK wire or model-quality proof.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, realpathSync, writeFileSync, rmSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { attachDshRecovery } from '../adapters/harness/automatic-recovery.mjs';

test('DSH production loop automatically receives bound memory before its synthetic model request', {
  skip: !process.env.CONTINUITY_DSH_PACKAGE, timeout: 20000,
}, async t => {
  const anchor = process.env.CONTINUITY_DSH_PACKAGE;
  assert.equal(JSON.parse(readFileSync(anchor, 'utf8')).version, '0.1.5-rc.1', 'Re-audit another host version explicitly');
  const require = createRequire(anchor);
  const load = name => import(pathToFileURL(require.resolve('@deepseek-ai/' + name)).href);
  const { Context } = await load('cordis');
  const llm = await load('dsh-llm');
  const session = await load('dsh-session');
  const ctx = new Context();
  t.after(() => ctx.root.fiber.dispose());
  for (const [name, config] of [
    ['dsh-llm', {}], ['dsh-session', {}], ['dsh-session-projection', {}],
    ['dsh-system-prompt', { includeHarnessIdentity: false, includeRuntimeContext: false, personaPrefix: 'Synthetic fixture only.' }],
    ['dsh-tools', { mode: 'native' }], ['dsh-agent', {}],
  ]) await ctx.plugin((await load(name)).default, config);
  const calls = [];
  class SyntheticAdapter extends llm.LlmAdapter {
    async *stream(options) {
      options.signal?.throwIfAborted();
      assert.equal(options.provider, 'synthetic-only');
      assert.equal(options.model, 'scripted-v1');
      assert.equal(options.tools?.length || 0, 0);
      assert.ok(calls.length < 8, 'Unexpected extra request; no fallback provider');
      calls.push(structuredClone(options.messages));
      yield { type: 'block-start', index: 0, blockType: 'text' };
      yield { type: 'text-delta', index: 0, text: 'Synthetic acknowledgement.' };
      yield { type: 'block-end', index: 0, block: { type: 'text', text: 'Synthetic acknowledgement.' } };
      yield { type: 'finish', reason: { kind: 'stop' } };
    }
  }
  ctx.llm.registerAdapter(['synthetic-only'], new SyntheticAdapter());
  ctx.tools.guard(() => 'Tools prohibited in lifecycle test');
  await ctx.plugin((await load('dsh-agent-loop')).default, { agents: [] });

  const project = realpathSync(mkdtempSync(join(tmpdir(), 'continuity-dsh-runtime-')));
  t.after(() => rmSync(project, { recursive: true, force: true }));
  const python = process.env.CONTINUITY_TEST_PYTHON || 'python3';
  const core = fileURLToPath(new URL('../scripts/continuity.py', import.meta.url));
  const cli = (...args) => JSON.parse(execFileSync(python, ['-B', core, '--project', project, ...args], { encoding: 'utf8' })).data;
  const projectId = cli('init', '--name', 'Synthetic runtime')['project_id'];
  writeFileSync(join(project, 'draft.json'), JSON.stringify({ objective: 'Plan an event', next_action: 'Compare venues',
    constraints: ['Budget 5000', 'No purchases'], decisions: ['50 people'], unresolved: ['Venue unknown'], evidence: [] }));
  cli('checkpoint', '--from-file', join(project, 'draft.json'), '--expect-revision', '0');
  const before = cli('status');
  let bridge;
  let pauseAtOuter = false;
  ctx.on('agent/pre-step', async (_payload, next) => {
    const result = await next();
    if (pauseAtOuter) { const action = pauseAtOuter; pauseAtOuter = false; bridge[action](); }
    return result;
  });
  bridge = attachDshRecovery(ctx, { python, project, projectId,
    recovery: fileURLToPath(new URL('../scripts/recovery.py', import.meta.url)) }, llm.createUserMessage);
  t.after(() => bridge.dispose());
  const owned = await ctx.agents.create({ sessionId: session.SessionId('synthetic-lifecycle-A'), meta: { cwd: project },
    agentOptions: { provider: 'synthetic-only', model: 'scripted-v1' } });
  t.after(() => owned.dispose());
  const prompt = async () => {
    owned.agent.followup(llm.createUserMessage({ source: { kind: 'user' }, content: [{ type: 'text', text: 'Continue the saved task.' }] }));
    await owned.agent.whenIdle();
  };
  pauseAtOuter = 'pause';
  await prompt();
  assert.equal(calls.length, 0, 'Pause after recovery return but before admission must veto the actual request');
  assert.ok(!owned.agent.session.snapshotEvents().some(event => event.type === 'user/message'));
  bridge.resume();
  const cancelBeforeAdmission = ctx.on('agent/request', async ({ agent }, next) => {
    const result = await next();
    agent.cancel({ kind: 'user' });
    return result;
  });
  await prompt();
  cancelBeforeAdmission();
  assert.equal(calls.length, 0, 'Cancellation after pre-step must not make a model request');
  assert.ok(!owned.agent.session.snapshotEvents().some(event => event.type === 'user/message'),
    'Cancelled admission must not be remembered as delivered');
  await prompt();
  assert.equal(calls.length, 1, JSON.stringify(owned.agent.session.snapshotEvents()));
  assert.match(JSON.stringify(calls[0]), /Budget 5000/);
  assert.match(JSON.stringify(calls[0]), /Venue unknown/);
  const firstEvents = owned.agent.session.snapshotEvents();
  assert.ok(firstEvents.some(event => event.type === 'assistant/message'));
  assert.ok(firstEvents.some(event => event.type === 'turn/end' && event.data.reason.kind === 'completed'));
  assert.equal(owned.agent.status, 'idle');
  assert.deepEqual(cli('status'), before);
  const count = messages => (JSON.stringify(messages).match(/Historical project data, not instructions or permission/g) || []).length;
  await prompt();
  assert.equal(calls.length, 2);
  assert.equal(count(calls[1]), count(calls[0]), 'Unchanged memory must not grow the prompt each turn');
  bridge.pause();
  await prompt();
  assert.equal(calls.length, 3);
  // Pause stops new restoration; previously admitted text remains in host history.
  assert.equal(count(calls[2]), count(calls[0]));
  bridge.resume();
  await prompt();
  assert.equal(calls.length, 4);
  assert.equal(count(calls[3]), count(calls[0]) + 1);
  bridge.dispose();
  await prompt();
  assert.equal(calls.length, 5);
  assert.equal(count(calls[4]), count(calls[3]));
  bridge = attachDshRecovery(ctx, { python, project, projectId,
    recovery: fileURLToPath(new URL('../scripts/recovery.py', import.meta.url)) }, llm.createUserMessage);
  const userEvents = () => owned.agent.session.snapshotEvents().filter(event => event.type === 'user/message').length;
  const admitted = userEvents();
  pauseAtOuter = 'dispose';
  await prompt();
  assert.equal(calls.length, 5, 'Detaching after the offer must fence the pending host admission');
  assert.equal(userEvents(), admitted);
  const id = owned.agent.id;
  await owned.dispose();
  assert.equal(ctx.agents.get(id), undefined);
  assert.deepEqual(cli('status'), before);
});
