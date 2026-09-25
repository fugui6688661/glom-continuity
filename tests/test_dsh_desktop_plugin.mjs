// Actual DSH command/settings/loop seams; synthetic provider, isolated files only.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, realpathSync, writeFileSync, rmSync, readFileSync, copyFileSync, symlinkSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';

test('native commands bind explicitly, persist pause across remount, and never call a model', {
  skip: !process.env.CONTINUITY_DSH_PACKAGE, timeout: 20000,
}, async t => {
  const anchor = process.env.CONTINUITY_DSH_PACKAGE;
  assert.equal(JSON.parse(readFileSync(anchor, 'utf8')).version, '0.1.5-rc.1');
  const require = createRequire(anchor);
  const load = name => import(pathToFileURL(require.resolve('@deepseek-ai/' + name)).href);
  const { Context } = await load('cordis');
  const llm = await load('dsh-llm');
  const session = await load('dsh-session');
  const root = realpathSync(mkdtempSync(join(tmpdir(), 'recaloom-native-command-')));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  symlinkSync(dirname(dirname(dirname(anchor))), join(root, 'node_modules'), 'dir');
  for (const file of ['native-plugin.mjs', 'automatic-recovery.mjs'])
    copyFileSync(fileURLToPath(new URL('../adapters/harness/' + file, import.meta.url)), join(root, file));
  const plugin = await import(pathToFileURL(join(root, 'native-plugin.mjs')).href);
  const python = process.env.CONTINUITY_TEST_PYTHON || 'python3';
  const core = fileURLToPath(new URL('../scripts/continuity.py', import.meta.url));
  const cli = (...args) => JSON.parse(execFileSync(python, ['-B', core, '--project', root, ...args], { encoding: 'utf8' })).data;
  const projectId = cli('init', '--name', 'Synthetic native binding').project_id;
  writeFileSync(join(root, 'draft.json'), JSON.stringify({ objective: 'Plan an event', next_action: 'Compare venues',
    constraints: ['Budget 5000'], decisions: ['50 people'], unresolved: ['Venue unknown'], evidence: [] }));
  cli('checkpoint', '--from-file', join(root, 'draft.json'), '--expect-revision', '0');
  const baseline = cli('status');
  const ctx = new Context();
  t.after(() => ctx.root.fiber.dispose());
  for (const [name, config] of [
    ['dsh-llm', {}], ['dsh-session', {}], ['dsh-session-projection', {}],
    ['dsh-system-prompt', { includeHarnessIdentity: false, includeRuntimeContext: false }],
    ['dsh-tools', { mode: 'native' }], ['dsh-agent', {}], ['dsh-commands', {}],
    ['dsh-settings-file', { path: join(root, 'settings.json'), watch: false }],
  ]) await ctx.plugin((await load(name)).default, config);
  const calls = [];
  class SyntheticAdapter extends llm.LlmAdapter {
    async *stream(options) {
      assert.equal(options.provider, 'synthetic-only');
      calls.push(structuredClone(options.messages));
      yield { type: 'block-start', index: 0, blockType: 'text' };
      yield { type: 'text-delta', index: 0, text: 'Synthetic only.' };
      yield { type: 'block-end', index: 0, block: { type: 'text', text: 'Synthetic only.' } };
      yield { type: 'finish', reason: { kind: 'stop' } };
    }
  }
  ctx.llm.registerAdapter(['synthetic-only'], new SyntheticAdapter());
  ctx.tools.guard(() => 'No tools in fixture');
  await ctx.plugin((await load('dsh-agent-loop')).default, { agents: [] });
  const config = { python, project: root, projectId, recovery: fileURLToPath(new URL('../scripts/recovery.py', import.meta.url)) };
  let mounted = await ctx.plugin(plugin, config);
  const owned = await ctx.agents.create({ sessionId: session.SessionId('native-A'), meta: { cwd: root },
    agentOptions: { provider: 'synthetic-only', model: 'scripted-v1' } });
  t.after(() => owned.dispose());
  const command = async text => (await ctx.commands.execute(owned.agent, text, [], new AbortController().signal)).result;
  assert.ok(ctx.commands.list(owned.agent).some(item => item.name === 'recaloom'));
  assert.match((await command('/recaloom')).text, /PAUSED/);
  assert.equal((await command('/recaloom resume')).kind, 'success');
  assert.match((await command('/recaloom status')).text, /ACTIVE/);
  assert.equal(calls.length, 0);
  const prompt = async () => {
    owned.agent.followup(llm.createUserMessage({ source: { kind: 'user' }, content: [{ type: 'text', text: 'Continue.' }] }));
    await owned.agent.whenIdle();
  };
  await prompt();
  assert.match(JSON.stringify(calls[0]), /Budget 5000/);
  assert.equal((await command('/recaloom pause')).kind, 'success');
  await mounted.dispose();
  assert.ok(!ctx.commands.list(owned.agent).some(item => item.name === 'recaloom'));
  mounted = await ctx.plugin(plugin, config);
  assert.match((await command('/recaloom status')).text, /PAUSED/);
  const cancelResume = new AbortController();
  const unwatchCommit = ctx.on('settings/updated', () => cancelResume.abort());
  await assert.rejects(ctx.commands.execute(owned.agent, '/recaloom resume', [], cancelResume.signal), { name: 'AbortError' });
  unwatchCommit();
  await mounted.dispose();
  mounted = await ctx.plugin(plugin, config);
  assert.match((await command('/recaloom status')).text, /PAUSED/, 'Cancelled activation must not silently enable after reload');
  const foreign = await ctx.agents.create({ sessionId: session.SessionId('native-other'), meta: { cwd: dirname(root) },
    agentOptions: { provider: 'synthetic-only', model: 'scripted-v1' } });
  t.after(() => foreign.dispose());
  const rejected = (await ctx.commands.execute(foreign.agent, '/recaloom resume', [], new AbortController().signal)).result;
  assert.equal(rejected.kind, 'error');
  assert.match(rejected.text, /UNBOUND_PROJECT/);
  assert.match((await command('/recaloom status')).text, /PAUSED/);
  await command('/recaloom resume');
  await mounted.dispose();
  mounted = await ctx.plugin(plugin, { ...config, projectId: 'different-project-id' });
  assert.match((await command('/recaloom status')).text, /PAUSED/, 'Stored permission cannot cross project identity');
  await command('/recaloom resume');
  await prompt();
  assert.equal(calls.length, 1, 'Wrong configured project ID must block before dispatch');
  assert.match((await command('/recaloom status')).text, /PROJECT_MISMATCH/);
  const ends = owned.agent.session.snapshotEvents().filter(event => event.type === 'turn/end');
  assert.equal(ends.at(-1).data.reason.kind, 'error', 'Official Chat needs a visible terminal error, not silent blocked');
  assert.match(JSON.stringify(ends.at(-1).data.reason), /Recaloom.*PROJECT_MISMATCH/);
  assert.doesNotMatch(JSON.stringify(ends.at(-1).data.reason), /Budget 5000/);
  assert.deepEqual(cli('status'), baseline, 'Control operations do not alter project memory');
  assert.equal(calls.length, 1, 'Control commands never dispatch to the provider');
  assert.equal((await command('/recaloom arbitrary-command')).kind, 'error');
  await mounted.dispose();
  assert.ok(!ctx.commands.list(owned.agent).some(item => item.name === 'recaloom'));
});
