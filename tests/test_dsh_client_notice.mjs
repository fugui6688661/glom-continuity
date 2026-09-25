// Browser companion contract. Public service ports are fakes; Cordis lifecycle is real.
// Real loader/render acceptance is a separate, isolated Web test.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import vm from 'node:vm';

const directory = new URL('../adapters/harness/client-notice/', import.meta.url);
function companion() {
  const manifest = JSON.parse(readFileSync(new URL('package.json', directory), 'utf8'));
  let registration;
  vm.runInNewContext(readFileSync(new URL('client.js', directory), 'utf8'), {
    window: { __ModuleLoader__: { load(value) {
      assert.equal(registration, undefined, 'Only one module registration');
      registration = value;
    } } },
  });
  assert.equal(registration.id, manifest.name);
  return registration.factory(() => { throw Error('No external browser imports expected'); });
}

test('command-first status is delivered to its own session input without sending a prompt', {
  skip: !process.env.CONTINUITY_DSH_PACKAGE,
}, async t => {
  const require = createRequire(process.env.CONTINUITY_DSH_PACKAGE);
  const { Context } = await import(pathToFileURL(require.resolve('@deepseek-ai/cordis')).href);
  const ctx = new Context();
  t.after(() => ctx.fiber.dispose());
  const calls = [];
  const origin = { id: 'A' };
  ctx.provide('commandUi', {});
  ctx.provide('sessions', { scope: id => id === 'A' ? origin : undefined });
  ctx.provide('conversation', { input: { for: scope => ({ notify: (level, text) => {
    calls.push({ scope: scope.id, level, text });
  } }) } });
  await ctx.plugin(companion());
  ctx.emit('command/executed', 'A', 'recaloom', { kind: 'success', text: 'Recaloom PAUSED' });
  assert.deepEqual(calls, [{ scope: 'A', level: 'info', text: 'Recaloom PAUSED' }]);
});

test('notices respect origin, malformed results, unload and remount', {
  skip: !process.env.CONTINUITY_DSH_PACKAGE,
}, async t => {
  const require = createRequire(process.env.CONTINUITY_DSH_PACKAGE);
  const { Context } = await import(pathToFileURL(require.resolve('@deepseek-ai/cordis')).href);
  const ctx = new Context();
  t.after(() => ctx.fiber.dispose());
  const calls = [];
  const scopes = new Map([['A', { id: 'A' }], ['B', { id: 'B' }]]);
  ctx.provide('commandUi', {});
  // `current` is deliberately B: a result from A must not land in B.
  ctx.provide('sessions', { current: 'B', scope: id => scopes.get(id) });
  ctx.provide('conversation', { input: { for: scope => ({ notify: (level, text) => {
    calls.push({ scope: scope.id, level, text });
  } }) } });
  const plugin = companion();
  let mounted = await ctx.plugin(plugin);
  ctx.emit('command/executed', 'A', 'recaloom', { kind: 'error', text: 'UNBOUND_PROJECT' });
  assert.deepEqual(calls, [{ scope: 'A', level: 'error', text: 'UNBOUND_PROJECT' }]);
  for (const result of [null, {}, { kind: 'success' }, { kind: 'success', text: '  ' },
    { kind: 'success', text: 123 }, { kind: 'unknown', text: 'ignore' }])
    ctx.emit('command/executed', 'A', 'recaloom', result);
  ctx.emit('command/executed', 'A', 'other', { kind: 'success', text: 'ignore' });
  scopes.delete('A');
  ctx.emit('command/executed', 'A', 'recaloom', { kind: 'success', text: 'late' });
  assert.equal(calls.length, 1, 'Closed origin must not fall back to current session');
  await mounted.dispose();
  ctx.emit('command/executed', 'B', 'recaloom', { kind: 'success', text: 'unloaded' });
  assert.equal(calls.length, 1, 'Disposed plugin must unregister its event listener');
  mounted = await ctx.plugin(plugin);
  ctx.emit('command/executed', 'B', 'recaloom', { kind: 'success', text: 'Recaloom PAUSED' });
  assert.equal(calls.length, 2, 'Remount must produce exactly one notification');
  assert.deepEqual(calls[1], { scope: 'B', level: 'info', text: 'Recaloom PAUSED' });
  await mounted.dispose();
});

test('client package declares its actual public discovery and dependency seams', async () => {
  const manifest = JSON.parse(readFileSync(new URL('package.json', directory), 'utf8'));
  assert.equal(manifest.private, true);
  assert.equal(manifest.dsh.client.platform, 'web');
  assert.deepEqual(manifest.dsh.client.inject, [
    '@deepseek-ai/dsh-client-ui-commands', '@deepseek-ai/dsh-api-session-controller',
    '@deepseek-ai/dsh-client-ui-conversation',
  ]);
  assert.equal(manifest.exports['./client'], './client.js');
  const host = await import(new URL(manifest.exports['.'], directory));
  assert.equal(host.apply(), undefined, 'Host half must not register duplicate commands');
  assert.deepEqual([...companion().inject], ['commandUi', 'sessions', 'conversation']);
});
