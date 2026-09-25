// Host-interface contract tests. The DSH-shaped boundary below is not a live SDK.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, realpathSync, writeFileSync, rmSync, existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { attachDshRecovery } from '../adapters/harness/automatic-recovery.mjs';

const python = process.env.CONTINUITY_TEST_PYTHON || 'python3';
const core = fileURLToPath(new URL('../scripts/continuity.py', import.meta.url));
const recovery = fileURLToPath(new URL('../scripts/recovery.py', import.meta.url));

function fixture(t, overrides = {}) {
  const project = realpathSync(mkdtempSync(join(tmpdir(), 'continuity-dsh-contract-')));
  t.after(() => rmSync(project, { recursive: true, force: true }));
  const cli = (...args) => JSON.parse(execFileSync(python, ['-B', core, '--project', project, ...args], { encoding: 'utf8' })).data;
  const projectId = cli('init', '--name', 'Synthetic event')['project_id'];
  writeFileSync(join(project, 'brief.txt'), 'Synthetic; no purchases.');
  writeFileSync(join(project, 'draft.json'), JSON.stringify({ objective: 'Plan an event', next_action: 'Compare venues',
    constraints: ['Budget 5000', 'No purchases'], decisions: ['50 people'], unresolved: ['Venue unknown'],
    evidence: [{ path: 'brief.txt', role: 'input' }] }));
  cli('checkpoint', '--from-file', join(project, 'draft.json'), '--expect-revision', '0');
  const listeners = new Map();
  const ctx = { on(event, fn) { listeners.set(event, fn); return () => listeners.delete(event); } };
  const bridge = attachDshRecovery(ctx, { python, recovery, project, projectId, ...overrides }, message => ({ ...message, id: randomUUID() }));
  t.after(() => bridge.dispose());
  const agent = { session: { id: 'session-A', header: { cwd: project } } };
  const request = { agent, messages: [{ source: { kind: 'user' }, content: [{ type: 'text', text: 'Continue' }] }],
    turn: 1, step: 1, signal: new AbortController().signal };
  const dispatch = (changes = {}, next) => {
    const payload = { ...request, ...changes };
    const downstream = next || (() => Promise.resolve({ kind: 'enter', messages: payload.messages }));
    return listeners.get('agent/pre-step')?.(payload, downstream) ?? downstream();
  };
  return { project, projectId, cli, agent, request, bridge, dispatch, listeners };
}

test('before-step returns complete historical project context without saving or claiming authority', async t => {
  const f = fixture(t);
  const before = f.cli('status');
  const result = await f.dispatch();
  assert.equal(result.kind, 'enter');
  assert.equal(result.messages.length, 2);
  const restored = result.messages[1];
  assert.equal(restored.source.kind, 'plugin');
  assert.equal(restored.source.plugin, 'recaloom-recovery');
  assert.match(restored.content[0].text, /Budget 5000/);
  assert.match(restored.content[0].text, /Venue unknown/);
  assert.match(restored.content[0].text, /not instructions or permission/);
  assert.deepEqual(f.cli('status'), before);
});

test('pause prevents future reads; resume revalidates; detach leaves original messages intact', async t => {
  const f = fixture(t);
  f.bridge.pause();
  writeFileSync(join(f.project, 'brief.txt'), 'Changed while paused');
  assert.equal((await f.dispatch()).messages.length, 1);
  assert.equal(f.bridge.status().state, 'paused');
  f.bridge.resume();
  assert.equal((await f.dispatch()).kind, 'reject');
  assert.equal(f.bridge.status().lastCode, 'EVIDENCE_CHANGED');
  f.bridge.dispose();
  assert.equal((await f.dispatch()).messages.length, 1);
  assert.equal(f.bridge.status().state, 'disposed');
  assert.throws(() => f.bridge.resume(), /disposed/i);
});

test('pausing an in-flight recovery withholds its late result', async t => {
  const f = fixture(t);
  const pending = f.dispatch();
  await new Promise(resolve => setImmediate(resolve));
  f.bridge.pause();
  assert.equal((await pending).kind, 'reject');
  assert.equal(f.bridge.status().state, 'paused');
});

test('pause cancels an unresponsive recovery process promptly', async t => {
  const f = fixture(t);
  f.bridge.dispose();
  const slow = join(f.project, 'slow-transport.py');
  writeFileSync(slow, 'import time\ntime.sleep(3)\n');
  const bridge = attachDshRecovery({ on(event, fn) { f.listeners.set(event, fn); return () => f.listeners.delete(event); } },
    { python, recovery: slow, project: f.project, projectId: f.projectId }, message => message);
  t.after(() => bridge.dispose());
  const pending = f.dispatch();
  await new Promise(resolve => setImmediate(resolve));
  const start = performance.now();
  bridge.pause();
  assert.equal((await pending).kind, 'reject');
  assert.ok(performance.now() - start < 1500, 'pause must abort, not wait for the transport timeout');
});

test('a session replaced during recovery never receives the former session context', async t => {
  const f = fixture(t);
  const pending = f.dispatch();
  await new Promise(resolve => setImmediate(resolve));
  f.agent.session = { id: 'session-B', header: { cwd: f.project } };
  assert.equal((await pending).kind, 'reject');
  assert.equal(f.bridge.status().lastCode, 'TARGET_CHANGED');
});

test('foreign projects are not read and a wrong bound identity blocks recovery', async t => {
  const f = fixture(t);
  const other = realpathSync(mkdtempSync(join(tmpdir(), 'continuity-unbound-')));
  t.after(() => rmSync(other, { recursive: true, force: true }));
  assert.equal((await f.dispatch({ agent: { session: { id: 'other', header: { cwd: other } } } })).messages.length, 1);
  assert.equal(f.bridge.status().lastCode, 'UNBOUND_PROJECT');
  const wrong = fixture(t, { projectId: 'incorrect-project-id' });
  assert.equal((await wrong.dispatch()).kind, 'reject');
  assert.equal(wrong.bridge.status().lastCode, 'PROJECT_MISMATCH');
});

test('cancel and detach during reading cannot deliver late context', async t => {
  for (const action of ['cancel', 'dispose']) {
    const f = fixture(t);
    const cancellation = new AbortController();
    const pending = f.dispatch({ signal: cancellation.signal });
    await new Promise(resolve => setImmediate(resolve));
    if (action === 'cancel') cancellation.abort();
    else f.bridge.dispose();
    assert.equal((await pending).kind, 'reject');
  }
});

test('changed evidence blocks a bound step; no message or downstream rejection cannot start a new step', async t => {
  const f = fixture(t);
  writeFileSync(join(f.project, 'brief.txt'), 'Approval revoked');
  assert.equal((await f.dispatch()).kind, 'reject');
  assert.equal(f.bridge.status().lastCode, 'EVIDENCE_CHANGED');
  assert.equal((await f.dispatch({ messages: [] })).messages.length, 0);
  assert.deepEqual(await f.dispatch({}, async () => ({ kind: 'reject' })), { kind: 'reject' });
});

test('a crashed transport cannot report OK even when stdout contains a success envelope', async t => {
  const f = fixture(t);
  f.bridge.dispose();
  const failed = join(f.project, 'failed-transport.py');
  writeFileSync(failed, 'import sys\nprint(\'{"ok":true,"code":"OK","data":{}}\')\nsys.exit(1)\n');
  const bridge = attachDshRecovery({ on(event, fn) { f.listeners.set(event, fn); return () => f.listeners.delete(event); } },
    { python, recovery: failed, project: f.project, projectId: f.projectId }, message => message);
  t.after(() => bridge.dispose());
  assert.equal((await f.dispatch()).kind, 'reject');
  assert.equal(bridge.status().lastCode, 'RECOVERY_UNAVAILABLE');
});

test('downstream empty batches stay empty even when starting a new request series', async t => {
  const f = fixture(t);
  for (const changes of [{}, { messages: [] }]) {
    const result = await f.dispatch(changes, async () => ({ kind: 'enter', messages: [], startsRequestSeries: true }));
    assert.equal(result.messages.length, 0);
  }
});

test('only a replacement covering the committed recovery invalidates its deduplication', async t => {
  const f = fixture(t);
  const first = await f.dispatch();
  const emit = event => f.listeners.get('session/event')(f.agent.session, event);
  emit({ type: 'user/message', seq: 2, surfaceOp: 'append', data: first.messages[1] });
  assert.equal((await f.dispatch()).messages.length, 1);
  emit({ type: 'system/message', seq: 3, surfaceOp: { op: 'replace', startSeq: 0, endSeq: 0 }, data: {} });
  assert.equal((await f.dispatch()).messages.length, 1, 'A system-only update did not remove our memory');
  emit({ type: 'user/message', seq: 4, surfaceOp: { op: 'replace', startSeq: 1, endSeq: 2 }, data: { id: 'summary' } });
  assert.equal((await f.dispatch()).messages.length, 2, 'A summary that removed the memory requires restoration');
});

test('transport success with the wrong delivery target is refused', async t => {
  const f = fixture(t);
  f.bridge.dispose();
  const transport = join(f.project, 'wrong-target.py');
  writeFileSync(transport, `import json, sys
args = sys.argv
get = lambda k: args[args.index(k) + 1]
target = dict(project_root=get('--project'), project_id=get('--project-id'), session_id=get('--session-id'), generation=get('--generation'))
if args[-1] == 'prepare':
    data = dict(delivery_state='prepared', receipt=dict(target=target))
else:
    target['session_id'] = 'someone-else'
    data = dict(delivery_state='ready', target=target, context=dict(instruction_authority='none', project_id=get('--project-id'), text='Wrong session'))
print(json.dumps(dict(ok=True, code='OK', data=data)))
`);
  const bridge = attachDshRecovery({ on(event, fn) { f.listeners.set(event, fn); return () => f.listeners.delete(event); } },
    { python, recovery: transport, project: f.project, projectId: f.projectId }, message => message);
  t.after(() => bridge.dispose());
  assert.equal((await f.dispatch()).kind, 'reject');
  assert.equal(bridge.status().lastCode, 'TARGET_MISMATCH');
});

test('cancellation waits for an unresponsive subprocess to exit', { skip: process.platform === 'win32' }, async t => {
  const f = fixture(t);
  f.bridge.dispose();
  const transport = join(f.project, 'ignores-term.py');
  writeFileSync(transport, `import os, signal, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
with open('synthetic-child.pid', 'w') as output: output.write(str(os.getpid()))
time.sleep(20)
`);
  const bridge = attachDshRecovery({ on(event, fn) { f.listeners.set(event, fn); return () => f.listeners.delete(event); } },
    { python, recovery: transport, project: f.project, projectId: f.projectId }, message => message);
  t.after(() => bridge.dispose());
  const pending = f.dispatch();
  const marker = join(f.project, 'synthetic-child.pid');
  const deadline = Date.now() + 2000;
  while (!existsSync(marker) && Date.now() < deadline) await new Promise(r => setTimeout(r, 10));
  assert.ok(existsSync(marker), 'Synthetic child must actually be running');
  const pid = Number(readFileSync(marker, 'utf8'));
  t.after(() => { try { process.kill(pid, 'SIGKILL'); } catch (error) { if (error.code !== 'ESRCH') throw error; } });
  bridge.pause();
  assert.equal(typeof bridge.drain, 'function', 'A supervisor must await actual reader exit, not only signal cancellation');
  await bridge.drain();
  assert.throws(() => process.kill(pid, 0), { code: 'ESRCH' }, 'Drain cannot complete with the reader alive');
  assert.equal((await pending).kind, 'reject');
  assert.throws(() => process.kill(pid, 0), { code: 'ESRCH' }, 'Rejected recovery must not leave the reader alive');
});
