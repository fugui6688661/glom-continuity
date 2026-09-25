// Opt-in production DSH seams; only synthetic models and isolated project/settings files.
// Set CONTINUITY_DSH_PACKAGE to the installed @deepseek-ai/dsh/package.json (0.1.5-rc.1),
// and optionally CONTINUITY_TEST_PYTHON to a Python executable. No dependencies download.
// The caller must impose a network-deny boundary (for example sandbox-exec on macOS).
// This test does not claim that selecting a synthetic adapter is a network sandbox.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, realpathSync, writeFileSync, readFileSync, copyFileSync, symlinkSync, rmSync } from 'node:fs';
import { join, dirname, isAbsolute, resolve } from 'node:path';
import { tmpdir } from 'node:os';

const namespace = 'recaloom-recovery';
const sentinel = 'NATIVE_RACE_SYNTHETIC_CONSTRAINT_5000';
const options = {
  skip: !process.env.CONTINUITY_DSH_PACKAGE && 'Set CONTINUITY_DSH_PACKAGE to opt into installed production DSH',
  timeout: 20000,
};
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};
const tick = () => new Promise(done => setImmediate(done));
let runtime;

function loadRuntime() {
  return runtime ??= (async () => {
    const anchor = resolve(process.env.CONTINUITY_DSH_PACKAGE);
    const metadata = JSON.parse(readFileSync(anchor, 'utf8'));
    assert.equal(metadata.name, '@deepseek-ai/dsh');
    assert.equal(metadata.version, '0.1.5-rc.1', 'These integration seams are pinned to production DSH 0.1.5-rc.1');
    const require = createRequire(anchor);
    const load = name => import(pathToFileURL(require.resolve('@deepseek-ai/' + name)).href);
    const { Context } = await load('cordis');
    const llm = await load('dsh-llm');
    const session = await load('dsh-session');
    const { FileSettingsProvider } = await load('dsh-settings-file');
    // Preserve the venv executable path; resolving its symlink would lose venv selection.
    const python = execFileSync(process.env.CONTINUITY_TEST_PYTHON || 'python3',
      ['-E', '-s', '-B', '-c', 'import sys; print(sys.executable)'], { encoding: 'utf8', timeout: 10000 }).trim();
    assert.ok(isAbsolute(python), 'The native wrapper requires an absolute Python executable');
    return { anchor, load, Context, llm, session, FileSettingsProvider, python };
  })();
}

async function fixture(t) {
  const { anchor, load, Context, llm, session, FileSettingsProvider, python } = await loadRuntime();
  const root = realpathSync(mkdtempSync(join(tmpdir(), 'recaloom-native-races-')));
  const gates = [];
  const allGates = [];
  const pendingCommands = new Set();
  const agents = [];
  let ctx;
  let mounted;
  let disposal;
  let baseline;
  const core = fileURLToPath(new URL('../scripts/continuity.py', import.meta.url));
  const cli = (...args) => JSON.parse(execFileSync(python,
    ['-E', '-s', '-B', core, '--project', root, ...args], { encoding: 'utf8', timeout: 10000 })).data;
  const dispose = () => disposal ??= Promise.resolve(mounted?.dispose());
  t.after(async () => {
    try {
      // Failed assertions/timeouts must not leave a persistence gate or child reader alive.
      for (const gate of allGates) gate.release.resolve();
      await Promise.allSettled([...pendingCommands]);
      try {
        await dispose();
      } finally {
        try { await Promise.all(agents.map(owned => owned.dispose())); }
        finally { await ctx?.root.fiber.dispose(); }
      }
      if (baseline) assert.deepEqual(cli('status'), baseline, 'Recovery/control operations must not mutate project memory');
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
  symlinkSync(dirname(dirname(dirname(anchor))), join(root, 'node_modules'), process.platform === 'win32' ? 'junction' : 'dir');
  // Copy the current checkout on each run, never a reviewer snapshot or a private profile.
  for (const file of ['native-plugin.mjs', 'automatic-recovery.mjs']) {
    copyFileSync(fileURLToPath(new URL('../adapters/harness/' + file, import.meta.url)), join(root, file));
  }
  const plugin = await import(pathToFileURL(join(root, 'native-plugin.mjs')).href);
  const projectId = cli('init', '--name', 'Synthetic native race regression').project_id;
  writeFileSync(join(root, 'draft.json'), JSON.stringify({
    objective: 'Plan a synthetic event', next_action: 'Compare venues', constraints: [sentinel],
    decisions: ['50 people'], unresolved: ['Venue unknown'], evidence: [],
  }));
  cli('checkpoint', '--from-file', join(root, 'draft.json'), '--expect-revision', '0');
  baseline = cli('status');
  ctx = new Context();
  class GatedFileSettingsProvider extends FileSettingsProvider {
    async persist(ns, section) {
      // Only control I/O timing. Production schema, write queue, persistence and commit run unchanged.
      const gate = gates.shift();
      if (gate) {
        gate.started.resolve();
        const outcome = await gate.release.promise;
        if (outcome?.fail) throw new Error('Synthetic persistence failure');
      }
      return super.persist(ns, section);
    }
  }
  for (const [name, config] of [
    ['dsh-llm', {}], ['dsh-session', {}], ['dsh-session-projection', {}],
    ['dsh-system-prompt', { includeHarnessIdentity: false, includeRuntimeContext: false }],
    ['dsh-tools', { mode: 'native' }], ['dsh-agent', {}], ['dsh-commands', {}],
  ]) await ctx.plugin((await load(name)).default, config);
  await ctx.plugin(GatedFileSettingsProvider, { path: join(root, 'settings.json'), watch: false });
  const calls = [];
  class SyntheticAdapter extends llm.LlmAdapter {
    async *stream(request) {
      assert.equal(request.provider, 'synthetic-only');
      calls.push(structuredClone(request.messages));
      yield { type: 'block-start', index: 0, blockType: 'text' };
      yield { type: 'text-delta', index: 0, text: 'Synthetic only.' };
      yield { type: 'block-end', index: 0, block: { type: 'text', text: 'Synthetic only.' } };
      yield { type: 'finish', reason: { kind: 'stop' } };
    }
  }
  ctx.llm.registerAdapter(['synthetic-only'], new SyntheticAdapter());
  ctx.tools.guard(() => 'No tools in synthetic fixture');
  await ctx.plugin((await load('dsh-agent-loop')).default, { agents: [] });
  const outer = { callback: undefined };
  ctx.on('agent/pre-step', async (_payload, next) => {
    const result = await next();
    if (outer.callback) {
      const callback = outer.callback;
      outer.callback = undefined;
      await callback(result);
    }
    return result;
  });
  const config = { python, project: root, projectId, recovery: fileURLToPath(new URL('../scripts/recovery.py', import.meta.url)) };
  mounted = await ctx.plugin(plugin, config);
  const createAgent = async cwd => {
    const owned = await ctx.agents.create({
      sessionId: session.SessionId('native-race-' + agents.length), meta: { cwd },
      agentOptions: { provider: 'synthetic-only', model: 'scripted-v1' },
    });
    agents.push(owned);
    return owned;
  };
  const owned = await createAgent(root);
  const command = (action, signal = new AbortController().signal, agent = owned.agent) => {
    const pending = ctx.commands.execute(agent, '/recaloom ' + action, [], signal).then(execution => {
      assert.ok(execution, 'Native command must remain registered until disposal');
      return execution.result;
    });
    pendingCommands.add(pending);
    pending.then(() => pendingCommands.delete(pending), () => pendingCommands.delete(pending));
    return pending;
  };
  const state = async () => {
    const result = await command('status');
    assert.equal(result.kind, 'success');
    return result.text.split('\n')[0];
  };
  const prompt = async (agent = owned.agent) => {
    agent.followup(llm.createUserMessage({ source: { kind: 'user' }, content: [{ type: 'text', text: 'Continue the synthetic task.' }] }));
    await agent.whenIdle();
  };
  return {
    ctx, root, calls, owned, command, state, prompt, outer, createAgent, dispose,
    hasMemory: () => JSON.stringify(calls).includes(sentinel),
    disk: () => JSON.parse(readFileSync(join(root, 'settings.json'), 'utf8')),
    gate() {
      const gate = { started: deferred(), release: deferred() };
      gates.push(gate);
      allGates.push(gate);
      return gate;
    },
    async remount(extra = {}) {
      await dispose();
      mounted = await ctx.plugin(plugin, { ...config, ...extra });
      disposal = undefined;
    },
  };
}

test('R1: an older resume cannot release a newer cancelled pause safety hold', options, async t => {
  const f = await fixture(t);
  const gate = f.gate();
  const resume = f.command('resume');
  await gate.started.promise;
  const abort = new AbortController();
  const pause = f.command('pause', abort.signal);
  const rejectedPause = assert.rejects(pause, { name: 'AbortError' });
  abort.abort();
  await rejectedPause;
  gate.release.resolve();
  await resume;
  const state = await f.state();
  assert.equal(f.calls.length, 0, 'Control commands must not dispatch a model request');
  await f.prompt();
  const observed = { state, restoredMemory: f.hasMemory() };
  t.diagnostic(JSON.stringify(observed));
  assert.deepEqual(observed, { state: 'Recaloom PAUSED', restoredMemory: false });
});

test('cancelled pause without an overlapping resume remains paused', options, async t => {
  const f = await fixture(t);
  await f.command('resume');
  const abort = new AbortController();
  const pause = f.command('pause', abort.signal);
  const rejectedPause = assert.rejects(pause, { name: 'AbortError' });
  abort.abort();
  await rejectedPause;
  assert.equal(await f.state(), 'Recaloom PAUSED');
  await f.prompt();
  assert.equal(f.hasMemory(), false);
});

test('R2: newer native Settings disable supersedes an already-queued resume', options, async t => {
  const f = await fixture(t);
  const gate = f.gate();
  const firstResume = f.command('resume');
  await gate.started.promise;
  const olderQueuedResume = f.command('resume');
  const newerDisable = f.ctx.settings.update(namespace, { enabled: false });
  gate.release.resolve();
  await newerDisable;
  assert.equal(f.ctx.settings.get(namespace).enabled, false, 'The newer disable must commit');
  assert.equal(f.disk()[namespace].enabled, false, 'The newer disable must be durable');
  await Promise.all([firstResume, olderQueuedResume]);
  const state = await f.state();
  assert.equal(f.calls.length, 0, 'Control commands must not dispatch a model request');
  await f.prompt();
  const observed = { state, persistedEnabled: f.disk()[namespace].enabled, restoredMemory: f.hasMemory() };
  t.diagnostic(JSON.stringify(observed));
  assert.deepEqual(observed, { state: 'Recaloom PAUSED', persistedEnabled: false, restoredMemory: false });
  await f.remount();
  assert.equal(await f.state(), 'Recaloom PAUSED', 'Native Settings disable must survive remount');
});

test('disposal removes the command and prevents later settings publication from restoring memory', options, async t => {
  const f = await fixture(t);
  await f.command('resume');
  await f.dispose();
  assert.equal(f.ctx.commands.list(f.owned.agent).some(item => item.name === 'recaloom'), false);
  f.ctx.settings.publish(f.disk());
  await tick();
  await f.prompt();
  assert.equal(f.hasMemory(), false);
});

test('disposal drains pending activation before removing its settings namespace', options, async t => {
  const f = await fixture(t);
  const gate = f.gate();
  const resume = f.command('resume');
  await gate.started.promise;
  let settled = false;
  const disposal = f.dispose().then(() => { settled = true; });
  await tick();
  assert.equal(settled, false, 'Disposal must wait for the pending activation');
  assert.notEqual(f.ctx.settings.get(namespace), undefined, 'Compensation still needs its registered namespace');
  gate.release.resolve();
  const result = await resume;
  assert.equal(result.kind, 'error');
  assert.match(result.text, /CANCELLED/);
  await disposal;
  assert.equal(f.ctx.settings.get(namespace), undefined);
  assert.equal(f.disk()[namespace].enabled, false);
  await f.remount();
  assert.equal(await f.state(), 'Recaloom PAUSED');
});

test('supervisor removal preparation drains an accepted activation and persists pause', options, async t => {
  const f = await fixture(t);
  const lifecycle = f.ctx.get('recaloomLifecycle');
  assert.equal(typeof lifecycle?.prepareRemoval, 'function', 'The trusted supervisor needs a public removal barrier');
  const gate = f.gate();
  const resume = f.command('resume');
  await gate.started.promise;
  let settled = false;
  const removal = lifecycle.prepareRemoval().then(result => { settled = true; return result; });
  await tick();
  assert.equal(settled, false, 'An accepted write must settle before removal readiness');
  assert.equal((await f.command('resume')).kind, 'error', 'No new activation may enter the closing queue');
  gate.release.resolve();
  assert.equal((await resume).kind, 'error');
  const receipt = await removal;
  assert.equal(receipt.state, 'quiesced');
  assert.equal(receipt.persistedEnabled, false);
  assert.equal(f.disk()[namespace].enabled, false);
  assert.equal(f.calls.length, 0, 'Preparing removal must not call a model');
  await f.prompt();
  assert.equal(f.hasMemory(), false);
  await f.remount();
  assert.equal(await f.state(), 'Recaloom PAUSED');
});

test('failed supervisor pause cannot report safe removal; explicit retry can persist it', options, async t => {
  const f = await fixture(t);
  await f.command('resume');
  const lifecycle = f.ctx.get('recaloomLifecycle');
  const gate = f.gate();
  const removal = lifecycle.prepareRemoval();
  const rejected = assert.rejects(removal, /REMOVAL_PAUSE_NOT_PERSISTED/);
  await gate.started.promise;
  gate.release.resolve({ fail: true });
  await rejected;
  assert.equal(lifecycle.status().readyForRemoval, false);
  assert.equal(f.disk()[namespace].enabled, true, 'A failed write must not be presented as persisted pause');
  assert.equal((await f.command('resume')).kind, 'error');
  await f.prompt();
  assert.equal(f.hasMemory(), false, 'The live reader remains fenced even when saving fails');
  await lifecycle.prepareRemoval();
  assert.equal(lifecycle.status().readyForRemoval, true);
  assert.equal(f.disk()[namespace].enabled, false);
});

test('later Settings writes invalidate removal readiness without reactivating the reader', options, async t => {
  const f = await fixture(t);
  const lifecycle = f.ctx.get('recaloomLifecycle');
  await lifecycle.prepareRemoval();
  assert.equal(lifecycle.status().readyForRemoval, true);
  await f.ctx.settings.update(namespace, { binding: 'changed-by-another-settings-client' });
  assert.equal(lifecycle.status().readyForRemoval, false, 'An earlier receipt is not current authorization to remove');
  await f.prompt();
  assert.equal(f.hasMemory(), false);
  await lifecycle.prepareRemoval();
  assert.equal(lifecycle.status().readyForRemoval, true);
});

test('removal fences new Settings activation before it can reach persistence', options, async t => {
  const f = await fixture(t);
  const lifecycle = f.ctx.get('recaloomLifecycle');
  await lifecycle.prepareRemoval();
  const gate = f.gate();
  const write = f.ctx.settings.update(namespace, { enabled: true });
  const outcome = await Promise.race([
    write.then(() => 'committed', () => 'rejected'),
    gate.started.promise.then(() => 'reached-persistence'),
  ]);
  // Always release a failed implementation so the fixture can clean up.
  gate.release.resolve();
  await Promise.allSettled([write]);
  assert.equal(outcome, 'rejected', 'A quiesced mount must reject reactivation before starting I/O');
  assert.equal(f.disk()[namespace].enabled, false);
  await f.dispose();
  await f.remount();
  assert.equal(await f.state(), 'Recaloom PAUSED');
});

test('disposal releases the namespace even when an overlapping removal save fails', options, async t => {
  const f = await fixture(t);
  await f.command('resume');
  const lifecycle = f.ctx.get('recaloomLifecycle');
  const gate = f.gate();
  const rejected = assert.rejects(lifecycle.prepareRemoval(), /REMOVAL_PAUSE_NOT_PERSISTED/);
  await gate.started.promise;
  const disposal = f.dispose();
  await tick();
  assert.notEqual(f.ctx.settings.get(namespace), undefined, 'Keep storage registered while its save is pending');
  gate.release.resolve({ fail: true });
  await rejected;
  await disposal;
  assert.equal(f.ctx.settings.get(namespace), undefined, 'A rejected save cannot leak a disposed namespace');
  assert.equal(lifecycle.status().readyForRemoval, false, 'Failed persistence is not safe removal');
});

test('successful removal save settles before overlapping disposal releases its namespace', options, async t => {
  const f = await fixture(t);
  await f.command('resume');
  const lifecycle = f.ctx.get('recaloomLifecycle');
  const gate = f.gate();
  const removal = lifecycle.prepareRemoval();
  await gate.started.promise;
  let disposed = false;
  const disposal = f.dispose().then(() => { disposed = true; });
  await tick();
  assert.equal(disposed, false);
  assert.notEqual(f.ctx.settings.get(namespace), undefined);
  gate.release.resolve();
  assert.equal((await removal).persistedEnabled, false);
  await disposal;
  assert.equal(f.ctx.settings.get(namespace), undefined);
  assert.equal(f.disk()[namespace].enabled, false);
  await f.remount();
  assert.equal(await f.state(), 'Recaloom PAUSED');
});

test('removal waits for a Settings activation already inside persistence', options, async t => {
  const f = await fixture(t);
  const lifecycle = f.ctx.get('recaloomLifecycle');
  const gate = f.gate();
  const activation = f.ctx.settings.update(namespace, { enabled: true });
  await gate.started.promise;
  let settled = false;
  const removal = lifecycle.prepareRemoval().then(result => { settled = true; return result; });
  await tick();
  assert.equal(settled, false);
  assert.equal(lifecycle.status().readyForRemoval, false);
  gate.release.resolve();
  await activation;
  await removal;
  assert.equal(lifecycle.status().readyForRemoval, true);
  assert.equal(f.disk()[namespace].enabled, false);
  await f.prompt();
  assert.equal(f.hasMemory(), false);
});

for (const mode of ['enabled', 'binding']) {
  test(`native Settings ${mode} revocation fences an offered recovery before AgentLoop admission`, options, async t => {
    const f = await fixture(t);
    await f.command('resume');
    const original = f.ctx.settings.get(namespace);
    let observedOffer = false;
    f.outer.callback = async result => {
      observedOffer = true;
      assert.equal(result.kind, 'enter');
      assert.ok(JSON.stringify(result.messages).includes(sentinel), 'There must be real recovered memory to revoke');
      await f.ctx.settings.update(namespace, mode === 'enabled' ? { enabled: false } : { binding: 'another-project' });
    };
    await f.prompt();
    assert.equal(observedOffer, true);
    assert.equal(f.calls.length, 0, 'The offered memory must not reach the model');
    assert.equal(await f.state(), 'Recaloom PAUSED');
    await f.ctx.settings.update(namespace, original);
    assert.equal(await f.state(), 'Recaloom ACTIVE');
    await f.prompt();
    assert.equal(f.calls.length, 1);
    assert.equal(f.hasMemory(), true, 'Restoring authorized settings must permit fresh recovery');
  });
}

test('other projects cannot read or change the binding or inherit its saved activation', options, async t => {
  const f = await fixture(t);
  await f.command('resume');
  const before = f.disk();
  const foreignRoot = realpathSync(mkdtempSync(join(f.root, 'different-project-')));
  const foreign = await f.createAgent(foreignRoot);
  for (const action of ['status', 'pause', 'resume']) {
    const result = await f.command(action, new AbortController().signal, foreign.agent);
    assert.equal(result.kind, 'error');
    assert.match(result.text, /UNBOUND_PROJECT/);
    assert.ok(!result.text.includes(f.root), 'Unbound commands must not disclose the bound project path');
  }
  assert.equal(await f.state(), 'Recaloom ACTIVE');
  assert.deepEqual(f.disk(), before);
  assert.equal(f.calls.length, 0);
  await f.prompt(foreign.agent);
  assert.equal(f.calls.length, 1);
  assert.equal(f.hasMemory(), false);
  await f.remount({ projectId: 'changed-project-identity' });
  assert.equal(await f.state(), 'Recaloom PAUSED');
});
