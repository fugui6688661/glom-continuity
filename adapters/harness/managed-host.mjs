// Trusted local lifecycle control. No model/tool/RPC registration or network listener.
import net from 'node:net';
import { chmodSync, fstatSync } from 'node:fs';
export const name = 'recaloom-managed-host';
export const inject = ['appReady', 'appExit', 'webServer', 'settings', 'clientModules'];

export async function apply(ctx, config) {
  const runId = process.env.RECALOOM_MANAGED_RUN_ID;
  const lockFd = Number(process.env.RECALOOM_MANAGED_LOCK_FD);
  if (!runId || !Number.isInteger(lockFd) || !fstatSync(lockFd).isFile())
    throw new Error('Managed host requires its owning launcher');
  let ready = false;
  let lifecycle;
  let stopping;
  const sockets = new Set();
  ctx.appReady.onReady(() => {
    lifecycle = ctx.get('recaloomLifecycle');
    if (Boolean(lifecycle) !== config.attached) { ctx.appExit(1); return; }
    ready = true;
  });
  const reply = (socket, value, done) => socket.end(JSON.stringify({
    home_id: config.homeId, run_id: runId, ...value,
  }) + '\n', done);
  const server = net.createServer(socket => {
    sockets.add(socket);
    socket.on('error', () => {});
    socket.once('close', () => sockets.delete(socket));
    socket.setTimeout(20000, () => socket.destroy());
    let buffer = '';
    let accepted = false;
    socket.on('data', data => {
      if (accepted) return;
      buffer += data.toString('utf8');
      if (Buffer.byteLength(buffer) > 1024) { socket.destroy(); return; }
      if (!buffer.includes('\n')) return;
      accepted = true;
      let request;
      try { request = JSON.parse(buffer.trim()); } catch { socket.destroy(); return; }
      if (!request || request.home_id !== config.homeId || request.run_id !== runId ||
          !['status', 'stop'].includes(request.action)) {
        reply(socket, { ok: false, code: 'INVALID_CONTROL_REQUEST' }); return;
      }
      if (request.action === 'status') {
        reply(socket, { ok: true, state: ready ? (stopping ? 'stopping' : 'running') : 'starting',
          port: ctx.webServer.port, pid: process.pid, memory_enabled: ctx.settings.get('recaloom-recovery')?.enabled ?? false,
          recovery_attached: Boolean(lifecycle),
          workspace_picker: ctx.get('directoryPicker')?.capability().kind ?? null,
          client_notice_attached: ctx.clientModules.graph().entries.some(row => row.id === 'recaloom-harness-notice'),
          lifecycle: lifecycle?.status().state ?? 'detached' });
        return;
      }
      if (!ready) { reply(socket, { ok: false, code: 'HOST_NOT_READY' }); return; }
      if (!stopping) {
        const attempt = Promise.resolve().then(async () => {
          if (lifecycle) {
            await lifecycle.prepareRemoval();
            if (!lifecycle.status().readyForRemoval) throw new Error('Removal readiness changed');
          }
        });
        stopping = attempt;
        // Invalidate failed receipts, not a newer retry created by another caller.
        void attempt.catch(() => { if (stopping === attempt) stopping = undefined; });
      }
      const attempt = stopping;
      void attempt.then(() => {
        // A successful cached receipt can also become stale before the host
        // actually exits. Every acknowledgement must check current readiness.
        if (lifecycle && !lifecycle.status().readyForRemoval) throw new Error('Removal readiness changed');
        // The response acknowledges quiescence, not process exit. The CLI also
        // waits for the inherited ownership lock to be released by all holders.
        reply(socket, { ok: true, state: 'stopping', recovery_attached: Boolean(lifecycle),
          persisted_pause: Boolean(lifecycle) }, error => {
            if (stopping !== attempt) return;
            // Transport completion is asynchronous: settings can invalidate the
            // acknowledged receipt before the actual exit request is made.
            try {
              if (error || (lifecycle && !lifecycle.status().readyForRemoval))
                throw new Error('Removal readiness changed');
            } catch {
              stopping = undefined;
              return;
            }
            ctx.appExit(0);
          });
      }).catch(() => {
        if (stopping === attempt) stopping = undefined;
        reply(socket, { ok: false, code: 'PAUSE_NOT_SAVED' });
      });
    });
  });
  await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(config.socket, () => { chmodSync(config.socket, 0o600); resolve(); });
  });
  return () => {
    ready = false;
    for (const socket of sockets) socket.destroy();
    return new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  };
}
