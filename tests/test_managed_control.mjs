// Real private socket; fake public host services. Not full SDK runtime proof.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, openSync, closeSync, rmSync } from 'node:fs';
import { join } from 'node:path';
import net from 'node:net';
import { apply } from '../adapters/harness/managed-host.mjs';

test('an invalidated removal receipt permits a fresh explicit stop attempt', async () => {
  const root = mkdtempSync('/tmp/recaloom-control-');
  const fd = openSync(join(root, 'lock'), 'wx', 0o600);
  const previous = [process.env.RECALOOM_MANAGED_RUN_ID, process.env.RECALOOM_MANAGED_LOCK_FD];
  process.env.RECALOOM_MANAGED_RUN_ID = 'synthetic-run';
  process.env.RECALOOM_MANAGED_LOCK_FD = String(fd);
  let onReady;
  let calls = 0;
  let exits = 0;
  let ready = false;
  const lifecycle = {
    async prepareRemoval() { ++calls; ready = calls > 1; },
    status: () => ({ state: ready ? 'quiesced' : 'quiescing', readyForRemoval: ready }),
  };
  const ctx = {
    appReady: { onReady(fn) { onReady = fn; } }, appExit() { ++exits; },
    webServer: { port: 12345 }, settings: { get: () => ({ enabled: false }) },
    clientModules: { graph: () => ({ entries: [] }) }, get: () => lifecycle,
  };
  let dispose;
  try {
    const path = join(root, 'control.sock');
    dispose = await apply(ctx, { homeId: 'synthetic-home', socket: path, attached: true });
    onReady();
    const stop = () => new Promise((resolve, reject) => {
      const client = net.createConnection(path);
      let buffer = '';
      client.setTimeout(2000, () => client.destroy(new Error('test socket timeout')));
      client.on('error', reject);
      client.on('connect', () => client.write(JSON.stringify({ home_id: 'synthetic-home', run_id: 'synthetic-run', action: 'stop' }) + '\n'));
      client.on('data', bytes => { buffer += bytes; });
      client.on('end', () => resolve(JSON.parse(buffer)));
    });
    assert.equal((await stop()).code, 'PAUSE_NOT_SAVED');
    assert.equal(exits, 0);
    assert.equal((await stop()).ok, true, 'Second request must prepare again instead of reusing an invalid receipt');
    assert.equal(calls, 2);
    assert.equal(exits, 1);
    // Host exit can be deferred: an old success must not certify a later,
    // changed Settings revision while this control server is still alive.
    ready = false;
    assert.equal((await stop()).code, 'PAUSE_NOT_SAVED');
    assert.equal(exits, 1);
    assert.equal((await stop()).ok, true);
    assert.equal(calls, 3);
    assert.equal(exits, 2);
  } finally {
    await dispose?.();
    closeSync(fd);
    ['RECALOOM_MANAGED_RUN_ID', 'RECALOOM_MANAGED_LOCK_FD'].forEach((key, index) => {
      if (previous[index] === undefined) delete process.env[key]; else process.env[key] = previous[index];
    });
    rmSync(root, { recursive: true, force: true });
  }
});

test('a pause invalidated after acknowledgement does not authorize deferred host exit', async t => {
  const root = mkdtempSync('/tmp/recaloom-control-');
  const fd = openSync(join(root, 'lock'), 'wx', 0o600);
  const previous = [process.env.RECALOOM_MANAGED_RUN_ID, process.env.RECALOOM_MANAGED_LOCK_FD];
  process.env.RECALOOM_MANAGED_RUN_ID = 'deferred-run';
  process.env.RECALOOM_MANAGED_LOCK_FD = String(fd);
  let onReady;
  let ready = false;
  let exits = 0;
  let deferred;
  const lifecycle = {
    async prepareRemoval() { ready = true; },
    status: () => ({ state: ready ? 'quiesced' : 'quiescing', readyForRemoval: ready }),
  };
  const ctx = {
    appReady: { onReady(fn) { onReady = fn; } }, appExit() { ++exits; },
    webServer: { port: 12345 }, settings: { get: () => ({ enabled: false }) },
    clientModules: { graph: () => ({ entries: [] }) }, get: () => lifecycle,
  };
  // Defer only the transport completion of this synthetic host's first stop.
  // The request and acknowledgement still use the real private Unix socket.
  const originalEnd = net.Socket.prototype.end;
  let hold = true;
  const transport = t.mock.method(net.Socket.prototype, 'end', function (...args) {
    if (hold && typeof args[0] === 'string' && args[0].includes('"home_id":"deferred-home"') &&
        args[0].includes('"state":"stopping"') && typeof args.at(-1) === 'function') {
      hold = false;
      deferred = args.pop();
    }
    return originalEnd.apply(this, args);
  });
  let dispose;
  try {
    const path = join(root, 'control.sock');
    dispose = await apply(ctx, { homeId: 'deferred-home', socket: path, attached: true });
    onReady();
    const stop = () => new Promise((resolve, reject) => {
      const client = net.createConnection(path);
      let buffer = '';
      client.setTimeout(2000, () => client.destroy(new Error('test socket timeout')));
      client.on('error', reject);
      client.on('connect', () => client.write(JSON.stringify({ home_id: 'deferred-home', run_id: 'deferred-run', action: 'stop' }) + '\n'));
      client.on('data', bytes => { buffer += bytes; });
      client.on('end', () => resolve(JSON.parse(buffer)));
    });
    assert.equal((await stop()).ok, true);
    assert.equal(typeof deferred, 'function', 'The exit transport callback must actually be delayed');
    assert.equal(exits, 0);
    ready = false; // A later public Settings revision invalidates the pause receipt.
    deferred();
    assert.equal(exits, 0, 'A stale acknowledgement must not exit the host');
    assert.equal((await stop()).ok, true, 'An explicit retry must prepare and persist a fresh pause');
    assert.equal(exits, 1);
  } finally {
    transport.mock.restore();
    await dispose?.();
    closeSync(fd);
    ['RECALOOM_MANAGED_RUN_ID', 'RECALOOM_MANAGED_LOCK_FD'].forEach((key, index) => {
      if (previous[index] === undefined) delete process.env[key]; else process.env[key] = previous[index];
    });
    rmSync(root, { recursive: true, force: true });
  }
});
